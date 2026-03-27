"""
Response Controller — Zara AI elite post-processor.
──────────────────────────────────────────────────────────────────────────────
This module implements the "Response Controller Layer" to:
  1. Enforce language consistency (rewrite if drift detected).
  2. Shape output based on mode (Trim Fast, Structure Pro, Relax Eco).
  3. Validate content quality and safety normalization.
"""

import logging
import re
from typing import Optional
from app.services.language_detector import is_language_consistent
from app.services.models.groq_service import GroqService

logger = logging.getLogger(__name__)

# Lightweight rewriter using Groq (cheaper/faster for corrections)
_rewriter = GroqService()

def response_controller(
    response: str, 
    mode: str, 
    target_lang: str, 
    is_pro_special: bool = False
) -> str:
    """
    Orchestrates the post-processing pipeline for elite behavioral consistency.
    """
    logger.info(f"🎮 Controlling response: mode={mode}, lang={target_lang}")
    
    # 1. HARD LANGUAGE LOCK
    if not is_language_consistent(response, target_lang):
        logger.warning(f"🌐 Language drift detected for {target_lang}. Triggering rewrite...")
        response = force_language_rewrite(response, target_lang)
    
    # 2. BEHAVIORAL SHAPING
    if mode == "fast":
        response = _shaping_fast(response)
    elif mode == "pro":
        response = _shaping_pro(response)
    elif mode == "eco":
        response = _shaping_eco(response)
        
    return response

def force_language_rewrite(text: str, lang: str) -> str:
    """
    Rewrites text strictly in the target language using a small model call.
    """
    rewrite_prompt = (
        f"Rewrite the following text EXCLUSIVELY in {lang}. "
        f"Do NOT change the meaning. Keep it natural and context-aware. "
        f"If {lang} is Tanglish or Hinglish, maintain the mixed script style perfectly.\n\n"
        f"Text to rewrite:\n{text}"
    )
    
    try:
        # Use Groq for fast, low-cost rewrites
        return _rewriter.generate(
            system_prompt="You are a linguistic correction engine. Respond ONLY with the rewritten text.",
            user_prompt=rewrite_prompt,
            temperature=0.3
        )
    except Exception as e:
        logger.error(f"Rewrite failed: {e}")
        return text # Return original if rewrite fails

def _shaping_fast(text: str) -> str:
    """Zara Fast: Aggressive compression to ensure speed-feel."""
    lines = text.strip().split("\n")
    if len(lines) > 6:
        logger.info("⚡ Trimming Fast response for brevity.")
        return "\n".join(lines[:5]) + "\n\n(Read more in Pro mode for full details...)"
    return text

def _shaping_pro(text: str) -> str:
    """Zara Pro: Ensure structural premium feel with headers and bullets."""
    # Ensure it starts with a professional header if missing
    if not text.startswith("#") and not text.startswith("🔹"):
        return f"### Analysis\n{text}"
    return text

def _shaping_eco(text: str) -> str:
    """Zara Eco: Humanization layer to soften the robotic tone."""
    # Formal-to-Conversational replacements
    replacements = {
        r"\bTherefore\b": "So",
        r"\bAdditionally\b": "Also",
        r"\bConsequently\b": "As a result",
        r"\bFurthermore\b": "Plus",
        r"\bIn conclusion\b": "To wrap up",
        r"\bI apologize\b": "I'm sorry",
        r"\butilize\b": "use",
        r"\b(assistance|assist)\b": "help",
    }
    
    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
    return text
