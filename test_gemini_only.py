import sys
import os
sys.path.append(os.getcwd())

from app.services.models.gemini_service import GeminiService

print("=" * 70)
print("TESTING GEMINI SERVICE WITH NEW API KEY")
print("=" * 70)

try:
    gemini = GeminiService()
    
    if not gemini.health_check():
        print("❌ Gemini service is not configured (no API key found)")
        sys.exit(1)
    
    print(f"\n✅ Service initialized successfully")
    print(f"📌 Model: {gemini.model_name}")
    
    print("\n🧪 Testing API call...")
    print("-" * 70)
    
    response = gemini.generate(
        system_prompt="You are a helpful assistant.",
        user_prompt="Say 'Hello, Gemini is working!' in exactly 5 words."
    )
    
    print(f"\n✅ SUCCESS! Response received:")
    print(f"📝 {response}")
    print("\n" + "=" * 70)
    print("✅ GEMINI API KEY IS VALID AND WORKING!")
    print("=" * 70)
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    print("\n" + "=" * 70)
    print("❌ GEMINI API KEY TEST FAILED")
    print("=" * 70)
    
    # Check error type
    if "400" in str(e) or "invalid" in str(e).lower():
        print("\n⚠️  Issue: Invalid API key")
        print("💡 Action: Verify the key at https://aistudio.google.com/apikey")
    elif "404" in str(e):
        print("\n⚠️  Issue: Model not found")
        print("💡 Action: Check if model name is correct")
    elif "429" in str(e):
        print("\n⚠️  Issue: Rate limit exceeded")
        print("💡 Action: Wait a moment and try again")
    
    sys.exit(1)
