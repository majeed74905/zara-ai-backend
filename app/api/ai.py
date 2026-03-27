"""
AI API Routes — Zara AI (Phase 1 / 2 / 3)
──────────────────────────────────────────────────────────────────────────────
Implements the full production-grade chat pipeline:

  1. Language Detection      → language_detector.detect_language()
  2. Prompt Engineering      → prompt_builder.build_system_prompt() / build_user_prompt()
  3. Response Cache          → response_cache.get_cached() / set_cached()
  4. Mode-Based LLM Routing  → llm_router.route_request()
  5. Conversation Memory     → DB (authenticated) or in-memory (anonymous)
  6. Interaction Metadata    → Returned alongside the response

Mode mapping (from frontend 'model' field):
  "zara-fast" → mode="fast"  (Groq, temperature=0.5, concise)
  "zara-pro"  → mode="pro"   (Gemini, temperature=0.7, structured)
  "zara-eco"  → mode="eco"   (OpenRouter, temperature=0.6, thoughtful)
  "auto"      → mode="pro"   (default to Pro)
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from app.api import deps
from app.core.config import settings
from app.models import User, PromptHistory
from app.services import chat_memory
from app.services.llm_router import llm_router, get_cost_summary
from app.services.language_detector import detect_language
from app.services.prompt_builder import build_system_prompt, build_user_prompt
from app.services import response_cache
from app.services.response_controller import response_controller
from pydantic import BaseModel
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


# ── Request / Response Models ─────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    model: str = "zara-pro"          # zara-fast | zara-pro | zara-eco | auto
    module: Optional[str] = "chat"   # chat | tutor | exam_prep | code_architect | github
    task: Optional[str] = "chat"     # Legacy field — retained for backward compat
    interaction_mode: Optional[str] = "chat"  # chat | care
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    model_used: str
    detected_language: str
    interaction_modules: Optional[Dict[str, Any]] = None
    # Elite Features
    is_dual: bool = False
    quick_answer: Optional[str] = None
    deep_explanation: Optional[str] = None


# ── Mode Resolver ─────────────────────────────────────────────────────────────

def resolve_mode(model: str, module: str) -> str:
    """
    Convert legacy 'model' field → canonical mode string.
    Module overrides take precedence for non-chat modules.
    """
    if module in ("tutor", "exam_prep"):
        return "pro"  # These need deep, structured responses
    if module in ("code_architect", "github"):
        return "fast"  # Code tasks need direct, confident answers

    mode_map = {
        "zara-fast": "fast",
        "zara-pro": "pro",
        "zara-eco": "eco",
        "auto": "pro",
    }
    return mode_map.get(model, "pro")


# ── Chat Endpoint ─────────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(
    request: ChatRequest,
    db: Session = Depends(deps.get_db),
    current_user: Optional[User] = Depends(deps.get_current_user_optional),
):
    module = request.module or "chat"
    task = request.task or "chat"
    it_mode = request.interaction_mode or "chat"

    # 1. Resolve mode (Fast / Pro / Eco)
    mode = resolve_mode(request.model, module)
    logger.info(f"Chat request: model={request.model} → mode={mode}, module={module}, task={task}")

    # 2. Detect language
    detected_language = detect_language(request.message)
    logger.info(f"Language detected: {detected_language}")

    # 3. IST timestamp
    utc_now = datetime.now(timezone.utc)
    ist_time = utc_now + timedelta(hours=5, minutes=30)
    current_time_str = ist_time.strftime("%d %B %Y, %I:%M:%S %p IST")

    # 4. Load conversation history
    history_messages: List[Dict[str, str]] = []
    use_memory_store = True

    if current_user and not current_user.is_privacy_mode:
        use_memory_store = False

    if use_memory_store:
        if request.session_id:
            history_messages = chat_memory.get_anon_history(request.session_id)
    else:
        db_history = (
            db.query(PromptHistory)
            .filter(PromptHistory.user_id == current_user.id)
            .order_by(PromptHistory.timestamp.desc())
            .limit(6)  # Last 3 exchanges = 6 messages
            .all()
        )
        for item in reversed(db_history):
            history_messages.append({"role": "user", "content": item.prompt})
            if item.response:
                history_messages.append({"role": "assistant", "content": item.response})

    # 5. Check cache (skip cache for care mode — emotional context must be fresh)
    response_text = None
    if it_mode != "care":
        response_text = response_cache.get_cached(
            mode=mode,
            language=detected_language,
            message=request.message,
            module=module,
        )
        if response_text:
            logger.info("Serving response from cache.")

    # 6. Build prompts (cache miss → call LLM)
    if not response_text:
        system_prompt = build_system_prompt(
            mode=mode,
            language=detected_language,
            module=module,
            interaction_mode=it_mode,
            current_time=current_time_str,
        )
        user_prompt = build_user_prompt(
            user_input=request.message,
            language=detected_language,
            history=history_messages,
        )
        context = {"history": history_messages}

        try:
            # Multi-model intelligent routing
            raw_response = llm_router.route_request(
                mode=mode,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                context=context,
                module=module,
                task=task,
            )
            
            # --- PHASE 3 UPGRADE: ELITE BEHAVIORAL SHAPING ---
            response_text = response_controller(
                response=raw_response,
                mode=mode,
                target_lang=detected_language
            )
            
        except Exception as e:
            logger.error(f"LLM routing/control failed: {e}")
            raise HTTPException(
                status_code=500,
                detail="AI service is currently unavailable. Please try again in a moment.",
            )

        # Cache successful responses (not care mode)
        if it_mode != "care":
            response_cache.set_cached(
                mode=mode,
                language=detected_language,
                message=request.message,
                module=module,
                response=response_text,
            )

    # 7. DUAL RESPONSE LOGIC (Elite Feature for Pro Mode)
    is_dual = False
    quick_answer = None
    deep_explanation = None
    
    if mode == "pro" and len(response_text) > 400:
        is_dual = True
        parts = response_text.split("\n\n")
        if len(parts) > 1:
            # Strictly split: first block is summary, rest is deep dive
            quick_answer = f"🔹 **Executive Summary**:\n{parts[0]}"
            deep_explanation = f"🔹 **Detailed Analysis**:\n" + "\n\n".join(parts[1:])
        else:
            # Hard cutoff if no paragraph breaks found
            quick_answer = f"🔹 **Executive Summary**:\n{response_text[:200]}..."
            deep_explanation = f"🔹 **Detailed Analysis**:\n{response_text}"

    # 8. Persist conversation history
    if not use_memory_store and current_user:
        try:
            db.add(PromptHistory(
                user_id=current_user.id,
                prompt=request.message,
                response=response_text,
            ))
            db.commit()
        except Exception as e:
            logger.error(f"Failed to save history to DB: {e}")
    elif use_memory_store and request.session_id:
        chat_memory.save_anon_history(request.session_id, request.message, response_text)

    # 9. Build interaction metadata
    tts_safe = response_text.replace("*", "").replace("#", "").replace("_", "")
    interaction_modules = {
        "branchable": True,
        "branch_payload": {
            "user_message": request.message,
            "assistant_message": response_text,
            "context_summary": response_text[:200] + ("..." if len(response_text) > 200 else ""),
        },
        "tts": {
            "enabled": True,
            "language": "auto",
            "voice_style": "natural",
            "tts_safe_text": tts_safe,
        },
        "copyable": True,
        "copy_text": response_text,
        "feedback": {"like_enabled": True, "dislike_enabled": True},
        "regenerate": {
            "enabled": True,
            "instruction": "Regenerate with improved clarity, depth, and structure",
        },
        "share": {
            "enabled": True,
            "share_text": response_text[:120] + "...",
            "full_text": response_text,
        },
        "more_options": {
            "save": True,
            "pin": True,
            "export": ["pdf", "txt", "md"],
            "report": True,
        },
        "meta": {
            "mode": mode,
            "detected_language": detected_language,
            "is_dual": is_dual,
        },
    }

    return ChatResponse(
        response=response_text,
        model_used=f"zara-{mode}",
        detected_language=detected_language,
        interaction_modules=interaction_modules,
        is_dual=is_dual,
        quick_answer=quick_answer,
        deep_explanation=deep_explanation
    )


# ── Session Management ────────────────────────────────────────────────────────

@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """Clear anonymous session memory."""
    chat_memory.clear_session(session_id)
    return {"msg": "Session memory cleared."}


# ── Analytics & Admin Endpoints ───────────────────────────────────────────────

@router.get("/analytics/costs")
async def get_cost_analytics(
    current_user: Optional[User] = Depends(deps.get_current_user_optional),
):
    """Return session-level cost tracking summary (Phase 3 analytics)."""
    return get_cost_summary()


@router.get("/analytics/cache")
async def get_cache_stats(
    current_user: Optional[User] = Depends(deps.get_current_user_optional),
):
    """Return cache statistics."""
    return response_cache.cache_stats()


@router.post("/analytics/cache/clear")
async def clear_response_cache(
    current_user: Optional[User] = Depends(deps.get_current_user_optional),
):
    """Clear response cache (admin operation)."""
    response_cache.clear_cache()
    return {"msg": "Response cache cleared."}
