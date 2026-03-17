
import os
import sys
import time
from sqlalchemy import create_engine, text
from datetime import datetime

# Fix path to import config and scripts
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
try:
    from config import config
except ImportError:
    import config

import ingest_nuclear
import sync_nuclear

def check_uf_remote_completion(uf):
    """Checks if the UF is already fully processed on the remote server."""
    print(f"Checking remote status for {uf.upper()}...")
    
    # 1. Count local files
    base_dir = config.RAW_LOGS_DIR
    state_dir = os.path.join(base_dir, uf.lower())
    local_count = 0
    if os.path.exists(state_dir):
        for root, _, files in os.walk(state_dir):
            for file in files:
                if file.endswith('.logjez'):
                    local_count += 1
    
    if local_count == 0:
        print(f"  No local files found for {uf.upper()}.")
        return True # Nothing to do
        
    # 2. Count remote processed unique files
    remote_engine = create_engine(config.REMOTE_POSTGRES_CONN)
    try:
        with remote_engine.connect() as conn:
            query = text("SELECT COUNT(DISTINCT source_file) FROM log_eventos WHERE source_file LIKE :pattern")
            remote_count = conn.execute(query, {"pattern": f"{uf.lower()}/%"}).scalar()
            
            print(f"{uf.upper()}: Local={local_count}, Remote={remote_count}")
            return remote_count >= local_count
    except Exception as e:
        print(f"Error checking remote: {e}")
        return False

def run_orchestration():
    print(f"\n{'='*60}")
    print(f"HYBRID MASTER ORCHESTRATOR ACTIVE")
    print(f"States to process: {['pr', 'sc', 'rs']}")
    print(f"{'='*60}\n")
    
    states = ['pr', 'sc', 'rs']
    
    for uf in states:
        print(f"\n STARTING STATE: {uf.upper()}")
        
        # Phase 1: Check Remote
        if check_uf_remote_completion(uf):
            print(f" State {uf.upper()} is already complete on remote. Skipping.")
            continue
            
        # Phase 2: Ingest Local
        print(f" Starting Nuclear Ingestion for {uf.upper()}...")
        ingest_nuclear.main(target_uf=uf)
        
        # Phase 3: Sync to Remote
        print(f" Starting Synchronization for {uf.upper()}...")
        sync_nuclear.sync_uf(uf)
        
        # Phase 4: Verification (Optional but safe)
        if check_uf_remote_completion(uf):
            print(f"State {uf.upper()} successfully processed, synced and cleaned.")
        else:
            print(f"State {uf.upper()} finished but remote count mismatch. Please check logs.")
            
    print(f"\n{'='*60}")
    print(f" ALL TARGET STATES PROCESSED.")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    run_orchestration()
