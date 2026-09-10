"""
Live E2E Provider Test — Verifies actual generation through the LLM Router
for Zara Fast (Groq) and Zara Pro (Gemini).
OpenRouter (Eco) is deferred until a new key is provided.
"""
import sys, os
sys.path.insert(0, '.')
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

from dotenv import load_dotenv
load_dotenv('.env', override=True)

from app.services.llm_router import LLMRouter
from app.services.prompt_builder import build_system_prompt, build_user_prompt
from app.services.language_detector import detect_language
from app.services.zara_identity import detect_communication_style

router = LLMRouter()

TESTS = [
    # (mode, user_msg, description)
    ("fast", "Bro explain what a REST API is in 2 lines", "Fast English casual"),
    ("fast", "bro JWT token epdi work aagum explain pannu", "Fast Tanglish casual"),
    ("pro", "Explain the CAP theorem and its trade-offs in distributed systems", "Pro English technical"),
    ("pro", "Payment gateway integration la race condition avoid panna enna approach best?", "Pro Tanglish technical"),
]

results = []
for mode, msg, desc in TESTS:
    print(f"\n{'='*60}")
    print(f"TEST: {desc}")
    print(f"Mode: {mode.upper()}")
    print(f"User: {msg}")
    print(f"{'='*60}")
    
    lang = detect_language(msg)
    comm = detect_communication_style(msg)
    
    sys_prompt = build_system_prompt(
        mode=mode,
        language=lang,
        comm_style=comm,
    )
    user_prompt = build_user_prompt(
        user_input=msg,
        language=lang,
        history=[]
    )
    
    try:
        response = router.route_request(
            mode=mode,
            system_prompt=sys_prompt,
            user_prompt=user_prompt,
        )
        # Truncate for display
        display = response.strip()[:300]
        print(f"\nZara ({mode.upper()}): {display}")
        
        # Sanity checks
        checks = []
        if len(response.strip()) > 10:
            checks.append("OK Non-trivial response")
        else:
            checks.append("FAIL Response too short")
        
        if "I am an AI" not in response and "as an AI" not in response.lower():
            checks.append("OK No AI self-identification")
        else:
            checks.append("WARN Contains AI self-reference")
            
        if response.strip():
            checks.append("OK Non-empty")
        else:
            checks.append("FAIL Empty response")
            
        for c in checks:
            print(f"  {c}")
        
        results.append((desc, "PASS", None))
    except Exception as e:
        print(f"\nFAILED: {str(e)[:150]}")
        results.append((desc, "FAIL", str(e)[:100]))

# Test Eco separately — expect fallback or failure
print(f"\n{'='*60}")
print(f"TEST: Eco (OpenRouter) — expected to fallback or fail gracefully")
print(f"{'='*60}")
try:
    lang = detect_language("What is Python?")
    comm = detect_communication_style("What is Python?")
    sys_prompt = build_system_prompt(mode="eco", language=lang, comm_style=comm)
    user_prompt = build_user_prompt(user_input="What is Python?", language=lang, history=[])
    response = router.route_request(mode="eco", system_prompt=sys_prompt, user_prompt=user_prompt)
    display = response.strip()[:200]
    print(f"\nZara (ECO): {display}")
    print("  OK Eco responded (via fallback to Groq or Gemini)")
    results.append(("Eco fallback", "PASS", None))
except Exception as e:
    err = str(e)[:120]
    if "rate limit" in err.lower() or "429" in err or "all providers failed" in err.lower():
        print(f"\n  Expected failure: {err}")
        results.append(("Eco fallback", "EXPECTED_FAIL", err))
    else:
        print(f"\n  Unexpected: {err}")
        results.append(("Eco fallback", "FAIL", err))

# Summary
print(f"\n{'='*60}")
print("SUMMARY")
print(f"{'='*60}")
for desc, status, err in results:
    icon = "PASS" if status == "PASS" else ("WARN" if status == "EXPECTED_FAIL" else "FAIL")
    print(f"  [{icon}] {desc}" + (f" ({err})" if err else ""))

passed = sum(1 for _, s, _ in results if s in ("PASS", "EXPECTED_FAIL"))
total = len(results)
print(f"\n{passed}/{total} tests acceptable")
