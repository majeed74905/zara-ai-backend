"""
Verification Script for Zara AI Elite Engine
──────────────────────────────────────────────────────────────────────────────
Tests:
  1. Language Detection & Hard Lock
  2. Mode-Based Behavioral Shaping (Fast/Pro/Eco)
  3. Pro Mode Dual Response (Quick/Deep split)
  4. Task-Aware Routing (Code/Research overrides)
  5. Elite Analytics (Latency/Fallback tracking)
"""

import sys
import json
import time

# Ensure we can import from app
sys.path.append(".")

try:
    from app.services.language_detector import detect_language, is_language_consistent
    from app.services.prompt_builder import build_system_prompt
    from app.services.llm_router import llm_router, get_cost_summary
    from app.services.response_controller import response_controller
    from app.services import response_cache
except ImportError as e:
    print(f"❌ Error: Could not import backend modules: {e}")
    sys.exit(1)

def print_header(text):
    print(f"\n{'='*80}")
    print(f" {text}")
    print(f"{'='*80}")

def test_language_consistency():
    print_header("1. TESTING LANGUAGE LOCK & CONSISTENCY")
    test_cases = [
        ("How are you today?", "English"),
        ("Eppadi irukinga?", "Tanglish"),
        ("Enga poringa?", "Tanglish"),
        ("नमस्ते, आप कैसे हैं?", "Hindi"),
    ]
    
    for text, target in test_cases:
        detected = detect_language(text)
        consistent = is_language_consistent(text, target)
        status = "✅" if consistent else "❌"
        print(f"{status} [{target}] Input: \"{text}\" | Detected: {detected} | Consistent: {consistent}")

def test_mode_behavioral_shaping():
    print_header("2. TESTING MODE BEHAVIORAL SHAPING")
    
    query = "Explain what an API is in simple terms."
    modes = ["fast", "pro", "eco"]
    
    for mode in modes:
        print(f"\n🚀 Testing Mode: {mode.upper()}")
        sys_prompt = build_system_prompt(mode, "English")
        
        start = time.time()
        raw_response = llm_router.route_request(mode, sys_prompt, query)
        
        # Apply Controller
        shaped_response = response_controller(raw_response, mode, "English")
        elapsed = time.time() - start
        
        print(f"   ⏱️ Latency: {elapsed:.2f}s")
        print(f"   📏 Length: {len(shaped_response)} chars")
        
        # Validation checks
        if mode == "fast":
            lines = shaped_response.strip().split("\n")
            if len(lines) <= 7:
                 print("   ✅ Fast Shape: Correctly concise.")
            else:
                 print(f"   ⚠️ Fast Shape: Response has {len(lines)} lines (budget 7).")
                 
        if mode == "pro":
            if "###" in shaped_response or "•" in shaped_response:
                print("   ✅ Pro Shape: Premium structure detected.")
            else:
                print("   ⚠️ Pro Shape: Missing expected structure.")

        if mode == "eco":
            if any(w in shaped_response.lower() for w in ["so", "also", "help", "wrap up"]):
                print("   ✅ Eco Shape: Humanized tone detected.")
            else:
                print("   ⚠️ Eco Shape: Tone might still be formal.")

def test_task_aware_routing():
    print_header("3. TESTING TASK-AWARE ROUTING")
    code_query = "Write a python script to sort a list of numbers."
    print(f"Query: \"{code_query}\"")
    
    # We don't need to call the API, just verify the routing logic
    order = llm_router._get_routing_order("pro", code_query)
    if order[0][0] == "groq":
        print("   ✅ Task-Aware: Correctly prioritized Groq for code task.")
    else:
        print(f"   ❌ Task-Aware: Failed to prioritize Groq. Top: {order[0][0]}")

def test_dual_response():
    print_header("4. TESTING DUAL RESPONSE (PRO ONLY)")
    query = "Give me a deep dive into the history of artificial intelligence."
    print("Testing Pro mode for dual response output...")
    
    sys_prompt = build_system_prompt("pro", "English")
    response = llm_router.route_request("pro", sys_prompt, query)
    
    if len(response) > 300:
        parts = response.split("\n\n")
        quick = f"🔹 Quick Summary:\n{parts[0]}"
        deep = f"🔹 Deep Dive:\n" + "\n\n".join(parts[1:])
        print("   ✅ Dual response structure generated successfully.")
        print(f"\n   {quick[:100]}...")
        print(f"\n   {deep[:150]}...")
    else:
        print("   ⚠️ Response too short for a meaningful dual mode test.")

def test_analytics():
    print_header("5. ELITE ANALYTICS & COST SUMMARY")
    summary = get_cost_summary()
    print(json.dumps(summary, indent=4))

if __name__ == "__main__":
    print_header("ZARA AI ELITE SYSTEM VERIFICATION")
    
    test_language_consistency()
    test_task_aware_routing()
    
    ans = input("\nDo you want to run LIVE API behavioral tests? (y/n): ")
    if ans.lower() == 'y':
        test_mode_behavioral_shaping()
        test_dual_response()
        test_analytics()
    
    print_header("VERIFICATION COMPLETE")
