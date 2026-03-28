import json
import os
import math
from typing import Optional, Dict, Any
from google import genai
from app.core.config import settings

MEMORY_FILE_PATH = os.path.join(os.path.dirname(__file__), "zara_memory.json")

def _load_memory() -> list:
    if not os.path.exists(MEMORY_FILE_PATH):
        return []
    with open(MEMORY_FILE_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def _save_memory(data: list):
    with open(MEMORY_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    dot = sum(a*b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a*a for a in vec1))
    norm2 = math.sqrt(sum(b*b for b in vec2))
    return dot / (norm1 * norm2) if norm1 and norm2 else 0.0

async def _get_embedding(text: str) -> list[float]:
    if not settings.GEMINI_API_KEY:
        return []
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    response = await client.aio.models.embed_content(
        model='text-embedding-004',
        contents=text
    )
    return response.embeddings[0].values

async def search_knowledge(error_msg: str, threshold: float = 0.85) -> Optional[Dict[str, Any]]:
    """L5: Semantic vector search using AI embeddings to match similar bugs."""
    mem_list = _load_memory()
    if not mem_list:
        return None
        
    query_emb = await _get_embedding(error_msg)
    if not query_emb:
        return None
        
    best_match = None
    highest_sim = 0.0
    
    for item in mem_list:
        sim = _cosine_similarity(query_emb, item.get("embedding", []))
        if sim > highest_sim:
            highest_sim = sim
            best_match = item
            
    if highest_sim >= threshold:
        return best_match
    return None

async def store_learning(error_msg: str, fix_patch: str, pattern: str = "auto_fix_patch"):
    """Saves the functional fix to permanent intelligence store with vector footprint."""
    mem_list = _load_memory()
    embedding = await _get_embedding(error_msg)
    
    mem_list.append({
        "error_msg": error_msg,
        "fix_patch": fix_patch,
        "pattern": pattern,
        "embedding": embedding
    })
    _save_memory(mem_list)
