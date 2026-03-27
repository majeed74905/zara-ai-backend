from abc import ABC, abstractmethod

class EmailProvider(ABC):
    @abstractmethod
    def send(self, to_email: str, subject: str, html_content: str) -> bool:
        """Sends an email. Returns True if successful, False otherwise."""
        pass
