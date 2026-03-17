
from sqlalchemy import create_engine, text
import os, sys
from dotenv import load_dotenv

load_dotenv()
LOCAL_URL = os.getenv("LOCAL_DATABASE_URL")
REMOTE_URL = os.getenv("REMOTE_DATABASE_URL")

def check(url, name):
    print(f"\n--- {name} ---")
    try:
        engine = create_engine(url)
        with engine.connect() as conn:
            # PR Count
            pr_count = conn.execute(text("SELECT count(distinct source_file) FROM log_eventos WHERE source_file LIKE 'pr/%'")).scalar()
            # Total Count
            total = conn.execute(text("SELECT count(*) FROM log_eventos")).scalar()
            print(f"PR Count: {pr_count}")
            print(f"Total Rows: {total}")
            
            # Other UFs with slash
            other_ufs = conn.execute(text("SELECT split_part(source_file, '/', 1) as uf, count(distinct source_file) FROM log_eventos WHERE source_file LIKE '%/%' GROUP BY 1")).fetchall()
            print(f"UFs with slash: {other_ufs}")
    except Exception as e:
        print(f"Error {name}: {e}")

check(LOCAL_URL, "LOCAL")
check(REMOTE_URL, "REMOTE")
