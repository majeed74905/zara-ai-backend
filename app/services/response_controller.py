"""
Response Controller — Zara AI post-processor.
──────────────────────────────────────────────────────────────────────────────
Conservative post-processing pipeline:

  1. AI-tell removal (deterministic strip of robotic filler phrases).
  2. Language validation — a local, deterministic check (no LLM call). Only when the
     reply clearly drifted from a confidently detected user language (e.g. English
     reply to a Tanglish user) do we spend ONE correction call.
  3. The correction protects code blocks, inline code and URLs with placeholders so
     technical content can never be translated or altered.

Design principles:
  - The system prompt is the personality; don't rewrite answers aggressively.
  - Don't truncate or shorten responses.
  - Never pay for an extra LLM call when the local check passes.
"""

import logging
import re
from typing import Optional, Tuple, Dict, Any
from app.services.language_detector import is_language_consistent, LanguageProfile, TRANSLITERATED_BASE
from app.services.communication_engine import ResponseStrategy, apply_safety_checks
from app.services.models.groq_service import GroqService

logger = logging.getLogger(__name__)

# Lightweight rewriter (only used on confirmed language drift)
_rewriter = GroqService()

# Modules whose output is free-form conversation (structured/JSON modules are never rewritten)
_CONVERSATIONAL_MODULES = {"chat", "tutor"}

# Minimum confidence in the user's language before we'd consider correcting a reply
_MIN_CORRECTION_CONFIDENCE = 0.6

_AI_TELL_PATTERNS = [
    r"(?s)<think>.*?</think>\s*",
    r"(?si)^Thinking Process:.*?\n\n",
    r"(?s)^We need (?:to )?answer.*?(?=\n\n|\n```|[A-Z][a-z]+:)",
    r"^As an AI(?: language model| assistant)?,?\s*",
    r"^As a large language model,?\s*",
    r"(?i)^(?:Sure|Of course)[,!.]?\s+I'd be (?:happy|glad) to help(?: you)?(?: with (?:that|this))?[.!]?\s*",
    r"(?i)^I'd be (?:happy|glad) to help(?: you)?(?: with (?:that|this))?[.!]?\s*",
    r"(?i)^Great question[.!]?\s*",
    r"(?i)^That's a great question[.!]?\s*",
    r"(?i)^Thank you for (?:your|the) question[.!]?\s*",
    r"(?i)^Absolutely[.!]?\s+",
    r"(?i)^Certainly[.!]?\s+",
    r"(?i)\s*I hope this helps[.!]?\s*$",
    r"(?i)\s*Let me know if you have any (?:other |more |further )?questions[.!]?\s*$",
    r"(?i)\s*Feel free to ask if you (?:need|have) (?:anything|any|more)[^.!?\n]*[.!]?\s*$",
    r"(?i)\s*How (?:can|may) I (?:help|assist) you(?: today)?\??\s*$",
]

_AI_TELL_COMPILED = [re.compile(p) for p in _AI_TELL_PATTERNS]

# Technical spans that must survive a rewrite untouched
_PROTECT_RE = re.compile(r"```[\s\S]*?```|`[^`\n]+`|https?://\S+")


def control_response(
    response: str,
    mode: str,
    target_lang: str,
    language_profile: Optional[LanguageProfile] = None,
    module: str = "chat",
    strategy: Optional[ResponseStrategy] = None,
) -> Tuple[str, Dict[str, Any]]:
    """Post-process a reply. Returns (text, metadata)."""
    meta: Dict[str, Any] = {"language_checked": False, "language_rewrite": False, "safety_fixes": []}

    text = _strip_ai_tells(response)

    if module not in _CONVERSATIONAL_MODULES:
        return text, meta

    confidence = language_profile.confidence if language_profile else 0.8
    uncertain = language_profile.uncertain if language_profile else False
    if not uncertain and confidence >= _MIN_CORRECTION_CONFIDENCE:
        meta["language_checked"] = True
        if not is_language_consistent(text, target_lang):
            logger.warning(f"Language drift detected (target={target_lang}, mode={mode}). Correcting once.")
            corrected = force_language_rewrite(text, target_lang)
            if corrected != text and is_language_consistent(corrected, target_lang):
                meta["language_rewrite"] = True
                text = _strip_ai_tells(corrected)
            else:
                logger.warning("Language correction did not produce a consistent reply; keeping original.")

    # Deterministic guardrails: no dependency-building language; crisis resources always present
    text, fixes = apply_safety_checks(text, strategy, target_lang)
    meta["safety_fixes"] = fixes
    return text, meta


def response_controller(
    response: str,
    mode: str,
    target_lang: str,
    is_pro_special: bool = False,
    language_profile: Optional[LanguageProfile] = None,
    module: str = "chat",
) -> str:
    """Backward-compatible wrapper returning only the processed text."""
    text, _ = control_response(response, mode, target_lang, language_profile, module)
    return text


def _protect(text: str) -> Tuple[str, list]:
    spans: list = []

    def repl(m: "re.Match[str]") -> str:
        spans.append(m.group(0))
        return f"⟦{len(spans) - 1}⟧"

    return _PROTECT_RE.sub(repl, text), spans


def _restore(text: str, spans: list) -> Optional[str]:
    for i, span in enumerate(spans):
        token = f"⟦{i}⟧"
        if token not in text:
            return None  # rewriter dropped a protected span → unsafe, reject
        text = text.replace(token, span, 1)
    return text


def _language_instruction(lang: str) -> str:
    if lang in TRANSLITERATED_BASE:
        return (
            f"{lang}: {TRANSLITERATED_BASE[lang]} written in English (Latin) letters, naturally mixed with English "
            f"technical words, exactly how people text in {lang}. Not pure English, not native script."
        )
    return f"{lang}, natural and conversational, keeping English technical terms where they appear."


def force_language_rewrite(text: str, lang: str) -> str:
    """
    Rewrite `text` into `lang` with a single small model call. Code blocks, inline code
    and URLs are replaced by placeholders first and restored afterwards.
    Returns the original text if the rewrite fails or damages protected content.
    """
    protected, spans = _protect(text)
    rewrite_prompt = (
        f"Rewrite the reply below into {_language_instruction(lang)}\n"
        "Rules: keep the exact meaning, tone, markdown formatting and emojis. "
        "Keep every placeholder like ⟦0⟧ exactly as-is. Output ONLY the rewritten reply.\n\n"
        f"Reply:\n{protected}"
    )
    system = "You are a precise multilingual rewriting engine. Output only the rewritten text."

    candidates = []
    if _rewriter.health_check():
        candidates.append(("groq", _rewriter))
    try:
        from app.services.models.openrouter_service import OpenRouterService
        or_rewriter = OpenRouterService()
        if or_rewriter.health_check():
            candidates.append(("openrouter", or_rewriter))
    except Exception as e:
        logger.debug(f"OpenRouter rewriter unavailable: {e}")

    for name, service in candidates:
        try:
            rewritten = service.generate(
                system_prompt=system,
                user_prompt=rewrite_prompt,
                temperature=0.3,
                max_tokens=max(600, len(text.split()) * 4),
                reasoning_effort="low",
            )
            restored = _restore(rewritten.strip(), spans)
            if restored:
                return restored
            logger.warning(f"{name} rewrite dropped protected content; discarding.")
        except Exception as e:
            logger.warning(f"{name} language rewrite failed: {e}")

    return text


def _strip_ai_tells(text: str) -> str:
    """
    Remove robotic filler phrases. Iterates to catch stacked tells
    ("Certainly! As an AI..."). Never returns an empty string.
    """
    original = text
    for _ in range(3):
        prev = text
        for pattern in _AI_TELL_COMPILED:
            text = pattern.sub("", text)
        text = text.strip()
        if text == prev:
            break
    return text if text else original.strip()
