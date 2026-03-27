
from typing import Dict, List, Optional
import time

# In-memory store for anonymous sessions
# Structure: { session_id: { "last_access": timestamp, "history": [ {"role": str, "content": str} ] } }
ANON_MEMORY_STORE: Dict[str, Dict] = {}

SESSION_TTL = 900  # 15 minutes expiration (Feature 10)

def clear_session(session_id: str):
    """Explicitly clears a session from memory."""
    if session_id in ANON_MEMORY_STORE:
        del ANON_MEMORY_STORE[session_id]

def get_anon_history(session_id: str) -> List[Dict[str, str]]:
    """Retrieves conversation history for an anonymous session."""
    cleanup_sessions()
    
    if session_id not in ANON_MEMORY_STORE:
        # Strict Expiry: If not in memory (expired or never existed), return empty.
        return []
    
    # Refresh access time
    ANON_MEMORY_STORE[session_id]['last_access'] = time.time()
    return ANON_MEMORY_STORE[session_id]['history']

def save_anon_history(session_id: str, user_message: str, ai_response: str):
    """Saves a turn to the anonymous memory store."""
    if session_id not in ANON_MEMORY_STORE:
        ANON_MEMORY_STORE[session_id] = {"last_access": time.time(), "history": []}
    
    history = ANON_MEMORY_STORE[session_id]['history']
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": ai_response})
    
    ANON_MEMORY_STORE[session_id]['last_access'] = time.time()

def cleanup_sessions():
    """Removes expired sessions."""
    current_time = time.time()
    expired = [
        sid for sid, data in ANON_MEMORY_STORE.items() 
        if current_time - data['last_access'] > SESSION_TTL
    ]
    for sid in expired:
        del ANON_MEMORY_STORE[sid]
