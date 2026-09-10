"""Language intelligence: scripts, transliteration, code-switching, context, validation."""

import pytest

from app.services.language_detector import (
    analyze_text,
    detect_language,
    detect_language_profile,
    is_language_consistent,
    strip_technical_content,
)


@pytest.mark.parametrize("text", [
    "Hello there, how are you?",
    "How are you?",
    "Can you help me?",
    "Hi, could you please explain this?",
    "Explain why my API request is failing.",
    "Bro I'm working on payment integration.",
    "My friend Anna told me about Chennai",
])
def test_english(text):
    assert detect_language(text) == "English"


@pytest.mark.parametrize("text", ["எப்படி இருக்கீங்க?", "எனக்கு இது புரியவில்லை"])
def test_tamil_script(text):
    p = analyze_text(text)
    assert p.language == "Tamil" and p.script == "tamil" and p.decisive


@pytest.mark.parametrize("text", [
    "hi macha eppadi irukka",
    "seri bro enna panra",
    "payment status update aagala",
    "seri bro saptiya?",
    "epdi solve panradhu",
    "bro idha konjam explain pannu",
    "anna idhu epdi fix panradhu",
    "anna database-la record save aagala",
    "bro login page open aagala",
    "bro payment API work aagala",
])
def test_tanglish_transliteration(text):
    p = analyze_text(text)
    assert p.language == "Tanglish"
    assert p.transliterated and p.script == "latin" and p.base_language == "Tamil"


@pytest.mark.parametrize("text", ["कैसे हो?", "मुझे यह समझ नहीं आ रहा", "भाई कैसे हो?"])
def test_hindi_script(text):
    assert detect_language(text) == "Hindi"


@pytest.mark.parametrize("text", [
    "bhai kaise karna hai",
    "payment nahi aa raha",
    "bhai payment nahi aa raha database mein",
    "mujhe samajh nahi aa raha",
    "kya problem hai",
    "bhai server restart karna hai",
])
def test_hinglish_transliteration(text):
    p = analyze_text(text)
    assert p.language == "Hinglish" and p.transliterated and p.base_language == "Hindi"


@pytest.mark.parametrize("text,expected", [
    ("സുഖമാണോ?", "Malayalam"),
    ("ಹೇಗಿದ್ದೀಯ?", "Kannada"),
    ("ఎలా ఉన్నావు?", "Telugu"),
])
def test_other_indic_scripts(text, expected):
    assert detect_language(text) == expected


def test_help_me_is_not_hinglish():
    # Regression: the old regex treated "<word> me" as Hinglish
    assert detect_language("Can you tell me more about this?") == "English"
    assert detect_language("give me the code") == "English"


@pytest.mark.parametrize("text", ["bro இந்த payment API work ஆகல", "இது database-la save ஆகல"])
def test_mixed_tamil_script_with_english(text):
    p = analyze_text(text)
    assert p.language == "Tamil" and p.code_mixed


def test_tanglish_with_error_message_stays_tanglish():
    assert detect_language("bro enna idhu TypeError: cannot read property of undefined") == "Tanglish"


@pytest.mark.parametrize("text", [
    "ok", "hmm", "yes", "no", "👍", "123", "",
    "SELECT * FROM users WHERE status='paid';",
    "https://example.com/payments/callback",
    '{"status": "paid", "id": 42}',
])
def test_neutral_messages_are_not_decisive(text):
    assert analyze_text(text).decisive is False


def test_neutral_message_inherits_conversation_language():
    history = [
        {"role": "user", "content": "hi macha eppadi irukka"},
        {"role": "assistant", "content": "Hi macha 😄 Nalla irukken!"},
    ]
    for follow_up in ["ok", "hmm", "SELECT * FROM users;", "thanks bro", "👍"]:
        p = detect_language_profile(follow_up, history)
        assert p.language == "Tanglish", follow_up
        assert p.source == "context"


def test_dynamic_switch_english_to_tanglish():
    history = [{"role": "user", "content": "Hi bro how are you?"}, {"role": "assistant", "content": "Hey!"}]
    assert detect_language("seri bro saptiya?", history) == "Tanglish"


def test_dynamic_switch_tanglish_to_english():
    history = [{"role": "user", "content": "seri bro enna panra"}]
    assert detect_language("Could you explain how the webhook retry logic works in detail?", history) == "English"


def test_conversation_aware_second_message():
    history = [{"role": "user", "content": "Bro I'm working on payment integration."}]
    assert detect_language("payment success aaguthu but db la save aagala", history) == "Tanglish"


def test_explicit_switch_wins():
    history = [{"role": "user", "content": "hi macha eppadi irukka"}]
    assert detect_language("ippo explain it in English please", history) == "English"


def test_language_field_for_structured_modules():
    assert detect_language("Generate 5 MCQ questions for Physics.\nLanguage: Tamil\nDifficulty: Easy") == "Tamil"


def test_no_signal_defaults_to_uncertain_english():
    p = detect_language_profile("ok", None)
    assert p.language == "English" and p.uncertain


def test_strip_technical_content_preserves_natural_words():
    text = "idhu enna error? `npm run build` failed, see https://x.io/a and src/app/main.py"
    stripped = strip_technical_content(text)
    assert "npm run build" not in stripped and "https" not in stripped and "main.py" not in stripped
    assert "idhu" in stripped and "enna" in stripped


# ── Response validation ───────────────────────────────────────────────────────

def test_english_reply_to_tanglish_user_is_flagged():
    reply = "Sure! I'm doing well, thank you for asking. How are you doing today? Let me know what you need."
    assert is_language_consistent(reply, "Tanglish") is False


def test_tanglish_reply_is_consistent():
    reply = "Seri bro 👍 Payment success aaguthu, aana database-la status update aagala-na callback flow check pannalaam."
    assert is_language_consistent(reply, "Tanglish") is True


def test_english_reply_to_tamil_user_is_flagged():
    assert is_language_consistent("I am doing well, thank you so much for asking me today.", "Tamil") is False


def test_hindi_reply_to_tamil_user_is_flagged():
    assert is_language_consistent("मैं ठीक हूँ, आप कैसे हैं? बताइए क्या मदद चाहिए।", "Tamil") is False


def test_tamil_reply_with_code_is_consistent():
    reply = "இந்த query-ஐ இப்படி மாற்றுங்கள்:\n```sql\nSELECT * FROM users WHERE status = 'paid';\n```\nஇப்போது சரியாக வேலை செய்யும்."
    assert is_language_consistent(reply, "Tamil") is True


def test_english_target_flags_other_script():
    assert is_language_consistent("நல்லா இருக்கேன், நீங்க எப்படி இருக்கீங்க? சொல்லுங்க.", "English") is False
    assert is_language_consistent("I'm good, thanks! What are we working on today?", "English") is True
