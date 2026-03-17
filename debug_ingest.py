
import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, text

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from config import config
from data_ingestion.ingest_nuclear import worker_proc

def debug():
    # Target a single file in SE
    uf = 'se'
    base_dir = r"C:\Users\marco\Downloads\TSE\data\raw_logs"
    state_dir = os.path.join(base_dir, uf)
    
    files = []
    if os.path.exists(state_dir):
        for f in os.listdir(state_dir):
            if f.endswith('.logjez'):
                files.append((os.path.join(state_dir, f), uf))
                break # Just one
    
    if not files:
        print("No files found!")
        return

    print(f"Testing file: {files[0]}")
    db_conn = config.LOCAL_POSTGRES_CONN
    print(f"DB Conn: {db_conn}")
    
    try:
        worker_proc(0, files, db_conn, "debug_run")
        print("Worker proc finished.")
    except Exception as e:
        print(f"Caught error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug()
