"""
AI API Routes — Zara AI
──────────────────────────────────────────────────────────────────────────────
Chat pipeline (Chat and Zara Care):

  1. Conversation history   → client-supplied per-conversation turns (preferred),
                               anonymous session memory, or DB history (legacy clients)
  2. Language intelligence  → language_detector.detect_language_profile()   (local)
  3. User style             → zara_identity.detect_communication_profile()  (local)
  4. Response strategy      → communication_engine.analyze_turn()           (local)
                               intent · emotion · depth · tone · warmth · variation
  5. Prompt                 → Zara core + mode personality (+ Care) + adaptation +
                               strategy + language lock
  6. Response cache         → only for standalone, substantive single-turn questions
  7. Mode-based routing     → llm_router (provider-independent personality)
  8. Response control       → filler removal, language validation, safety checks
  9. Persistence + metadata

No step besides generation (and a rare language correction) calls an LLM.

Mode mapping (from frontend 'model' field):
  "zara-fast" → "fast"   "zara-pro" → "pro"   "zara-eco" → "eco"   "auto" → "pro"
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.api import deps
from app.models import User, PromptHistory
from app.services import chat_memory
from app.services.llm_router import llm_router, get_cost_summary, ProviderRoutingError
from app.services.language_detector import detect_language_profile
from app.services.prompt_builder import build_system_prompt, build_user_prompt
from app.services.zara_identity import detect_communication_profile, build_voice_persona_prompt
from app.services.communication_engine import analyze_turn
from app.services import response_cache
from app.services.response_controller import control_response
from app.core.rate_limiter import rate_limit_check
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

MAX_MESSAGE_CHARS = 15000
MAX_HISTORY_TURNS = 12          # messages (≈ 6 exchanges) sent to the model
MAX_HISTORY_ITEM_CHARS = 4000   # per message, keeps context windows bounded


# ── Request / Response Models ─────────────────────────────────────────────────

class HistoryItem(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    model: str = "zara-pro"          # zara-fast | zara-pro | zara-eco | auto
    module: Optional[str] = "chat"   # chat | tutor | exam_prep | code_architect | github
    task: Optional[str] = "chat"     # Legacy field — retained for backward compat
    interaction_mode: Optional[str] = "chat"  # chat | care
    session_id: Optional[str] = Field(default=None, max_length=128)
    # Recent turns of THIS conversation (client-side source of truth). When provided,
    # it replaces server-side history lookups.
    history: Optional[List[HistoryItem]] = Field(default=None, max_length=50)
    # The user's own words when `message` also carries appended context (file analysis,
    # repository manifest...). Used for language/style/intent detection only.
    user_text: Optional[str] = Field(default=None, max_length=MAX_MESSAGE_CHARS)
    # "Think deeper" toggle in the UI: more reasoning budget, same personality
    deep_thinking: bool = False
    # User's local hour (0–23) so greetings can be time-aware; falls back to IST
    client_hour: Optional[int] = Field(default=None, ge=0, le=23)


class ChatResponse(BaseModel):
    response: str
    model_used: str
    detected_language: str
    interaction_modules: Optional[Dict[str, Any]] = None
    # Elite Features
    is_dual: bool = False
    quick_answer: Optional[str] = None
    deep_explanation: Optional[str] = None


class PersonaRequest(BaseModel):
    model: str = "zara-fast"
    interaction_mode: Optional[str] = "chat"   # chat | care
    recent_context: Optional[List[HistoryItem]] = Field(default=None, max_length=50)


# ── Helpers ───────────────────────────────────────────────────────────────────

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


def _sanitize_history(items: Optional[List[HistoryItem]]) -> List[Dict[str, str]]:
    """Normalize client-supplied turns: valid roles only, bounded size, last N turns."""
    clean: List[Dict[str, str]] = []
    for item in items or []:
        role = (item.role or "").lower()
        if role == "model":
            role = "assistant"
        if role not in ("user", "assistant"):
            continue
        content = (item.content or "").strip()
        if not content:
            continue
        clean.append({"role": role, "content": content[:MAX_HISTORY_ITEM_CHARS]})
    return clean[-MAX_HISTORY_TURNS:]


def _load_history(request: ChatRequest, db: Session, current_user: Optional[User]) -> List[Dict[str, str]]:
    if request.history is not None:
        return _sanitize_history(request.history)

    if current_user and not current_user.is_privacy_mode:
        db_history = (
            db.query(PromptHistory)
            .filter(PromptHistory.user_id == current_user.id)
            .order_by(PromptHistory.timestamp.desc())
            .limit(3)
            .all()
        )
        turns: List[Dict[str, str]] = []
        for item in reversed(db_history):
            turns.append({"role": "user", "content": item.prompt[:MAX_HISTORY_ITEM_CHARS]})
            if item.response:
                turns.append({"role": "assistant", "content": item.response[:MAX_HISTORY_ITEM_CHARS]})
        return turns

    if request.session_id:
        return chat_memory.get_anon_history(request.session_id)[-MAX_HISTORY_TURNS:]
    return []


_ROUTING_ERROR_RESPONSES = {
    "rate_limited": (429, "Zara is getting a lot of requests right now. Please try again in a few seconds."),
    "timeout": (504, "The AI service took too long to respond. Please try again."),
    "not_configured": (503, "Zara's AI service isn't configured on the server yet."),
    "unavailable": (503, "Zara's AI service is temporarily unavailable. Please try again in a moment."),
}


# ── Chat Endpoint ─────────────────────────────────────────────────────────────
# Sync endpoint on purpose: provider SDK calls block, so FastAPI runs this in its
# threadpool instead of stalling the event loop for every other request.

@router.post("/chat", response_model=ChatResponse)
def chat_with_ai(
    request: ChatRequest,
    db: Session = Depends(deps.get_db),
    current_user: Optional[User] = Depends(deps.get_current_user_optional),
    _rl=Depends(rate_limit_check(scope="chat", max_requests=30, window_seconds=60)),
):
    cleaned_message = (request.message or "").strip()
    if not cleaned_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty or whitespace only.")
    if len(request.message) > MAX_MESSAGE_CHARS:
        raise HTTPException(status_code=413, detail="Message exceeds maximum allowed length of 15,000 characters.")

    module = request.module or "chat"
    task = request.task or "chat"
    it_mode = request.interaction_mode if request.interaction_mode in ("chat", "care") else "chat"
    mode = resolve_mode(request.model, module)

    # IST timestamp
    ist_time = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    current_time_str = ist_time.strftime("%d %B %Y, %I:%M:%S %p IST")

    history_messages = _load_history(request, db, current_user)
    detection_text = (request.user_text or "").strip() or request.message

    # Local conversational intelligence (no LLM calls)
    lang_profile = detect_language_profile(detection_text, history_messages or None)
    detected_language = lang_profile.language
    comm_profile = detect_communication_profile(detection_text, history_messages or None)
    comm_style = comm_profile.get("primary_style", "casual")
    strategy = analyze_turn(
        detection_text,
        history=history_messages,
        comm_profile=comm_profile,
        mode=mode,
        module=module,
        interaction_mode=it_mode,
        client_hour=request.client_hour if request.client_hour is not None else ist_time.hour,
    )

    # Cache only standalone, substantive questions — never greetings/small talk
    # (identical cached replies make Zara feel robotic) or multi-turn/care chats.
    cacheable = (
        it_mode != "care"
        and not history_messages
        and len(detection_text.split()) >= 6
        and not strategy.emotion.is_negative
    )

    response_text = response_cache.get_cached(mode, detected_language, request.message, module) if cacheable else None
    route_meta: Dict[str, Any] = {"provider": "cache" if response_text else None, "fallback_used": False}
    control_meta: Dict[str, Any] = {}

    if not response_text:
        system_prompt = build_system_prompt(
            mode=mode,
            language=detected_language,
            module=module,
            interaction_mode=it_mode,
            current_time=current_time_str,
            comm_style=comm_profile,
            language_profile=lang_profile,
            strategy=strategy,
        )
        user_prompt = build_user_prompt(
            user_input=request.message,
            language=detected_language,
            language_profile=lang_profile,
        )
        context = {"history": history_messages}

        try:
            raw_response, route_meta = llm_router.route_request_with_meta(
                mode=mode,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                context=context,
                module=module,
                task=task,
                deep_thinking=request.deep_thinking,
                max_tokens_cap=strategy.max_tokens_cap,
                temperature_boost=strategy.temperature_boost,
            )
            response_text, control_meta = control_response(
                response=raw_response,
                mode=mode,
                target_lang=detected_language,
                language_profile=lang_profile,
                module=module,
                strategy=strategy,
            )
        except ProviderRoutingError as e:
            status, detail = _ROUTING_ERROR_RESPONSES.get(e.kind, _ROUTING_ERROR_RESPONSES["unavailable"])
            logger.error(f"LLM routing failed (kind={e.kind}): {e}")
            raise HTTPException(status_code=status, detail=detail)
        except Exception as e:
            logger.exception(f"Chat pipeline failed: {e}")
            raise HTTPException(status_code=500, detail="Something went wrong while generating a reply. Please try again.")

        if cacheable:
            response_cache.set_cached(mode, detected_language, request.message, module, response_text)

    # Observability — metadata only, never message content
    s = strategy.to_log()
    logger.info(
        "zara_chat selected_zara_model=zara-%s module=%s interaction_mode=%s detected_language=%s "
        "language_confidence=%.2f script=%s transliteration_detected=%s code_mixed=%s language_source=%s "
        "personality_profile=%s intent=%s emotion=%s emotion_confidence=%.2f intensity=%s crisis=%s depth=%s "
        "tone=%s warmth=%s provider=%s fallback_used=%s language_rewrite=%s safety_fixes=%s history_turns=%d",
        mode, module, it_mode, detected_language, lang_profile.confidence, lang_profile.script,
        lang_profile.transliterated, lang_profile.code_mixed, lang_profile.source,
        f"zara-{mode}{'-care' if it_mode == 'care' else ''}", s["intent"], s["emotion"],
        s["emotion_confidence"], s["intensity"], s["crisis"], s["depth"], s["tone"], s["warmth"],
        route_meta.get("provider"), route_meta.get("fallback_used"),
        control_meta.get("language_rewrite", False), control_meta.get("safety_fixes", []),
        len(history_messages),
    )

    # DUAL RESPONSE LOGIC (Pro mode long answers)
    is_dual = False
    quick_answer = None
    deep_explanation = None
    if mode == "pro" and len(response_text) > 400:
        is_dual = True
        parts = response_text.split("\n\n")
        if len(parts) > 1:
            quick_answer = parts[0]
            deep_explanation = "\n\n".join(parts[1:])
        else:
            quick_answer = response_text[:200] + "..."
            deep_explanation = response_text

    # Persist conversation history
    if current_user and not current_user.is_privacy_mode:
        try:
            db.add(PromptHistory(user_id=current_user.id, prompt=detection_text, response=response_text))
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to save history to DB: {e}")
    elif request.session_id:
        chat_memory.save_anon_history(request.session_id, detection_text, response_text)

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
            "personality": f"zara-{mode}",
            "interaction_mode": it_mode,
            "detected_language": detected_language,
            "language_script": lang_profile.script,
            "language_confidence": lang_profile.confidence,
            "transliterated": lang_profile.transliterated,
            "code_mixed": lang_profile.code_mixed,
            "communication_style": comm_style,
            "intent": strategy.intent,
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
        deep_explanation=deep_explanation,
    )


# ── Voice persona (Live Mode) ─────────────────────────────────────────────────

@router.post("/persona")
def get_voice_persona(
    request: PersonaRequest,
    _rl=Depends(rate_limit_check(scope="persona", max_requests=20, window_seconds=60)),
):
    """
    System instruction for client-side voice sessions (Live Mode), built from the same
    Zara identity + mode personality (+ Care) + communication rules as chat, so Live and
    Chat feel like one Zara.
    """
    mode = resolve_mode(request.model, "chat")
    context = _sanitize_history(request.recent_context)
    return {
        "zara_model": f"zara-{mode}",
        "interaction_mode": "care" if request.interaction_mode == "care" else "chat",
        "system_instruction": build_voice_persona_prompt(mode, context, care=request.interaction_mode == "care"),
    }


# ── Session Management ────────────────────────────────────────────────────────

@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """Clear anonymous session memory."""
    chat_memory.clear_session(session_id)
    return {"msg": "Session memory cleared."}


# ── Analytics & Admin Endpoints (authenticated) ───────────────────────────────

@router.get("/analytics/costs")
async def get_cost_analytics(current_user: User = Depends(deps.get_current_active_user)):
    """Return session-level cost tracking summary."""
    return get_cost_summary()


@router.get("/analytics/cache")
async def get_cache_stats(current_user: User = Depends(deps.get_current_active_user)):
    """Return cache statistics."""
    return response_cache.cache_stats()


@router.post("/analytics/cache/clear")
async def clear_response_cache(current_user: User = Depends(deps.get_current_active_user)):
    """Clear response cache."""
    response_cache.clear_cache()
    return {"msg": "Response cache cleared."}
