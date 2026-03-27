import sys
import os
sys.path.append(os.getcwd())

from app.services.models.openrouter_service import OpenRouterService

print("=" * 70)
print("TESTING OPENROUTER SERVICE (ECO MODE)")
print("=" * 70)

try:
    openrouter = OpenRouterService()
    
    if not openrouter.health_check():
        print("❌ OpenRouter service is not configured (no API key found)")
        print("\n💡 Action: Add OPENROUTER_API_KEY to .env file")
        print("   Get your key at: https://openrouter.ai/keys")
        sys.exit(1)
    
    print(f"\n✅ Service initialized successfully")
    print(f"📌 Model: {openrouter.model_name}")
    print(f"📌 Base URL: https://openrouter.ai/api/v1")
    
    print("\n🧪 Testing API call...")
    print("-" * 70)
    
    # Test with ECO mode system prompt
    eco_system_prompt = """You are ZARA ECO.
You are efficient, concise, and cost-aware.
You provide short, clear answers.
You avoid unnecessary explanations."""
    
    response = openrouter.generate(
        system_prompt=eco_system_prompt,
        user_prompt="Explain what Python is in exactly 15 words."
    )
    
    print(f"\n✅ SUCCESS! Response received:")
    print(f"📝 {response}")
    print(f"\n📊 Response length: {len(response.split())} words")
    print("\n" + "=" * 70)
    print("✅ OPENROUTER API KEY IS VALID AND WORKING!")
    print("=" * 70)
    print("\n🎉 ECO Mode is now powered by OpenRouter!")
    print("   - Cost-effective")
    print("   - Fast responses")
    print("   - Access to multiple models")
    print("   - Flexible and scalable")
    print("=" * 70)
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    print("\n" + "=" * 70)
    print("❌ OPENROUTER API KEY TEST FAILED")
    print("=" * 70)
    
    # Check error type
    if "401" in str(e) or "invalid" in str(e).lower() or "unauthorized" in str(e).lower():
        print("\n⚠️  Issue: Invalid API key")
        print("💡 Action: Verify the key at https://openrouter.ai/keys")
    elif "429" in str(e):
        print("\n⚠️  Issue: Rate limit exceeded")
        print("💡 Action: Wait a moment and try again")
    elif "404" in str(e):
        print("\n⚠️  Issue: Model not found")
        print("💡 Action: Check if model name is correct")
    
    import traceback
    traceback.print_exc()
    sys.exit(1)
