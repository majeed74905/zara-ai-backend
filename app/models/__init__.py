from .users import User, EmailVerification, RefreshToken
from .ai import AIUsage
from .logs import ActivityLog, PromptHistory
from .reports import FlaggedContent

# Export all models for easy access and Alembic autogenerate.
# Importing FlaggedContent here ensures its table is registered on Base.metadata
# BEFORE main.py calls Base.metadata.create_all() (otherwise the table is never created).
__all__ = [
    "User",
    "EmailVerification",
    "RefreshToken",
    "AIUsage",
    "PromptHistory",
    "ActivityLog",
    "FlaggedContent",
]
