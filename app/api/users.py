from fastapi import APIRouter, Depends
from app.api import deps
from app.schemas import user as user_schemas
from app.models import User
from sqlalchemy.orm import Session

router = APIRouter()

@router.get("/me", response_model=user_schemas.UserResponse)
def read_user_me(
    current_user: User = Depends(deps.get_current_active_user),
):
    return current_user

from typing import Optional
@router.get("/me/history")
def read_history(
    skip: int = 0,
    limit: int = 50,
    current_user: Optional[User] = Depends(deps.get_current_user_optional),
    db: Session = Depends(deps.get_db)
):
    """Retrieves authenticated user's prompt history. Feature 08: Controlled response for guests."""
    if not current_user:
        return {"error": "Authentication required to access history", "locked": True}
        
    from app.models import PromptHistory 
    history = db.query(PromptHistory).filter(PromptHistory.user_id == current_user.id).order_by(PromptHistory.timestamp.desc()).offset(skip).limit(limit).all()
    return history

@router.delete("/me/history")
def clear_history(
    current_user: User = Depends(deps.get_current_active_user),
    db: Session = Depends(deps.get_db)
):
    from app.models import PromptHistory
    db.query(PromptHistory).filter(PromptHistory.user_id == current_user.id).delete()
    db.commit()
    return {"msg": "History cleared successfully"}

@router.post("/me/privacy")
def set_privacy_mode(
    is_enabled: bool,
    current_user: User = Depends(deps.get_current_active_user),
    db: Session = Depends(deps.get_db)
):
    current_user.is_privacy_mode = is_enabled
    db.commit()
    db.refresh(current_user)
    db.commit()
    db.refresh(current_user)
    return {"msg": f"Privacy mode {'enabled' if is_enabled else 'disabled'}", "is_privacy_mode": current_user.is_privacy_mode}

@router.post("/me/auto-delete")
def set_auto_delete(
    days: int,
    current_user: User = Depends(deps.get_current_active_user),
    db: Session = Depends(deps.get_db)
):
    """Configures auto-deletion of history older than X days."""
    current_user.auto_delete_days = days if days > 0 else None
    db.commit()
    return {"msg": f"Auto-delete set to {days} days" if days > 0 else "Auto-delete disabled"}

@router.delete("/me")
def delete_account(
    current_user: User = Depends(deps.get_current_active_user),
    db: Session = Depends(deps.get_db)
):
    """
    PERMANENTLY DELETE ACCOUNT.
    Removes user and all associated data (history, logs, tokens).
    This action is irreversible.
    Required for Google Play Store & GDPR compliance.
    """
    db.delete(current_user)
    db.commit()
    return {"msg": "Account permanently deleted. Goodbye."}

@router.get("/me/history/search")
def search_history(
    q: str,
    current_user: User = Depends(deps.get_current_active_user),
    db: Session = Depends(deps.get_db)
):
    """Feature 14: Search authenticated history."""
    from app.models import PromptHistory
    # Simple ILIKE search for now. For scale, use TSVECTOR.
    results = db.query(PromptHistory).filter(
        PromptHistory.user_id == current_user.id,
        (PromptHistory.prompt.ilike(f"%{q}%")) | (PromptHistory.response.ilike(f"%{q}%"))
    ).order_by(PromptHistory.timestamp.desc()).limit(50).all()
    return results

@router.get("/me/history/export")
def export_history(
    format: str = "txt",
    current_user: User = Depends(deps.get_current_active_user),
    db: Session = Depends(deps.get_db)
):
    """Feature 15: Export authenticated history."""
    from app.models import PromptHistory
    from fastapi.responses import Response
    
    history = db.query(PromptHistory).filter(PromptHistory.user_id == current_user.id).order_by(PromptHistory.timestamp.asc()).all()
    
    if format == "pdf":
        from fpdf import FPDF
        import tempfile
        
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"Zara AI Chat History - {current_user.email}", ln=1, align='C')
        
        for item in history:
            pdf.set_font("Arial", 'B', 10)
            pdf.multi_cell(0, 10, f"You ({item.timestamp}): {item.prompt}")
            pdf.set_font("Arial", '', 10)
            # Sanitize latin-1 issues roughly
            safe_response = item.response.encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 10, f"AI: {safe_response}")
            pdf.ln(5)
            
        return Response(content=pdf.output(dest='S').encode('latin-1'), media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=history.pdf"})
    
    else: # TXT default
        content = f"Zara AI Chat History - {current_user.email}\n==========================================\n\n"
        for item in history:
            content += f"You ({item.timestamp}): {item.prompt}\n"
            content += f"AI: {item.response}\n"
            content += "------------------------------------------\n"
        
        return Response(content=content, media_type="text/plain", headers={"Content-Disposition": "attachment; filename=history.txt"})
