from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class FlaggedContent(Base):
    """
    Stores content flagged by users as offensive/incorrect.
    Critical for Google Play 'Generative AI' compliance.
    """
    __tablename__ = "flagged_content"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Nullable if guest (though app requires login)
    message_content = Column(Text, nullable=False)
    flag_reason = Column(String, nullable=True) # e.g. "Hate Speech", "Sexual", "Other"
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    is_resolved = Column(Boolean, default=False)

    user = relationship("User")
