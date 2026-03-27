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
    conn.commit() # Ensure auto-commit mode or manual commit
    
    # 1. Add is_privacy_mode
    print("Migrating Users...")
    try:
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_privacy_mode BOOLEAN DEFAULT FALSE NOT NULL;"))
        print("✔ Updated users table (added is_privacy_mode).")
    except Exception as e:
        print(f"Note on Users: {e}")

    # 2. Add strict user_id to prompt_history
    print("Enforcing Strict Rules on History...")
    try:
        # Check if table exists
        result = conn.execute(text("SELECT to_regclass('prompt_history');"))
        if result.scalar():
            # Delete illegal anonymous history first (Rule: No History without User ID)
            del_res = conn.execute(text("DELETE FROM prompt_history WHERE user_id IS NULL;"))
            print(f"✔ Purged {del_res.rowcount} illegal anonymous history records.")
            
            # Alter column to enforce NOT NULL
            conn.execute(text("ALTER TABLE prompt_history ALTER COLUMN user_id SET NOT NULL;"))
            print("✔ Enforced NOT NULL constraint on prompt_history.user_id.")
        else:
            print("⚠ prompt_history table not found (will be created by app).")
            
    except Exception as e:
        print(f"Note on History: {e}")
        
    conn.commit()
    print("Migration Complete.")
