# 🚀 RENDER BACKEND DEPLOYMENT GUIDE

To deploy your backend to Render, follow these steps:

## 1. Create a New Web Service
1. Sign in to [Render Dashboard](https://dashboard.render.com).
2. Click **New +** → **Web Service**.
3. Connect your Git repository.

## 2. Configure Service Settings
- **Name**: `zara-ai-backend` (or your preferred name)
- **Environment**: `Python 3`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn -w 1 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:$PORT`

## 3. Environment Variables (CRITICAL)
Add these variables in the **Environment** tab of your Render service:

| Key | Value (Example) |
| :--- | :--- |
| `PROJECT_NAME` | `Zara AI` |
| `SECRET_KEY` | `Generate a long random string` |
| `DATABASE_URL` | `your_postgresql_url` (Ensure it ends with `?sslmode=require`) |
| `FRONTEND_URL` | `https://zara-ai-assists.netlify.app` |
| `GOOGLE_CALLBACK_URL` | `https://your-service-name.onrender.com/api/v1/auth/google/callback` |
| `RESEND_API_KEY` | `re_...` (Your Resend Key) |
| `BREVO_SMTP_PASS` | `xkeysib-...` (Your Brevo API Key) |
| `EMAILS_FROM_EMAIL` | `majeed74905@gmail.com` (Verified Sender) |
| `API_KEY` | `your_google_ai_api_key` |
| `GROQ_API_KEY` | `...` |
| `STABILITY_API_KEY` | `...` |

## 4. Database Setup
If you haven't already:
1. Create a PostgreSQL database on [Render](https://dashboard.render.com/new/database) or [Neon.tech](https://neon.tech).
2. Grab the Internal/External URL and put it in the `DATABASE_URL` environment variable.

## 5. Google OAuth Update
Go to your **Google Cloud Console**:
1. Add `https://your-service-name.onrender.com` to **Authorized Redirect URIs**.
2. Specifically add: `https://your-service-name.onrender.com/api/v1/auth/google/callback`

---
### ✅ Deployment Features Included
- **Auto-Migration**: The app is configured to auto-create tables on startup.
- **Production Email**: Uses Resend API (Primary) and Brevo API (Fallback).
- **Security**: Token expiry set to production-safe 15 minutes.
