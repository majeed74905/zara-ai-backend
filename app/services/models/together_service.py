from openai import OpenAI
from app.core.config import settings
from app.services.models.base_llm import BaseLLMService
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class TogetherAIService(BaseLLMService):
    """
    Together AI Service - ECO Mode Provider
    Replaces DeepSeek for cost-effective, efficient AI responses
    """
    def __init__(self):
        if settings.TOGETHER_API_KEY:
            self.client = OpenAI(
                api_key=settings.TOGETHER_API_KEY,
                base_url="https://api.together.xyz/v1"
            )
            # Using Mixtral for ECO mode - efficient and cost-effective
            self.model_name = "mistralai/Mixtral-8x7B-Instruct-v0.1"
        else:
            self.client = None
            logger.warning("TOGETHER_API_KEY not found. Together AI Service disabled.")

    def health_check(self) -> bool:
        return self.client is not None

    def generate(self, system_prompt: str, user_prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        if not self.client:
            raise ValueError("Together AI Service is not configured.")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        if context and context.get("history"):
            # Insert history between system and user
            messages[1:1] = context["history"]

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.7,
                max_tokens=512,
                top_p=0.7,
                stop=None
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Together AI Generation Error: {e}")
            raise e
