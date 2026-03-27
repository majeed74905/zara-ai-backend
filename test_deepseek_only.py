import sys
import os
sys.path.append(os.getcwd())

from app.services.models.deepseek_service import DeepSeekService

print("=" * 70)
print("TESTING DEEPSEEK SERVICE WITH NEW API KEY")
print("=" * 70)

try:
    deepseek = DeepSeekService()
    
    if not deepseek.health_check():
        print("❌ DeepSeek service is not configured (no API key found)")
        sys.exit(1)
    
    print(f"\n✅ Service initialized successfully")
    print(f"📌 Model: {deepseek.model_name}")
    print(f"📌 API Key: sk-...{deepseek.client.api_key[-10:]}")
    
    print("\n🧪 Testing API call...")
    print("-" * 70)
    
    response = deepseek.generate(
        system_prompt="You are a helpful assistant.",
        user_prompt="Say 'Hello, DeepSeek is working!' in exactly 5 words."
    )
    
    print(f"\n✅ SUCCESS! Response received:")
    print(f"📝 {response}")
    print("\n" + "=" * 70)
    print("✅ DEEPSEEK API KEY IS VALID AND WORKING!")
    print("=" * 70)
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    print("\n" + "=" * 70)
    print("❌ DEEPSEEK API KEY TEST FAILED")
    print("=" * 70)
    
    # Check if it's a balance issue
    if "402" in str(e) or "Insufficient Balance" in str(e):
        print("\n⚠️  Issue: Insufficient account balance")
        print("💡 Action: Add credits at https://platform.deepseek.com/")
    elif "401" in str(e) or "invalid" in str(e).lower():
        print("\n⚠️  Issue: Invalid API key")
        print("💡 Action: Verify the key is correct")
    
    sys.exit(1)
