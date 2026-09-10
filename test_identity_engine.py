"""
Zara Identity Engine — Verification Tests
Tests the core functionality of the centralized identity system.
"""

import sys
sys.path.insert(0, ".")

from app.services.zara_identity import (
    build_identity_prompt,
    detect_communication_style,
    get_mode_personality,
    get_compact_core_identity,
)
from app.services.prompt_builder import build_system_prompt, build_user_prompt
from app.services.response_controller import response_controller

PASS = 0
FAIL = 0

def check(name, condition):
    global PASS, FAIL
    if condition:
        print(f"  ✓ {name}")
        PASS += 1
    else:
        print(f"  ✗ {name}")
        FAIL += 1

# ─── 1. MODE PERSONALITIES ARE DISTINCT ─────────────────────────────────────
print("\n═══ 1. Mode Personality Distinctness ═══")

fast_prompt = build_identity_prompt("fast", "English")
pro_prompt = build_identity_prompt("pro", "English")
eco_prompt = build_identity_prompt("eco", "English")

check("Fast prompt contains 'Conversational Zara'", "Conversational Zara" in fast_prompt)
check("Pro prompt contains 'Expert Partner'", "Expert Partner" in pro_prompt)
check("Eco prompt contains 'Efficient Assistant'", "Efficient Assistant" in eco_prompt)

check("Fast != Pro", fast_prompt != pro_prompt)
check("Pro != Eco", pro_prompt != eco_prompt)
check("Fast != Eco", fast_prompt != eco_prompt)

check("All contain core identity (Mohammed Majeed)", 
      "Mohammed Majeed" in fast_prompt and "Mohammed Majeed" in pro_prompt and "Mohammed Majeed" in eco_prompt)
check("All contain safety", 
      "CRISIS SAFETY" in fast_prompt and "CRISIS SAFETY" in pro_prompt and "CRISIS SAFETY" in eco_prompt)
check("All contain anti-AI-tell rules",
      "As an AI" in fast_prompt and "As an AI" in pro_prompt and "As an AI" in eco_prompt)

# ─── 2. COMMUNICATION STYLE DETECTION ───────────────────────────────────────
print("\n═══ 2. Communication Style Detection ═══")

check("Casual: 'bro this isn't working'", detect_communication_style("bro this isn't working") == "casual")
check("Formal: 'Could you please explain the architectural implications of this change'", 
      detect_communication_style("Could you please explain the architectural implications of this change") == "formal")
check("Technical: 'The webhook endpoint returns a 500 when the transaction rollback fails'", 
      detect_communication_style("The webhook endpoint returns a 500 when the transaction rollback fails") == "technical")
check("Beginner: 'I don't understand what an API is'", 
      detect_communication_style("I don't understand what an API is") == "beginner")
check("Short: 'fix this'", detect_communication_style("fix this") == "short")
check("Tanglish casual: 'machi idhu work aagala da'", 
      detect_communication_style("machi idhu work aagala da") == "casual")

# ─── 3. USER ADAPTATION IN PROMPTS ──────────────────────────────────────────
print("\n═══ 3. User Adaptation ═══")

casual_prompt = build_identity_prompt("fast", "English", comm_style="casual")
formal_prompt = build_identity_prompt("fast", "English", comm_style="formal")
technical_prompt = build_identity_prompt("fast", "English", comm_style="technical")
beginner_prompt = build_identity_prompt("fast", "English", comm_style="beginner")

check("Casual adaptation present", "USER STYLE: CASUAL" in casual_prompt)
check("Formal adaptation present", "USER STYLE: FORMAL" in formal_prompt)
check("Technical adaptation present", "USER STYLE: TECHNICAL" in technical_prompt)
check("Beginner adaptation present", "USER STYLE: BEGINNER" in beginner_prompt)

check("Adaptation doesn't erase personality (all still Fast)", 
      "Conversational Zara" in casual_prompt and 
      "Conversational Zara" in formal_prompt and 
      "Conversational Zara" in technical_prompt)

# ─── 4. LANGUAGE ADAPTATION ─────────────────────────────────────────────────
print("\n═══ 4. Language Adaptation ═══")

tamil_prompt = build_identity_prompt("pro", "Tamil")
tanglish_prompt = build_identity_prompt("eco", "Tanglish")
english_prompt = build_identity_prompt("fast", "English")

check("Tamil prompt has Tamil rules", "LANGUAGE: TAMIL" in tamil_prompt)
check("Tanglish prompt has Tanglish rules", "LANGUAGE: TANGLISH" in tanglish_prompt)
check("English prompt has English rules", "LANGUAGE: ENGLISH" in english_prompt)

# ─── 5. MODULE RULES ────────────────────────────────────────────────────────
print("\n═══ 5. Module Rules ═══")

tutor_prompt = build_identity_prompt("pro", "English", module="tutor")
exam_prompt = build_identity_prompt("eco", "English", module="exam_prep")
code_prompt = build_identity_prompt("fast", "English", module="code_architect")
chat_prompt = build_identity_prompt("fast", "English", module="chat")

check("Tutor module rules present", "TUTOR MODE" in tutor_prompt)
check("Exam module rules present", "EXAM PREP MODE" in exam_prompt)
check("Code module rules present", "CODE ARCHITECT MODE" in code_prompt)
check("Chat has no module rules", "TUTOR MODE" not in chat_prompt and "EXAM PREP" not in chat_prompt)

# ─── 6. CARE MODE ───────────────────────────────────────────────────────────
print("\n═══ 6. Care Mode ═══")

care_prompt = build_identity_prompt("fast", "English", interaction_mode="care")
normal_prompt = build_identity_prompt("fast", "English", interaction_mode="chat")

check("Care mode rules present when active", "CARE MODE" in care_prompt)
check("Care mode rules absent in normal chat", "CARE MODE" not in normal_prompt)

# ─── 7. PROMPT BUILDER DELEGATION ───────────────────────────────────────────
print("\n═══ 7. Prompt Builder Backward Compat ═══")

system_prompt = build_system_prompt(
    mode="pro",
    language="English",
    module="chat",
    interaction_mode="chat",
    current_time="10 September 2026, 12:00:00 PM IST",
    comm_style="technical",
)
check("build_system_prompt returns valid prompt", len(system_prompt) > 100)
check("build_system_prompt contains Pro personality", "Expert Partner" in system_prompt)
check("build_system_prompt contains time", "10 September 2026" in system_prompt)
check("build_system_prompt contains technical adaptation", "USER STYLE: TECHNICAL" in system_prompt)

user_prompt = build_user_prompt("hello world", "English", [{"role": "user", "content": "hi"}])
check("build_user_prompt contains user message", "hello world" in user_prompt)
check("build_user_prompt contains language reminder", "RESPOND IN ENGLISH" in user_prompt)
check("build_user_prompt contains history", "CONVERSATION HISTORY" in user_prompt)

# ─── 8. RESPONSE CONTROLLER ────────────────────────────────────────────────
print("\n═══ 8. Response Controller ═══")

# AI-tell stripping
test_response = "Great question! Here's how to fix your code."
cleaned = response_controller(test_response, "fast", "English")
check("AI-tell 'Great question!' stripped", "Great question!" not in cleaned)
check("Useful content preserved after strip", "fix your code" in cleaned)

# Eco does NOT do word replacement anymore
test_eco = "Therefore, you should utilize the additional assistance."
eco_result = response_controller(test_eco, "eco", "English")
check("Eco no longer replaces 'Therefore' → 'So'", "Therefore" in eco_result)
check("Eco no longer replaces 'utilize' → 'use'", "utilize" in eco_result)

# Normal response passes through cleanly
clean_response = "Your MySQL query has a missing WHERE clause on the JOIN."
check("Clean response passes through unchanged (fast)", 
      response_controller(clean_response, "fast", "English") == clean_response)
check("Clean response passes through unchanged (pro)", 
      response_controller(clean_response, "pro", "English") == clean_response)
check("Clean response passes through unchanged (eco)", 
      response_controller(clean_response, "eco", "English") == clean_response)

# ─── 9. COMPACT CORE IDENTITY ──────────────────────────────────────────────
print("\n═══ 9. Compact Core Identity (Frontend) ═══")

compact = get_compact_core_identity()
check("Compact identity contains creator", "Mohammed Majeed" in compact)
check("Compact identity contains auth protocol", "Afzal" in compact)
check("Compact identity contains safety", "CRISIS SAFETY" in compact)
check("Compact identity does NOT contain mode personality", 
      "Conversational Zara" not in compact and "Expert Partner" not in compact)

# ─── SUMMARY ────────────────────────────────────────────────────────────────
print(f"\n{'═' * 50}")
print(f"Results: {PASS} passed, {FAIL} failed out of {PASS + FAIL} tests")
if FAIL == 0:
    print("ALL TESTS PASSED ✓")
else:
    print(f"FAILURES: {FAIL}")
    sys.exit(1)
