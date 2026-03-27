from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.api import deps
from app.models import User
from app.models.reports import FlaggedContent

router = APIRouter()

class ReportCreate(BaseModel):
    message_content: str
    reason: Optional[str] = "Unspecified"

@router.post("/", status_code=201)
def report_content(
    report: ReportCreate,
    current_user: User = Depends(deps.get_current_active_user),
    db: Session = Depends(deps.get_db)
):
    """
    Endpoint for users to flag/report offensive AI content.
    MANDATORY for Google Play Generative AI Policy.
    """
    try:
        new_report = FlaggedContent(
            user_id=current_user.id,
            message_content=report.message_content,
            flag_reason=report.reason
        )
        db.add(new_report)
        db.commit()
        return {"msg": "Report submitted. Thank you for making Zara AI safer."}
    except Exception as e:
        # Log error but don't crash user experience
        print(f"Reporting error: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit report")
