# Zara AI - Manual Testing Instructions

## Current Status
✅ **Frontend**: Running successfully on http://localhost:3000
❌ **Backend**: Not running (optional for basic chat functionality)

## How to Test Zara AI Chat

### Step 1: Open the Application
1. Open your web browser
2. Navigate to: **http://localhost:3000**
3. You should see the Zara AI interface with a welcome screen

### Step 2: Test the Chat Interface
1. Look for the chat input area at the bottom of the screen
2. Type: **"hello"**
3. Press **Enter** or click the send button

### Expected Response
Zara AI should respond with a greeting. Based on the system prompt, it follows a "Conversational Mirroring Protocol" and should respond naturally, for example:
- "Hi! How can I help you today? 😊"
- "Hello! What would you like to do?"

### What to Check
- ✅ Does the message appear in the chat?
- ✅ Does Zara AI respond within a few seconds?
- ✅ Is the response coherent and friendly?
- ✅ Are there any error messages?

## Features Available (Without Backend)
- ✅ **Chat Mode**: Direct conversation with Gemini AI
- ✅ **App Builder**: Build applications with AI assistance
- ✅ **Code Mode**: Code assistance and generation
- ✅ **Student Mode**: Educational tutoring
- ✅ **Image Mode**: Image generation and analysis
- ✅ **Video Mode**: Video generation
- ✅ **Live Mode**: Real-time voice interaction

## Features Requiring Backend
- ❌ **User Authentication**: Sign up, login, OTP verification
- ❌ **Chat History Sync**: Saving chats to database
- ❌ **Multi-device Sync**: Access chats from different devices

## Technical Details

### Frontend Configuration
- **Port**: 3000
- **Gemini API Key**: Configured in `frontend/.env`
- **Model**: gemini-1.5-flash
- **Framework**: React 18 + Vite 7

### Chat Implementation
The chat uses Google Gemini API directly from the browser:
- File: `frontend/services/gemini.ts`
- Function: `sendMessageToGeminiStream()`
- Streaming: Yes (real-time response)

### System Identity
Zara AI identifies as:
> "You are a highly advanced, empathetic, and professional AI companion developed by Mohammed Majeed"

### Special Features
1. **Emotional Support Mode** (Heart icon): Activates empathetic responses
2. **Google Search** (Globe icon): Enables web grounding
3. **Deep Thinking** (Brain icon): Uses extended reasoning
4. **Offline Mode**: Basic responses when internet is unavailable

## Troubleshooting

### If Zara AI doesn't respond:
1. Check browser console (F12) for errors
2. Verify the Gemini API key is valid
3. Check if you have internet connection
4. Look for quota exceeded errors (API limits)

### If you see "QUOTA EXCEEDED":
The Gemini API has rate limits. Wait 30 seconds and try again.

### If the page doesn't load:
1. Ensure the dev server is running: `npm run dev` in the frontend folder
2. Check if port 3000 is available
3. Clear browser cache and reload

## Backend Setup (Optional)

To enable authentication and database features:

1. Install Python dependencies (requires PostgreSQL drivers)
2. Run: `uvicorn app.main:app --reload` from the backend folder
3. Backend will start on http://localhost:8000

Note: Backend requires proper PostgreSQL setup and may need additional configuration.

---

**Developed by**: Mohammed Majeed
**Last Updated**: January 24, 2026
