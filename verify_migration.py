import sys
import os
sys.path.append(os.getcwd())

print("=" * 70)
print("VERIFYING MIGRATION - IMPORT CHECK")
print("=" * 70)

try:
    print("\n1. Importing Together AI Service...")
    from app.services.models.together_service import TogetherAIService
    print("   ✅ Together AI Service imported successfully")
    
    print("\n2. Importing LLM Router...")
    from app.services.llm_router import llm_router
    print("   ✅ LLM Router imported successfully")
    
    print("\n3. Checking Router Services...")
    print(f"   - Gemini: {'✅ Configured' if llm_router.gemini.health_check() else '⚠️ No API key'}")
    print(f"   - Together AI: {'✅ Configured' if llm_router.together.health_check() else '⚠️ No API key (expected)'}")
    print(f"   - Groq: {'✅ Configured' if llm_router.groq.health_check() else '⚠️ No API key'}")
    
    print("\n4. Verifying No DeepSeek Imports...")
    try:
        from app.services.models.deepseek_service import DeepSeekService
        print("   ⚠️ DeepSeek still importable (file exists for rollback)")
    except:
        print("   ✅ DeepSeek not in import path")
    
    # Check if router has deepseek attribute
    if hasattr(llm_router, 'deepseek'):
        print("   ❌ ERROR: Router still has 'deepseek' attribute!")
        sys.exit(1)
    else:
        print("   ✅ Router does not have 'deepseek' attribute")
    
    # Check if router has together attribute
    if hasattr(llm_router, 'together'):
        print("   ✅ Router has 'together' attribute")
    else:
        print("   ❌ ERROR: Router missing 'together' attribute!")
        sys.exit(1)
    
    print("\n" + "=" * 70)
    print("✅ MIGRATION VERIFICATION PASSED!")
    print("=" * 70)
    print("\n📋 Summary:")
    print("   ✅ Together AI service created and importable")
    print("   ✅ LLM Router updated to use Together AI")
    print("   ✅ No DeepSeek references in active router")
    print("   ✅ All imports working correctly")
    print("\n🎯 Next Step: Add TOGETHER_API_KEY to .env file")
    print("=" * 70)
    
except Exception as e:
    print(f"\n❌ VERIFICATION FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
