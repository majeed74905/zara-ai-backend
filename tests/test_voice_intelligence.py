"""Zara Live: fusing what was said with how it was said (deterministic, no audio, no LLM)."""

import pytest

from app.services.communication_engine import analyze_turn
from app.services.language_detector import detect_language
from app.services.voice_intelligence import (
    ProsodySignals,
    build_turn_note,
    fuse_voice_signals,
)


def _state(msg, prosody=None, care=True, mode="fast"):
    strategy = analyze_turn(msg, [], {}, mode=mode, interaction_mode="care" if care else "chat")
    return fuse_voice_signals(strategy, detect_language(msg), prosody, care_mode=care)


LOW_SLOW = ProsodySignals(energy=0.2, speech_rate=1.4, avg_pause_ms=1100, long_pauses=3, duration_ms=5200)
HOT_FAST = ProsodySignals(energy=0.85, speech_rate=4.1, duration_ms=2000)
NEUTRAL = ProsodySignals(energy=0.5, speech_rate=2.6, duration_ms=1800)


def test_prosody_parsing_is_defensive():
    p = ProsodySignals.from_dict({"energy": "0.4", "speech_rate": None, "long_pauses": 2, "laughter": True})
    assert p.energy == 0.4 and p.speech_rate is None and p.long_pauses == 2 and p.laughter
    assert ProsodySignals.from_dict(None).available is False
    assert ProsodySignals.from_dict({"energy": "oops"}).energy is None


def test_words_and_voice_agreeing_gives_high_confidence():
    s = _state("today romba bad ah pochu", LOW_SLOW)
    assert s.confidence == "high"
    assert s.emotion_signals.get("sadness", 0) >= 0.6
    assert s.response_strategy == "listen_first"       # Care listens first
    assert s.language == "Tanglish"


def test_prosody_alone_never_becomes_certainty():
    s = _state("okay", LOW_SLOW)
    assert s.confidence in ("low", "medium")
    note = build_turn_note(s)
    assert "don't name a feeling" in note or "NOT sure how they feel" in note


def test_low_confidence_note_stays_open_ended():
    s = _state("okay")
    note = build_turn_note(s)
    assert "everything okay?" in note and "Reply in" in note


def test_laughter_dampens_a_gloomy_reading():
    sad_only = _state("bro I'm dead tired")
    laughing = _state("bro I'm dead tired 😂", ProsodySignals(energy=0.6, speech_rate=3.0, laughter=True))
    assert laughing.emotion_signals.get("happiness", 0) > 0
    assert laughing.emotion_signals.get("tiredness", 0) < sad_only.emotion_signals.get("tiredness", 1)
    assert laughing.response_strategy != "listen_first"


def test_excitement_is_celebrated_and_frustration_is_calmed():
    assert _state("I got first prize!", HOT_FAST).response_strategy == "celebrate"
    assert _state("indha code evlo try pannalum work aagala!", HOT_FAST).response_strategy == "calm"


def test_unstated_doubt_asks_before_answering():
    assert _state("bro enaku oru doubt", NEUTRAL, care=False).response_strategy == "clarify"


def test_crisis_overrides_everything_and_note_carries_help():
    s = _state("enaku saaganum pola irukku", LOW_SLOW)
    assert s.response_strategy == "safety" and s.confidence == "high"
    note = build_turn_note(s)
    assert "14416" in note and "112" in note


def test_note_is_guidance_never_a_diagnosis():
    note = build_turn_note(_state("today romba bad ah pochu", LOW_SLOW))
    assert "NOT proof" in note
    for banned in ("depressed", "diagnos", "you sound sad", "proves"):
        assert banned not in note.lower()


def test_note_describes_how_they_spoke_including_interruption():
    s = _state("wait wait adhu already try panniten",
               ProsodySignals(energy=0.8, speech_rate=4.2, interrupted=True))
    note = build_turn_note(s)
    assert "cut you off" in note


def test_listen_only_request_keeps_advice_out_of_voice():
    s = _state("advice venda, summa pesanum", NEUTRAL)
    assert s.response_strategy == "listen_first"
    assert "No advice" in build_turn_note(s)


def test_chat_mode_voice_still_works_without_care():
    s = _state("explain JWT", NEUTRAL, care=False)
    assert s.response_strategy == "answer"
    assert "spoken-length turn" in build_turn_note(s)


def test_state_log_has_no_transcript():
    log = _state("today romba bad ah pochu", LOW_SLOW).to_log()
    assert set(log) == {"language", "intent", "top_signal", "top_signal_p", "confidence", "strategy"}
