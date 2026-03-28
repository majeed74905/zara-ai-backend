# Guest-First Architecture for Zara AI Assist

## 1. Project Analysis
**Core Philosophy:** "Guest Mode First". The application provides full AI utility to anonymous users. Authentication is strictly a value-add feature for data persistence (history).

### User Flows
- **Anonymous User**: Opens app -> Uses Chat/Tools -> Backend processes request -> Response returned -> **NO DATA SAVED**.
- **Authenticated User**: Opens app -> Logs in -> Backend issues Token -> Uses Chat -> Backend processes request -> Response returned -> **DATA SAVED to DB**.

### Security & Data Boundaries
- **Trust Boundary**: The Frontend is untrusted. The Backend is the sole enforcer of the "No Auth = No History" rule.
- **Data Isolation**: History records in the database (`prompt_history`) have a non-nullable `user_id`. It is physically impossible to store an orphan record.

## 2. System Architecture
```mermaid
graph TD
    User[User (Guest/Auth)] -->|HTTPS| Frontend[React SPA]
    Frontend -->|JSON + Optional Bearer Token| Backend[FastAPI Gateway]
    
    subgraph "Backend Services"
        Backend -->|Strict Logic| AuthCheck{Has Token?}
        AuthCheck -->|Yes| UserCtx[Load User Context]
        AuthCheck -->|No| GuestCtx[Guest Context]
        
        UserCtx --> AI_Engine[AI Router (Groq/Gemini/DS)]
        GuestCtx --> AI_Engine
        
        AI_Engine -->|Response| SaveLogic{Context == User?}
        SaveLogic -->|Yes| DB[(PostgreSQL)]
        SaveLogic -->|No| Discard[Discard History]
    end
```

## 3. Authentication Strategy
- **Method**: OAuth2 with Password Flow (Bearer Token).
- **Token Lifecycle**:
    -   **Access Token**: Short-lived (30 min). Used for API access.
    -   **Refresh Token**: Long-lived (7 days). Used to renew access.
- **Non-Blocking**: The frontend `ChatService` attempts to attach a token if available, but proceeds without one if not. API endpoints are designed to accept both states.

## 4. Backend Enforcement (The Rule)
The backend enforces the rules through Dependency Injection in FastAPI.

### Middleware / Dependency Logic
- `get_current_user_optional`: Returns `User` object if valid token presented, else `None`. Does **NOT** raise 401 for missing token.
- `get_current_active_user`: Returns `User` or raises 401. Used **ONLY** for history retrieval endpoints (`GET /history`).

### API Rules
1.  `POST /api/chat`: Uses `get_current_user_optional`.
    -   If `user` is found: **Save** prompt/response to DB.
    -   If `user` is `None`: **Do not save**.
2.  `GET /api/history`: Uses `get_current_active_user`.
    -   If `user` is missing: Request rejected (401). Use is blocked from seeing history.

## 5. Database Design
The schema enforces constraint integrity.

```python
class PromptHistory(Base):
    __tablename__ = "prompt_history"
    id = Column(Integer, primary_key=True)
    # NON-NULLABLE FOREIGN KEY is the ultimate safeguard
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False) 
    prompt = Column(Text, nullable=False)
    response = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=func.now())
```

- **Validation**: If the application logic fails and tries to insert a record for a Guest (user_id=None), the Database Engine itself will throw an `IntegrityError` and reject the write. This is the "Fail-Safe".

## 6. Docker Architecture
Standard microservices pattern.
- **frontend**: Nginx serving React static build.
- **backend**: Uvicorn/FastAPI.
- **db**: PostgreSQL.

**Isolation**: The `db` container is ONLY accessible by `backend`. Authenticated or not, the frontend can never touch the DB directly.

## 7. Failure & Edge Cases
- **Token Expiry during Chat**: Request proceeds as "Guest". History for that specific message is validly *not saved* (or negotiated via client re-login). *Design Choice: Fail gracefully to Guest mode or prompt re-login.* -> **Decision**: Prompt re-login if token was present but expired; treat as Guest if no token.
- **Logout**: Frontend discards token. Next request is Guest. Backend sees no user. No history saved. Old history remains in DB but is inaccessible.

## 8. Final Validation Checklist
1.  [x] **App works without sign-in**: `/api/chat` endpoint does not require auth.
2.  [x] **History never saves without sign-in**: `PromptHistory` requires `user_id`. Logic checks for user presence.
3.  [x] **History never shows without sign-in**: `/api/history` endpoint requires strict auth.
4.  [x] **DB Enforces Rule**: `nullable=False` constraint on `user_id`.
