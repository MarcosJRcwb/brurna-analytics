
import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
try:
    from config import config
except ImportError:
    import config

def get_stats(engine_url, name):
    print(f"\n=== {name} Database Stats ===")
    try:
        engine = create_engine(engine_url)
        with engine.connect() as conn:
            # 1. NEW FORMAT (with slash)
            res_slash = conn.execute(text("SELECT split_part(source_file, '/', 1) as uf, count(distinct source_file) FROM log_eventos WHERE source_file LIKE '%/%' GROUP BY 1 ORDER BY 1")).fetchall()
            print("New Format (uf/filename):")
            for row in res_slash:
                print(f"  UF: {row[0].upper()} | Files: {row[1]}")
            
            # 2. OLD FORMAT (no slash)
            old_count = conn.execute(text("SELECT count(distinct source_file) FROM log_eventos WHERE source_file NOT LIKE '%/%'")).scalar()
            print(f"Old Format (no slash) Unique Files: {old_count}")
            
            # 3. TOTAL
            total_events = conn.execute(text("SELECT count(*) FROM log_eventos")).scalar()
            print(f"Total Database Rows: {total_events}")
            
    except Exception as e:
        print(f"Error in {name}: {e}")

if __name__ == "__main__":
    load_dotenv()
    get_stats(config.REMOTE_POSTGRES_CONN, "Remote")
    get_stats(config.LOCAL_POSTGRES_CONN, "Local")
