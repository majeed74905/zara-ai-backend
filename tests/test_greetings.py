"""Natural greetings: detection, classification, compound intents, context, time, modes, Care — no canned replies."""

import pytest

from app.services.communication_engine import analyze_turn, build_strategy_block, detect_greeting
from app.services.language_detector import detect_language


def _turn(msg, history=None, mode="fast", care=False, hour=None, profile=None):
    return analyze_turn(msg, history or [], profile or {}, mode=mode,
                        interaction_mode="care" if care else "chat", client_hour=hour)


# ── Detection across languages, typos and elongations ─────────────────────────

@pytest.mark.parametrize("msg", [
    "hi", "hello", "hey", "hey there", "heyy", "hii", "hiiiii", "heyyyy", "hlo", "helo", "yo", "sup",
    "good morning", "good afternoon", "good evening", "what's up", "how are you", "how's it going",
    "hi bro", "hi macha", "hi maah", "hey macha", "hey bro", "hi maah ❤️", "good morning maah",
    "eppadi irukka", "eppadi irukke", "epdi irukka", "epdi iruka", "eppadi rukka",
    "வணக்கம்", "எப்படி இருக்க?", "எப்படி இருக்கீங்க?", "நல்லா இருக்கீங்களா?",
    "hello bhai", "hi bhai", "kaise ho", "kya haal hai", "bhai kya haal hai", "कैसे हो?", "नमस्ते",
])
def test_greetings_detected(msg):
    s = _turn(msg)
    assert s.greeting.is_greeting, msg
    assert s.intent == "greeting", msg
    assert s.depth == "minimal"


@pytest.mark.parametrize("msg,lang", [
    ("hi", "English"), ("eppadi irukka", "Tanglish"), ("epdi iruka", "Tanglish"),
    ("எப்படி இருக்க", "Tamil"), ("bhai kaise ho", "Hinglish"), ("कैसे हो", "Hindi"),
])
def test_greeting_language(msg, lang):
    history = []
    # a single "hi" has no language signal → uncertain English (model mirrors the user)
    assert detect_language(msg, history) == lang


@pytest.mark.parametrize("msg", ["hi maah", "hi maah ❤️", "good morning maah"])
def test_tamil_address_terms_lean_tanglish(msg):
    # "maah" is a Tamil affectionate address term — Zara must not answer in English/Hinglish
    assert detect_language(msg) == "Tanglish"


def test_checkin_guidance_forbids_invented_activities():
    block = build_strategy_block(_turn("enna panra"))
    assert "Never invent human activities" in block and "coffee" in block


def test_not_everything_with_hi_is_a_greeting():
    assert not _turn("this is a high priority bug in the login API").greeting.is_greeting
    assert not _turn("which is better, hibernate or jpa?").greeting.is_greeting


@pytest.mark.parametrize("msg", ["enna panra", "enna pannitu irukka", "saptiya", "bhai kya scene", "kya kar raha hai"])
def test_checkins_are_greeting_style_small_talk(msg):
    s = _turn(msg)
    assert s.greeting.is_greeting and "checkin" in s.greeting.types
    assert s.intent == "small_talk" and s.depth in ("minimal", "short")


# ── Classification ────────────────────────────────────────────────────────────

def test_greeting_types():
    assert _turn("hi").greeting.types == ["simple"]
    assert "casual" in _turn("hi bro").greeting.types
    assert "affectionate" in _turn("hi maah ❤️").greeting.types
    assert "time_based" in _turn("good morning").greeting.types
    assert "how_are_you" in _turn("how are you?").greeting.types
    assert "playful" in _turn("heyyyy").greeting.types


# ── Greeting + another intent ─────────────────────────────────────────────────

def test_greeting_plus_technical_request():
    s = _turn("hi bro payment issue irukku")
    assert s.greeting.is_greeting and s.greeting.has_followup
    assert s.intent == "technical" and s.depth != "minimal"
    block = build_strategy_block(s)
    assert "don't reply with only a greeting" in block


def test_greeting_plus_emotional_disclosure():
    s = _turn("hi maah, today romba bad ah pochu")
    assert s.greeting.has_followup and s.intent == "emotional_share"
    assert "emotional" in s.greeting.types
    assert "Comfort before solutions" in build_strategy_block(s)


def test_greeting_plus_question():
    s = _turn("hi zara, can you explain how JWT works?")
    assert s.greeting.has_followup and s.intent in ("technical", "question")


# ── How-are-you, check-in replies, multi-turn ─────────────────────────────────

def test_how_are_you_guidance_no_disclaimer():
    block = build_strategy_block(_turn("how are you?"))
    assert "no 'as an AI'" in block and "ask them back" in block


def test_multi_turn_greeting_conversation_evolves():
    h1 = [{"role": "user", "content": "hi macha"}, {"role": "assistant", "content": "Hi macha! Nalla irukken, nee eppadi irukka?"}]
    s = _turn("naan super ah irukken", h1)
    assert s.intent == "checkin_reply" and s.depth == "minimal"
    assert "keep the conversation moving" in build_strategy_block(s)
    assert _turn("I'm good, you?", [{"role": "assistant", "content": "Hey! How are you?"}]).intent == "checkin_reply"
    assert _turn("theek hoon", [{"role": "assistant", "content": "Badhiya hoon bhai, tu bata kaisa hai?"}]).intent == "checkin_reply"


def test_second_greeting_does_not_restart_conversation():
    h = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "Hey! 😄"}]
    s = _turn("hi macha", h)
    assert s.greeting.already_greeted
    assert "don't restart" in build_strategy_block(s)
    assert "Hey!" in s.avoid_openers[0]


# ── Time awareness ────────────────────────────────────────────────────────────

def test_time_of_day_is_offered_not_forced():
    s = _turn("hi", hour=20)
    assert s.greeting.time_of_day == "evening"
    assert "don't force it" in build_strategy_block(s)
    s2 = _turn("good morning", hour=8)
    assert s2.greeting.said_time_greeting == "morning" and "Return the greeting" in build_strategy_block(s2)
    assert _turn("hi").greeting.time_of_day is None


# ── Returning / emotional context ─────────────────────────────────────────────

def test_returning_user_relevant_topic():
    h = [{"role": "user", "content": "bro tomorrow exam irukku"}, {"role": "assistant", "content": "All the best da!"}]
    s = _turn("hi macha", h)
    assert "returning" in s.greeting.types
    assert "tomorrow exam irukku" in s.greeting.topic_snippet
    assert "If it's genuinely relevant" in build_strategy_block(s)


def test_greeting_after_bad_day_checks_in_gently():
    h = [{"role": "user", "content": "today was horrible"}, {"role": "assistant", "content": "I'm sorry… want to talk?"}]
    s = _turn("hi maah", h)
    assert s.emotional_thread == "sad"
    assert "gently check in" in build_strategy_block(s)


def test_no_unrelated_topic_retrieval():
    h = [{"role": "user", "content": "what is a REST API"}, {"role": "assistant", "content": "It's…"}]
    assert _turn("hi", h).greeting.topic_snippet is None


# ── Tone, warmth, emojis, modes, Care ─────────────────────────────────────────

def test_no_forced_affection_or_slang():
    s = _turn("hello", profile={"formality": "neutral"})
    block = build_strategy_block(s)
    assert s.warmth <= 1 and "Emojis: none or one" in block and "Don't use slang" in block
    assert _turn("hi love", care=True).warmth == 4
    assert _turn("hi love", care=False).warmth == 3


def test_modes_get_different_greeting_style():
    blocks = {m: build_strategy_block(_turn("hi bro", mode=m)) for m in ("fast", "pro", "eco")}
    assert "Zara Fast greeting" in blocks["fast"]
    assert "Zara Pro greeting" in blocks["pro"] and "not formal" in blocks["pro"]
    assert "Zara Eco greeting" in blocks["eco"]


def test_care_greeting_is_warmer():
    s = _turn("good morning maah", care=True, hour=7)
    block = build_strategy_block(s)
    assert "Zara Care" in block and s.warmth >= 3


def test_social_turns_get_variation_not_templates():
    s = _turn("hi")
    assert s.temperature_boost > 0
    block = build_strategy_block(s)
    assert "never a template" in block and "How can I assist you?" in block  # listed as forbidden
    assert _turn("Explain JWT refresh tokens in detail").temperature_boost == 0


def test_detect_greeting_direct():
    g = detect_greeting("hiiiii macha 😄")
    assert g.is_greeting and not g.has_followup and "casual" in g.types
