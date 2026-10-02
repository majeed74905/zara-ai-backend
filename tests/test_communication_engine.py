"""Communication engine: intent, emotion, depth, warmth, variation, safety — all deterministic."""

import pytest

from app.services.communication_engine import (
    analyze_turn,
    apply_safety_checks,
    build_strategy_block,
    check_reply_quality,
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


def test_normal_reply_untouched_placeholder():
    pass


# ── Zara Care: what the person needs right now ───────────────────────────────

@pytest.mark.parametrize("msg,need", [
    ("summa pesanum, advice venda", "listen_only"),
    ("i just want to talk, no advice", "listen_only"),
    ("enaku advice venum", "advice"),
    ("enna panna nu therila, enna pannalam?", "advice"),
    ("naan useless ah irukena?", "reassurance"),
    ("ennaala mudiyala da", "reassurance"),
    ("today my friend treated me so badly, naan avlo help panniruken but he didn't even care at all", "venting"),
    ("today romba bad ah pochu", "comfort"),
    ("something happened but solla mudila", "unclear"),
    ("I don't know what I'm feeling", "unclear"),
    ("happy ah iruken but somehow sad ah kooda irukku", "mixed"),
])
def test_care_need_detection(msg, need):
    assert _turn(msg, care=True).care_need == need


def test_care_need_only_in_care_mode():
    assert _turn("today romba bad ah pochu", care=False).care_need is None


def test_listen_only_persists_in_the_conversation():
    h = [{"role": "user", "content": "advice venda da, summa pesanum"},
         {"role": "assistant", "content": "Seri nanba, sollu."}]
    assert _turn("en friend enna ignore panran", h, care=True).care_need == "listen_only"
    # until they ask for advice
    assert _turn("ippo enna panna?", h, care=True).care_need == "advice"


@pytest.mark.parametrize("msg,situation", [
    ("interview reject pannitaanga", "rejection"),
    ("naan fail aayiten", "failure"),
    ("en friend enna betray pannitaan", "friendship"),
    ("pesurathukku yaarume illa", "loneliness"),
    ("exam nala romba tension", "academic"),
    ("naan romba thappu panniten", "guilt"),
    ("enna pathi enakke kevalama irukku", "shame"),
])
def test_situation_detection(msg, situation):
    assert _turn(msg, care=True).situation == situation


def test_emotional_turns_get_short_acknowledging_replies():
    assert _turn("today romba bad ah pochu", care=True).depth == "short"
    block = build_strategy_block(_turn("bro today romba bad ah pochu", care=True))
    assert "Comfort first" in block and "Advice only if they ask" in block


def test_listen_only_blocks_advice_in_prompt_and_validator():
    s = _turn("summa pesanum, advice venda", care=True)
    assert "No tips, no steps" in build_strategy_block(s)
    tips = "Here are 5 ways to feel better:\n1. Sleep well\n2. Exercise\n3. Journal\n4. Talk\n5. Breathe"
    assert "needed to be heard" in (check_reply_quality(tips, s) or "")


def test_care_validator_rejects_fake_experience_and_diagnosis():
    s = _turn("naan fail aayiten", care=True)
    assert "human experience" in (check_reply_quality("I went through the same thing da, it hurts.", s) or "")
    assert "label their mental state" in (check_reply_quality("You are clearly depressed about this failure.", s) or "")


def test_care_validator_accepts_short_warm_acknowledgement():
    s = _turn("today romba bad ah pochu", care=True)
    assert check_reply_quality("Aiyo nanba… enna aachu? Sollu, naan kekkuren.", s) is None


# ── Tanglish conversation & Zara Care ────────────────────────────────────────

@pytest.mark.parametrize("msg", [
    "naan fail aayiten", "code anuppuren", "aprom", "paravala", "bro naan project la stuck aayiten",
    "nalla irukiya", "purinjiduchu", "pesalama", "miss panniten", "interview mudinjiduchu",
])
def test_tanglish_phrases_are_not_english(msg):
    from app.services.language_detector import detect_language
    assert detect_language(msg) == "Tanglish"


@pytest.mark.parametrize("msg,intent", [
    ("pesalama", "wants_to_talk"),
    ("konjam pesu", "wants_to_talk"),
    ("let's talk", "wants_to_talk"),
    ("enaku oru doubt", "request_help"),
    ("bro help pannu", "request_help"),
    ("project complete aagala", "technical"),
    ("backend work aagala", "technical"),
    ("I got first prize", "celebration"),
])
def test_new_intents(msg, intent):
    s = _turn(msg)
    assert s.intent == intent and s.depth in ("short", "medium")


def test_wants_to_talk_is_companionship_not_a_task():
    block = build_strategy_block(_turn("pesalama", care=True))
    assert "just want to talk" in block and "Don't turn it into a service request" in block


def test_unstated_help_invites_details():
    block = build_strategy_block(_turn("enaku oru doubt"))
    assert "haven't said what it's about" in block and "don't guess the topic" in block


@pytest.mark.parametrize("msg,emotion", [
    ("naan fail aayiten", "sad"),
    ("I got first prize", "excited"),
    ("miss panniten", "affectionate"),
])
def test_tanglish_emotion_cues(msg, emotion):
    assert detect_emotion(msg).emotion == emotion


def test_finishing_something_is_not_automatically_good_news():
    # "mudinjiduchu" just means finished — Zara must ask, not congratulate
    assert detect_emotion("interview mudinjiduchu").emotion == "neutral"


def test_event_update_links_back_to_what_they_told_us():
    h = [{"role": "user", "content": "tomorrow interview irukku"},
         {"role": "assistant", "content": "All the best nanba!"}]
    s = _turn("interview mudinjiduchu", h, care=True)
    assert s.event_update == "tomorrow interview irukku"
    block = build_strategy_block(s)
    assert "reporting back" in block and "don't assume it went well" in block
    assert _turn("interview mudinjiduchu", []).event_update is None


def test_care_prompt_keeps_tanglish_and_mirrors_address_term():
    from app.services.prompt_builder import build_system_prompt
    from app.services.language_detector import detect_language_profile
    from app.services.zara_identity import detect_communication_profile
    msg = "nanba today romba bad ah pochu"
    lang = detect_language_profile(msg)
    s = _turn(msg, care=True)
    prompt = build_system_prompt("fast", lang.language, interaction_mode="care",
                                 comm_style=detect_communication_profile(msg), language_profile=lang, strategy=s)
    assert "NATURAL TAMIL / TANGLISH WARMTH" in prompt
    assert "formal literary Tamil" in prompt
    assert s.address_term == "nanba" and "\"nanba\"" in prompt


# ── Naturalness validator ────────────────────────────────────────────────────

def test_validator_rejects_emoji_overload():
    assert "too many emojis" in (check_reply_quality("Heyy nanba 😄❤️🔥🥺😂", _turn("hi")) or "")


def test_validator_rejects_repeated_opener():
    s = _turn("hello", [{"role": "assistant", "content": "Hey nanba! Enna panra?"}])
    msg = check_reply_quality("Hey nanba! Eppadi irukka?", s, "Hey nanba! Enna panra?")
    assert msg and "opened exactly like your previous reply" in msg


def test_validator_accepts_a_good_varied_reply():
    s = _turn("hello", [{"role": "assistant", "content": "Hey nanba! Enna panra?"}])
    assert check_reply_quality("Heyy! Sollu, enna matter? 😄", s, "Hey nanba! Enna panra?") is None


def test_normal_reply_untouched():
    s = _turn("hi")
    text, fixes = apply_safety_checks("Hey! 😄", s, "English")
    assert text == "Hey! 😄" and fixes == []
