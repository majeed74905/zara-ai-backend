"""
Verification Test for Zara Language + Communication Style Matching Engine
Tests requirements 1 through 10 from the specification:
  - Mode + Language Test across Fast, Pro, Eco on:
    "Bro payment success aaguthu but database la status update aagala da"
  - Multi-turn Language Switch Test:
    Turn 1: "Bro idha Tanglish la explain pannunga."
    Turn 2: "Now explain the technical implementation in English."
    Turn 3: "Seri, ippo short ah sollu."
  - Communication Style & Emotion Profiling:
    casual, formal, technical, beginner, short/direct, detailed, friendly, frustrated, confused
  - Anti-Mimicry Directive Presence & Integrity
  - First-Class Tanglish Technical Directives
"""

import sys
sys.path.insert(0, ".")

from app.services.language_detector import detect_language, is_language_consistent
from app.services.zara_identity import (
    build_identity_prompt,
    detect_communication_style,
    detect_communication_profile,
    get_mode_personality,
)
from app.services.prompt_builder import build_system_prompt

PASS = 0
FAIL = 0

def check(name: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    if condition:
        print(f"  ✓ {name}")
        PASS += 1
    else:
        print(f"  ✗ {name} {detail}")
        FAIL += 1


def run_tests():
    print("=" * 80)
    print("ZARA LANGUAGE + COMMUNICATION MATCHING ENGINE — TEST SUITE")
    print("=" * 80)

    # ─────────────────────────────────────────────────────────────────────────
    # REQUIREMENT 8: MODE + LANGUAGE TEST (SAME MESSAGE ACROSS FAST, PRO, ECO)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n[TEST 1] Requirement 8: Mode + Language Test")
    print("Test input: 'Bro payment success aaguthu but database la status update aagala da'")
    print("-" * 80)

    test_msg = "Bro payment success aaguthu but database la status update aagala da"
    detected_lang = detect_language(test_msg)
    profile = detect_communication_profile(test_msg)

    check("Language detected as Tanglish", detected_lang == "Tanglish", f"got {detected_lang}")
    check("Style detected as casual", profile["primary_style"] == "casual", f"got {profile['primary_style']}")
    check("Technicality recognized", profile["technicality"] == "technical", f"got {profile['technicality']}")

    # Build prompts for Zara Fast, Zara Pro, Zara Eco
    fast_prompt = build_system_prompt("fast", detected_lang, comm_style=profile)
    pro_prompt = build_system_prompt("pro", detected_lang, comm_style=profile)
    eco_prompt = build_system_prompt("eco", detected_lang, comm_style=profile)

    # 1. Fast Mode Verification
    check("Fast prompt contains Conversational Zara personality", "MODE: ZARA FAST" in fast_prompt)
    check("Fast prompt contains Tanglish first-class instructions", "LANGUAGE: TANGLISH" in fast_prompt)
    check("Fast prompt has quick/conversational reasoning directive", "Lead with the answer" in fast_prompt)
    check("Fast prompt contains Anti-Mimicry protocol", "ANTI-MIMICRY PROTOCOL" in fast_prompt)

    # 2. Pro Mode Verification
    check("Pro prompt contains Expert Partner personality", "MODE: ZARA PRO" in pro_prompt)
    check("Pro prompt contains Tanglish first-class instructions", "LANGUAGE: TANGLISH" in pro_prompt)
    check("Pro prompt has trade-offs and deep reasoning directive", "Surface trade-offs, edge cases" in pro_prompt)
    check("Pro prompt contains Anti-Mimicry protocol", "ANTI-MIMICRY PROTOCOL" in pro_prompt)

    # 3. Eco Mode Verification
    check("Eco prompt contains Efficient Assistant personality", "MODE: ZARA ECO" in eco_prompt)
    check("Eco prompt contains Tanglish first-class instructions", "LANGUAGE: TANGLISH" in eco_prompt)
    check("Eco prompt has minimal-useful/high-density directive", "maximum utility with minimum tokens" in eco_prompt)
    check("Eco prompt contains Anti-Mimicry protocol", "ANTI-MIMICRY PROTOCOL" in eco_prompt)

    # Distinctness check
    check("Fast, Pro, Eco produce distinct prompt behavioral configurations",
          fast_prompt != pro_prompt and pro_prompt != eco_prompt and fast_prompt != eco_prompt)

    # ─────────────────────────────────────────────────────────────────────────
    # REQUIREMENT 9: MULTI-TURN LANGUAGE SWITCH TEST
    # ─────────────────────────────────────────────────────────────────────────
    print("\n[TEST 2] Requirement 9: Dynamic Multi-Turn Language Switch Test")
    print("-" * 80)

    # Turn 1: User asks in Tanglish
    turn1_user = "Bro idha Tanglish la explain pannunga."
    turn1_history = []
    lang_turn1 = detect_language(turn1_user, turn1_history)
    check("Turn 1 ('Bro idha Tanglish la explain pannunga.') -> Tanglish", lang_turn1 == "Tanglish", f"got {lang_turn1}")

    # Turn 2: User switches to English
    turn2_user = "Now explain the technical implementation in English."
    turn2_history = [
        {"role": "user", "content": turn1_user},
        {"role": "assistant", "content": "Sure, Tanglish la solren: Webhook payload verify pannanum..."}
    ]
    lang_turn2 = detect_language(turn2_user, turn2_history)
    check("Turn 2 ('Now explain the technical implementation in English.') -> English", lang_turn2 == "English", f"got {lang_turn2}")

    # Turn 3: User switches back to Tanglish and asks for short
    turn3_user = "Seri, ippo short ah sollu."
    turn3_history = turn2_history + [
        {"role": "user", "content": turn2_user},
        {"role": "assistant", "content": "Here is the technical implementation using transactional database locks..."}
    ]
    lang_turn3 = detect_language(turn3_user, turn3_history)
    profile_turn3 = detect_communication_profile(turn3_user, turn3_history)
    
    check("Turn 3 ('Seri, ippo short ah sollu.') -> Tanglish", lang_turn3 == "Tanglish", f"got {lang_turn3}")
    check("Turn 3 length preference recognized as short_direct", profile_turn3["length_pref"] == "short_direct", f"got {profile_turn3['length_pref']}")

    prompt_turn3 = build_system_prompt("fast", lang_turn3, comm_style=profile_turn3)
    check("Turn 3 prompt includes Short & Direct pacing directive", "SHORT & DIRECT" in prompt_turn3)
    check("Turn 3 prompt includes Tanglish language directive", "LANGUAGE: TANGLISH" in prompt_turn3)

    # ─────────────────────────────────────────────────────────────────────────
    # REQUIREMENT 2 & 4: COMMUNICATION STYLE & EMOTION PROFILING
    # ─────────────────────────────────────────────────────────────────────────
    print("\n[TEST 3] Communication Style & Emotion Profiling")
    print("-" * 80)

    style_scenarios = [
        # (text, expected_primary, expected_emotion, expected_length)
        ("dei idhu romba mokka ah iruku 😂", "casual", "frustrated", "normal"),
        ("I'm totally confused, what does a webhook even mean??", "beginner", "confused", "normal"),
        ("Thanks a lot bro! awesome explanation nandri", "casual", "friendly", "normal"),
        ("The webhook succeeds but the transaction isn't committed.", "technical", "neutral", "normal"),
        ("Dear Zara, could you please provide a formal assessment?", "formal", "neutral", "normal"),
        ("Bro idhu work aagala.", "casual", "neutral", "normal"),
        ("just the fix please", "short", "neutral", "short_direct"),
        ("can you provide an in-depth architectural deep dive?", "technical", "neutral", "detailed"),
    ]

    for text, exp_primary, exp_emotion, exp_length in style_scenarios:
        p = detect_communication_profile(text)
        status_prim = p["primary_style"] == exp_primary
        status_emo = p["emotion"] == exp_emotion
        status_len = p["length_pref"] == exp_length

        check(f"Profile for '{text[:40]}...'",
              status_prim and status_emo and status_len,
              f"got (primary={p['primary_style']}, emo={p['emotion']}, len={p['length_pref']}) vs expected ({exp_primary}, {exp_emotion}, {exp_length})")

    # ─────────────────────────────────────────────────────────────────────────
    # REQUIREMENT 5: FIRST-CLASS TANGLISH TECHNICAL GUIDELINES
    # ─────────────────────────────────────────────────────────────────────────
    print("\n[TEST 4] Requirement 5: Technical Tanglish First-Class Rules")
    print("-" * 80)

    tanglish_prompt = build_system_prompt("pro", "Tanglish", comm_style="casual")
    check("Contains rule: Keep technical nouns in English", "Keep technical nouns and concepts in English" in tanglish_prompt)
    check("Contains rule: Do not translate to archaic pure Tamil", "DO NOT translate technical concepts into archaic" in tanglish_prompt)
    check("Contains rule: Do not force pure English", "DO NOT force pure English" in tanglish_prompt)
    check("Contains realistic technical Tanglish example", "Payment gateway la success aaguthu" in tanglish_prompt)

    # ─────────────────────────────────────────────────────────────────────────
    # REQUIREMENT 4: ANTI-MIMICRY INTEGRITY
    # ─────────────────────────────────────────────────────────────────────────
    print("\n[TEST 5] Requirement 4: Anti-Mimicry Directive")
    print("-" * 80)

    for m in ["fast", "pro", "eco"]:
        pr = build_system_prompt(m, "English", comm_style="casual")
        check(f"Anti-mimicry protocol present in {m.upper()}", "ANTI-MIMICRY PROTOCOL" in pr)
        check(f"Anti-mimicry contains explicit 'DO NOT COPY' warning in {m.upper()}", "DO NOT COPY THE USER LITERALLY" in pr)

    # ─────────────────────────────────────────────────────────────────────────
    # SUMMARY
    # ─────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print(f"RESULTS: {PASS} passed, {FAIL} failed out of {PASS + FAIL} tests")
    print("=" * 80)

    if FAIL > 0:
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
