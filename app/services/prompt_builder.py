"""
Prompt Builder for Zara AI
──────────────────────────────────────────
Thin orchestration layer that delegates to the centralized Zara Identity Engine
(zara_identity.py) for all personality and identity concerns.

Public API:
    build_system_prompt()  → assembles a complete system prompt
    build_user_prompt()    → wraps the current user input with a language reminder

Conversation history is NOT embedded in the user prompt. It is passed to providers
as real chat turns (context["history"]), so each provider sees one clean copy.
"""

from typing import Optional, List, Dict, Any, Union
import logging

from app.services.language_detector import LanguageProfile
from app.services.communication_engine import ResponseStrategy
from app.services.zara_identity import build_identity_prompt, build_language_reminder

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def build_system_prompt(
    mode: str,
    language: str,
    module: str = "chat",
    interaction_mode: str = "chat",
    current_time: str = "",
    comm_style: Union[str, Dict[str, Any]] = "casual",
    language_profile: Optional[LanguageProfile] = None,
    strategy: Optional[ResponseStrategy] = None,
) -> str:
    """
    Assembles a complete, production-grade system prompt by delegating
    to the centralized Zara Identity Engine.

    Args:
        mode: "fast" | "pro" | "eco"
        language: Human-readable language from language_detector (e.g., "Tamil", "Tanglish")
        module: "chat" | "tutor" | "exam_prep" | "code_architect" | "github"
        interaction_mode: "chat" | "care"
        current_time: Current IST time string (for clock injection)
        comm_style: User communication style from detect_communication_profile()
        language_profile: Full detection result (script, code-mixing, confidence)
        strategy: Per-turn response strategy from communication_engine.analyze_turn()
    """
    return build_identity_prompt(
        mode=mode,
        language=language,
        comm_style=comm_style,
        module=module,
        interaction_mode=interaction_mode,
        current_time=current_time,
        language_profile=language_profile,
        strategy=strategy,
    )


def build_user_prompt(
    user_input: str,
    language: str,
    history: Optional[List[Dict[str, Any]]] = None,
    language_profile: Optional[LanguageProfile] = None,
) -> str:
    """
    Prefix the raw user message with a short, final language reminder.

    `history` is accepted for backward compatibility but intentionally not embedded:
    providers receive it as structured chat turns.
    """
    reminder = build_language_reminder(language, language_profile)
    return f"{reminder}\n\n{user_input}"
