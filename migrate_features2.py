from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("DATABASE_URL")
if not url:
    print("No DATABASE_URL found")
    exit(1)

print(f"Connecting to {url.split('@')[1] if '@' in url else 'DB'}...")
engine = create_engine(url)

with engine.connect() as conn:
    conn.commit()
    
    # 1. Add auto_delete_days to users
    print("Adding auto_delete_days to users...")
    try:
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS auto_delete_days INTEGER DEFAULT NULL;"))
        print("✔ Added auto_delete_days column.")
    except Exception as e:
        print(f"Note: {e}")

    # 2. Add Index for History Search (user_id, timestamp) - standard usage
    print("optimizing History Table...")
    try:
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_history_user_timestamp ON prompt_history (user_id, timestamp DESC);"))
        print("✔ Added index on (user_id, timestamp).")
    except Exception as e:
        print(f"Note: {e}")

    conn.commit()
    print("Migration Complete.")
