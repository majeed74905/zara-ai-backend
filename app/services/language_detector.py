"""
Language Detection Engine for Zara AI
────────────────────────────────────────
Deterministic, conversation-aware language detection. No LLM calls.

Pipeline (per message):
  1. Explicit switch requests ("in English", "tamil la sollu", "Language: Hindi").
  2. Technical-content stripping (code, SQL, URLs, paths, stack traces, identifiers)
     so a pasted error or query never decides the conversation language.
  3. Unicode script analysis (Tamil, Devanagari, Malayalam, Kannada, Telugu, ...).
  4. Transliteration scoring for Latin-script Indian languages
     (Tanglish, Hinglish, Manglish, Tenglish, Kanglish) using weighted lexicons
     and morphological suffix patterns — Latin script is NOT assumed to be English.
  5. English evidence scoring (function words), so "help me" is English, not Hinglish.
  6. langdetect only for longer Latin text with no English/Indic signal (French, Spanish...).

Conversation layer:
  - A message with a decisive signal sets the language (users can switch any time).
  - Neutral/short messages ("ok", "hmm", "👍", pure code) inherit the most recent
    decisive language from the user's previous turns.
  - With no signal at all, we fall back to English but mark the result uncertain so
    the prompt tells the model to mirror the user instead of forcing English.

Public API (backward compatible):
  detect_language(text, history) -> str
  detect_language_profile(text, history) -> LanguageProfile
  analyze_text(text) -> LanguageProfile            (single message, no context)
  is_language_consistent(text, target_language) -> bool
  strip_technical_content(text) -> str
"""

import logging
import re
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# Map langdetect codes → human-readable names passed into prompts
LANGUAGE_MAP = {
    "en": "English",
    "ta": "Tamil",
    "hi": "Hindi",
    "mr": "Marathi",
    "ne": "Nepali",
    "ar": "Arabic",
    "fa": "Persian",
    "ml": "Malayalam",
    "te": "Telugu",
    "kn": "Kannada",
    "bn": "Bengali",
    "gu": "Gujarati",
    "pa": "Punjabi",
    "ur": "Urdu",
    "fr": "French",
    "de": "German",
    "es": "Spanish",
    "pt": "Portuguese",
    "nl": "Dutch",
    "id": "Indonesian",
    "zh-cn": "Chinese (Simplified)",
    "zh-tw": "Chinese (Traditional)",
    "ja": "Japanese",
    "ko": "Korean",
    "ru": "Russian",
    "uk": "Ukrainian",
    "it": "Italian",
    "tr": "Turkish",
    "pl": "Polish",
    "vi": "Vietnamese",
    "th": "Thai",
}

# Transliterated (Latin-script) variants and the native language they belong to
TRANSLITERATED_BASE = {
    "Tanglish": "Tamil",
    "Hinglish": "Hindi",
    "Manglish": "Malayalam",
    "Tenglish": "Telugu",
    "Kanglish": "Kannada",
}

NATIVE_TO_TRANSLITERATED = {v: k for k, v in TRANSLITERATED_BASE.items()}


@dataclass
class LanguageProfile:
    """Result of language analysis for one message (or a conversation)."""
    language: str = "English"        # Name used in prompts: "Tanglish", "Tamil", "English", ...
    confidence: float = 0.0          # 0.0 – 1.0
    script: str = "none"             # "latin", "tamil", "devanagari", ... or "none"
    transliterated: bool = False     # Indian language written in Latin script
    code_mixed: bool = False         # Regional language mixed with English words
    base_language: str = "English"   # "Tamil" for both Tamil and Tanglish
    source: str = "default"          # explicit | script | lexicon | english | langdetect | context | default
    decisive: bool = False           # Did this message carry a real language signal?

    @property
    def uncertain(self) -> bool:
        return self.source == "default" or self.confidence < 0.5

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["uncertain"] = self.uncertain
        return d


# ─────────────────────────────────────────────────────────────────────────────
# EXPLICIT LANGUAGE SWITCH REQUESTS
# ─────────────────────────────────────────────────────────────────────────────

_EXPLICIT_SWITCH_PATTERNS: List[Tuple[str, "re.Pattern[str]"]] = [
    ("Tanglish", re.compile(r"(?i)\b(?:in tanglish|tanglish (?:la|le|il|mein|me|please)|tanglish-la|switch to tanglish|(?:reply|talk|speak|explain(?: it| this)?|answer) in tanglish)\b")),
    ("Hinglish", re.compile(r"(?i)\b(?:in hinglish|hinglish (?:me|mein|please)|switch to hinglish|(?:reply|talk|speak|explain(?: it| this)?|answer) in hinglish)\b")),
    ("English", re.compile(r"(?i)\b(?:in english|english (?:la|le|il|mein|me|please)|english-la|switch to english|(?:reply|talk|speak|explain(?: it| this)?|answer|give(?: it| this)?) in english|only english)\b")),
    ("Tamil", re.compile(r"(?i)\b(?:in tamil|tamil (?:la|le|il|please)|tamil-la|tamilil|thamizh ?la|switch to tamil|(?:reply|talk|speak|explain(?: it| this)?|answer) in tamil)\b")),
    ("Hindi", re.compile(r"(?i)\b(?:in hindi|hindi (?:me|mein|please)|switch to hindi|(?:reply|talk|speak|explain(?: it| this)?|answer) in hindi)\b")),
    ("Malayalam", re.compile(r"(?i)\b(?:in malayalam|malayalam(?:thil)? please|switch to malayalam|(?:reply|talk|speak|explain(?: it| this)?|answer) in malayalam)\b")),
    ("Kannada", re.compile(r"(?i)\b(?:in kannada|kannada(?:dalli)? please|switch to kannada|(?:reply|talk|speak|explain(?: it| this)?|answer) in kannada)\b")),
    ("Telugu", re.compile(r"(?i)\b(?:in telugu|telugu(?:lo)? please|switch to telugu|(?:reply|talk|speak|explain(?: it| this)?|answer) in telugu)\b")),
]

# "Language: Tamil" style fields used by structured modules (exam generator, etc.)
_LANGUAGE_FIELD_RE = re.compile(r"(?im)^\s*(?:output\s+)?language\s*[:=]\s*([A-Za-z]+)\s*$")
_FIELD_LANGUAGES = {
    "english": "English", "tamil": "Tamil", "tanglish": "Tanglish", "hindi": "Hindi",
    "hinglish": "Hinglish", "malayalam": "Malayalam", "kannada": "Kannada", "telugu": "Telugu",
    "bengali": "Bengali", "marathi": "Marathi", "urdu": "Urdu", "arabic": "Arabic",
    "french": "French", "spanish": "Spanish", "german": "German",
}


def _check_explicit_switch(text: str) -> Optional[str]:
    """Check if the user explicitly requested a response language."""
    for lang, pattern in _EXPLICIT_SWITCH_PATTERNS:
        if pattern.search(text):
            return lang
    field = _LANGUAGE_FIELD_RE.search(text)
    if field:
        return _FIELD_LANGUAGES.get(field.group(1).lower())
    return None


# ─────────────────────────────────────────────────────────────────────────────
# TECHNICAL CONTENT STRIPPING
# ─────────────────────────────────────────────────────────────────────────────

_STRIP_PATTERNS = [
    re.compile(r"```[\s\S]*?```"),                                  # fenced code
    re.compile(r"```[\s\S]*$"),                                     # unterminated fence
    re.compile(r"`[^`\n]*`"),                                       # inline code
    re.compile(r"https?://\S+|www\.\S+"),                           # URLs
    re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),                    # emails
    re.compile(r"(?im)^\s*(?:SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|WITH)\b.*$"),  # SQL lines
    re.compile(r"(?i)\b(?:SELECT\s+.+?\s+FROM|INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM)\b[^.?!\n]*;?"),
    re.compile(r"(?m)^\s*(?:File \".*\", line \d+.*|at [\w$.<>]+ \(.*\)|Traceback \(most recent call last\):)\s*$"),
    re.compile(r"(?m)^\s*[{\[][\s\S]*?[}\]]\s*$"),                  # JSON-ish lines
    re.compile(r"(?:[A-Za-z]:)?(?:[\w.-]+[\\/])+[\w.-]+"),          # file paths
    re.compile(r"\b[\w-]+\.(?:py|js|jsx|ts|tsx|java|go|rb|php|cs|cpp|c|h|json|yml|yaml|toml|sql|md|txt|env|css|html|sh)\b"),
    re.compile(r"\b\w+_\w+\b"),                                     # snake_case identifiers
    re.compile(r"\b[a-z]+(?:[A-Z][a-z0-9]+)+\b"),                   # camelCase identifiers
    re.compile(r"\b(?:[A-Z][a-z0-9]+){2,}\b"),                      # PascalCase / TypeError
    re.compile(r"[<>{}()\[\];=*#|\\^~$]+"),                         # code punctuation
    re.compile(r"\b\d+(?:[.,:]\d+)*\b"),                            # numbers / versions / times
]


def strip_technical_content(text: str) -> str:
    """Remove code, SQL, URLs, paths and identifiers so only natural language remains."""
    if not text:
        return ""
    cleaned = text
    for pattern in _STRIP_PATTERNS:
        cleaned = pattern.sub(" ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


# ─────────────────────────────────────────────────────────────────────────────
# UNICODE SCRIPTS
# ─────────────────────────────────────────────────────────────────────────────

# (script name, language, regex of letters)
_SCRIPTS: List[Tuple[str, str, "re.Pattern[str]"]] = [
    ("tamil", "Tamil", re.compile(r"[஀-௿]")),
    ("devanagari", "Hindi", re.compile(r"[ऀ-ॿ]")),
    ("malayalam", "Malayalam", re.compile(r"[ഀ-ൿ]")),
    ("kannada", "Kannada", re.compile(r"[ಀ-೿]")),
    ("telugu", "Telugu", re.compile(r"[ఀ-౿]")),
    ("bengali", "Bengali", re.compile(r"[ঀ-৿]")),
    ("gujarati", "Gujarati", re.compile(r"[઀-૿]")),
    ("gurmukhi", "Punjabi", re.compile(r"[਀-੿]")),
    ("odia", "Odia", re.compile(r"[଀-୿]")),
    ("arabic", "Arabic", re.compile(r"[؀-ۿݐ-ݿ]")),
    ("hebrew", "Hebrew", re.compile(r"[֐-׿]")),
    ("cyrillic", "Russian", re.compile(r"[Ѐ-ӿ]")),
    ("greek", "Greek", re.compile(r"[Ͱ-Ͽ]")),
    ("thai", "Thai", re.compile(r"[฀-๿]")),
    ("hangul", "Korean", re.compile(r"[가-힯ᄀ-ᇿ]")),
    ("kana", "Japanese", re.compile(r"[぀-ヿ]")),
    ("han", "Chinese (Simplified)", re.compile(r"[一-鿿]")),
]
_LATIN_RE = re.compile(r"[A-Za-zÀ-ɏ]")
_URDU_ONLY_RE = re.compile(r"[ٹڈڑںےۓھ]")
_INDIC_SCRIPTS = {"tamil", "devanagari", "malayalam", "kannada", "telugu", "bengali", "gujarati", "gurmukhi", "odia"}

SCRIPT_OF_LANGUAGE = {lang: script for script, lang, _ in _SCRIPTS}
SCRIPT_OF_LANGUAGE.update({"Urdu": "arabic", "Marathi": "devanagari", "Nepali": "devanagari"})


def _script_counts(text: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for script, _, pattern in _SCRIPTS:
        n = len(pattern.findall(text))
        if n:
            counts[script] = n
    latin = len(_LATIN_RE.findall(text))
    if latin:
        counts["latin"] = latin
    return counts


# ─────────────────────────────────────────────────────────────────────────────
# TRANSLITERATION LEXICONS (weights: 2.0 distinctive, 1.0 likely, 0.4 ambiguous particle)
# ─────────────────────────────────────────────────────────────────────────────

def _lex(strong: str, medium: str = "", weak: str = "") -> Dict[str, float]:
    table: Dict[str, float] = {}
    for words, weight in ((weak, 0.4), (medium, 1.0), (strong, 2.0)):
        for w in words.split():
            table[w] = weight
    return table


_LEXICONS: Dict[str, Dict[str, float]] = {
    "Tanglish": _lex(
        strong=(
            "eppadi epdi yeppadi epdiyo irukka iruka irukken irukkeen irukeen irukkinga irukeenga irukeengala "
            "irukku iruku irukkudhu irukudhu irundhuchu irundha enna yenna ennadhu enaku enakku unaku unakku "
            "namma naanga neenga ungalukku idhu idha idhula idhuku adhu adha adhula edhu edhuku yen yenda "
            "panra panren panrom panringa panreenga panradhu pannu pannunga pannanum pannala pannitu pannalaam "
            "pannitten panniten pannirukken sollu sollunga solren solla sonna sollala mudiyala mudiyum "
            "theriyala theriyum theriyuma theriyadhu theriyudhu puriyala puriyudhu puriyuma puriyave "
            "aagala aagudhu aaguthu aagum aaguma aachu aachi aayiduchu aagiduchu agala aguthu agudhu "
            "varala varudhu varuthu vandhuchu kedaikala kedaikkala kedaikudhu saptiya saaptiya saptingala saapten "
            "saptachu seri sari seringa nalla nallaa nallarukken romba rombha konjam kammi macha machan machi "
            "machaan nanba nanbaa nanban dei vaada poda vaanga ponga kelu kelunga paaru paarunga ippo ippa "
            "appo appadiye inga anga enga innaiku inniki naalaiku nethu thaan dhaan dhan maadhiri madhiri "
            "mokka semma sema kalakkal thala thalaiva vanakkam vanakam aana aanaa illa illai illaya illana "
            "kudunga kudu podunga podu vachu vechu pola kooda mattum solluda epovum eppovum"
        ),
        medium="anna akka thambi thangachi mama mame mams avan aval avanga ivan maah chellam kutty",
        weak="da di pa ma la le nu ah va po na",
    ),
    "Hinglish": _lex(
        strong=(
            "kya kyaa kyun kyon kaise kaisa kaisi kaha kahan kab kaun kitna kitne mujhe mujhko tujhe humko "
            "hamara hamare tumhara tumhare aapka aapke apna apne mera meri mere tera teri tere nahi nahin "
            "nai bhai bhaiya yaar yar accha acha achha theek thik bilkul abhi sirf matlab samajh samjha "
            "samjhao samjho samajhna batao bata bataiye bolo suno dekho chalo karna karne karta karti karte "
            "karo kariye kijiye kiya kiye hota hoti hote hoga hogi raha rahi rahe gaya gayi gaye chahiye "
            "sakta sakti sakte milta milega dena lena kuch bahut bohot zyada jyada thoda aur lekin kyunki "
            "agar magar haan hanji arre arey wala wali wale yeh woh isko usko isme usme hum tum aap hain "
            "hoon hun bhi"
        ),
        medium="hai ho mein kar ke liye wo ye",
        weak="ka ki ko se pe par na toh to",
    ),
    "Manglish": _lex(
        strong=(
            "njan ningal ningalku entha enthu enthaa sugamano sukhamano cheyyam cheyyanam cheythu cheyyu "
            "ariyilla ariyam ariyo evide aanu alle allo illallo kazhicho kazhichu chetta chettan chechi mone "
            "mole pinne kollam kollaam venda vendi undo poyi vannu ente nte ninte parayu paranju "
            "manassilayi manassilayilla"
        ),
        medium="sheri und",
    ),
    "Tenglish": _lex(
        strong=(
            "ela unnavu unnava unnaru unnav bagunnava bagunnara baagunnaa emi enti endi cheppu cheppandi "
            "chestunna chestunnav chesava chesanu cheyali cheyyi ledu kaadu avunu nenu nuvvu meeru "
            "kavali ekkada enduku vachindi ayindi avvaledu raledu telusu teliyadu chala baga ippudu "
            "akkada ikkada mari"
        ),
        medium="raa ra",
    ),
    "Kanglish": _lex(
        strong=(
            "hegiddiya hegiddira hegidira hegide yenu yenri maadi maadu maadbeku gottilla gottu gotthu beku "
            "beda naanu neenu nimma nanna banni hogi aaytu aagilla swalpa sakkath yaake elli illi alli "
            "channagide chennagide oota maadidya"
        ),
        medium="guru maga",
    ),
}

# Morphological patterns for Latin-script Tamil and Hindi (catch words not in the lexicon)
_SUFFIX_PATTERNS: Dict[str, List[Tuple["re.Pattern[str]", float]]] = {
    "Tanglish": [
        (re.compile(r"^\w{2,}(?:aagala|agala|aagudhu|aaguthu|aayiduchu|aachu)$"), 2.0),
        (re.compile(r"^\w{3,}(?:udhu|uthu|iduchu|ichu)$"), 1.5),
        (re.compile(r"^\w{3,}(?:unga|ringa|reenga|eenga|kkanum|kanum|lama|laama)$"), 1.5),
        (re.compile(r"^[a-z0-9]+-(?:la|le|ku|kku|oda|ah)$"), 1.0),   # database-la, server-ku
    ],
    "Hinglish": [
        (re.compile(r"^[a-z0-9]+-(?:mein|wala|wali|wale)$"), 1.0),
    ],
}

_ENGLISH_WORDS = set("""
i i'm im i've i'll i'd you you're your yours we we're our they they're their he she it it's its is are was were
be been being am do does did don't doesn't didn't can can't cannot could couldn't would wouldn't should shouldn't will won't
the a an and or but if then so because of to in on at for with from by about into over under this that these
those what what's why how how's when where which who whom whose my me mine please thanks thank hello hey yes
not have has had get got want need know think help explain tell give make let let's working today now just
really very much more some any there here all also only still than as out up down again tomorrow yesterday
something anything everything nothing someone anyone could're sure maybe okay
""".split())

_WORD_RE = re.compile(r"[a-z][a-z'\-]*")

# Words that carry no language signal on their own (universal loanwords / chat fillers)
_NEUTRAL_WORDS = set("""
ok okay k hmm hmmm hm yes no ya yeah yep nope bro sis dude lol haha hehe pls plz thx ty hi hii hiii hello hey
""".split())


@dataclass
class _LatinScores:
    regional: Dict[str, float]
    strong_hits: Dict[str, int]
    english: float
    words: int
    content_words: int


def _score_latin(text: str) -> _LatinScores:
    tokens = _WORD_RE.findall(text.lower())
    regional = {lang: 0.0 for lang in _LEXICONS}
    strong_hits = {lang: 0 for lang in _LEXICONS}
    english = 0.0
    content = 0

    for tok in tokens:
        bare = tok.strip("'-")
        if not bare:
            continue
        if bare in _NEUTRAL_WORDS:
            continue
        content += 1
        if bare in _ENGLISH_WORDS:
            english += 1.0
        for lang, table in _LEXICONS.items():
            w = table.get(bare)
            if w is None:
                for pattern, pw in _SUFFIX_PATTERNS.get(lang, []):
                    if pattern.match(bare):
                        w = pw
                        break
            if w:
                regional[lang] += w
                if w >= 1.5:
                    strong_hits[lang] += 1

    # Ambiguous particles (weight 0.4) only count when the language already has real evidence
    for lang in regional:
        if strong_hits[lang] == 0 and regional[lang] < 1.0:
            regional[lang] = 0.0

    return _LatinScores(regional, strong_hits, english, len(tokens), content)


def _langdetect_latin(text: str) -> Optional[Tuple[str, float]]:
    """Statistical detection for longer Latin text with no English/Indic evidence."""
    try:
        from langdetect import DetectorFactory, detect_langs  # type: ignore[import-untyped]
        DetectorFactory.seed = 42
        candidates = detect_langs(text)
        if not candidates:
            return None
        top = candidates[0]
        name = LANGUAGE_MAP.get(top.lang)
        if name and top.prob >= 0.85:
            return name, float(top.prob)
    except Exception as e:
        logger.debug(f"langdetect unavailable/failed: {e}")
    return None


# ─────────────────────────────────────────────────────────────────────────────
# SINGLE-MESSAGE ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

def analyze_text(text: str) -> LanguageProfile:
    """Analyze one message without conversation context."""
    if not text or not text.strip():
        return LanguageProfile()

    explicit = _check_explicit_switch(text)
    if explicit:
        return LanguageProfile(
            language=explicit,
            confidence=0.97,
            script=SCRIPT_OF_LANGUAGE.get(TRANSLITERATED_BASE.get(explicit, explicit), "latin"),
            transliterated=explicit in TRANSLITERATED_BASE,
            base_language=TRANSLITERATED_BASE.get(explicit, explicit),
            source="explicit",
            decisive=True,
        )

    natural = strip_technical_content(text)
    if not natural:
        return LanguageProfile()  # pure code / URL / numbers → no signal

    counts = _script_counts(natural)
    latin_letters = counts.get("latin", 0)
    native = {k: v for k, v in counts.items() if k != "latin"}

    # ── Native (non-Latin) scripts ───────────────────────────────────────────
    if native:
        script, letters = max(native.items(), key=lambda kv: kv[1])
        language = next(lang for s, lang, _ in _SCRIPTS if s == script)
        if script == "arabic" and _URDU_ONLY_RE.search(natural):
            language = "Urdu"
        elif script == "han" and "kana" in native:
            script, language = "kana", "Japanese"
        # Indic script is a decisive signal even when mixed with English tech terms
        is_indic = script in _INDIC_SCRIPTS
        if is_indic or letters >= latin_letters * 0.5:
            code_mixed = latin_letters > 0
            confidence = 0.97 if not code_mixed else 0.92
            return LanguageProfile(
                language=language,
                confidence=confidence,
                script=script,
                transliterated=False,
                code_mixed=code_mixed,
                base_language=language,
                source="script",
                decisive=True,
            )

    if not latin_letters:
        return LanguageProfile()  # emoji / punctuation only

    # ── Latin script: transliteration vs English vs other ────────────────────
    scores = _score_latin(natural)
    best_lang, best = max(scores.regional.items(), key=lambda kv: kv[1])
    strong = scores.strong_hits[best_lang]
    eng = scores.english

    if best >= 2.0 and (best >= eng * 0.6 or strong >= 2):
        confidence = min(0.97, 0.6 + 0.08 * best - 0.02 * eng)
        return LanguageProfile(
            language=best_lang,
            confidence=round(max(confidence, 0.6), 2),
            script="latin",
            transliterated=True,
            code_mixed=eng > 0 or scores.content_words > best,
            base_language=TRANSLITERATED_BASE[best_lang],
            source="lexicon",
            decisive=True,
        )

    if best >= 1.0 and eng < 1.0:
        # Weak regional signal (e.g. "ok da", "anna help") — usable, but let context confirm
        return LanguageProfile(
            language=best_lang,
            confidence=0.45,
            script="latin",
            transliterated=True,
            code_mixed=True,
            base_language=TRANSLITERATED_BASE[best_lang],
            source="lexicon",
            decisive=False,
        )

    if eng >= 2.0 or (eng >= 1.0 and scores.content_words >= 4):
        return LanguageProfile(
            language="English",
            confidence=round(min(0.95, 0.55 + 0.1 * eng), 2),
            script="latin",
            base_language="English",
            source="english",
            decisive=True,
        )

    if scores.content_words >= 3 and eng < 1.0 and best < 1.0:
        guess = _langdetect_latin(natural)
        if guess and guess[0] != "English":
            name, prob = guess
            return LanguageProfile(
                language=name,
                confidence=round(min(prob, 0.9), 2),
                script="latin",
                base_language=name,
                source="langdetect",
                decisive=True,
            )

    # Short English-looking text ("hello", "thanks bro", "ok") — weak English, not decisive
    return LanguageProfile(
        language="English",
        confidence=0.4 if eng else 0.3,
        script="latin",
        base_language="English",
        source="english" if eng else "default",
        decisive=False,
    )


# ─────────────────────────────────────────────────────────────────────────────
# CONVERSATION-AWARE DETECTION
# ─────────────────────────────────────────────────────────────────────────────

def _recent_user_texts(history: Optional[List[Dict[str, str]]], limit: int = 6) -> List[str]:
    if not history:
        return []
    texts = [
        str(msg.get("content", "")) for msg in reversed(history)
        if msg.get("role") == "user" and msg.get("content")
    ]
    return texts[:limit]


def detect_language_profile(
    text: str,
    history: Optional[List[Dict[str, str]]] = None,
) -> LanguageProfile:
    """
    Conversation-aware detection. The current message wins when it carries a decisive
    signal; otherwise the most recent decisive user turn (or explicit request) is inherited.
    """
    current = analyze_text(text or "")
    if current.decisive:
        return current

    for past_text in _recent_user_texts(history):
        past = analyze_text(past_text)
        if not past.decisive:
            continue
        # A weak signal in the current turn pointing elsewhere does not override context
        inherited = LanguageProfile(**{**asdict(past)})
        inherited.source = "context"
        inherited.decisive = False
        inherited.confidence = round(max(0.55, past.confidence * 0.9), 2)
        if current.language == past.language and current.source == "lexicon":
            inherited.confidence = round(min(0.95, inherited.confidence + 0.05), 2)
        return inherited

    if current.source == "lexicon":
        return current  # weak regional signal, nothing better available
    return LanguageProfile(
        language="English",
        confidence=current.confidence if current.language == "English" else 0.3,
        script=current.script,
        base_language="English",
        source=current.source if current.source != "default" else "default",
        decisive=False,
    )


def detect_language(
    text: str,
    history: Optional[List[Dict[str, str]]] = None,
) -> str:
    """Backward-compatible wrapper returning just the language name."""
    return detect_language_profile(text, history).language


# ─────────────────────────────────────────────────────────────────────────────
# RESPONSE VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

def _native_script_ratio(text: str, script: str) -> float:
    counts = _script_counts(text)
    total = sum(counts.values())
    if not total:
        return 0.0
    return counts.get(script, 0) / total


def is_language_consistent(text: str, target_language: str) -> bool:
    """
    Lightweight check that a generated response matches the target language.
    Conservative: only flags clear drift. Code, SQL, URLs and identifiers are ignored.
    """
    if not text or not target_language:
        return True

    natural = strip_technical_content(text)
    words = natural.split()
    if len(words) < 5:
        return True

    base = TRANSLITERATED_BASE.get(target_language, target_language)
    target_script = SCRIPT_OF_LANGUAGE.get(base)

    # Transliterated targets (Tanglish, Hinglish, ...)
    if target_language in TRANSLITERATED_BASE:
        if target_script and _native_script_ratio(natural, target_script) >= 0.25:
            return True  # native script of the same language — not a drift
        scores = _score_latin(natural)
        regional = scores.regional.get(target_language, 0.0)
        if len(words) < 15:
            return regional >= 1.0
        return regional >= 2.0

    # Native-script targets (Tamil, Hindi, Malayalam, ...): require a real share of that script
    if target_script and target_script != "latin":
        return _native_script_ratio(natural, target_script) >= 0.25

    # English target: flag only when the reply is predominantly another script
    # or clearly transliterated regional text.
    if target_language == "English":
        counts = _script_counts(natural)
        total = sum(counts.values()) or 1
        if counts.get("latin", 0) / total < 0.5:
            return False
        scores = _score_latin(natural)
        best = max(scores.regional.values())
        return not (best >= 4.0 and best > scores.english)

    # Other Latin languages: statistical check when possible
    guess = _langdetect_latin(natural)
    if guess is None:
        return True
    return guess[0] == target_language
