# 🤖 Automatic Model Switching Feature

## Overview

Zara AI now includes **intelligent automatic model switching** that seamlessly switches between different Gemini models when rate limits are hit. This ensures uninterrupted service and optimal performance.

## How It Works

### Model Priority System

The system tries models in the following priority order:

1. **Gemini 2.5 Flash** (Primary)
   - 5 requests/minute
   - 250K tokens/minute
   - 20 requests/day

2. **Gemini 2.5 Flash Lite** (Fallback 1)
   - 10 requests/minute
   - 250K tokens/minute
   - 20 requests/day

3. **Gemini 3 Flash** (Fallback 2)
   - 5 requests/minute
   - 250K tokens/minute
   - 20 requests/day

4. **Gemini 1.5 Flash** (Fallback 3 - Legacy)
   - 15 requests/minute
   - 1M tokens/minute
   - 1,500 requests/day

### Automatic Switching Logic

1. **Rate Limit Detection**: When a model hits its rate limit (429 error), the system automatically marks it as blocked
2. **Fallback**: The system immediately tries the next available model in the priority list
3. **Retry Management**: Blocked models are automatically unblocked after their cooldown period
4. **Persistent Tracking**: Rate limit counters are saved to localStorage and persist across sessions

### Features

✅ **Seamless Switching** - Automatic fallback when limits are hit  
✅ **Real-time Tracking** - Monitor usage for all models  
✅ **Smart Recovery** - Automatic unblocking after cooldown  
✅ **User Notifications** - See which model is being used  
✅ **Visual Dashboard** - View status of all models  

## User Interface

### Model Status Button

A floating button in the bottom-right corner shows:
- 🤖 Icon
- Current active model name
- Click to open detailed status panel

### Model Status Panel

Shows for each model:
- **Priority ranking** (#1, #2, etc.)
- **Availability status** (✓ Available / ✗ Limited)
- **Requests per minute** with progress bar
- **Requests per day** with progress bar
- **Cooldown timer** if blocked

### Reset Function

For testing purposes, you can reset all rate limit trackers:
1. Click the Model Status button
2. Click "🔄 Reset All Trackers"
3. Confirm the action

## Technical Implementation

### Files Created

1. **`frontend/services/modelManager.ts`**
   - Core model management logic
   - Rate limit tracking
   - Model selection algorithm
   - Persistent storage

2. **`frontend/components/ModelStatus.tsx`**
   - React component for status display
   - Real-time updates
   - Interactive UI

3. **`frontend/styles/ModelStatus.css`**
   - Beautiful gradient styling
   - Smooth animations
   - Responsive design

### Files Modified

1. **`frontend/services/geminiRest.ts`**
   - Integrated model manager
   - Automatic retry logic
   - Error handling for rate limits

2. **`frontend/App.tsx`**
   - Added ModelStatusButton component
   - Integrated into main layout

## Usage Examples

### Normal Operation

```typescript
// User sends a message
// System automatically selects best available model
// Message is processed successfully
```

### Rate Limit Hit

```typescript
// User sends a message
// Gemini 2.5 Flash returns 429 (rate limited)
// System automatically tries Gemini 2.5 Flash Lite
// Message is processed successfully
// User sees: "🤖 Using Gemini 2.5 Flash Lite"
```

### All Models Limited

```typescript
// User sends a message
// All models are rate limited
// System shows detailed error:
// "⚠️ All AI models are currently rate-limited.
//  Please wait a moment and try again.
//  
//  Status:
//  • Gemini 2.5 Flash: 5/5 requests/min, 20/20 requests/day
//  • Gemini 2.5 Flash Lite: 10/10 requests/min, 20/20 requests/day
//  ..."
```

## Rate Limit Tracking

### Storage Format

```json
{
  "gemini-2.5-flash": {
    "modelName": "gemini-2.5-flash",
    "requestCount": 3,
    "tokenCount": 450,
    "dailyRequestCount": 15,
    "lastMinuteReset": 1706097600000,
    "lastDayReset": 1706097600000,
    "isBlocked": false
  }
}
```

### Automatic Resets

- **Minute counter**: Resets every 60 seconds
- **Daily counter**: Resets every 24 hours
- **Block status**: Clears after retry-after period

## Configuration

### Adding New Models

To add a new model to the rotation:

```typescript
// In modelManager.ts
export const AVAILABLE_MODELS: ModelConfig[] = [
    // ... existing models
    {
        name: 'new-model-name',
        displayName: 'New Model Display Name',
        rpm: 10,  // requests per minute
        tpm: 100000,  // tokens per minute
        rpd: 100,  // requests per day
        priority: 5  // lower = higher priority
    }
];
```

### Adjusting Rate Limits

Update the model configuration in `modelManager.ts`:

```typescript
{
    name: 'gemini-2.5-flash',
    displayName: 'Gemini 2.5 Flash',
    rpm: 10,  // Change this
    tpm: 500000,  // Change this
    rpd: 50,  // Change this
    priority: 1
}
```

## Benefits

1. **Uninterrupted Service**: Users rarely see rate limit errors
2. **Optimal Performance**: Always uses the best available model
3. **Transparency**: Users can see which model is being used
4. **Cost Efficiency**: Distributes load across multiple models
5. **Developer Friendly**: Easy to add new models or adjust limits

## Monitoring

### Console Logs

The system provides detailed console logging:

```
[Gemini REST] Attempt 1/4: Using Gemini 2.5 Flash (3/5 RPM, 15/20 RPD)
[Gemini REST] ✓ Successfully completed with Gemini 2.5 Flash
```

Or when switching:

```
[Gemini REST] Attempt 1/4: Using Gemini 2.5 Flash (5/5 RPM, 20/20 RPD)
[Gemini REST] Gemini 2.5 Flash rate limited. Trying next model...
[Gemini REST] Attempt 2/4: Using Gemini 2.5 Flash Lite (0/10 RPM, 0/20 RPD)
[Gemini REST] ✓ Successfully completed with Gemini 2.5 Flash Lite
```

### User Notifications

When a model switch occurs, users see:

```
🤖 Using Gemini 2.5 Flash Lite

[AI response continues here...]
```

## Troubleshooting

### Issue: All models showing as limited

**Solution**: 
1. Click the Model Status button
2. Check the cooldown timers
3. Wait for the shortest timer to expire
4. Or click "Reset All Trackers" for testing

### Issue: Model not switching automatically

**Solution**:
1. Check browser console for errors
2. Verify API key is valid
3. Check if localStorage is enabled
4. Clear browser cache and reload

### Issue: Wrong model being used

**Solution**:
1. Check model priority in `modelManager.ts`
2. Verify rate limits are correctly configured
3. Reset trackers to clear any stale data

## Future Enhancements

Potential improvements:

- [ ] Backend rate limit tracking (shared across users)
- [ ] Model performance analytics
- [ ] Custom model preferences
- [ ] Automatic model testing
- [ ] Smart model selection based on query type
- [ ] Cost optimization algorithms

## API Reference

### ModelManager

```typescript
// Get best available model
const modelInfo = modelManager.getBestAvailableModel();

// Record a successful request
modelManager.recordRequest(modelName, estimatedTokens);

// Record a rate limit error
modelManager.recordRateLimitError(modelName, retryAfterSeconds);

// Get status of all models
const status = modelManager.getModelStatus();

// Reset all trackers
modelManager.resetAll();
```

## License

This feature is part of Zara AI and follows the same license as the main project.

---

**Last Updated**: January 24, 2026  
**Version**: 1.0.0  
**Author**: Zara AI Team
