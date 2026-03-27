from threading import Thread
import time
import schedule
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import User, PromptHistory
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

def run_auto_delete_job():
    """Checks all users with auto_delete_days set and purges old history."""
    db: Session = SessionLocal()
    try:
        users = db.query(User).filter(User.auto_delete_days != None).all()
        for user in users:
            try:
                days = user.auto_delete_days
                if days and days > 0:
                    cutoff = datetime.utcnow() - timedelta(days=days)
                    deleted_count = db.query(PromptHistory).filter(
                        PromptHistory.user_id == user.id,
                        PromptHistory.timestamp < cutoff
                    ).delete()
                    if deleted_count > 0:
                        logger.info(f"Auto-deleted {deleted_count} records for user {user.id}")
            except Exception as e:
                logger.error(f"Error processing auto-delete for user {user.id}: {e}")
        db.commit()
    except Exception as e:
        logger.error(f"Auto-delete job failed: {e}")
    finally:
        db.close()

def start_scheduler():
    # Schedule to run every hour
    schedule.every().hour.do(run_auto_delete_job)
    
    def loop():
        while True:
            schedule.run_pending()
            time.sleep(60)
            
    Thread(target=loop, daemon=True).start()
    logger.info("Background Auto-Delete Scheduler Started.")
