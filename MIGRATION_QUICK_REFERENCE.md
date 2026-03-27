# 🔁 DeepSeek → Together AI Migration - Quick Reference

## ✅ What Changed

| Component | Before | After |
|-----------|--------|-------|
| **ECO Mode Provider** | DeepSeek | Together AI |
| **Model** | deepseek-reasoner | Mixtral-8x7B-Instruct |
| **API Key** | DEEPSEEK_API_KEY | TOGETHER_API_KEY |
| **Service File** | deepseek_service.py | together_service.py |

## 🎯 Service Mapping

```
FAST Mode → Groq (llama-3.3-70b-versatile)
PRO Mode  → Gemini (gemini-2.5-flash)
ECO Mode  → Together AI (Mixtral-8x7B) ✨ NEW!
```

## 🔑 Get Your Together AI API Key

1. Visit: https://api.together.xyz/
2. Sign up or log in
3. Navigate to API Keys section
4. Create new API key
5. Copy the key

## ⚙️ Configuration

Add to `.env`:
```bash
TOGETHER_API_KEY=your_together_api_key_here
```

## 🧪 Testing

### Test Together AI Only
```bash
python test_together_only.py
```

### Test All Services
```bash
python test_all_services.py
```

### Test via API
```bash
curl -X POST http://localhost:8000/api/v1/ai/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Explain Python",
    "module": "tutor",
    "task": "explain"
  }'
```

## 📊 Expected Response

Together AI should respond for:
- `module: "tutor"`
- `module: "exam_prep"`
- `module: "code_architect"` with `task: "design"` or `task: "analyze"`

## 🔄 Rollback (If Needed)

1. Uncomment in `.env`: `DEEPSEEK_API_KEY=...`
2. In `llm_router.py`, change:
   - `from app.services.models.together_service import TogetherAIService` → `from app.services.models.deepseek_service import DeepSeekService`
   - `self.together = TogetherAIService()` → `self.deepseek = DeepSeekService()`
   - Replace all `self.together` with `self.deepseek`
3. Restart server

## ✅ Validation Checklist

- [ ] Together AI API key added to .env
- [ ] `python test_together_only.py` passes
- [ ] `python test_all_services.py` shows all 3 services working
- [ ] Tutor module uses Together AI
- [ ] Exam Prep module uses Together AI
- [ ] Logs show "Together AI" responses
- [ ] No errors in server logs
- [ ] Response quality is good
- [ ] Response time is fast

## 🎉 Benefits

✅ **Cost-Effective** - Better pricing than DeepSeek
✅ **Faster** - Lower latency responses
✅ **Reliable** - No balance issues
✅ **Production-Ready** - Stable infrastructure

## 📞 Support

If you encounter issues:
1. Check API key is correct
2. Verify .env file is loaded
3. Check server logs for errors
4. Test with `test_together_only.py`
5. Verify Together AI account has credits

## 🔗 Resources

- Together AI Docs: https://docs.together.ai/
- Together AI Dashboard: https://api.together.xyz/
- Migration Report: See `MIGRATION_REPORT.txt`
