import sys
import os
sys.path.append(os.getcwd())

print("=" * 70)
print("VERIFYING OPENROUTER MIGRATION")
print("=" * 70)

try:
    print("\n1. Importing OpenRouter Service...")
    from app.services.models.openrouter_service import OpenRouterService
    print("   ✅ OpenRouter Service imported successfully")
    
    print("\n2. Importing LLM Router...")
    from app.services.llm_router import llm_router
    print("   ✅ LLM Router imported successfully")
    
    print("\n3. Checking Router Services...")
    print(f"   - Gemini: {'✅ Configured' if llm_router.gemini.health_check() else '⚠️ No API key'}")
    print(f"   - OpenRouter: {'✅ Configured' if llm_router.openrouter.health_check() else '⚠️ No API key (expected)'}")
    print(f"   - Groq: {'✅ Configured' if llm_router.groq.health_check() else '⚠️ No API key'}")
    
    print("\n4. Verifying No Together AI References...")
    # Check if router has together attribute
    if hasattr(llm_router, 'together'):
        print("   ❌ ERROR: Router still has 'together' attribute!")
        sys.exit(1)
    else:
        print("   ✅ Router does not have 'together' attribute")
    
    # Check if router has openrouter attribute
    if hasattr(llm_router, 'openrouter'):
        print("   ✅ Router has 'openrouter' attribute")
    else:
        print("   ❌ ERROR: Router missing 'openrouter' attribute!")
        sys.exit(1)
    
    print("\n5. Checking DeepSeek References...")
    if hasattr(llm_router, 'deepseek'):
        print("   ❌ ERROR: Router still has 'deepseek' attribute!")
        sys.exit(1)
    else:
        print("   ✅ Router does not have 'deepseek' attribute")
    
    print("\n" + "=" * 70)
    print("✅ MIGRATION VERIFICATION PASSED!")
    print("=" * 70)
    print("\n📋 Summary:")
    print("   ✅ OpenRouter service created and importable")
    print("   ✅ LLM Router updated to use OpenRouter")
    print("   ✅ No Together AI references in active router")
    print("   ✅ No DeepSeek references in active router")
    print("   ✅ All imports working correctly")
    print("\n🎯 Next Step: Add OPENROUTER_API_KEY to .env file")
    print("   Get your key at: https://openrouter.ai/keys")
    print("=" * 70)
    
except Exception as e:
    print(f"\n❌ VERIFICATION FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
