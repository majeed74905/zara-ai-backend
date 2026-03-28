import logging
from typing import Dict, Any
from google import genai
from app.core.config import settings

logger = logging.getLogger("ZaraAI_FixAgent")

async def generate_fix(analysis: Dict[str, Any]) -> str:
    if analysis.get('root_cause') == 'KNOWN_ERROR':
         logger.info("Fix Agent deploying remembered structural fix.")
         return analysis.get('context', "")
         
    if analysis.get('severity') == 'CRITICAL_SECURITY':
        return "" # Abort

    logger.info("Fix Agent engineering patch...")
    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    prompt = f"""
    You are the Fix Module of an L4 Autonomous Engineering System.
    Review this error diagnostic and output a minimal, safe, exact code patch that resolves the issue without introducing breaking changes.

    Diagnosis: {analysis}

    Output the precise, actionable code fix necessary.
    RULES:
    - Minimal change
    - No breaking features
    - Production safe
    """

    try:
        response = await client.aio.models.generate_content(
            model='gemini-1.5-pro',
            contents=prompt
        )
        return response.text
    except Exception as e:
        logger.error(f"Fix Agent failed: {e}")
        return ""
