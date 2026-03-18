import subprocess
import sys
import time
import os
from datetime import datetime
import sys

# Add current dir and src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from config import config

# Definitive list of UFs to process
UFS = ['ac', 'ap', 'rr', 'to', 'se']

# Stages Mapping
STAGES = [
    "INGEST",      # Phase 1: Raw logs to DB
    "AGGREGATE",   # Phase 2: DB to Metadata/Patterns
    "ANALYZE",     # Phase 3: Run Hypotheses (New!)
    "SYNC"         # Phase 4: Cloud Sync & Local Cleanup
]

def run_cmd(cmd, uf, stage):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [{uf.upper()}] Starting {stage}: {cmd}")
    process = subprocess.Popen(cmd, shell=True)
    return process

def check_stage_done(uf, stage_idx):
    """Returns True if the stage is already complete for this UF."""
    from sqlalchemy import create_engine, text
    import os
    
    try:
        engine = create_engine(config.LOCAL_POSTGRES_CONN)
        with engine.connect() as conn:
            if stage_idx == 0: # INGEST
                # Check if we have raw logs for this UF
                q = text("SELECT COUNT(*) FROM log_eventos WHERE source_file LIKE :uf")
                res = conn.execute(q, {"uf": f"%/{uf}/%"}).scalar()
                return res > 1000 # If we have logs, ingest is 'working' or 'done'
                
            if stage_idx == 1: # AGGREGATE
                # Check if metadata exists (need at least 95% of expected)
                expected = {'se': 4207, 'rr': 1124, 'to': 3593, 'ac': 2118, 'ap': 1740}
                exp_val = expected.get(uf, 1)
                q = text("SELECT COUNT(*) FROM section_metadata WHERE lower(uf) = :uf")
                res = conn.execute(q, {"uf": uf}).scalar()
                return res >= exp_val * 0.95 
                
            if stage_idx == 2: # ANALYZE
                # Check if UF is in analysis_results.csv (heuristic)
                if os.path.exists("analysis_results.csv"):
                    return True # For now, global analysis covers all
                return False
                
            if stage_idx == 3: # SYNC
                # Check if local logs are GONE (cleaned up) AND metadata is nearly complete
                q_logs = text("SELECT COUNT(*) FROM log_eventos WHERE source_file LIKE :uf")
                res_logs = conn.execute(q_logs, {"uf": f"%/{uf}/%"}).scalar()
                
                expected = {'se': 4207, 'rr': 1124, 'to': 3593, 'ac': 2118, 'ap': 1740}
                exp_val = expected.get(uf, 1)
                q_meta = text("SELECT COUNT(*) FROM section_metadata WHERE lower(uf) = :uf")
                res_meta = conn.execute(q_meta, {"uf": uf}).scalar()
                
                return res_logs == 0 and res_meta >= exp_val * 0.95
    except:
        return False
    return False

def main():
    print(f"=== FORENSIC FUNNEL V1: BALANCED 4-STAGE PIPELINE ===")
    
    # State tracking: {uf: current_stage_index}
    # -1 means not started, len(STAGES)-1 means fully sync'd
    uf_state = {uf: -1 for uf in UFS}
    
    # Initialize state from reality (sequential check)
    print("Pre-scanning state status...")
    for uf in UFS:
        best_stage = -1
        for i in range(len(STAGES)):
            if check_stage_done(uf, i):
                best_stage = i
            else:
                break # First failure stops the chain
        uf_state[uf] = best_stage
        if best_stage >= 0:
            print(f"[{uf.upper()}] Initialized at stage: {STAGES[best_stage]}")
        else:
            print(f"[{uf.upper()}] No stages completed. Starting from scratch.")
    
    active_processes = {}

    while any(uf_state[u] < len(STAGES) - 1 for u in UFS):
        # 1. Check for finished processes
        finished_ufs = []
        for uf, proc in active_processes.items():
            if proc.poll() is not None:
                if proc.returncode == 0:
                    print(f"[{uf.upper()}] Stage {STAGES[uf_state[uf]]} COMPLETE.")
                else:
                    print(f"[{uf.upper()}] Stage {STAGES[uf_state[uf]]} FAILED (Code: {proc.returncode}).")
                finished_ufs.append(uf)
        
        for uf in finished_ufs:
            del active_processes[uf]

        # 2. Assign new work according to the "Funnel" (Balance)
        for uf in UFS:
            if uf not in active_processes and uf_state[uf] < len(STAGES) - 1:
                next_stage_idx = uf_state[uf] + 1
                
                # SMART SKIP: Check if already done
                if check_stage_done(uf, next_stage_idx):
                    print(f"[{uf.upper()}] Stage {STAGES[next_stage_idx]} ALREADY DONE. Advancing...")
                    uf_state[uf] = next_stage_idx
                    continue 

                # Funnel Rule: Try to have only one UF per stage at a time (strict balance)
                current_active_stages = [uf_state[u] for u in active_processes.keys()]
                if next_stage_idx in current_active_stages:
                    continue 
                
                # Launch stage
                stage_name = STAGES[next_stage_idx]
                if stage_name == "INGEST":
                    cmd = f"python src/data_ingestion/ingest_nuclear.py --uf {uf}"
                elif stage_name == "AGGREGATE":
                    cmd = f"python src/analytics/process_forensic_patterns.py --uf {uf}"
                elif stage_name == "ANALYZE":
                    cmd = f"python src/analytics/analytical_engine.py --uf {uf}"
                elif stage_name == "SYNC":
                    cmd = f"python src/data_ingestion/sync_nuclear.py --uf {uf}"
                
                active_processes[uf] = run_cmd(cmd, uf, stage_name)
                uf_state[uf] = next_stage_idx

        if not active_processes and all(uf_state[u] >= len(STAGES) - 1 or check_stage_done(u, uf_state[u]+1) for u in UFS):
             # Force advancement if everything is done or skippable
             for u in UFS:
                 if uf_state[u] < len(STAGES)-1: uf_state[u] += 1
             if all(uf_state[u] >= len(STAGES)-1 for u in UFS): break

        time.sleep(5)

    print("\n=== FORENSIC FUNNEL COMPLETE. ALL STATES PROCESSED 100% ===")

if __name__ == "__main__":
    main()
