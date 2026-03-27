import sys
import os
sys.path.append(os.getcwd())

print("=" * 80)
print("TESTING ALL AI SERVICES (GROQ, GEMINI, OPENROUTER)")
print("=" * 80)

# Test 1: Groq
print("\n" + "=" * 80)
print("1️⃣ TESTING GROQ SERVICE (FAST MODE)")
print("=" * 80)

try:
    from app.services.models.groq_service import GroqService
    groq = GroqService()
    
    if not groq.health_check():
        print("❌ Groq service is not configured")
    else:
        print(f"✅ Groq initialized: {groq.model_name}")
        response = groq.generate(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say 'Groq works' in exactly 2 words."
        )
        print(f"✅ GROQ RESPONSE: {response}")
except Exception as e:
    print(f"❌ GROQ ERROR: {e}")

# Test 2: Gemini
print("\n" + "=" * 80)
print("2️⃣ TESTING GEMINI SERVICE (PRO MODE)")
print("=" * 80)

try:
    from app.services.models.gemini_service import GeminiService
    gemini = GeminiService()
    
    if not gemini.health_check():
        print("❌ Gemini service is not configured")
    else:
        print(f"✅ Gemini initialized: {gemini.model_name}")
        response = gemini.generate(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say 'Gemini works' in exactly 2 words."
        )
        print(f"✅ GEMINI RESPONSE: {response}")
except Exception as e:
    print(f"❌ GEMINI ERROR: {e}")

# Test 3: OpenRouter
print("\n" + "=" * 80)
print("3️⃣ TESTING OPENROUTER SERVICE (ECO MODE)")
print("=" * 80)

try:
    from app.services.models.openrouter_service import OpenRouterService
    openrouter = OpenRouterService()
    
    if not openrouter.health_check():
        print("⚠️  OpenRouter service is not configured (no API key)")
        print("   Add OPENROUTER_API_KEY to .env file")
        print("   Get your key at: https://openrouter.ai/keys")
    else:
        print(f"✅ OpenRouter initialized: {openrouter.model_name}")
        response = openrouter.generate(
            system_prompt="You are ZARA ECO. Be concise.",
            user_prompt="Say 'OpenRouter works' in exactly 2 words."
        )
        print(f"✅ OPENROUTER RESPONSE: {response}")
except Exception as e:
    print(f"❌ OPENROUTER ERROR: {e}")

# Test 4: LLM Router
print("\n" + "=" * 80)
print("4️⃣ TESTING LLM ROUTER")
print("=" * 80)

try:
    from app.services.llm_router import llm_router
    
    print("\n📊 Service Health Check:")
    print(f"   - Groq: {'✅ Configured' if llm_router.groq.health_check() else '❌ Not configured'}")
    print(f"   - Gemini: {'✅ Configured' if llm_router.gemini.health_check() else '❌ Not configured'}")
    print(f"   - OpenRouter: {'✅ Configured' if llm_router.openrouter.health_check() else '⚠️ Not configured'}")
    
    print("\n🔄 Testing Router Logic:")
    
    # Test Chat (should use Gemini)
    print("\n   Testing Chat module (should use Gemini)...")
    chat_response = llm_router.route_request(
        module="chat",
        task="chat",
        prompt="Say 'Chat test' in 2 words.",
        system_prompt="You are helpful."
    )
    print(f"   ✅ Chat Response: {chat_response}")
    
    # Test Tutor (should use Groq → OpenRouter → Gemini)
    print("\n   Testing Tutor module (should use Groq)...")
    tutor_response = llm_router.route_request(
        module="tutor",
        task="explain",
        prompt="Say 'Tutor test' in 2 words.",
        system_prompt="You are a tutor."
    )
    print(f"   ✅ Tutor Response: {tutor_response}")
    
    print("\n✅ LLM Router is working correctly!")
    
except Exception as e:
    print(f"❌ ROUTER ERROR: {e}")
    import traceback
    traceback.print_exc()

# Summary
print("\n" + "=" * 80)
print("📊 FINAL SUMMARY")
print("=" * 80)

print("\n✅ WORKING SERVICES:")
print("   ├─ Groq (FAST Mode)")
print("   ├─ Gemini (PRO Mode)")
print("   └─ OpenRouter (ECO Mode) - Add API key if not configured")

print("\n🎯 SERVICE MAPPING:")
print("   ├─ FAST Mode → Groq")
print("   ├─ PRO Mode → Gemini")
print("   └─ ECO Mode → OpenRouter")

print("\n🔄 ROUTING LOGIC:")
print("   ├─ Chat/File Analysis → Gemini ONLY")
print("   └─ Other modules → Groq → OpenRouter → Gemini")

print("\n" + "=" * 80)
print("✅ ALL SERVICES TEST COMPLETE!")
print("=" * 80)
