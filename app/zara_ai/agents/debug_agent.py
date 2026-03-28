import logging
from typing import Dict, Any, Optional
from google import genai
from app.core.config import settings

logger = logging.getLogger("ZaraAI_DebugAgent")

async def analyze_error(error_msg: str, traceback_str: str, past_memory: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Classifies the runtime error, locating the root cause and severity."""
    logger.info("Debug Agent evaluating trace...")

    # If already remembered, we might skip deep analysis
    if past_memory and 'fix_patch' in past_memory:
         return {
            "root_cause": "KNOWN_ERROR",
            "severity": "LOW",
            "context": past_memory['fix_patch']
         }

    # Otherwise run true analysis
    if not settings.GEMINI_API_KEY:
        logger.error("Debug Agent missing LLM logic API Key. Cannot proceed.")
        return {"severity": "CRITICAL", "root_cause": "System misconfigured."}

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    prompt = f"""
    You are an L4 Autonomous System Architect. 
    Analyze this runtime exception and determine its root cause, severity, and the specific affected modules/files.

    ERROR: {error_msg}
    TRACEBACK: {traceback_str}

    Return your findings in standard JSON format:
    {{
        "root_cause": "Explanation of the failure",
        "affected_files": ["app/main.py", ...],
        "severity": "CRITICAL|HIGH|MEDIUM|LOW",
        "is_security_risk": boolean
    }}
    """
    
    try:
        response = await client.aio.models.generate_content(
            model='gemini-1.5-pro', # Use deeper reasoning model for orchestration natively
            contents=prompt
        )
        
        # Simplified parser assumptions
        resp_text = response.text.strip('```json').strip('```').strip()
        import json
        analysis = json.loads(resp_text)
        
        if analysis.get('is_security_risk'):
            analysis['severity'] = 'CRITICAL_SECURITY'
            
        return analysis
    except Exception as e:
        logger.error(f"Debug Agent failed to construct logic parse: {e}")
        return {"severity": "UNKNOWN", "root_cause": str(e)}
