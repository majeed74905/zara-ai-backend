"""Zara personality layer: distinct modes, shared core, provider independence, language lock."""

from app.services.language_detector import detect_language_profile
from app.services.prompt_builder import build_system_prompt, build_user_prompt
from app.services.zara_identity import (
    build_voice_persona_prompt,
    detect_communication_profile,
    get_generation_config,
)

MSG = "Explain why my API request is failing."


def _prompt(mode, message=MSG, history=None):
    lang = detect_language_profile(message, history)
    return build_system_prompt(
        mode=mode,
        language=lang.language,
        comm_style=detect_communication_profile(message, history),
        language_profile=lang,
    )


def test_each_mode_has_its_own_personality_block():
    fast, pro, eco = _prompt("fast"), _prompt("pro"), _prompt("eco")
    assert "MODE: ZARA FAST" in fast and "MODE: ZARA PRO" not in fast and "MODE: ZARA ECO" not in fast
    assert "MODE: ZARA PRO" in pro and "MODE: ZARA FAST" not in pro
    assert "MODE: ZARA ECO" in eco and "MODE: ZARA FAST" not in eco
    assert len({fast, pro, eco}) == 3


def test_behavioral_characteristics_differ():
    fast, pro, eco = _prompt("fast"), _prompt("pro"), _prompt("eco")
    assert "Natural Everyday Human" in fast and "follow-up question" in fast
    assert "Expert Conversational Partner" in pro and "assumptions" in pro and "caveats" in pro
    assert "Simple, Warm & Efficient" in eco and "1–3 short sentences" in eco


def test_all_modes_share_core_identity_and_values():
    for mode in ("fast", "pro", "eco"):
        p = _prompt(mode)
        assert "You are ZARA AI" in p
        assert "HONESTY & ACCURACY" in p
        assert "CRISIS SAFETY" in p
        assert "never claim to be a human" in p


def test_personality_is_independent_of_provider():
    # Generation settings belong to the Zara mode; no provider name decides personality
    fast, pro, eco = get_generation_config("fast"), get_generation_config("pro"), get_generation_config("eco")
    assert eco["max_tokens"] < fast["max_tokens"] < pro["max_tokens"]
    for mode in ("fast", "pro", "eco"):
        prompt = _prompt(mode)
        for provider in ("Groq", "Gemini", "OpenRouter"):
            assert f"MODE: {provider}" not in prompt


def test_language_lock_is_last_and_matches_user():
    history = [{"role": "user", "content": "hi macha eppadi irukka"}]
    for mode in ("fast", "pro", "eco"):
        p = _prompt(mode, "bro payment status update aagala database la", history)
        tail = p[-2500:]
        assert "LANGUAGE LOCK" in tail and "TANGLISH" in tail
        assert "Do NOT reply in plain English" in tail


def test_technical_preservation_rule_present():
    p = _prompt("fast", "இந்த error என்ன meaning?")
    assert "NEVER translate or alter technical content" in p
    assert "TAMIL SCRIPT" in p


def test_uncertain_language_tells_model_to_mirror():
    p = _prompt("eco", "ok")
    assert "could not be determined confidently" in p


def test_user_prompt_has_short_reminder_and_no_duplicated_history():
    lang = detect_language_profile("bhai payment nahi aa raha")
    up = build_user_prompt("bhai payment nahi aa raha", lang.language, history=[{"role": "user", "content": "OLD"}], language_profile=lang)
    assert up.startswith("[Reply language: Hinglish")
    assert "OLD" not in up and up.endswith("bhai payment nahi aa raha")


def test_robotic_phrases_are_banned_in_core():
    p = _prompt("fast", "hi")
    for phrase in ("How can I assist you today?", "As an AI", "Certainly!"):
        assert phrase in p  # listed under banned filler
    assert "Banned filler" in p


def test_voice_persona_uses_same_identity_and_mode():
    ctx = [{"role": "user", "content": "I'm working on a payment API"}, {"role": "assistant", "content": "Nice, which gateway?"}]
    v = build_voice_persona_prompt("pro", ctx)
    assert "MODE: ZARA PRO" in v and "You are ZARA AI" in v
    assert "SPOKEN LANGUAGE LOCK" in v
    assert "payment API" in v
