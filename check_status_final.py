
import sys
import os
from sqlalchemy import create_engine, text

# Add root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))
# from src.config import config  # WRONG
from config import config

def check():
    try:
        eng_local = create_engine(config.LOCAL_POSTGRES_CONN)
        eng_remote = create_engine(config.REMOTE_POSTGRES_CONN)
        
        with eng_local.connect() as conn:
            q = text("SELECT count(1) FROM section_metadata WHERE lower(uf)='se'")
            local_meta = conn.execute(q).scalar() or 0
            
            q_logs = text("SELECT count(1) FROM log_eventos WHERE source_file LIKE '%/se/%'")
            local_logs = conn.execute(q_logs).scalar() or 0
            
        with eng_remote.connect() as conn:
            q = text("SELECT count(1) FROM section_metadata WHERE lower(uf)='se'")
            remote_meta = conn.execute(q).scalar() or 0
            
        print(f"SE Status:")
        print(f"  Local Meta: {local_meta}")
        print(f"  Local Logs: {local_logs}")
        print(f"  Remote Meta: {remote_meta}")
        print(f"  Total Goal: 4207")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check()
