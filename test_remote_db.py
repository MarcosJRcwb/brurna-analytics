
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

REMOTE_URL = os.getenv("REMOTE_DATABASE_URL")
print(f"Connecting to: {REMOTE_URL[:30]}...")

try:
    engine = create_engine(REMOTE_URL)
    with engine.connect() as conn:
        count = conn.execute(text("SELECT count(*) FROM log_eventos")).scalar()
        print(f"Remote count: {count}")
except Exception as e:
    print(f"FAILED: {e}")
