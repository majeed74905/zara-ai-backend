"""
Zara Live — voice intelligence (deterministic signal fusion, no LLM calls)
══════════════════════════════════════════════════════════════════════════════
Live Mode streams audio straight to a native-audio model, so this layer does NOT
transcribe or generate speech. It turns each finished user turn into a short,
internal note that conditions how Zara handles the NEXT turn:

    transcript (what was said)      → language / intent / emotion / care need
                                      (shared communication_engine — one brain)
  + prosody  (how it was said)      → energy, speaking rate, pauses, interruption, laughter
  + conversation state              → turn count, previous signals (a rough baseline)
          ▼
    fuse_voice_signals()  → VoiceState: emotion SIGNALS with probabilities, a
                            confidence level, and a response strategy
          ▼
    build_turn_note()     → one line the client injects as an internal note
                            ("[note] …"), never spoken, never shown

Hard rules baked in here:
  • Prosody is evidence, never proof. Low energy can mean sadness, tiredness, a bad
    mic or simply a calm speaker — so signals carry probabilities and a confidence
    level, and low confidence produces hedged, open phrasing ("everything okay?").
  • Never a diagnosis, never "your voice proves…".
  • Laughter dampens negative readings instead of amplifying them.
  • Crisis wording always wins over every other strategy.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.services.communication_engine import ResponseStrategy

# Prosody thresholds. Deliberately loose: these are weak signals, not measurements of feeling.
_LOW_ENERGY = 0.35          # normalized 0..1 RMS
_HIGH_ENERGY = 0.72
_SLOW_RATE = 1.9            # words per second
_FAST_RATE = 3.4
_LONG_PAUSE_MS = 900


@dataclass
class ProsodySignals:
    """Acoustic measurements from the browser. Every field is optional — it may not be available."""
    energy: Optional[float] = None            # 0..1, mean RMS while speaking
    energy_variation: Optional[float] = None  # 0..1, std-dev of RMS
    speech_rate: Optional[float] = None       # words per second
    avg_pause_ms: Optional[float] = None
    long_pauses: int = 0
    duration_ms: Optional[float] = None
    interrupted: bool = False                 # user cut Zara off
    laughter: bool = False

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "ProsodySignals":
        d = data or {}

        def num(key: str) -> Optional[float]:
            v = d.get(key)
            try:
                return float(v) if v is not None else None
            except (TypeError, ValueError):
                return None

        return cls(
            energy=num("energy"),
            energy_variation=num("energy_variation"),
            speech_rate=num("speech_rate"),
            avg_pause_ms=num("avg_pause_ms"),
            long_pauses=int(d.get("long_pauses") or 0),
            duration_ms=num("duration_ms"),
            interrupted=bool(d.get("interrupted")),
            laughter=bool(d.get("laughter")),
        )

    @property
    def available(self) -> bool:
        return any(v is not None for v in (self.energy, self.speech_rate, self.avg_pause_ms))


@dataclass
class VoiceState:
    """Internal state for one finished user turn. Never shown to the user."""
    language: str = "English"
    intent: str = "question"
    emotion_signals: Dict[str, float] = field(default_factory=dict)
    confidence: str = "low"          # low | medium | high
    response_strategy: str = "answer"  # listen_first | comfort | celebrate | calm | clarify | answer | safety
    prosody_note: Optional[str] = None
    care_mode: bool = False

    def to_log(self) -> Dict[str, Any]:
        top = max(self.emotion_signals.items(), key=lambda kv: kv[1], default=("none", 0.0))
        return {
            "language": self.language,
            "intent": self.intent,
            "top_signal": top[0],
            "top_signal_p": round(top[1], 2),
            "confidence": self.confidence,
            "strategy": self.response_strategy,
        }


# Semantic emotion → the signal it contributes
_EMOTION_TO_SIGNAL = {
    "crisis": "distress",
    "distressed": "overwhelm",
    "sad": "sadness",
    "stressed": "stress",
    "lonely": "loneliness",
    "frustrated": "frustration",
    "tired": "tiredness",
    "confused": "confusion",
    "excited": "happiness",
    "affectionate": "warmth",
}

_NEGATIVE_SIGNALS = {"sadness", "stress", "overwhelm", "loneliness", "frustration", "tiredness", "distress"}


def _describe_prosody(p: ProsodySignals) -> Optional[str]:
    """Plain description of HOW they spoke — facts only, no interpretation."""
    if not p.available:
        return None
    bits: List[str] = []
    if p.energy is not None:
        if p.energy <= _LOW_ENERGY:
            bits.append("quiet/low energy")
        elif p.energy >= _HIGH_ENERGY:
            bits.append("loud/high energy")
    if p.speech_rate is not None:
        if p.speech_rate <= _SLOW_RATE:
            bits.append("speaking slowly")
        elif p.speech_rate >= _FAST_RATE:
            bits.append("speaking fast")
    if p.long_pauses >= 2 or (p.avg_pause_ms or 0) >= _LONG_PAUSE_MS:
        bits.append("long pauses/hesitation")
    if p.laughter:
        bits.append("laughing")
    if p.interrupted:
        bits.append("cut you off")
    return ", ".join(bits) if bits else None


def fuse_voice_signals(
    strategy: ResponseStrategy,
    language: str,
    prosody: Optional[ProsodySignals] = None,
    care_mode: bool = False,
) -> VoiceState:
    """Combine what was said (strategy) with how it was said (prosody) into one state."""
    p = prosody or ProsodySignals()
    signals: Dict[str, float] = {}

    # 1. Semantic evidence — the words carry the most weight
    sem = strategy.emotion
    if sem.emotion != "neutral":
        name = _EMOTION_TO_SIGNAL.get(sem.emotion, sem.emotion)
        signals[name] = min(0.95, sem.confidence)

    # 2. Acoustic evidence — nudges only, never conclusive on its own
    if p.energy is not None and p.speech_rate is not None:
        low_and_slow = p.energy <= _LOW_ENERGY and p.speech_rate <= _SLOW_RATE
        hot = p.energy >= _HIGH_ENERGY and p.speech_rate >= _FAST_RATE
        if low_and_slow:
            for name in ("sadness", "tiredness"):
                signals[name] = min(0.75, signals.get(name, 0.0) + 0.25)
        if hot:
            # Loud and fast is ambiguous on its own (excited? angry? just emphatic?).
            # Only let the WORDS decide which; otherwise record plain arousal.
            if sem.emotion in ("frustrated", "stressed"):
                name = "frustration"
            elif sem.emotion == "excited" or p.laughter:
                name = "happiness"
            else:
                name = "intensity"
            signals[name] = min(0.85, signals.get(name, 0.0) + 0.25)
    if p.long_pauses >= 2:
        signals["hesitation"] = min(0.7, signals.get("hesitation", 0.0) + 0.3)

    # 3. Laughter outweighs a gloomy reading ("bro I'm dead tired 😂")
    if p.laughter:
        signals["happiness"] = min(0.9, signals.get("happiness", 0.0) + 0.35)
        for name in list(signals):
            if name in _NEGATIVE_SIGNALS:
                signals[name] = round(signals[name] * 0.5, 2)

    signals = {k: round(v, 2) for k, v in signals.items() if v >= 0.15}

    # 4. Confidence: words and voice agreeing is the only way to be confident
    top_name, top_p = max(signals.items(), key=lambda kv: kv[1], default=("none", 0.0))
    semantic_strong = sem.emotion != "neutral" and sem.confidence >= 0.75
    acoustic_agrees = bool(p.available and top_p >= 0.6)
    if sem.crisis or (semantic_strong and acoustic_agrees):
        confidence = "high"
    elif semantic_strong or top_p >= 0.6:
        confidence = "medium"
    else:
        confidence = "low"

    # 5. Response strategy
    light_hearted = p.laughter and signals.get("happiness", 0.0) >= max(
        [signals.get(n, 0.0) for n in _NEGATIVE_SIGNALS] or [0.0]
    )
    if sem.crisis:
        response_strategy = "safety"
    elif light_hearted and not sem.crisis:
        # They're laughing about it — don't turn it into a counselling session
        response_strategy = "celebrate" if signals.get("happiness", 0.0) >= 0.6 else "answer"
    elif strategy.care_need in ("listen_only", "venting"):
        response_strategy = "listen_first"
    elif top_name == "frustration" or sem.emotion == "frustrated":
        # Frustration wants a calm, practical hand — not a counselling turn
        response_strategy = "calm"
    elif strategy.care_need in ("comfort", "reassurance", "unclear", "mixed") or (
        top_name in _NEGATIVE_SIGNALS and top_p >= 0.4   # weak acoustic hints don't force a care turn
    ):
        response_strategy = "listen_first" if care_mode else "comfort"
    elif strategy.care_need == "celebrate" or top_name == "happiness":
        response_strategy = "celebrate"
    elif strategy.intent in ("request_help", "unclear") or strategy.vague_problem or top_name == "confusion":
        response_strategy = "clarify"
    else:
        response_strategy = "answer"

    return VoiceState(
        language=language,
        intent=strategy.intent,
        emotion_signals=signals,
        confidence=confidence,
        response_strategy=response_strategy,
        prosody_note=_describe_prosody(p),
        care_mode=care_mode,
    )


_STRATEGY_NOTE = {
    "listen_first": "Listen first: one short acknowledgement and a single gentle question, then stop and let them talk. No advice, no lists.",
    "comfort": "Acknowledge the feeling in one short line, then ask what happened. Keep it gentle and brief.",
    "celebrate": "Match their energy — react first, celebrate properly, then ask about it.",
    "calm": "Stay calm and steady. Acknowledge the frustration, then move to the practical next check.",
    "clarify": "Ask one focused question to get the missing detail before answering. Don't guess.",
    "answer": "Answer naturally in a spoken-length turn, then pause for them.",
    "safety": "SAFETY FIRST: stay calm and warm, take it seriously, encourage them to reach out right now to someone they trust and to a crisis line (India: Tele-MANAS 14416, emergency 112). Don't make yourself the reason to stay.",
}

_CONFIDENCE_NOTE = {
    "high": "",
    "medium": "You are NOT sure how they feel — use tentative wording ('romba heavy-a irukka pola?', 'that sounds rough') and let them correct you.",
    "low": "You have no real read on their mood — don't name a feeling. Stay neutral and open ('everything okay?', 'sollu').",
}


def build_turn_note(state: VoiceState) -> str:
    """
    One compact internal note for the model about how to handle the next turn.
    The client sends it as "[note] …"; the system prompt forbids speaking it aloud.
    """
    parts: List[str] = [f"Reply in {state.language}."]

    if state.prosody_note:
        parts.append(f"They sounded: {state.prosody_note} (voice cues only — NOT proof of how they feel).")

    if state.emotion_signals and state.confidence != "low":
        top = max(state.emotion_signals.items(), key=lambda kv: kv[1])
        parts.append(f"Possible {top[0]} (~{int(top[1] * 100)}%).")

    note = _CONFIDENCE_NOTE.get(state.confidence)
    if note:
        parts.append(note)

    parts.append(_STRATEGY_NOTE.get(state.response_strategy, _STRATEGY_NOTE["answer"]))
    if state.care_mode and state.response_strategy not in ("safety",):
        parts.append("Zara Care: warm, unhurried, never clinical.")
    return " ".join(parts)
