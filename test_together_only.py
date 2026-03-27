import sys
import os
sys.path.append(os.getcwd())

from app.services.models.together_service import TogetherAIService

print("=" * 70)
print("TESTING TOGETHER AI SERVICE (ECO MODE)")
print("=" * 70)

try:
    together = TogetherAIService()
    
    if not together.health_check():
        print("❌ Together AI service is not configured (no API key found)")
        print("\n💡 Action: Add TOGETHER_API_KEY to .env file")
        print("   Get your key at: https://api.together.xyz/")
        sys.exit(1)
    
    print(f"\n✅ Service initialized successfully")
    print(f"📌 Model: {together.model_name}")
    
    print("\n🧪 Testing API call...")
    print("-" * 70)
    
    # Test with ECO mode system prompt
    eco_system_prompt = """You are ZARA ECO.
You are efficient, cost-aware, concise, and helpful.
You minimize token usage.
You avoid unnecessary verbosity.
You provide clear, direct answers."""
    
    response = together.generate(
        system_prompt=eco_system_prompt,
        user_prompt="Explain what Python is in exactly 15 words."
    )
    
    print(f"\n✅ SUCCESS! Response received:")
    print(f"📝 {response}")
    print(f"\n📊 Response length: {len(response.split())} words")
    print("\n" + "=" * 70)
    print("✅ TOGETHER AI API KEY IS VALID AND WORKING!")
    print("=" * 70)
    print("\n🎉 ECO Mode is now powered by Together AI!")
    print("   - Cost-effective")
    print("   - Fast responses")
    print("   - Efficient token usage")
    print("=" * 70)
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    print("\n" + "=" * 70)
    print("❌ TOGETHER AI API KEY TEST FAILED")
    print("=" * 70)
    
    # Check error type
    if "401" in str(e) or "invalid" in str(e).lower() or "unauthorized" in str(e).lower():
        print("\n⚠️  Issue: Invalid API key")
        print("💡 Action: Verify the key at https://api.together.xyz/")
    elif "429" in str(e):
        print("\n⚠️  Issue: Rate limit exceeded")
        print("💡 Action: Wait a moment and try again")
    elif "404" in str(e):
        print("\n⚠️  Issue: Model not found")
        print("💡 Action: Check if model name is correct")
    
    import traceback
    traceback.print_exc()
    sys.exit(1)
