import sys
import os
sys.path.append(os.getcwd())

from groq import Groq
from app.core.config import settings

print("=" * 70)
print("TESTING GROQ SERVICE WITH NEW API KEY")
print("=" * 70)

try:
    # Get API key from settings
    api_key = settings.GROQ_API_KEY
    
    if not api_key:
        print("❌ No Groq API key found in settings")
        sys.exit(1)
    
    print(f"\n✅ API Key loaded: gsk_...{api_key[-10:]}")
    
    # Initialize client
    client = Groq(api_key=api_key)
    
    # Test 1: llama-3.3-70b-versatile (current model in service)
    print("\n" + "=" * 70)
    print("TEST 1: llama-3.3-70b-versatile (Current Service Model)")
    print("=" * 70)
    
    response1 = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "user", "content": "Say 'Hello from Llama!' in exactly 4 words."}
        ],
        temperature=0.2,
        max_tokens=50
    )
    print(f"✅ Response: {response1.choices[0].message.content}")
    
    # Test 2: openai/gpt-oss-120b (model from your example)
    print("\n" + "=" * 70)
    print("TEST 2: openai/gpt-oss-120b (Your Requested Model)")
    print("=" * 70)
    
    response2 = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "user", "content": "Say 'Hello from GPT-OSS!' in exactly 4 words."}
        ],
        temperature=1,
        max_completion_tokens=100,
        top_p=1,
        reasoning_effort="medium"
    )
    print(f"✅ Response: {response2.choices[0].message.content}")
    
    # Test 3: Streaming test (like your example)
    print("\n" + "=" * 70)
    print("TEST 3: Streaming Response Test")
    print("=" * 70)
    
    print("🔄 Streaming response: ", end="", flush=True)
    completion = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "user", "content": "Write a short greeting in 10 words."}
        ],
        temperature=1,
        max_completion_tokens=100,
        top_p=1,
        reasoning_effort="medium",
        stream=True,
        stop=None
    )
    
    for chunk in completion:
        print(chunk.choices[0].delta.content or "", end="", flush=True)
    
    print("\n\n" + "=" * 70)
    print("✅ ALL GROQ TESTS PASSED!")
    print("=" * 70)
    print("\n✅ API Key is VALID and WORKING!")
    print("✅ Both models are accessible:")
    print("   - llama-3.3-70b-versatile ✅")
    print("   - openai/gpt-oss-120b ✅")
    print("=" * 70)
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    print("\n" + "=" * 70)
    print("❌ GROQ API KEY TEST FAILED")
    print("=" * 70)
    
    # Check error type
    if "401" in str(e) or "invalid" in str(e).lower():
        print("\n⚠️  Issue: Invalid API key")
        print("💡 Action: Verify the key at https://console.groq.com/")
    elif "429" in str(e):
        print("\n⚠️  Issue: Rate limit exceeded")
        print("💡 Action: Wait a moment and try again")
    elif "404" in str(e):
        print("\n⚠️  Issue: Model not found")
        print("💡 Action: Check if model name is correct")
    
    import traceback
    traceback.print_exc()
    sys.exit(1)
