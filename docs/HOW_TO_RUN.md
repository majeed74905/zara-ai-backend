# 🚀 How to Run Zara AI Assists - Platinum Guide

Welcome to the **Zara AI Assists** ecosystem! This is a high-performance, full-stack AI platform integrating **FastAPI** (Python) for enterprise-grade logic and **React/Vite** (TypeScript) for a premium, ultra-responsive user experience.

---

## 📋 System Prerequisites

Ensure your environment meets these standards before initialization:

1.  **Node.js** (v18.0+) - [Official Website](https://nodejs.org/)
2.  **Python** (v3.10+) - [Official Website](https://python.org/)
3.  **Graphviz** (Required for AI Architecture Visualization) - [Download](https://graphviz.org/download/)
    *   *Windows Note*: After installation, ensure `dot.exe` is in your PATH or installed at `C:\Program Files\Graphviz\bin\dot.exe`.

---

## 🏗️ Deployment Architecture

*   **Core Backend**: FastAPI (Default: `http://localhost:8000`)
    *   Handles Multi-Model Routing (Groq, Gemini, DeepSeek).
    *   Secure SMTP Email & OTP Services.
    *   Advanced File & Image Analysis.
*   **Web UI**: React + Vite (Default: `http://localhost:3001` in this build)
    *   Dynamic Glassmorphism Interface.
    *   Real-time AI Chat & Diagram Rendering.

---

## 🛠️ Phase 1: Backend Initialization (Terminal 1)

1.  **Enter Directory**:
    ```powershell
    cd backend
    ```
2.  **Environment Setup**:
    ```powershell
    python -m venv venv
    .\venv\Scripts\activate  # Windows
    # source venv/bin/activate # Mac/Linux
    ```
3.  **Install Engine**:
    ```powershell
    pip install -r requirements.txt
    ```
4.  **Configuration**:
    *   Ensure `backend/.env` contains your `GOOGLE_API_KEY` and `SMTP_PASSWORD`.
    *   *Note*: Ensure variable values in `.env` are NOT wrapped in quotes (e.g., `ALGORITHM=HS256`).
5.  **Ignite Server**:
    ```powershell
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    ```
    ✅ **Goal**: `Application startup complete` visible in console.

---

## 🎨 Phase 2: Frontend Synthesis (Terminal 2)

1.  **Enter Directory**:
    ```powershell
    cd frontend
    ```
2.  **Sync Dependencies**:
    ```powershell
    npm install
    ```
3.  **Boot UI**:
    ```powershell
    npm run dev -- --port 3001 --host
    ```
    ✅ **Goal**: `VITE vX.X.X  ready` at `http://localhost:3001`.

---

## 🚀 Phase 3: Validation & Usage

1.  **Access Portal**: Go to **[http://localhost:3001](http://localhost:3001)**.
2.  **AI Analysis**: Drag & drop any PDF, Docx, or Image into the chat for instant analysis.
3.  **Architecture Mode**: Ask Zara to "Show me a flowchart of..." to see the **Graphviz Engine** render live diagrams.
4.  **Stability Mode**: Use the **Image Studio** tab to generate artwork via Stability AI.

---

## 🔑 Crucial .env Mapping

| Variable | Purpose | Status |
| :--- | :--- | :--- |
| `GOOGLE_API_KEY` | Powers Gemini Pro/Flash & Vision | **Essential** |
| `GROQ_API_KEY` | Powers Zara Fast (Llama 3.3) | Optional |
| `SMTP_PASSWORD` | App Password for Email Alerts | **Essential** |
| `DATABASE_URL` | PostgreSQL (Neon) storage | **Essential** |

---

## ❓ Troubleshooting & Support

*   **CORS Blocked**: Re-check your `.env` for quotes. The system is designed to handle `*` origins automatically once the environment is clean.
*   **Diagrams Not Rendering**: Ensure Graphviz is installed and the `dot` command is recognizable in your system terminal.
*   **Email Sending Failed**: Verify "Less Secure Apps" or "App Passwords" are enabled on your Gmail account.

---

**Designed for Innovation. Built for Performance.** 🤖
