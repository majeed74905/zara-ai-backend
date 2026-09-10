"""Communication engine: intent, emotion, depth, warmth, variation, safety — all deterministic."""

import pytest

from app.services.communication_engine import (
    analyze_turn,
    apply_safety_checks,
    build_strategy_block,
    detect_emotion,
)


def _turn(msg, history=None, mode="fast", care=False, profile=None):
    return analyze_turn(msg, history or [], profile or {}, mode=mode, interaction_mode="care" if care else "chat")


# ── Intent & response length ──────────────────────────────────────────────────

@pytest.mark.parametrize("msg,intent", [
    ("hi", "greeting"),
    ("hi bro", "greeting"),
    ("hi maah", "greeting"),
    ("hi macha eppadi irukka", "greeting"),
    ("hey bro what's up", "greeting"),
    ("भाई कैसे हो?", "greeting"),
    ("எப்படி இருக்க?", "greeting"),
    ("thanks bro", "thanks"),
    ("ok", "acknowledgement"),
    ("hmm", "acknowledgement"),
    ("seri bro", "acknowledgement"),
    ("👍", "acknowledgement"),
    ("bye da", "goodbye"),
    ("miss you", "affection"),
    ("love you zara", "affection"),
    ("enna panra da", "small_talk"),
    ("bhai kya kar raha hai", "small_talk"),
    ("சாப்பிட்டீங்களா?", "small_talk"),
])
def test_conversational_intents_get_minimal_or_short_replies(msg, intent):
    s = _turn(msg)
    assert s.intent == intent
    assert s.depth in ("minimal", "short")
    assert s.max_tokens_cap is not None  # small token budget → lower latency


def test_simple_tech_question_is_short_complex_is_detailed():
    assert _turn("what is an API?").depth == "short"
    long_q = ("Explain why my payment callback is randomly failing and why only one out of "
              "several attempts gets stored in MySQL.")
    s = _turn(long_q, mode="pro")
    assert s.intent == "technical" and s.depth == "detailed" and s.max_tokens_cap is None


def test_professional_explain_request_is_detailed_not_small_talk():
    s = _turn("Please explain the architecture.")
    assert s.intent == "question" and s.depth == "detailed"


def test_tanglish_tech_problem_asks_for_details():
    s = _turn("bro API error varudhu")
    assert s.intent == "technical" and s.depth == "medium"


def test_eco_is_leaner_than_fast_and_pro():
    msg = "how does JWT authentication work between my frontend and backend"
    assert _turn(msg, mode="eco").depth == "short"
    assert _turn(msg, mode="fast").depth == "medium"
    assert _turn(msg, mode="pro").depth == "detailed"


# ── Emotion ───────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("msg,emotion", [
    ("bro romba kadupa irukku 😭", "frustrated"),
    ("today romba worst ah pochu", "sad"),
    ("maah innikku romba kashtama irundhuchu", "sad"),
    ("exam nenachu bayama irukku da", "stressed"),
    ("I am feeling quite stressed about the upcoming examination.", "stressed"),
    ("ellarum busy... naan mattum thaniya irukken", "lonely"),
    ("enaku onnum purila", "confused"),
    ("broooo work aayiduchu 🔥🔥", "excited"),
    ("bro I'm happy today 🔥", "excited"),
    ("enaku romba overwhelming ah irukku", "distressed"),
])
def test_emotions_detected_across_languages(msg, emotion):
    sig = detect_emotion(msg)
    assert sig.emotion == emotion
    assert sig.confidence >= 0.55


@pytest.mark.parametrize("msg", [
    "I don't want to live anymore",
    "saaganum pola irukku",
    "मैं मरना चाहता हूँ",
    "எனக்கு வாழ பிடிக்கல",
])
def test_crisis_detection(msg):
    sig = detect_emotion(msg)
    assert sig.crisis and sig.intensity == "high"
    s = _turn(msg)
    assert s.intent == "emotional_share" and s.depth == "medium"
    assert "Tele-MANAS 14416" in build_strategy_block(s)


def test_neutral_messages_do_not_invent_emotion():
    for msg in ["what is an API?", "Please explain the architecture.", "ok", "SELECT * FROM users;"]:
        assert detect_emotion(msg).emotion == "neutral"


def test_laughing_emoji_is_playful_not_sad():
    sig = detect_emotion("bro I accidentally deleted the file 😂😭")
    assert sig.emotion == "neutral" and sig.playful


def test_upset_user_gets_comfort_before_solutions():
    s = _turn("bro exam romba bad ah pochu 😭")
    assert s.intent == "emotional_share"
    block = build_strategy_block(s)
    assert "Comfort before solutions" in block or "Listen first" in block


def test_distress_slows_down_and_suggests_grounding():
    block = build_strategy_block(_turn("enaku romba overwhelming ah irukku"))
    assert "Slow down" in block and "grounding" in block


def test_emotional_continuity_across_turns():
    history = [
        {"role": "user", "content": "I'm worried about my interview tomorrow."},
        {"role": "assistant", "content": "That's understandable. Want to prep together?"},
    ]
    s = _turn("okay maah", history)
    assert s.emotional_thread == "stressed"
    assert "Continuity" in build_strategy_block(s)


# ── Tone, warmth, address terms ───────────────────────────────────────────────

def test_warmth_follows_the_user():
    assert _turn("Could you help me debug this API?").warmth <= 1
    assert _turn("hi bro").warmth == 2
    assert _turn("hi maah").warmth == 3
    # Romantic-style warmth only in Care, and only after the user sets that tone
    assert _turn("love you zara", care=False).warmth == 3
    assert _turn("love you zara", care=True).warmth == 4
    assert _turn("hello", care=True).warmth == 2


def test_professional_user_gets_no_slang():
    s = _turn("Could you help me debug this API?", profile={"formality": "formal"})
    assert s.tone == "professional" and s.warmth == 0
    assert "Don't use slang" in build_strategy_block(s)


def test_address_term_detected_from_user():
    assert _turn("hi macha eppadi irukka").address_term == "macha"
    assert _turn("enaku oru doubt", [{"role": "user", "content": "bro"}]).address_term == "bro"
    assert _turn("hello there").address_term is None


def test_repetition_avoidance_uses_recent_openers():
    history = [
        {"role": "user", "content": "hi bro"},
        {"role": "assistant", "content": "Seri bro 👍 sollu"},
        {"role": "user", "content": "payment work aagala"},
        {"role": "assistant", "content": "Seri bro, enna error varudhu?"},
    ]
    s = _turn("thanks bro", history)
    assert "Seri bro 👍" in s.avoid_openers
    assert "do NOT open the same way" in build_strategy_block(s)


def test_vague_problem_asks_before_assuming():
    history = [{"role": "user", "content": "bro oru problem irukku"}, {"role": "assistant", "content": "Sollu bro, enna problem?"}]
    s = _turn("payment work aagala", history)
    assert s.vague_problem
    assert "ask ONE focused clarifying question" in build_strategy_block(s)
    detailed = _turn("my payment webhook returns 200 but the order status stays pending in MySQL after the callback")
    assert not detailed.vague_problem
    assert not _turn("what is an API?").vague_problem


def test_short_follow_up_uses_context():
    history = [{"role": "user", "content": "bro oru problem irukku"}, {"role": "assistant", "content": "Sollu bro, enna problem?"}]
    assert _turn("payment work aagala", history).intent == "technical"
    assert _turn("then what", history).intent == "follow_up"


# ── Safety post-checks ────────────────────────────────────────────────────────

def test_dependency_language_is_removed():
    s = _turn("miss you", care=True)
    text, fixes = apply_safety_checks("Aww ❤️ I'm here. You only need me. Tell me about your day?", s, "English")
    assert "only need me" not in text and "I'm here" in text
    assert fixes == ["removed_dependency_language"]


def test_crisis_resources_added_in_user_language_when_missing():
    s = _turn("saaganum pola irukku")
    text, fixes = apply_safety_checks("Ayyo… naan kekkaren, enna aachu?", s, "Tanglish")
    assert "14416" in text and "added_crisis_resources" in fixes
    assert "thaniya" in text  # Tanglish footer


def test_crisis_resources_not_duplicated():
    s = _turn("I want to die")
    reply = "I'm really glad you told me. Please call Tele-MANAS 14416 or 112 right now."
    text, fixes = apply_safety_checks(reply, s, "English")
    assert text == reply and fixes == []


def test_normal_reply_untouched():
    s = _turn("hi")
    text, fixes = apply_safety_checks("Hey! 😄", s, "English")
    assert text == "Hey! 😄" and fixes == []
