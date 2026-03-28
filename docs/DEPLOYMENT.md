# Zara AI - Image Generation Module Deployment Guide

## 1. Backend Deployment (Railway / Render)

### Option A: Railway
1. **Connect GitHub**: linking this repository.
2. **Setup Service**: Select the `backend` folder as the root directory.
3. **Environment Variables**:
   - `HUGGINGFACE_API_KEY`: Get a free token from https://huggingface.co/settings/tokens
   - `SECRET_KEY`: Generate a secure random string.
   - `DATABASE_URL`: Railway provides a PostgreSQL database variable automatically.
   - `API_V1_STR`: `/api/v1`
4. **Build Command**: `pip install -r requirements.txt` (Railway detects this automatically).
5. **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Option B: Render
1. **New Web Service**: Connect your repo.
2. **Root Directory**: `backend`
3. **Build Command**: `pip install -r requirements.txt`
4. **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port 10000`
5. **Environment Variables**: Add same variables as above.

## 2. Frontend Deployment (Netlify)

1. **New Site from Git**: Connect your repo.
2. **Build Settings**:
   - **Base directory**: `frontend`
   - **Build command**: `npm run build` (or `vite build`)
   - **Publish directory**: `dist`
3. **Environment Variables**:
   - `VITE_API_URL`: The URL of your deployed backend (e.g., `https://zara-backend.up.railway.app/api/v1`)
     *IMPORTANT*: Ensure `/api/v1` is included if your backend expects it, or just the base domain depending on your configuration. Code uses `${API_URL}/image-generation...`.

## 3. Folder Structure Overview

```
zara-ai-assists/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── image_generation.py  # NEW: Image Gen Router
│   │   ├── schemas/
│   │   │   └── image.py             # NEW: Pydantic Models
│   │   ├── main.py                  # UPDATED: Router inclusion
│   │   └── core/config.py           # UPDATED: Env config
│   ├── requirements.txt
│   └── .env.example                 # NEW: Example config
└── frontend/
    ├── components/
    │   └── ImageMode.tsx            # UPDATED: UI with Style Select & Backend Integration
    ├── services/
    │   └── imageService.ts          # NEW: Service to call backend
    └── vite-env.d.ts                # NEW: Type definitions
```

## 4. Verification

1. **Backend**: 
   - Test POST to `/api/v1/image-generation/generate-image` with body `{"prompt": "test", "style": "realistic"}`.
   - Headers: `Authorization` not needed for this endpoint unless specific auth is added (currently open).
2. **Frontend**:
   - Navigate to Image Studio.
   - Select "Generate" tab.
   - Select Style.
   - Enter prompt and click PROCESS.
   - Verify image appears.
