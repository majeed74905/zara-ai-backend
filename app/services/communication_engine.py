"""
Zara Communication Engine — deterministic conversational intelligence
══════════════════════════════════════════════════════════════════════════════
Runs locally before every generation (no LLM calls, microseconds) and decides
HOW Zara should answer this particular turn:

    USER MESSAGE + HISTORY (+ user's local hour)
          │
          ├─ Greeting      is it a greeting? which kind (simple, casual, affectionate, time-based,
          │                how-are-you, check-in, returning, playful, emotional)? is there a real
          │                request or feeling after the "hi"? what time of day is it for them?
          ├─ Intent        greeting / thanks / "ok" / goodbye / affection / emotional share /
          │                celebration / technical / question / follow-up / check-in reply / task
          ├─ Emotion       emotion + confidence + intensity (+ crisis), multilingual cues
          ├─ Depth         minimal / short / medium / detailed (proportional to the need)
          ├─ Tone          casual / professional / technical / neutral
          ├─ Warmth        0–4, only as warm as the USER has made the conversation
          ├─ Address term  bro / macha / maah / bhai ... that the user actually uses
          └─ Variation     openers Zara used recently, so replies don't start the same way
          ▼
    ResponseStrategy → prompt block (zara_identity) + token budget / temperature (router)
                     + safety post-checks (response_controller)

The strategy never hard-codes replies; it gives the model precise, per-turn guidance and
the model generates the words. Shared by Chat, Care and Live (voice persona).
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# ─────────────────────────────────────────────────────────────────────────────
# INTENT PATTERNS (English, Tanglish, Tamil, Hinglish, Hindi, other Indic greetings)
# ─────────────────────────────────────────────────────────────────────────────

_ADDRESS = r"(?:[\s,]+(?:zara|bro|broo+|macha|machi|machan|maah|maa|ma|da|di|dude|nanba|nanbaa|thala|bhai|yaar|anna|akka|there|buddy|chellam|baby|babe|jaan|love|dear|guru|maga))*"

_GREETING_WORD = (
    r"(?:hi+|hello+|hel+o+|hlo+|hey+|heya|hiya|hai+|yo+|sup|howdy|hola|vanakkam|vanakam|namaste|namaskar|"
    r"namaskara|namaskaram|salaam|salam|(?:good|gud)\s*(?:morning|afternoon|evening)|gm|morning|evening|"
    r"வணக்கம்|காலை வணக்கம்|नमस्ते|नमस्कार|സുപ്രഭാതം|നമസ്കാരം|ನಮಸ್ಕಾರ|నమస్కారం)"
)
_TRAILING = r"[\s!.,?😄😊🙂👋❤️☀️🔥😁🤗]*"

_GREETING_RE = re.compile(r"^" + _GREETING_WORD + _ADDRESS + _TRAILING + r"$")
_GREET_PREFIX_RE = re.compile(r"^" + _GREETING_WORD + _ADDRESS + r"[\s!.,😄😊🙂👋❤️☀️🔥]*")
_HOW_ARE_YOU_RE = re.compile(
    r"\b(?:how are (?:you|u)|how r u|how'?s it going|how you doing|how are you doing|how have you been|"
    r"how'?s (?:your|ur) day|what'?s up|wassup|whats up|sup|"
    r"eppadi (?:irukk?\w*|rukk?\w*)|epdi (?:irukk?\w*|rukk?\w*)|eppudi (?:irukk?\w*)|nalla irukk?eengala|nalla irukkiya|"
    r"kaise ho|kaise hain|kaisa hai|kaisi ho|kya haal(?: hai)?|kya hal hai|sab badhiya|sab theek|"
    r"sugamano|sukhamano|ela unnav\w*|ela unnaru|hegiddiya|hegidira|hegiddeera)\b"
    r"|எப்படி இருக்|நல்லா இருக்கீங்களா|நல்லா இருக்கியா|कैसे हो|कैसे हैं|क्या हाल|സുഖമാണോ|ಹೇಗಿದ್ದೀ|ఎలా ఉన్నా"
)
_THANKS_RE = re.compile(
    r"\b(?:thanks|thank you|thank u|thanku|thx|tysm|ty|nandri|nanri|dhanyavaad|dhanyavad|shukriya|thanks a lot)\b"
    r"|நன்றி|धन्यवाद|शुक्रिया"
)
_ACK_RE = re.compile(
    r"^(?:ok+|okay+|okie|k+|kk|hmm+|hm+|mm+|seri|sari|sariya|achha|acha|accha|theek hai|thik hai|cool|fine|"
    r"got it|alright|right|yes|yeah|ya|yup|haan|han|aama|aamam|done|nice|super|👍|👌|🙂)"
    + _ADDRESS + r"[\s!.,👍👌😄😊🙂❤️]*$"
)
_GOODBYE_RE = re.compile(
    r"\b(?:bye+|goodbye|good ?night|gn|see (?:you|ya)|cya|tata|ttyl|talk later|poitu varen|poittu varen|"
    r"chalo bye|shubh ratri|nalla thoongu)\b"
)
_AFFECTION_RE = re.compile(
    r"\b(?:love (?:you|u)|luv (?:you|u)|miss (?:you|u)|i like you|romba pudikkum|pyaar|i adore you)\b|[❤💕💖😘🥰🤗]"
)
_SMALL_TALK_RE = re.compile(
    r"\b(?:what are you doing|wyd|what'?s new|enna panra|enna panreenga|enna panringa|enna pannitu irukk?\w*|"
    r"kya kar rah[ae]? h(?:o|ai)|kya kar rahi|kya chal raha|kya scene|saaptiya|saptiya|saapteengala|khana khaya)\b"
    r"|சாப்பிட்டீங்களா|சாப்பிட்டியா|என்ன பண்ற|क्या कर रहे|खाना खाया"
)
_EXPLAIN_START_RE = re.compile(r"^(?:please |kindly |can you |could you )?(?:explain|describe|tell me about|walk me through)\b")
_QUESTION_START_RE = re.compile(
    r"^(?:what|why|how|when|where|who|which|can|could|would|should|is|are|do|does|did|will|"
    r"enna|epdi|eppadi|yen|yaen|edhu|evlo|kya|kaise|kyun|kab|kaun|kaha|kitna)\b"
)
_DETAIL_REQUEST_RE = re.compile(
    r"\b(?:in detail|detailed|step[- ]by[- ]step|deep dive|explain (?:everything|thoroughly|fully)|full guide|"
    r"elaborate|architecture|design|compare|comparison|difference between|pros and cons|trade-?offs|debug|diagnose|"
    r"root cause|why .* (?:randomly|sometimes|only))\b"
)
_TECH_RE = re.compile(
    r"\b(?:api|apis|error|errors|bug|bugs|database|db|server|code|coding|sql|mysql|postgres|query|deploy|deployment|"
    r"function|exception|stack ?trace|backend|frontend|login|payment|webhook|callback|json|http|https|request|"
    r"response|build|compile|crash|docker|git|github|react|python|java|javascript|typescript|node|npm|css|html|"
    r"config|jwt|auth|token|endpoint|schema|migration|cache|redis|kafka|latency|timeout|status code|404|500|"
    r"undefined|null|null pointer|framework|library|algorithm|app|website)\b"
)

# Greeting sub-signals
_TIME_GREETING_RE = re.compile(
    r"\b(?:good|gud)\s*(morning|afternoon|evening)\b|\b(gm)\b|^(morning|evening)\b|(காலை வணக்கம்|सुप्रभात|സുപ്രഭാതം)"
)
# Zara (the assistant) asked how the user is doing in its last message
_CHECKIN_QUESTION_RE = re.compile(
    r"(?:how (?:are|about) (?:you|u)|how'?s it going|how you doing|what about you|and you\??|you\?\s*$|"
    r"nee eppadi|neenga eppadi|eppadi irukk|epdi irukk|nee epdi|tu bata|aap kaise|kaise ho|kaisa hai|kya haal|"
    r"எப்படி இருக்|कैसे हो|कैसे हैं|ela unnav|sugamano|hegiddiya)",
    re.IGNORECASE,
)
# The user describes their own state ("naan nalla irukken", "I'm good", "badhiya hoon")
_STATE_REPLY_RE = re.compile(
    r"\b(?:i'?m (?:good|fine|great|ok|okay|alright|doing (?:good|well|great|ok|fine)|well|tired|bored|busy)|"
    r"(?:good|fine|great|not bad|all good|doing well|pretty good)|"
    r"nalla(?:a)? irukk?\w*|nallaa|super ah irukk?\w*|mass ah|jolly ah|semma ah|irukken|irukkom|"
    r"badhiya|badiya|mast hoon|theek hoon|thik hoon|main theek|sab badhiya|hoon)\b"
    r"|நல்லா இருக்கேன்|நல்லா இருக்கேன்|ठीक हूँ|बढ़िया"
)
# Life events worth checking in on when a returning user greets
_LIFE_EVENT_RE = re.compile(
    r"\b(?:exam|exams|test|interview|trip|travel|journey|project|deadline|presentation|meeting|match|result|results|"
    r"surgery|hospital|doctor|appointment|wedding|birthday|job|placement|viva|review|demo|launch|pariksha|"
    r"exam-ku|interview-ku)\b|பரீட்சை|தேர்வு|நேர்காணல்|परीक्षा|इंटरव्यू"
)
_ELONGATION_RE = re.compile(r"([a-z])\1{2,}")

# ─────────────────────────────────────────────────────────────────────────────
# EMOTION CUES — (regex, weight). Lowercased input. Script cues need no \b.
# ─────────────────────────────────────────────────────────────────────────────

def _cues(*pairs: Tuple[str, float]) -> List[Tuple["re.Pattern[str]", float]]:
    return [(re.compile(p), w) for p, w in pairs]


_EMOTION_CUES: Dict[str, List[Tuple["re.Pattern[str]", float]]] = {
    "crisis": _cues(
        (r"\b(?:suicide|suicidal|kill myself|end my life|end it all|want to die|wanna die|don'?t want to live|"
         r"no reason to live|better off dead|self[- ]harm|hurt myself|cut myself)\b", 3.0),
        (r"\b(?:saaganum|saaga poren|sethu poiduven|sethuduven|uyir vaazha pidikkala|vaazha pidikkala|"
         r"marna chahta|marna chahti|jeena nahi|jeene ka mann nahi|khudkushi|mar jaunga|mar jaungi)\b", 3.0),
        (r"தற்கொலை|சாகணும்|சாக போறேன்|வாழ பிடிக்கல|मरना चाहता|मरना चाहती|जीना नहीं|आत्महत्या|खुदकुशी", 3.0),
    ),
    "distressed": _cues(
        (r"\b(?:overwhelm(?:ed|ing)?|breaking down|can'?t (?:take|handle) (?:it|this)|falling apart|panic(?:king)?|"
         r"panic attack|can'?t breathe|losing it)\b", 2.0),
        (r"\b(?:romba overwhelming|thaanga mudiyala|thaangala|sahan nahi|bardasht nahi)\b", 2.0),
    ),
    "sad": _cues(
        (r"\b(?:sad|upset|depressed|down|hurt|heartbroken|broke up|breakup|crying|cried|cry|miserable|"
         r"bad day|worst day|terrible day|horrible|disappointed|let down|failed|feel low|feeling low)\b", 1.5),
        (r"\b(?:kashtama|kashtam|kastama|kavalai|azhudhen|azhuren|worst ah|bad ah pochu|mood off|mood sari illa|"
         r"manasu sari illa|dukhi|udaas|dukh|rona aa raha|dil toot)\b", 1.5),
        (r"கஷ்டமா|வருத்தம்|அழுத|மனசு சரியில்ல|दुखी|उदास|दुख", 1.5),
        (r"[😢😞😔💔🥺]", 1.0),
        (r"😭", 0.5),
    ),
    "stressed": _cues(
        (r"\b(?:stress(?:ed|ful)?|pressure|tension|tense|anxious|anxiety|worried|worry|nervous|scared|afraid|"
         r"deadline|exam tomorrow|interview tomorrow)\b", 1.5),
        (r"\b(?:bayama|bayam|bayamaa|payama|tension ah|ghabrahat|chinta|dar lag raha|darr)\b", 1.5),
        (r"பயமா|டென்ஷன்|கவலை|चिंता|डर|घबराहट", 1.5),
    ),
    "lonely": _cues(
        (r"\b(?:lonely|alone|nobody|no one (?:cares|to talk)|no friends|left out|isolated|by myself)\b", 1.5),
        (r"\b(?:thaniya|thanimai|naan mattum|ellarum busy|yaarum illa|akela|akeli|akelapan|koi nahi)\b", 1.5),
        (r"தனியா|தனிமை|अकेला|अकेली", 1.5),
    ),
    "frustrated": _cues(
        (r"\b(?:frustrat\w*|irritat\w*|annoy\w*|fed up|sick of|hate this|wtf|ugh+|argh+|so done|useless|"
         r"keeps failing|again and again|not working again)\b", 1.5),
        (r"\b(?:kadupa|kaduppa|kaduppu|erichal|mokka|waste ah|kadup|gussa|pareshan|dimaag kharab|bakwaas)\b", 1.5),
        (r"[😤😡🤬]", 1.0),
    ),
    "tired": _cues(
        (r"\b(?:tired|exhausted|drained|sleepy|burn(?:ed|t) out|burnout|no energy|worn out)\b", 1.2),
        (r"\b(?:romba tired|mudiyala|sorvaa|thakaan|thak gaya|thak gayi|neend aa rahi)\b", 1.2),
        (r"சோர்வா|थक गया|थक गई", 1.2),
    ),
    "confused": _cues(
        (r"\b(?:confus\w*|don'?t understand|dont understand|not getting it|no idea|lost|makes no sense|"
         r"what does (?:this|that) mean)\b", 1.5),
        (r"\b(?:puriyala|purila|puriyave illa|onnum puriyala|onnum purila|samajh nahi|samajh nahin|kuch samajh)\b", 1.5),
        (r"புரியல|புரியவில்லை|समझ नहीं", 1.5),
    ),
    "excited": _cues(
        (r"\b(?:happy|excited|yay+|yes{3,}|woo+|finally|awesome|amazing|so good|got the job|got selected|"
         r"passed|cleared|it worked|works now|nailed it|best day)\b", 1.5),
        (r"\b(?:work aayiduchu|aayiduchu|semma happy|romba happy|santhosham|jolly|khush|maza aa gaya|ho gaya yaar)\b", 1.5),
        (r"சந்தோஷம்|ஜாலி|खुश|मज़ा", 1.5),
        (r"[🔥🎉🥳🤩]", 0.8),
    ),
    "affectionate": _cues(
        (r"\b(?:love (?:you|u)|luv (?:you|u)|miss (?:you|u)|i like you|you'?re sweet|so sweet|chellam|kutty)\b", 1.5),
        (r"[❤💕💖😘🥰🤗]", 0.8),
    ),
}

_INTENSIFIER_RE = re.compile(
    r"\b(?:very|so|really|too|extremely|totally|completely|romba|rombha|remba|bahut|bohot|ekdum|sema|semma)\b|!!+|(.)\1{3,}"
)
_LAUGH_RE = re.compile(r"😂|🤣|\b(?:lol|lmao|haha+|hehe+)\b")

_NEGATIVE_EMOTIONS = {"crisis", "distressed", "sad", "stressed", "lonely", "frustrated", "tired", "confused"}

# ─────────────────────────────────────────────────────────────────────────────
# ADDRESS TERMS & WARMTH
# ─────────────────────────────────────────────────────────────────────────────

_ADDRESS_TERMS = [
    "macha", "machi", "machan", "maah", "nanba", "thala", "bro", "bhai", "yaar", "dude",
    "anna", "akka", "chellam", "kutty", "baby", "babe", "jaan", "da", "di",
]
_ADDRESS_TERM_RE = re.compile(r"\b(" + "|".join(_ADDRESS_TERMS) + r")\b")
_ROMANTIC_RE = re.compile(
    r"\b(?:love (?:you|u)|luv (?:you|u)|miss (?:you|u)|baby|babe|jaan|darling|sweetheart|my love|chellam|kutty|hi love|hey love)\b|[😘🥰💕💖]"
)
_AFFECTIONATE_RE = re.compile(r"\b(?:maah|dear)\b|[❤🤗]")
_CASUAL_RE = re.compile(r"\b(?:bro|macha|machi|machan|da|di|dude|bhai|yaar|nanba|thala|lol|haha)\b|😂|🤣")


@dataclass
class EmotionSignal:
    emotion: str = "neutral"
    confidence: float = 0.0
    intensity: str = "low"     # low | moderate | high
    crisis: bool = False
    playful: bool = False

    @property
    def is_negative(self) -> bool:
        return self.emotion in _NEGATIVE_EMOTIONS


@dataclass
class GreetingSignal:
    """What kind of greeting this is — guidance for the model, never a canned reply."""
    is_greeting: bool = False
    types: List[str] = field(default_factory=list)   # simple, casual, affectionate, time_based, how_are_you,
                                                      # checkin, returning, playful, emotional
    asks_how_are_you: bool = False
    has_followup: bool = False          # "hi bro, payment issue irukku" → greeting + another intent
    remainder: str = ""                 # text after the greeting part
    time_of_day: Optional[str] = None   # morning | afternoon | evening | night (user's local time)
    said_time_greeting: Optional[str] = None  # "morning" if the user said "good morning"
    already_greeted: bool = False       # conversation is already going
    topic_snippet: Optional[str] = None # recent life event the user mentioned (exam, interview…)


@dataclass
class ResponseStrategy:
    intent: str = "question"
    emotion: EmotionSignal = field(default_factory=EmotionSignal)
    depth: str = "medium"              # minimal | short | medium | detailed
    tone: str = "neutral"              # casual | professional | technical | neutral
    warmth: int = 1                    # 0 professional … 4 romantic-style
    address_term: Optional[str] = None
    avoid_openers: List[str] = field(default_factory=list)
    emotional_thread: Optional[str] = None
    care_mode: bool = False
    max_tokens_cap: Optional[int] = None
    vague_problem: bool = False        # short technical complaint → ask before assuming
    mode: str = "fast"
    greeting: GreetingSignal = field(default_factory=GreetingSignal)
    temperature_boost: float = 0.0     # a bit more variation for social turns

    def to_log(self) -> Dict[str, Any]:
        return {
            "intent": self.intent,
            "emotion": self.emotion.emotion,
            "emotion_confidence": round(self.emotion.confidence, 2),
            "intensity": self.emotion.intensity,
            "crisis": self.emotion.crisis,
            "depth": self.depth,
            "tone": self.tone,
            "warmth": self.warmth,
            "greeting": "+".join(self.greeting.types) if self.greeting.is_greeting else "",
        }


# ─────────────────────────────────────────────────────────────────────────────
# ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

def detect_emotion(text: str) -> EmotionSignal:
    """Emotion from conversational cues. Low confidence → treat as neutral (never assume)."""
    t = (text or "").lower()
    if not t.strip():
        return EmotionSignal()

    scores: Dict[str, float] = {}
    for emotion, cues in _EMOTION_CUES.items():
        s = sum(w for pattern, w in cues if pattern.search(t))
        if s:
            scores[emotion] = s

    playful = bool(_LAUGH_RE.search(t))
    if playful and "sad" in scores and scores["sad"] <= 0.5:
        scores.pop("sad")  # "😂😭" is laughter, not sadness

    if "crisis" in scores:
        return EmotionSignal("crisis", 0.95, "high", crisis=True)

    if not scores:
        return EmotionSignal(playful=playful)

    emotion, score = max(scores.items(), key=lambda kv: kv[1])
    intensifiers = len(_INTENSIFIER_RE.findall(t))
    confidence = min(0.95, 0.35 + 0.25 * score + 0.05 * intensifiers)
    if confidence < 0.55:
        return EmotionSignal("neutral", confidence, "low", playful=playful)

    if emotion == "distressed" or score >= 3.0 or intensifiers >= 2:
        intensity = "high"
    elif score >= 1.5 or intensifiers >= 1:
        intensity = "moderate"
    else:
        intensity = "low"
    return EmotionSignal(emotion, round(confidence, 2), intensity, playful=playful)


def _time_of_day(hour: Optional[int]) -> Optional[str]:
    if hour is None or not 0 <= hour <= 23:
        return None
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 22:
        return "evening"
    return "night"


def _life_event_snippet(history: List[Dict[str, str]]) -> Optional[str]:
    """Most recent user message mentioning a life event (exam, interview…), trimmed."""
    for msg in reversed((history or [])[-12:]):
        if msg.get("role") != "user":
            continue
        content = str(msg.get("content", "")).strip()
        if _LIFE_EVENT_RE.search(content.lower()):
            return content[:120]
    return None


def detect_greeting(
    text: str,
    history: Optional[List[Dict[str, str]]] = None,
    client_hour: Optional[int] = None,
    emotion: Optional[EmotionSignal] = None,
) -> GreetingSignal:
    """Recognize natural greetings (typos, elongations, scripts, address terms) and classify them."""
    history = history or []
    raw = (text or "").strip()
    t = _ELONGATION_RE.sub(r"\1\1", raw.lower())   # "hiiiii" → "hii", "heyyyy" → "heyy"
    words = t.split()
    if not t:
        return GreetingSignal()

    prefix = _GREET_PREFIX_RE.match(t)
    how_are_you = bool(_HOW_ARE_YOU_RE.search(t))
    checkin = bool(_SMALL_TALK_RE.search(t))

    remainder = t[prefix.end():].strip(" ,.!?") if prefix else t
    remainder_is_social = (
        not remainder
        or bool(_HOW_ARE_YOU_RE.fullmatch(remainder.strip(" ?!."))
                or (_HOW_ARE_YOU_RE.search(remainder) and len(remainder.split()) <= 6))
        or bool(_SMALL_TALK_RE.search(remainder) and len(remainder.split()) <= 6)
        or bool(re.fullmatch(_ADDRESS.replace("[\\s,]+", "[\\s,]*") + _TRAILING, remainder))
    )

    if prefix:
        is_greeting = True
        has_followup = not remainder_is_social
    elif how_are_you and len(words) <= 7:
        is_greeting, has_followup, remainder = True, False, ""
    elif checkin and len(words) <= 6 and not history:
        is_greeting, has_followup, remainder = True, False, ""
    else:
        return GreetingSignal()

    sig = GreetingSignal(is_greeting=is_greeting, has_followup=has_followup,
                         remainder=remainder if has_followup else "")
    sig.asks_how_are_you = how_are_you
    sig.time_of_day = _time_of_day(client_hour)
    tm = _TIME_GREETING_RE.search(t)
    if tm:
        said = next((g for g in tm.groups() if g), "")
        sig.said_time_greeting = "morning" if said in ("gm", "காலை வணக்கம்", "सुप्रभात", "സുപ്രഭാതം") else said
    sig.already_greeted = any(m.get("role") == "assistant" for m in history)
    if history:
        sig.topic_snippet = _life_event_snippet(history)

    types: List[str] = []
    if sig.said_time_greeting:
        types.append("time_based")
    if how_are_you:
        types.append("how_are_you")
    if checkin:
        types.append("checkin")
    if _ROMANTIC_RE.search(t) or _AFFECTIONATE_RE.search(t):
        types.append("affectionate")
    elif _CASUAL_RE.search(t) or _ADDRESS_TERM_RE.search(t):
        types.append("casual")
    if _LAUGH_RE.search(t) or re.search(r"\b(?:yo+|sup|heyy+|hii+)\b", t):
        types.append("playful")
    if emotion and emotion.is_negative and emotion.confidence >= 0.6:
        types.append("emotional")
    if sig.already_greeted or sig.topic_snippet:
        types.append("returning")
    if not types:
        types.append("simple")
    sig.types = types
    return sig


def _is_checkin_reply(text: str, history: List[Dict[str, str]]) -> bool:
    """User answering Zara's 'how are you?' ("naan nalla irukken", "I'm good, you?")."""
    last_assistant = next((m for m in reversed(history or []) if m.get("role") == "assistant"), None)
    if not last_assistant or not _CHECKIN_QUESTION_RE.search(str(last_assistant.get("content", ""))):
        return False
    t = (text or "").strip().lower()
    return len(t.split()) <= 10 and bool(_STATE_REPLY_RE.search(t)) and not _TECH_RE.search(t)


def _detect_intent(text: str, emotion: EmotionSignal, history: List[Dict[str, str]]) -> str:
    t = (text or "").strip().lower()
    words = t.split()
    if not t:
        return "unclear"
    if "```" in t:
        return "technical"
    if emotion.crisis:
        return "emotional_share"
    if _ACK_RE.match(t):
        return "acknowledgement"
    if _GREETING_RE.match(_ELONGATION_RE.sub(r"\1\1", t)) or (_HOW_ARE_YOU_RE.search(t) and len(words) <= 7):
        return "greeting"
    if _THANKS_RE.search(t) and len(words) <= 6:
        return "thanks"
    if _GOODBYE_RE.search(t) and len(words) <= 6:
        return "goodbye"
    if _AFFECTION_RE.search(t) and len(words) <= 8 and not _TECH_RE.search(t):
        return "affection"
    if _SMALL_TALK_RE.search(t) and len(words) <= 8:
        return "small_talk"
    if emotion.emotion == "excited" and emotion.confidence >= 0.6 and not _QUESTION_START_RE.match(t):
        return "celebration"
    if emotion.is_negative and emotion.confidence >= 0.6 and emotion.emotion != "confused" and not _TECH_RE.search(t):
        return "emotional_share"
    if _TECH_RE.search(t):
        return "technical"
    if _EXPLAIN_START_RE.match(t) or _DETAIL_REQUEST_RE.search(t):
        return "question"
    if len(words) <= 5 and history and not t.endswith("?"):
        return "follow_up"
    if "?" in t or _QUESTION_START_RE.match(t):
        return "question"
    if len(words) <= 4:
        return "small_talk"
    return "task"


_DEPTH_ORDER = ["minimal", "short", "medium", "detailed"]


def _shift(depth: str, delta: int) -> str:
    i = max(0, min(len(_DEPTH_ORDER) - 1, _DEPTH_ORDER.index(depth) + delta))
    return _DEPTH_ORDER[i]


def _decide_depth(intent: str, text: str, emotion: EmotionSignal, mode: str, module: str) -> str:
    t = (text or "").lower()
    words = len(t.split())
    wants_detail = bool(_DETAIL_REQUEST_RE.search(t))

    if module != "chat":
        return "detailed"
    if intent in ("greeting", "thanks", "acknowledgement", "goodbye", "affection", "checkin_reply"):
        return "minimal"
    if emotion.crisis:
        return "medium"
    if intent == "emotional_share":
        depth = "medium" if emotion.intensity == "high" else "short"
    elif intent in ("celebration", "small_talk", "follow_up"):
        depth = "short"
    elif intent == "technical":
        is_definition = bool(re.match(r"^(?:what is|what's|what are|define|meaning of)\b", t))
        if is_definition and words <= 8 and not wants_detail:
            depth = "short"  # "what is an API?" → a clean 2–3 sentence answer
        else:
            depth = "detailed" if (wants_detail or words >= 25) else "medium"
    elif intent == "question":
        depth = "detailed" if wants_detail else ("short" if words <= 8 else "medium")
    else:
        depth = "detailed" if wants_detail else "medium"

    # The Zara model shapes depth: Pro digs deeper on real problems, Eco stays lean
    if mode == "pro" and intent in ("technical", "question", "task") and depth == "medium" and words >= 8:
        depth = "detailed"
    if mode == "eco" and not wants_detail and not emotion.crisis:
        depth = _shift(depth, -1) if depth in ("medium", "detailed") else depth
    return depth


def _decide_tone(comm_profile: Dict[str, Any], intent: str) -> str:
    formality = comm_profile.get("formality", "neutral")
    technicality = comm_profile.get("technicality", "general")
    if formality == "formal":
        return "professional"
    if formality == "casual":
        return "casual"
    if technicality == "technical" or intent == "technical":
        return "technical"
    return "neutral"


def _decide_warmth(texts: List[str], tone: str, care_mode: bool) -> int:
    """Warmth follows what the USER has established in this conversation (current + recent turns)."""
    joined = " ".join(texts).lower()
    if _ROMANTIC_RE.search(joined):
        level = 4 if care_mode else 3
    elif _AFFECTIONATE_RE.search(joined):
        level = 3
    elif _CASUAL_RE.search(joined) or tone == "casual":
        level = 2
    elif tone == "professional":
        level = 0
    else:
        level = 1
    if care_mode:
        level = max(level, 2)  # Care is always at least warm
    return level


def _address_term(texts: List[str]) -> Optional[str]:
    for text in texts:  # newest first
        m = _ADDRESS_TERM_RE.findall((text or "").lower())
        if m:
            # Prefer the most specific term the user used (macha/maah over da)
            ranked = sorted(set(m), key=lambda w: _ADDRESS_TERMS.index(w))
            return ranked[0]
    return None


def _recent_openers(history: List[Dict[str, str]], limit: int = 3) -> List[str]:
    openers = []
    for msg in reversed(history or []):
        if msg.get("role") != "assistant":
            continue
        first_line = str(msg.get("content", "")).strip().split("\n", 1)[0]
        words = first_line.split()[:3]
        if words:
            openers.append(" ".join(words))
        if len(openers) >= limit:
            break
    return openers


def _emotional_thread(history: List[Dict[str, str]]) -> Optional[str]:
    """If the user recently shared a strong feeling, remember it for continuity."""
    for msg in reversed((history or [])[-8:]):
        if msg.get("role") != "user":
            continue
        sig = detect_emotion(str(msg.get("content", "")))
        if sig.emotion != "neutral" and sig.confidence >= 0.6:
            return sig.emotion
    return None


_TOKEN_CAPS = {"minimal": 400, "short": 700}
_SOCIAL_INTENTS = {"greeting", "checkin_reply", "thanks", "acknowledgement", "goodbye", "small_talk", "affection"}


def analyze_turn(
    message: str,
    history: Optional[List[Dict[str, str]]] = None,
    comm_profile: Optional[Dict[str, Any]] = None,
    mode: str = "fast",
    module: str = "chat",
    interaction_mode: str = "chat",
    client_hour: Optional[int] = None,
) -> ResponseStrategy:
    """Build the response strategy for the current turn."""
    history = history or []
    comm_profile = comm_profile or {}
    care_mode = interaction_mode == "care"

    emotion = detect_emotion(message)
    greeting = detect_greeting(message, history, client_hour, emotion)

    if greeting.is_greeting and greeting.has_followup:
        # "hi bro, payment issue irukku" → the request after the greeting drives the reply
        intent = _detect_intent(greeting.remainder, emotion, history)
        if intent in ("greeting", "acknowledgement", "unclear"):
            intent, greeting.has_followup = "greeting", False
    elif greeting.is_greeting and "checkin" not in greeting.types:
        intent = "greeting"
    else:
        intent = _detect_intent(message, emotion, history)

    if intent not in ("technical", "emotional_share") and _is_checkin_reply(message, history):
        intent = "checkin_reply"

    depth_text = greeting.remainder if greeting.has_followup else message
    depth = _decide_depth(intent, depth_text, emotion, mode, module)
    tone = _decide_tone(comm_profile, intent)

    recent_user = [message] + [
        str(m.get("content", "")) for m in reversed(history) if m.get("role") == "user"
    ][:6]
    warmth = _decide_warmth(recent_user, tone, care_mode)
    thread = _emotional_thread(history) if emotion.emotion == "neutral" else None
    t = (message or "").strip().lower()
    vague = (
        module == "chat"
        and intent == "technical"
        and len(t.split()) <= 6
        and "```" not in t
        and not re.match(r"^(?:what is|what's|what are|define|meaning of)\b", t)
    )

    return ResponseStrategy(
        vague_problem=vague,
        intent=intent,
        emotion=emotion,
        depth=depth,
        tone=tone,
        warmth=warmth,
        address_term=_address_term(recent_user),
        avoid_openers=_recent_openers(history),
        emotional_thread=thread,
        care_mode=care_mode,
        max_tokens_cap=_TOKEN_CAPS.get(depth) if module == "chat" else None,
        mode=(mode or "fast").lower(),
        greeting=greeting,
        temperature_boost=0.15 if (module == "chat" and intent in _SOCIAL_INTENTS) else 0.0,
    )


# ─────────────────────────────────────────────────────────────────────────────
# PROMPT RENDERING
# ─────────────────────────────────────────────────────────────────────────────

_INTENT_GUIDE = {
    "greeting": "They're greeting you. Greet back naturally, like a person, in their language and energy — start a conversation, not a service desk.",
    "checkin_reply": "They just answered how they're doing. React naturally to what they said (share the vibe) and keep the conversation moving — e.g. ask about their day or plans. Don't switch to 'how can I help'.",
    "thanks": "They're thanking you. A short, warm acknowledgement — vary the wording.",
    "acknowledgement": "A tiny acknowledgement (ok / hmm / seri / 👍). Reply with a tiny natural response, or gently continue the current thread if context calls for it. Never 'How can I help you?'.",
    "goodbye": "They're wrapping up. A short, warm goodbye.",
    "affection": "They're being affectionate. Receive it warmly and sweetly, stay grounded and honest, never possessive.",
    "emotional_share": "They're sharing how they feel. Listen first: acknowledge, comfort, then invite them to say more. Don't jump into advice unless they ask.",
    "celebration": "They're excited / sharing good news. Celebrate with them and match their energy, then ask what happened.",
    "technical": "A technical problem or question. Understand it first; if key details are missing (exact error, what they tried), ask for them; otherwise diagnose and give concrete next steps.",
    "question": "A question. Answer it directly.",
    "follow_up": "A short follow-up on the ongoing topic. Use the conversation context instead of starting over.",
    "small_talk": "Casual small talk. Keep it light and natural.",
    "task": "A request or task. Do it well at the right depth.",
    "unclear": "The intent is unclear. Respond briefly and naturally; a short clarifying question is fine.",
}

_DEPTH_GUIDE = {
    "minimal": "VERY SHORT — a few words to one sentence. No explanations, no lists.",
    "short": "SHORT — 1 to 3 sentences.",
    "medium": "MEDIUM — a focused answer: a short paragraph or a few compact steps.",
    "detailed": "DETAILED — as thorough as the problem needs: structured explanation or diagnosis with concrete next steps. Still no padding.",
}

_EMOTION_GUIDE = {
    "crisis": "SAFETY FIRST. They may be in danger. Respond with calm warmth, take it seriously, encourage them to reach out right now to someone they trust and to a crisis line (India: Tele-MANAS 14416, free 24x7; emergency 112; elsewhere, local emergency services). Don't guilt them, don't be their only support.",
    "distressed": "They sound overwhelmed. Slow down: gentle, short sentences, suggest one small grounding step (a breath, a pause), and invite them to share. No jokes, no advice lists.",
    "sad": "They sound down. Comfort before solutions: acknowledge tentatively ('sounds like…'), be gentle, let them talk. No jokes.",
    "stressed": "They sound stressed/anxious. Validate it, reassure calmly, and offer to take it one step at a time.",
    "lonely": "They may be feeling lonely. Be warm and present, invite them to talk; where it fits, gently encourage connecting with people in their life too.",
    "frustrated": "They're frustrated. Acknowledge it briefly and kindly, then move toward fixing it. No lecturing.",
    "tired": "They sound tired. Be gentle and brief; don't pile on.",
    "confused": "They're confused. Reassure ('no worries') and go slowly, one step at a time.",
    "excited": "They're excited. Share the excitement genuinely.",
    "affectionate": "They're being affectionate. Warm, sweet, grounded.",
}

_TONE_GUIDE = {
    "casual": "casual and friendly",
    "professional": "polished and professional — no slang",
    "technical": "clear and technical",
    "neutral": "natural and friendly",
}

_WARMTH_GUIDE = {
    0: "0/4 professional — courteous, no pet names, emojis rarely.",
    1: "1/4 friendly — warm but not familiar.",
    2: "2/4 warm — casual friend energy.",
    3: "3/4 affectionate — the user has set an affectionate tone; sweet, caring wording is welcome.",
    4: "4/4 romantic-style warmth — the user has explicitly set this tone; loving, tender wording is OK, but never possessive or dependency-building.",
}

_GREETING_MODE_STYLE = {
    "fast": "Zara Fast greeting: quick, natural, a little energetic — a few words.",
    "pro": "Zara Pro greeting: polished, warm and natural (not formal, not stiff) — one easy sentence.",
    "eco": "Zara Eco greeting: simple and warm — the lightest natural reply.",
}

_TIME_WORDS = {"morning": "morning", "afternoon": "afternoon", "evening": "evening", "night": "late night"}


def _greeting_lines(strategy: ResponseStrategy) -> List[str]:
    g = strategy.greeting
    lines = [f"- GREETING ({', '.join(g.types)}). Have a conversation — never a template or a scripted line:"]
    if g.has_followup:
        lines.append(
            "  • They greeted you AND said something more. Greet back in a word or two, then respond to the rest "
            "right away — don't reply with only a greeting."
        )
    else:
        lines.append("  • Reply in their language and energy, and keep it short (a few words to one sentence).")
        if g.asks_how_are_you:
            lines.append(
                "  • They asked how you are: answer briefly and naturally that you're doing good (no 'as an AI' "
                "disclaimer), then ask them back."
            )
        elif "checkin" in g.types:
            lines.append(
                "  • It's a casual check-in (what are you doing / did you eat): answer playfully but honestly in a line — "
                "you're here chatting with them — then ask them back."
            )
        elif g.types == ["simple"] or g.types == ["playful"]:
            lines.append("  • A minimal greeting deserves a minimal reply; a light invite ('what's up?') is optional, not required.")
        else:
            lines.append("  • A light, natural invite to continue is good (e.g. asking what's up / how they are) — once, not a form.")
        lines.append(
            "  • Never invent human activities or experiences (eating, drinking coffee, sleeping, sitting somewhere, "
            "going out). Warm and natural, but truthful."
        )
    if g.time_of_day:
        tw = _TIME_WORDS[g.time_of_day]
        if g.said_time_greeting:
            lines.append(f"  • They said good {g.said_time_greeting}; it's {tw} for them. Return the greeting naturally.")
        else:
            lines.append(f"  • It's {tw} for them. You MAY weave that in naturally if it fits — don't force it, never state the exact time.")
    if g.topic_snippet and not g.has_followup:
        lines.append(
            f"  • Returning context: earlier they said \"{g.topic_snippet}\". If it's genuinely relevant now, you may "
            "naturally ask about it (e.g. how it went / if they're ready). If not relevant, ignore it."
        )
    if g.already_greeted:
        lines.append("  • The conversation is already going — don't restart it; continue naturally from where you are.")
    lines.append("  • Never: 'How can I assist you?', 'How may I help you today?', 'Welcome to Zara', 'Thank you for greeting me'.")
    if strategy.warmth <= 1:
        lines.append("  • Emojis: none or one.")
    else:
        lines.append("  • Emojis: at most one or two that fit — never a string of them.")
    lines.append(f"  • {_GREETING_MODE_STYLE.get(strategy.mode, _GREETING_MODE_STYLE['fast'])}")
    if strategy.care_mode:
        lines.append("  • Zara Care: a little warmer and more present; affection only at the level they've set.")
    return lines


def build_strategy_block(strategy: ResponseStrategy) -> str:
    """Per-turn guidance block for the system prompt (internal — the model must not mention it)."""
    e = strategy.emotion
    lines = ["## THIS TURN — RESPONSE STRATEGY (internal guidance; never mention it)"]
    lines.append(f"- What they're doing: {_INTENT_GUIDE.get(strategy.intent, _INTENT_GUIDE['task'])}")

    if strategy.greeting.is_greeting:
        lines.extend(_greeting_lines(strategy))

    if e.emotion != "neutral":
        certainty = "clear" if e.confidence >= 0.75 else "possible"
        lines.append(f"- Emotional read ({certainty}, intensity {e.intensity}): {_EMOTION_GUIDE.get(e.emotion, '')}")
        if e.confidence < 0.75 and not e.crisis:
            lines.append("  The signal isn't certain — use tentative words ('seems like…'), never tell them how they feel.")
    elif e.playful:
        lines.append("- Mood: light-hearted/playful. A bit of humor is fine.")
    else:
        lines.append("- Emotional read: no clear emotion — don't assume one.")

    if strategy.emotional_thread and strategy.emotional_thread != "neutral":
        lines.append(
            f"- Continuity: earlier in this conversation they seemed {strategy.emotional_thread}. "
            "If it fits naturally, keep that in mind or gently check in — don't reset the mood."
        )

    if strategy.vague_problem:
        lines.append(
            "- The problem description is very short/vague. Don't assume the exact scenario or invent details — "
            "ask ONE focused clarifying question (e.g. what exactly happens / the exact error), optionally mentioning the 2 most common causes."
        )

    lines.append(f"- Reply size: {_DEPTH_GUIDE[strategy.depth]}")
    lines.append(f"- Tone: {_TONE_GUIDE.get(strategy.tone, 'natural')}. Warmth {_WARMTH_GUIDE[strategy.warmth]}")

    if strategy.address_term and strategy.warmth >= 2:
        lines.append(f"- They use \"{strategy.address_term}\" — you may use it once, naturally (not every sentence).")
    elif strategy.warmth <= 1:
        lines.append("- Don't use slang or pet names they haven't used.")

    if strategy.avoid_openers:
        quoted = ", ".join(f'"{o}"' for o in strategy.avoid_openers)
        lines.append(f"- Vary your wording: do NOT open the same way as your recent replies ({quoted}).")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# DETERMINISTIC SAFETY POST-CHECKS
# ─────────────────────────────────────────────────────────────────────────────

_DEPENDENCY_SENTENCE_RE = re.compile(
    r"[^.!?\n]*\b(?:you only need me|you don'?t need anyone else|i'?m all you need|don'?t talk to anyone else|"
    r"promise (?:me )?you'?ll never leave|never leave me|if you leave(?: me)?,? i'?ll be (?:sad|hurt|lonely)|"
    r"only i understand you|nobody else understands you)\b[^.!?\n]*[.!?]?",
    re.IGNORECASE,
)

_HELPLINE_RE = re.compile(r"14416|112|helpline|crisis line|emergency|tele-?manas|988|hotline", re.IGNORECASE)

_CRISIS_FOOTER = {
    "Tanglish": "Nee thaniya idha face panna vendam — ippove unakku nambikkaiyana oruthar kitta pesu, illa Tele-MANAS 14416 (free, 24x7) call pannu. Emergency-na 112. 💙",
    "Tamil": "நீ இதைத் தனியாக சமாளிக்க வேண்டாம் — இப்போதே நம்பிக்கையான ஒருவரிடம் பேசு, அல்லது Tele-MANAS 14416 (இலவசம், 24x7) அழை. அவசரம் என்றால் 112. 💙",
    "Hinglish": "Tumhe ye akele face nahi karna — abhi kisi bharosemand insaan se baat karo, ya Tele-MANAS 14416 (free, 24x7) call karo. Emergency ho to 112. 💙",
    "Hindi": "आपको यह अकेले नहीं झेलना है — अभी किसी भरोसेमंद इंसान से बात करें, या Tele-MANAS 14416 (मुफ़्त, 24x7) पर कॉल करें। आपात स्थिति में 112। 💙",
    "English": "You don't have to face this alone — please reach out right now to someone you trust, or call Tele-MANAS 14416 (free, 24x7, India). If you're in immediate danger, call 112 or your local emergency number. 💙",
}


def apply_safety_checks(text: str, strategy: Optional[ResponseStrategy], language: str) -> Tuple[str, List[str]]:
    """
    Deterministic guardrails (no LLM):
      - remove possessive / dependency-building sentences (any mode, mandatory in Care)
      - guarantee crisis resources are present when a crisis signal was detected
    Returns (text, list_of_applied_fixes).
    """
    fixes: List[str] = []
    cleaned = _DEPENDENCY_SENTENCE_RE.sub("", text)
    if cleaned != text:
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned).strip()
        if cleaned:
            text = cleaned
            fixes.append("removed_dependency_language")

    if strategy and strategy.emotion.crisis and not _HELPLINE_RE.search(text):
        footer = _CRISIS_FOOTER.get(language, _CRISIS_FOOTER["English"])
        text = f"{text.rstrip()}\n\n{footer}"
        fixes.append("added_crisis_resources")
    return text, fixes
