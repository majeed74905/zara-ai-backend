"""
Language Detection Module for Zara AI
────────────────────────────────────────
Phase 1: Detects user input language and returns a standardized language code.
Phase 2: Handles mixed-language inputs (Tanglish, Hinglish) gracefully.

Returns a human-readable language name that can be embedded directly into
system prompts to force model output in the correct language.
"""

import logging
import re

logger = logging.getLogger(__name__)

# Map langdetect codes → human-readable names passed into prompts
LANGUAGE_MAP = {
    "en": "English",
    "ta": "Tamil",
    "hi": "Hindi",
    "ar": "Arabic",
    "ml": "Malayalam",
    "te": "Telugu",
    "kn": "Kannada",
    "bn": "Bengali",
    "ur": "Urdu",
    "fr": "French",
    "de": "German",
    "es": "Spanish",
    "pt": "Portuguese",
    "zh-cn": "Chinese (Simplified)",
    "zh-tw": "Chinese (Traditional)",
    "ja": "Japanese",
    "ko": "Korean",
    "ru": "Russian",
    "it": "Italian",
    "tr": "Turkish",
}

# Patterns to detect Tanglish (Tamil written in Roman/Latin characters)
TANGLISH_KEYWORDS = [
    r"\b(nalla|nanbaa|nanba|machi|machan|da|pa|bro|akka|anna|enna|innaiku|epdi|eppadi|eppo|sollu|vanakam|super|tambi|atha|ille|illai|irukka|iruku|irukku|irukinga|irukkinga|vibe|dei|yenna|sollunga|pannunga|enga|anga|inga|theriyuma|theriyadu|theriyale)\b",
]

# Patterns to detect Hinglish (Hindi written in Roman/Latin characters)
HINGLISH_KEYWORDS = [
    r"\b(kya|hai|hain|mera|tera|bhai|yaar|kaise|kaisa|theek|thik|bilkul|abhi|sirf|matlab|samajh|bol|suno|dekho|bata|karo|kyun|kab|kuch|nahi|nahin|bahut|accha|acha|arre|bolo|hoga|hogi|kaafi|seedha|toh|toh)\b",
]


def _check_mixed_language(text: str) -> str | None:
    """
    Checks if text contains regional transliteration patterns.
    Returns 'Tanglish', 'Hinglish', or None.
    """
    text_lower = text.lower()
    for pattern in TANGLISH_KEYWORDS:
        if re.search(pattern, text_lower):
            return "Tanglish"
    for pattern in HINGLISH_KEYWORDS:
        if re.search(pattern, text_lower):
            return "Hinglish"
    return None


def is_language_consistent(text: str, target_language: str) -> bool:
    """
    Checks if the given text is consistent with the target language.
    For mixed languages (Tanglish/Hinglish), it ensures presence of regional patterns.
    For pure languages, it uses langdetect.
    """
    if not text or not target_language:
        return True
    
    # 1. Check for mixed languages
    if target_language == "Tanglish":
        # Ensure it's not JUST pure English without any Tamil transliteration
        return _check_mixed_language(text) == "Tanglish"
    if target_language == "Hinglish":
        return _check_mixed_language(text) == "Hinglish"
    
    # 2. Check for pure languages
    try:
        from langdetect import detect
        detected = detect(text)
        
        # Mapping for langdetect codes to compare against our human-readable names
        reverse_map = {v: k for k, v in LANGUAGE_MAP.items()}
        target_code = reverse_map.get(target_language)
        
        if not target_code:
            return True # Unknown language name, skip check
            
        # Allow some drift for very short responses
        if len(text.split()) < 5:
            return True
            
        # For English, allow anything (it's the global fallback)
        if target_code == "en":
            return True
            
        return detected == target_code
    except:
        return True # Default to True if detection fails

def detect_language(text: str) -> str:
    """
    Detects the language of the input text.

    Priority:
    1. Check for Tanglish / Hinglish mixed-language patterns first.
    2. Delegate to langdetect for non-mixed inputs.
    3. Fallback to English if detection fails.

    Returns a human-readable language name (e.g., "Tamil", "English", "Tanglish").
    """
    if not text or not text.strip():
        return "English"

    # Step 1: Check for mixed-language first (highest priority)
    mixed = _check_mixed_language(text)
    if mixed:
        logger.info(f"Mixed language detected: {mixed}")
        return mixed

    # Step 2: Use langdetect
    try:
        from langdetect import detect, DetectorFactory
        DetectorFactory.seed = 42  # For deterministic results
        lang_code = detect(text)
        human_name = LANGUAGE_MAP.get(lang_code, "English")
        logger.info(f"Language detected: {lang_code} → {human_name}")
        return human_name
    except Exception as e:
        logger.warning(f"Language detection failed: {e}. Defaulting to English.")
        return "English"
