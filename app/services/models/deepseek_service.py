from openai import OpenAI
from app.core.config import settings
from app.services.models.base_llm import BaseLLMService
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class DeepSeekService(BaseLLMService):
    def __init__(self):
        if settings.DEEPSEEK_API_KEY:
            self.client = OpenAI(
                api_key=settings.DEEPSEEK_API_KEY,
                base_url="https://api.deepseek.com"
            )
            self.model_name = "deepseek-reasoner" # For Tutor/Exam/Design logic
        else:
            self.client = None
            logger.warning("DEEPSEEK_API_KEY not found. DeepSeek Service disabled.")

    def health_check(self) -> bool:
        return self.client is not None

    def generate(self, system_prompt: str, user_prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        if not self.client:
            raise ValueError("DeepSeek Service is not configured.")

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
                stream=False
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"DeepSeek Generation Error: {e}")
            raise e
