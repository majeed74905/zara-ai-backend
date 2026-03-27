from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseLLMService(ABC):
    """
    Abstract Base Class for all LLM Service Implementations.
    Enforces a consistent interface for the Router.
    """

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Generates a response from the LLM.
        
        Args:
            system_prompt (str): The system identity/instructions.
            user_prompt (str): The user's specific request.
            context (dict): Optional context (e.g., file content, previous messages).
            
        Returns:
            str: The generated text response.
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Checks if the service is configured and reachable."""
        pass
