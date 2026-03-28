# 🚀 PRODUCTION DEPLOYMENT GUIDE (RENDER + NETLIFY)

## 1. RENDER BACKEND (.env)
Copy these to Render → Dashboard → Your Service → Environment Variables.

```env
PROJECT_NAME=Zara AI
API_V1_STR=/api/v1
SECRET_KEY=A_VERY_STRONG_RANDOM_SECRET_FOR_JWT_SIGNING
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
ALGORITHM=HS256

# Database (Neon/ElephantSQL)
DATABASE_URL=postgresql://user:pass@host/db?sslmode=require

# Google AI (Gemini)
API_KEY=AIzaSy... (Your Google API Key)

# Google OAuth (APIs & Services -> Credentials)
GOOGLE_CLIENT_ID=...apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-...
GOOGLE_CALLBACK_URL=https://my-project-5u48.onrender.com/api/v1/auth/google/callback
FRONTEND_URL=https://zara-ai-assists.netlify.app

# SMTP & Email (Dual Provider Strategy for reliability)
# 1. PRIMARY: Resend API (Critical: Verification, Reset, Magic Links)
# Sender will be onboarding@resend.dev (No domain needed)
RESEND_API_KEY=re_... (Your Resend API Key)

# 2. SECONDARY: Brevo SMTP (Non-critical: Welcome, Alerts)
BREVO_SMTP_HOST=smtp-relay.brevo.com
BREVO_SMTP_PORT=587
BREVO_SMTP_USER=... (Brevo SMTP Key Login)
BREVO_SMTP_PASS=... (Brevo SMTP Key Password)

EMAILS_FROM_EMAIL=... (Your verified Brevo sender email)
EMAILS_FROM_NAME=Zara AI Security

# Other APIs
GROQ_API_KEY=gsk_...
DEEPSEEK_API_KEY=sk-...
STABILITY_API_KEY=sk-...
```

---

## 2. NETLIFY FRONTEND (.env)
Copy these to Netlify → Site settings → Environment variables.

```env
VITE_API_URL=https://my-project-5u48.onrender.com/api/v1
VITE_GOOGLE_CLIENT_ID=306255418398-a1825de9qn06b9v35mbpc2kvad9g1oep.apps.googleusercontent.com
```

---

## 3. GOOGLE CLOUD CONSOLE SETUP
Go to **APIs & Services > Credentials > OAuth Client ID**.

### **Authorized JavaScript Origins**
- `http://localhost:5173`
- `https://zara-ai-assists.netlify.app`

### **Authorized Redirect URIs**
- `http://localhost:8000/api/v1/auth/google/callback`
- `https://my-project-5u48.onrender.com/api/v1/auth/google/callback`

---

## 4. ROOT CAUSE ANALYSIS SUMMARY
| Issue | Root Cause | Fix Applied |
| :--- | :--- | :--- |
| **Google Error 400** | Missing or partial Redirect URI in Google Console vs Code. | Implemented explicit `/callback` endpoint and synced URIs. |
| **JSON Parse Error** | Frontend calling `localhost:8000` or relative paths on Netlify. | Switched to absolute `VITE_API_URL` env variable in all services. |
| **SMTP Failures** | Incorrect port/secure settings or missing App Password. | Added `SMTP_SECURE` logic and STARTTLS support in `email.py`. |
| **Localhost Redirects**| Backend redirecting to `localhost:3000` after OAuth. | Added `FRONTEND_URL` setting for dynamic production redirection. |
