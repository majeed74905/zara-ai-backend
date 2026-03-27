from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class AIUsage(Base):
    __tablename__ = "ai_usage"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False, default=func.current_date())
    prompts_count = Column(Integer, default=0)
    tokens_used = Column(Integer, default=0)

    user = relationship("User", back_populates="ai_usage")

class RateLimit(Base):
    __tablename__ = "rate_limits"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(String, unique=True, nullable=False) # e.g., 'user', 'admin'
    max_prompts_per_day = Column(Integer, default=100)
    max_requests_per_minute = Column(Integer, default=10)
