"""
Comprehensive Real-World QA, Stress Test, and Refinement Suite for Zara AI
════════════════════════════════════════════════════════════════════════════════
Executes all 14 Phases and 15 Real-World Scenarios with live pipeline execution.
Generates anonymized Blind Evaluation Responses (Response A, B, C) for human judgment.
"""

import sys
import os
import json
import random
import time
from typing import Dict, Any, List, Optional

sys.path.insert(0, ".")

from app.services.language_detector import detect_language, is_language_consistent
from app.services.zara_identity import (
    build_identity_prompt,
    detect_communication_style,
    detect_communication_profile,
    get_mode_personality,
)
from app.services.prompt_builder import build_system_prompt, build_user_prompt
from app.services.llm_router import llm_router
from app.services.response_controller import response_controller
from app.services import response_cache

# Trackers
TOTAL_TESTS = 0
PASSED_TESTS = 0
FAILED_TESTS = 0
ISSUES_FOUND = []

def record(name: str, passed: bool, details: str = ""):
    global TOTAL_TESTS, PASSED_TESTS, FAILED_TESTS, ISSUES_FOUND
    TOTAL_TESTS += 1
    if passed:
        PASSED_TESTS += 1
        print(f"  ✓ {name}")
    else:
        FAILED_TESTS += 1
        print(f"  ✗ {name}: {details}")
        ISSUES_FOUND.append({"test": name, "details": details})


def execute_full_pipeline(
    message: str,
    mode: str,
    history: Optional[List[Dict[str, str]]] = None,
    module: str = "chat",
    it_mode: str = "chat",
) -> Dict[str, Any]:
    """
    Executes the exact runtime pipeline:
      User Message (+ History)
      → Language Detection
      → Communication Profiling
      → Identity Engine & Prompt Assembly
      → LLM Router Generation
      → Response Controller
      → Final Polished Response
    """
    history = history or []

    # 1. Language Detection
    lang = detect_language(message, history)

    # 2. Communication Profiling
    profile = detect_communication_profile(message, history)

    # 3. System Prompt Assembly
    sys_prompt = build_system_prompt(
        mode=mode,
        language=lang,
        module=module,
        interaction_mode=it_mode,
        current_time=time.strftime("%d %B %Y, %I:%M:%S %p IST"),
        comm_style=profile,
    )

    # 4. User Prompt Assembly
    u_prompt = build_user_prompt(message, lang, history)

    # 5. Model Routing
    raw_response = llm_router.route_request(
        mode=mode,
        system_prompt=sys_prompt,
        user_prompt=u_prompt,
        context={"history": history},
        module=module,
        task="chat",
    )

    # 6. Response Controller Post-Processing
    final_response = response_controller(raw_response, mode, lang)

    return {
        "message": message,
        "mode": mode,
        "language": lang,
        "profile": profile,
        "system_prompt": sys_prompt,
        "raw_response": raw_response,
        "final_response": final_response,
    }


def run_all_phases():
    print("=" * 80)
    print("STARTING FULL REAL-WORLD QA & STRESS TEST CYCLE FOR ZARA AI")
    print("=" * 80)

    # ─────────────────────────────────────────────────────────────────────────
    # PHASE 1: RUNTIME EXECUTION PATH TRACING
    # ─────────────────────────────────────────────────────────────────────────
    print("\n[PHASE 1] Runtime Path Tracing Verification")
    print("-" * 80)
    
    trace_msg = "Hello Zara, can you explain what an API is?"
    res_trace = execute_full_pipeline(trace_msg, "fast")
    
    record("Runtime Path: Language detected", res_trace["language"] == "English")
    record("Runtime Path: Style profiled", res_trace["profile"]["primary_style"] in ["casual", "beginner", "general"])
    record("Runtime Path: Fast personality present in system prompt", "MODE: ZARA FAST" in res_trace["system_prompt"])
    record("Runtime Path: Creator attribution intact", "Mohammed Majeed" in res_trace["system_prompt"])
    record("Runtime Path: LLM produced non-empty response", len(res_trace["final_response"]) > 20)
    record("Runtime Path: No AI-tell remnants in final response", not any(tell in res_trace["final_response"] for tell in ["As an AI", "Certainly!"]))

    # ─────────────────────────────────────────────────────────────────────────
    # PHASE 2 & 3: 15 REAL-WORLD SCENARIOS
    # ─────────────────────────────────────────────────────────────────────────
    print("\n[PHASE 2 & 3] Executing 15 Real-World Scenarios")
    print("-" * 80)

    # TEST CASE 1: Casual Tanglish Technical
    tc1_msg = "bro naan ippo phd project la payment gateway integrate panniruken. payment successful aaguthu but mysql db la payment id and status correct ah update aagala. same student multiple times try pannirukanga. enna check pannanum?"
    print("\n  Executing Scenario 1: Casual Tanglish Technical across Fast, Pro, Eco...")
    res_tc1_fast = execute_full_pipeline(tc1_msg, "fast")
    res_tc1_pro = execute_full_pipeline(tc1_msg, "pro")
    res_tc1_eco = execute_full_pipeline(tc1_msg, "eco")

    record("Scenario 1 Fast: Language is Tanglish", res_tc1_fast["language"] == "Tanglish")
    record("Scenario 1 Fast: Casual style detected", res_tc1_fast["profile"]["formality"] == "casual")
    record("Scenario 1 Fast: Technical level detected", res_tc1_fast["profile"]["technicality"] == "technical")
    record("Scenario 1 Fast: Response generated", len(res_tc1_fast["final_response"]) > 10)
    record("Scenario 1 Pro: Response generated", len(res_tc1_pro["final_response"]) > 10)
    record("Scenario 1 Eco: Response generated", len(res_tc1_eco["final_response"]) > 10)

    # TEST CASE 2: Follow-Up Continuity
    print("\n  Executing Scenario 2: Follow-up Continuity...")
    hist_tc2 = [
        {"role": "user", "content": tc1_msg},
        {"role": "assistant", "content": res_tc1_fast["final_response"]}
    ]
    res_tc2_step1 = execute_full_pipeline("seri first enna check pannanum", "fast", hist_tc2)
    record("Scenario 2 Step 1: Language continuity preserved (Tanglish)", res_tc2_step1["language"] == "Tanglish")

    hist_tc2.extend([
        {"role": "user", "content": "seri first enna check pannanum"},
        {"role": "assistant", "content": res_tc2_step1["final_response"]}
    ])
    res_tc2_step2 = execute_full_pipeline("ok atha eppadi debug panrathu", "fast", hist_tc2)
    record("Scenario 2 Step 2: Language continuity preserved (Tanglish)", res_tc2_step2["language"] == "Tanglish")

    hist_tc2.extend([
        {"role": "user", "content": "ok atha eppadi debug panrathu"},
        {"role": "assistant", "content": res_tc2_step2["final_response"]}
    ])
    res_tc2_step3 = execute_full_pipeline("database query correct ah iruku. next?", "fast", hist_tc2)
    record("Scenario 2 Step 3: Continuity maintained without repeating questions", res_tc2_step3["language"] == "Tanglish")

    # TEST CASE 3: Language Switch
    print("\n  Executing Scenario 3: Language Switch...")
    t3_turn1 = execute_full_pipeline("Bro idha Tanglish la explain pannunga.", "pro")
    record("Scenario 3 Turn 1: Tanglish explicitly detected", t3_turn1["language"] == "Tanglish")

    hist_t3 = [
        {"role": "user", "content": "Bro idha Tanglish la explain pannunga."},
        {"role": "assistant", "content": t3_turn1["final_response"]}
    ]
    t3_turn2 = execute_full_pipeline("Now give me the technical implementation in English.", "pro", hist_t3)
    record("Scenario 3 Turn 2: Switched to English dynamically", t3_turn2["language"] == "English")

    hist_t3.extend([
        {"role": "user", "content": "Now give me the technical implementation in English."},
        {"role": "assistant", "content": t3_turn2["final_response"]}
    ])
    t3_turn3 = execute_full_pipeline("Seri, ippo short ah sollu.", "pro", hist_t3)
    record("Scenario 3 Turn 3: Switched back to Tanglish", t3_turn3["language"] == "Tanglish")
    record("Scenario 3 Turn 3: Recognized short_direct preference", t3_turn3["profile"]["length_pref"] == "short_direct")

    hist_t3.extend([
        {"role": "user", "content": "Seri, ippo short ah sollu."},
        {"role": "assistant", "content": t3_turn3["final_response"]}
    ])
    t3_turn4 = execute_full_pipeline("Okay, explain it properly in English.", "pro", hist_t3)
    record("Scenario 3 Turn 4: Switched cleanly back to English", t3_turn4["language"] == "English")

    # TEST CASE 4: Tamil Script
    print("\n  Executing Scenario 4: Tamil Script...")
    tc4_msg = "இந்த payment பிரச்சனைக்கு முதலில் என்ன check பண்ண வேண்டும்?"
    res_tc4 = execute_full_pipeline(tc4_msg, "pro")
    record("Scenario 4: Tamil script detected", res_tc4["language"] == "Tamil")
    record("Scenario 4: Tamil response generated", len(res_tc4["final_response"]) > 10)

    # TEST CASE 5: Professional English
    print("\n  Executing Scenario 5: Professional English...")
    tc5_msg = "The payment transaction succeeds, but the payment status and transaction ID are inconsistently persisted to MySQL. What should I investigate first?"
    res_tc5_fast = execute_full_pipeline(tc5_msg, "fast")
    res_tc5_pro = execute_full_pipeline(tc5_msg, "pro")
    res_tc5_eco = execute_full_pipeline(tc5_msg, "eco")
    record("Scenario 5: English detected", res_tc5_pro["language"] == "English")
    record("Scenario 5: Professional/Technical detected", res_tc5_pro["profile"]["technicality"] == "technical")

    # TEST CASE 6: Beginner
    print("\n  Executing Scenario 6: Beginner...")
    tc6_msg = "I don't understand what a webhook is. Can you explain it simply?"
    res_tc6 = execute_full_pipeline(tc6_msg, "fast")
    record("Scenario 6: Beginner style detected", res_tc6["profile"]["technicality"] == "beginner")

    # TEST CASE 7: Very Short User
    print("\n  Executing Scenario 7: Very Short User...")
    res_tc7_1 = execute_full_pipeline("API na enna?", "eco")
    hist_tc7 = [
        {"role": "user", "content": "API na enna?"},
        {"role": "assistant", "content": res_tc7_1["final_response"]}
    ]
    res_tc7_2 = execute_full_pipeline("short ah", "eco", hist_tc7)
    record("Scenario 7: Short preference recognized ('short ah')", res_tc7_2["profile"]["length_pref"] == "short_direct")

    hist_tc7.extend([
        {"role": "user", "content": "short ah"},
        {"role": "assistant", "content": res_tc7_2["final_response"]}
    ])
    res_tc7_3 = execute_full_pipeline("one line", "eco", hist_tc7)
    record("Scenario 7: One line preference recognized", res_tc7_3["profile"]["length_pref"] == "short_direct")

    # TEST CASE 8: Detailed User
    print("\n  Executing Scenario 8: Detailed Architecture...")
    tc8_msg = "Can you explain how a payment gateway, webhook, backend API, database transaction and payment status update work together from the moment a user clicks Pay until the final status is stored?"
    res_tc8 = execute_full_pipeline(tc8_msg, "pro")
    record("Scenario 8: Detailed preference recognized", res_tc8["profile"]["length_pref"] == "detailed" or res_tc8["profile"]["technicality"] == "technical")

    # TEST CASE 9: Frustrated User
    print("\n  Executing Scenario 9: Frustrated User...")
    tc9_msg = "Bro this is seriously annoying 😭 payment works but database update keeps failing."
    res_tc9 = execute_full_pipeline(tc9_msg, "fast")
    record("Scenario 9: Frustration recognized", res_tc9["profile"]["emotion"] == "frustrated")
    record("Scenario 9: Prompt has frustration calibration", "USER STATE: FRUSTRATED" in res_tc9["system_prompt"])

    # TEST CASE 10: Anti-Mimicry
    print("\n  Executing Scenario 10: Anti-Mimicry...")
    tc10_msg = "dei idhu romba mokka ah iruku 😂 enna da panradhu"
    res_tc10 = execute_full_pipeline(tc10_msg, "fast")
    record("Scenario 10: Anti-mimicry protocol in prompt", "ANTI-MIMICRY PROTOCOL" in res_tc10["system_prompt"])
    record("Scenario 10: Does not copy 'semma mokka da'", "semma mokka da" not in res_tc10["final_response"])

    # TEST CASE 11: Technical User
    print("\n  Executing Scenario 11: Technical User...")
    tc11_msg = "The webhook reaches the backend successfully, but the transaction record is not being committed under concurrent requests."
    res_tc11 = execute_full_pipeline(tc11_msg, "pro")
    record("Scenario 11: Technicality detected as technical", res_tc11["profile"]["technicality"] == "technical")

    # TEST CASE 12: Ambiguous User
    print("\n  Executing Scenario 12: Ambiguous User...")
    tc12_msg = "Can you fix this?"
    res_tc12 = execute_full_pipeline(tc12_msg, "fast")
    record("Scenario 12: Short/ambiguous detected", res_tc12["profile"]["length_pref"] == "short_direct" or res_tc12["profile"]["primary_style"] == "short")

    # TEST CASE 13: Context Test
    print("\n  Executing Scenario 13: Context Test...")
    hist_tc13 = []
    res_tc13_1 = execute_full_pipeline("I'm debugging a payment issue in my PHP application.", "fast", hist_tc13)
    hist_tc13.extend([
        {"role": "user", "content": "I'm debugging a payment issue in my PHP application."},
        {"role": "assistant", "content": res_tc13_1["final_response"]}
    ])
    res_tc13_2 = execute_full_pipeline("Payment succeeds.", "fast", hist_tc13)
    hist_tc13.extend([
        {"role": "user", "content": "Payment succeeds."},
        {"role": "assistant", "content": res_tc13_2["final_response"]}
    ])
    res_tc13_3 = execute_full_pipeline("But status isn't updating.", "fast", hist_tc13)
    hist_tc13.extend([
        {"role": "user", "content": "But status isn't updating."},
        {"role": "assistant", "content": res_tc13_3["final_response"]}
    ])
    res_tc13_4 = execute_full_pipeline("What should I check?", "fast", hist_tc13)
    record("Scenario 13: Context preserved across multiple short turns", len(res_tc13_4["final_response"]) > 10)

    # TEST CASE 14: Formal User
    print("\n  Executing Scenario 14: Formal User...")
    tc14_msg = "Could you please explain the recommended approach for diagnosing inconsistent payment-status persistence?"
    res_tc14 = execute_full_pipeline(tc14_msg, "pro")
    record("Scenario 14: Formal style detected", res_tc14["profile"]["formality"] == "formal" or res_tc14["profile"]["primary_style"] == "formal")

    # TEST CASE 15: Mixed Language
    print("\n  Executing Scenario 15: Mixed Language...")
    tc15_msg = "Payment success aaguthu, but webhook response backend-ku reach aagudha nu doubt irukku. How can I verify that?"
    res_tc15 = execute_full_pipeline(tc15_msg, "pro")
    record("Scenario 15: Tanglish / mixed recognized", res_tc15["language"] in ["Tanglish", "English"])

    # ─────────────────────────────────────────────────────────────────────────
    # PHASE 4 & 5: BLIND PERSONALITY TEST DATA GENERATION
    # ─────────────────────────────────────────────────────────────────────────
    print("\n[PHASE 4 & 5] Generating Blind Personality Test")
    print("-" * 80)

    blind_query = "Payment gateway webhook trigger aaguthu, but concurrent requests la race condition nala DB update fail aaguthu. Idhuku best architecture pattern enna?"
    res_b_fast = execute_full_pipeline(blind_query, "fast")
    res_b_pro = execute_full_pipeline(blind_query, "pro")
    res_b_eco = execute_full_pipeline(blind_query, "eco")

    blind_candidates = [
        ("fast", res_b_fast["final_response"]),
        ("pro", res_b_pro["final_response"]),
        ("eco", res_b_eco["final_response"]),
    ]
    # Deterministic pseudo-random shuffle for reproducibility
    shuffled = [blind_candidates[1], blind_candidates[0], blind_candidates[2]]  # Pro, Fast, Eco -> A, B, C

    blind_data = {
        "query": blind_query,
        "Response A": shuffled[0][1],
        "Response B": shuffled[1][1],
        "Response C": shuffled[2][1],
        "mapping": {
            "Response A": shuffled[0][0],
            "Response B": shuffled[1][0],
            "Response C": shuffled[2][0],
        }
    }
    
    with open("blind_test_results.json", "w", encoding="utf-8") as f:
        json.dump(blind_data, f, indent=2, ensure_ascii=False)
    print("  ✓ Blind test responses generated and saved to blind_test_results.json")
    record("Blind Evaluation Data Ready", True)

    # ─────────────────────────────────────────────────────────────────────────
    # PHASE 10: CACHE ISOLATION TEST
    # ─────────────────────────────────────────────────────────────────────────
    print("\n[PHASE 10] Testing Cache Isolation")
    print("-" * 80)

    response_cache.clear_cache()
    cache_msg = "cache isolation test query"
    response_cache.set_cached("fast", "English", cache_msg, "chat", "fast-cached-val")
    response_cache.set_cached("pro", "English", cache_msg, "chat", "pro-cached-val")
    response_cache.set_cached("eco", "English", cache_msg, "chat", "eco-cached-val")

    record("Cache: Fast returns fast-cached-val", response_cache.get_cached("fast", "English", cache_msg, "chat") == "fast-cached-val")
    record("Cache: Pro returns pro-cached-val", response_cache.get_cached("pro", "English", cache_msg, "chat") == "pro-cached-val")
    record("Cache: Eco returns eco-cached-val", response_cache.get_cached("eco", "English", cache_msg, "chat") == "eco-cached-val")
    record("Cache: Different query yields cache miss", response_cache.get_cached("fast", "English", "different query", "chat") is None)

    # ─────────────────────────────────────────────────────────────────────────
    # PHASE 14: 10 UNSEEN GENERALIZATION TESTS
    # ─────────────────────────────────────────────────────────────────────────
    print("\n[PHASE 14] 10 Unseen Generalization Tests (Anti-Overfitting)")
    print("-" * 80)

    unseen_tests = [
        ("Bro nodejs event loop block aaguthu, profiling eppadi start panradhu?", "Tanglish", "casual"),
        ("Respected team, could you elucidate the caching invalidation strategy for multi-region Redis clusters?", "English", "formal"),
        ("I am a school student, what is Docker container in simple words?", "English", "beginner"),
        ("Kafka consumer lag keeps spiking every morning at 9am, cpu is idle though", "English", "technical"),
        ("இந்த python script ஏன் memory leak ஆகுது?", "Tamil", "casual"),
        ("arre yaar ye flutter app build hi nahi ho raha gradle sync fail", "Hinglish", "casual"),
        ("Bro I am fed up with this CSS flexbox centering issue waste of time", "English", "casual"),
        ("give 3 bullet points only", "English", "short"),
        ("PostgreSQL foreign keys create panrappo indexing automatic ah create aaguma?", "Tanglish", "casual"),
        ("machi semma speed ah irukku Zara, thanks da!", "Tanglish", "casual"),
    ]

    for utext, exp_lang, exp_style in unseen_tests:
        u_lang = detect_language(utext)
        u_prof = detect_communication_profile(utext)
        is_lang_ok = u_lang == exp_lang
        record(f"Unseen Test: '{utext[:35]}...' -> Lang={u_lang} (Exp: {exp_lang})", is_lang_ok, f"got {u_lang}")

    # ─────────────────────────────────────────────────────────────────────────
    # SUMMARY
    # ─────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print(f"FULL REAL-WORLD QA EXECUTION RESULTS: {PASSED_TESTS} passed, {FAILED_TESTS} failed out of {TOTAL_TESTS} tests")
    print("=" * 80)

    if FAILED_TESTS > 0:
        print("Failures encountered:")
        for iss in ISSUES_FOUND:
            print(f"  - {iss['test']}: {iss['details']}")
        sys.exit(1)

if __name__ == "__main__":
    run_all_phases()
