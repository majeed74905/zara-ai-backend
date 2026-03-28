# 🚀 Quick Start Guide - Automatic Model Switching

## What You Got

I've implemented a **smart automatic model switching system** for Zara AI that:

✅ **Automatically switches** between Gemini models when rate limits are hit  
✅ **Tracks usage** for each model in real-time  
✅ **Shows status** via a beautiful floating button  
✅ **Persists data** across browser sessions  
✅ **Provides transparency** - you always know which model is being used  

## Visual Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    USER SENDS MESSAGE                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Check Best Available Model                     │
│  (Looks at rate limits for all models)                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  TRY #1: Gemini 2.5 Flash (5 RPM, 20 RPD)                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                    Rate Limited?
                    ╱         ╲
                  NO           YES
                  │             │
                  ▼             ▼
            ┌─────────┐   ┌──────────────────────────────────┐
            │ SUCCESS │   │ TRY #2: Gemini 2.5 Flash Lite    │
            │ Return  │   │ (10 RPM, 20 RPD)                 │
            └─────────┘   └────────────┬─────────────────────┘
                                       │
                                  Rate Limited?
                                  ╱         ╲
                                NO           YES
                                │             │
                                ▼             ▼
                          ┌─────────┐   ┌──────────────────────┐
                          │ SUCCESS │   │ TRY #3: Gemini 3     │
                          │ Return  │   │ Flash (5 RPM, 20 RPD)│
                          └─────────┘   └────────┬─────────────┘
                                                 │
                                            Rate Limited?
                                            ╱         ╲
                                          NO           YES
                                          │             │
                                          ▼             ▼
                                    ┌─────────┐   ┌─────────────┐
                                    │ SUCCESS │   │ TRY #4:     │
                                    │ Return  │   │ Gemini 1.5  │
                                    └─────────┘   │ Flash       │
                                                  └──────┬──────┘
                                                         │
                                                         ▼
                                                  ┌─────────────┐
                                                  │ Success or  │
                                                  │ Show Error  │
                                                  └─────────────┘
```

## How to Use

### 1. Run the Frontend

```bash
cd "c:\Users\majeed\Downloads\zara-ai-assists (Modify)\frontend"
npm run dev
```

### 2. Open in Browser

Navigate to: `http://localhost:5173` (or whatever port Vite shows)

### 3. Look for the Model Status Button

In the **bottom-right corner**, you'll see:

```
┌─────────────────────────┐
│ 🤖 Gemini 2.5 Flash    │
└─────────────────────────┘
```

### 4. Click to View Status

A beautiful panel will open showing:

```
╔═══════════════════════════════════════════════════════╗
║            🤖 AI Model Status                         ║
╠═══════════════════════════════════════════════════════╣
║                                                       ║
║  #1  Gemini 2.5 Flash              ✓ Available       ║
║      Requests/Min:  3/5   [████░░░░░░]               ║
║      Requests/Day:  15/20 [███████░░░]               ║
║                                                       ║
║  #2  Gemini 2.5 Flash Lite         ✓ Available       ║
║      Requests/Min:  0/10  [░░░░░░░░░░]               ║
║      Requests/Day:  0/20  [░░░░░░░░░░]               ║
║                                                       ║
║  #3  Gemini 3 Flash                ✓ Available       ║
║      Requests/Min:  2/5   [████░░░░░░]               ║
║      Requests/Day:  11/20 [█████░░░░░]               ║
║                                                       ║
║  #4  Gemini 1.5 Flash              ✓ Available       ║
║      Requests/Min:  0/15  [░░░░░░░░░░]               ║
║      Requests/Day:  0/1500[░░░░░░░░░░]               ║
║                                                       ║
║           [🔄 Reset All Trackers]                     ║
╚═══════════════════════════════════════════════════════╝
```

### 5. Send Messages

Just chat normally! The system will:
- Automatically select the best model
- Switch models if rate limits are hit
- Show you which model is being used
- Track all usage in real-time

## What Happens When You Chat

### Normal Chat
```
You: "Hello, how are you?"

[System uses Gemini 2.5 Flash]

Zara AI: "Hello! I'm doing great, thank you for asking! 
How can I help you today?"
```

### When Rate Limit is Hit
```
You: "Tell me about AI"

[System tries Gemini 2.5 Flash → Rate Limited!]
[System switches to Gemini 2.5 Flash Lite]

Zara AI: "🤖 Using Gemini 2.5 Flash Lite

Artificial Intelligence (AI) refers to..."
```

### When All Models are Limited
```
You: "Hello"

[All models are rate limited]

Error: "⚠️ All AI models are currently rate-limited.

Please wait a moment and try again.

Status:
• Gemini 2.5 Flash: 5/5 requests/min, 20/20 requests/day
• Gemini 2.5 Flash Lite: 10/10 requests/min, 20/20 requests/day
• Gemini 3 Flash: 5/5 requests/min, 20/20 requests/day
• Gemini 1.5 Flash: 15/15 requests/min, 1500/1500 requests/day"
```

## Console Logs

Open browser DevTools (F12) to see detailed logs:

```
[Gemini REST] Attempt 1/4: Using Gemini 2.5 Flash (3/5 RPM, 15/20 RPD)
[Gemini REST] ✓ Successfully completed with Gemini 2.5 Flash
```

When switching:
```
[Gemini REST] Attempt 1/4: Using Gemini 2.5 Flash (5/5 RPM, 20/20 RPD)
[Gemini REST] Gemini 2.5 Flash rate limited. Trying next model...
[Gemini REST] Attempt 2/4: Using Gemini 2.5 Flash Lite (0/10 RPM, 0/20 RPD)
[Gemini REST] ✓ Successfully completed with Gemini 2.5 Flash Lite
```

## Testing the System

### Test 1: Normal Operation
1. Send a message
2. Check console - should use Gemini 2.5 Flash
3. Response should appear normally

### Test 2: View Status
1. Click the 🤖 button
2. See all models and their usage
3. Close panel

### Test 3: Rapid Messages (Trigger Rate Limit)
1. Send 5+ messages quickly
2. Watch console for model switching
3. See notification when model changes

### Test 4: Reset Trackers
1. Click 🤖 button
2. Click "Reset All Trackers"
3. Confirm
4. All counters should reset to 0

## Files to Review

1. **`AUTO_MODEL_SWITCHING.md`** - Full documentation
2. **`IMPLEMENTATION_SUMMARY.md`** - Technical details
3. **`frontend/services/modelManager.ts`** - Core logic
4. **`frontend/components/ModelStatus.tsx`** - UI component
5. **`frontend/services/geminiRest.ts`** - Integration

## Troubleshooting

### Issue: Button not showing
- **Solution**: Clear browser cache and reload

### Issue: Models not switching
- **Solution**: Check browser console for errors

### Issue: All models showing as limited
- **Solution**: Click "Reset All Trackers" or wait for cooldown

### Issue: Compilation errors
- **Solution**: Run `npm install` and restart dev server

## Key Features

🎯 **Smart Selection** - Always picks the best available model  
🔄 **Automatic Fallback** - Seamlessly switches when needed  
📊 **Real-time Tracking** - See usage for all models  
💾 **Persistent Storage** - Survives page refreshes  
🎨 **Beautiful UI** - Modern, gradient design  
🔍 **Transparency** - Always know which model is active  
⚡ **Fast** - Minimal overhead  
🛠️ **Configurable** - Easy to add models or adjust limits  

## Model Priority

1. **Gemini 2.5 Flash** - Primary (fastest, most capable)
2. **Gemini 2.5 Flash Lite** - Fallback 1 (higher RPM)
3. **Gemini 3 Flash** - Fallback 2 (alternative)
4. **Gemini 1.5 Flash** - Fallback 3 (legacy, high limits)

## Rate Limits

| Model | RPM | TPM | RPD |
|-------|-----|-----|-----|
| Gemini 2.5 Flash | 5 | 250K | 20 |
| Gemini 2.5 Flash Lite | 10 | 250K | 20 |
| Gemini 3 Flash | 5 | 250K | 20 |
| Gemini 1.5 Flash | 15 | 1M | 1500 |

## Next Steps

1. ✅ Run `npm run dev`
2. ✅ Open browser
3. ✅ Click 🤖 button to see status
4. ✅ Send messages to test
5. ✅ Watch console logs
6. ✅ Enjoy automatic model switching!

---

**That's it!** Your Zara AI now has intelligent automatic model switching. 🎉

No more rate limit errors! The system handles everything automatically.
