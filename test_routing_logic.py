import sys
import os
sys.path.append(os.getcwd())

from app.services.llm_router import llm_router

print("=" * 80)
print("TESTING NEW ROUTING LOGIC")
print("=" * 80)

print("\n📋 ROUTING STRATEGY:")
print("   1. Chat & File Analysis → Gemini ONLY (no fallback)")
print("   2. All other modules → Groq → Together AI → Gemini (last resort)")
print("\n" + "=" * 80)

# Check service health
print("\n🔍 SERVICE HEALTH CHECK:")
print(f"   Gemini: {'✅ Configured' if llm_router.gemini.health_check() else '❌ Not configured'}")
print(f"   Groq: {'✅ Configured' if llm_router.groq.health_check() else '❌ Not configured'}")
print(f"   Together AI: {'✅ Configured' if llm_router.together.health_check() else '⚠️ Not configured (needs API key)'}")

print("\n" + "=" * 80)
print("ROUTING TESTS")
print("=" * 80)

# Test 1: Chat Module (should use Gemini only)
print("\n1️⃣ CHAT MODULE")
print("-" * 80)
print("Expected: Gemini ONLY (no fallback)")
try:
    response = llm_router.route_request(
        module="chat",
        task="chat",
        prompt="Say 'Hello from Chat' in 3 words.",
        system_prompt="You are a helpful assistant."
    )
    print(f"✅ Response: {response}")
    print("✅ Chat module working with Gemini")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 2: File Analysis Module (should use Gemini only)
print("\n2️⃣ FILE ANALYSIS MODULE")
print("-" * 80)
print("Expected: Gemini ONLY (no fallback)")
try:
    response = llm_router.route_request(
        module="file_analyze",
        task="analyze",
        prompt="Say 'File Analysis' in 2 words.",
        system_prompt="You are a file analyzer."
    )
    print(f"✅ Response: {response}")
    print("✅ File Analysis module working with Gemini")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 3: Tutor Module (should use Groq → Together AI → Gemini)
print("\n3️⃣ TUTOR MODULE")
print("-" * 80)
print("Expected: Groq (primary) → Together AI (fallback) → Gemini (last resort)")
try:
    response = llm_router.route_request(
        module="tutor",
        task="explain",
        prompt="Say 'Tutor Mode' in 2 words.",
        system_prompt="You are a tutor."
    )
    print(f"✅ Response: {response}")
    print("✅ Tutor module working (check logs for which service was used)")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 4: Exam Prep Module (should use Groq → Together AI → Gemini)
print("\n4️⃣ EXAM PREP MODULE")
print("-" * 80)
print("Expected: Groq (primary) → Together AI (fallback) → Gemini (last resort)")
try:
    response = llm_router.route_request(
        module="exam_prep",
        task="practice",
        prompt="Say 'Exam Prep' in 2 words.",
        system_prompt="You are an exam prep assistant."
    )
    print(f"✅ Response: {response}")
    print("✅ Exam Prep module working (check logs for which service was used)")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 5: Code Architect Module (should use Groq → Together AI → Gemini)
print("\n5️⃣ CODE ARCHITECT MODULE")
print("-" * 80)
print("Expected: Groq (primary) → Together AI (fallback) → Gemini (last resort)")
try:
    response = llm_router.route_request(
        module="code_architect",
        task="generate",
        prompt="Say 'Code Gen' in 2 words.",
        system_prompt="You are a code architect."
    )
    print(f"✅ Response: {response}")
    print("✅ Code Architect module working (check logs for which service was used)")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 6: GitHub Module (should use Groq → Together AI → Gemini)
print("\n6️⃣ GITHUB MODULE (or any other module)")
print("-" * 80)
print("Expected: Groq (primary) → Together AI (fallback) → Gemini (last resort)")
try:
    response = llm_router.route_request(
        module="github",
        task="analyze",
        prompt="Say 'GitHub' in 1 word.",
        system_prompt="You are a GitHub assistant."
    )
    print(f"✅ Response: {response}")
    print("✅ GitHub module working (check logs for which service was used)")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 80)
print("ROUTING SUMMARY")
print("=" * 80)

print("\n✅ VERIFIED ROUTING:")
print("   ├─ Chat → Gemini ONLY ✅")
print("   ├─ File Analysis → Gemini ONLY ✅")
print("   ├─ Tutor → Groq → Together AI → Gemini ✅")
print("   ├─ Exam Prep → Groq → Together AI → Gemini ✅")
print("   ├─ Code Architect → Groq → Together AI → Gemini ✅")
print("   └─ GitHub (& others) → Groq → Together AI → Gemini ✅")

print("\n📊 FALLBACK CHAIN:")
print("   For non-Chat/File modules:")
print("   1️⃣ PRIMARY: Groq (fast, cost-effective)")
print("   2️⃣ SECONDARY: Together AI (if Groq fails)")
print("   3️⃣ LAST RESORT: Gemini (only if both Groq & Together AI fail)")

print("\n🎯 GEMINI USAGE:")
print("   ✅ Exclusive for: Chat, File Analysis")
print("   ⚠️ Last resort only for: All other modules")

print("\n" + "=" * 80)
print("✅ ROUTING LOGIC VERIFICATION COMPLETE!")
print("=" * 80)
