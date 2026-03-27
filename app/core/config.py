from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Zara AI"
    API_V1_STR: str = "/api/v1"
    
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"
    
    DATABASE_URL: str
    
    SMTP_SERVER: Optional[str] = None
    SMTP_PORT: Optional[int] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: Optional[str] = None
    EMAILS_FROM_NAME: Optional[str] = None

    # API Keys
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_CALLBACK_URL: Optional[str] = None
    FRONTEND_URL: str = "https://zara-ai-assists.netlify.app/"
    
    # Use field aliases or post-init to ensure GEMINI/GOOGLE/API_KEY are bridged
    GOOGLE_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    API_KEY: Optional[str] = None
    
    GROQ_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None  # OpenRouter for ECO mode
    # Deprecated - migrated to OpenRouter
    TOGETHER_API_KEY: Optional[str] = None
    DEEPSEEK_API_KEY: Optional[str] = None
    STABILITY_API_KEY: Optional[str] = None

    # Email Providers
    RESEND_API_KEY: Optional[str] = None
    
    BREVO_SMTP_HOST: str = "smtp-relay.brevo.com"
    BREVO_SMTP_PORT: int = 587
    BREVO_SMTP_USER: Optional[str] = None
    BREVO_SMTP_PASS: Optional[str] = None

    # Common
    BACKEND_URL: Optional[str] = None

    # SMTP Secure flag
    SMTP_SECURE: bool = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Determine the best key to use for Google/Gemini services
        effective_key = self.GOOGLE_API_KEY or self.GEMINI_API_KEY or self.API_KEY
        if effective_key:
            if not self.GOOGLE_API_KEY: self.GOOGLE_API_KEY = effective_key
            if not self.GEMINI_API_KEY: self.GEMINI_API_KEY = effective_key
            if not self.API_KEY: self.API_KEY = effective_key

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

settings = Settings()
