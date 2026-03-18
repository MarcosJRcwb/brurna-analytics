import subprocess
import sys
import time
import os
import argparse
from datetime import datetime
from pathlib import Path

# Add current dir and src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from config import config

# Stages Mapping (5 Stages now)
STAGES = [
    "DOWNLOAD",    # Phase 0: Acquisition
    "INGEST",      # Phase 1: Raw logs to DB
    "AGGREGATE",   # Phase 2: DB to Metadata/Patterns
    "ANALYZE",     # Phase 3: Run Hypotheses
    "SYNC"         # Phase 4: Cloud Sync & Local Cleanup
]

# Section counts for 1T 2022 (Consistency check)
EXPECTED_COUNTS = {
    'AC': 2118, 'AL': 6696, 'AP': 1740, 'AM': 8087, 'BA': 34151, 'CE': 22763,
    'DF': 4048, 'ES': 9534, 'GO': 16867, 'MA': 17756, 'MT': 8408, 'MS': 7083,
    'MG': 50125, 'PA': 19574, 'PB': 10403, 'PR': 25932, 'PE': 22171, 'PI': 9287,
    'RJ': 34220, 'RN': 7926, 'RS': 27043, 'RO': 3543, 'RR': 1124, 'SC': 16340,
    'SE': 3911, 'SP': 100994, 'TO': 3591, 'ZZ': 971
}

def run_cmd(cmd, uf, stage):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [{uf.upper()}] Starting {stage}: {cmd}")
    process = subprocess.Popen(cmd, shell=True)
    return process

def check_stage_done(uf, stage_idx):
    """Returns True if the stage is already complete for this UF."""
    from sqlalchemy import create_engine, text
    import os
    
    uf_lower = uf.lower()
    uf_upper = uf.upper()
    
    try:
        engine = create_engine(config.LOCAL_POSTGRES_CONN)
        with engine.connect() as conn:
            if stage_idx == 0: # DOWNLOAD
                # Check if directory exists and has files
                raw_dir = Path(config.RAW_LOGS_DIR) / uf_lower
                if raw_dir.exists():
                    files = list(raw_dir.glob("*"))
                    return len(files) > 10 # Heuristic for data present
                return False

            if stage_idx == 1: # INGEST
                # Check if we have raw logs for this UF in DB
                q = text("SELECT COUNT(*) FROM log_eventos WHERE source_file LIKE :uf_pat")
                res = conn.execute(q, {"uf_pat": f"%/{uf_lower}/%"}).scalar()
                # If we have significant logs, ingest is 'working' or 'done'
                # We expect roughly 7.5k logs per urn. Even 5% is a good sign.
                exp_logs = EXPECTED_COUNTS.get(uf_upper, 1000) * 500 # conservative
                return res > exp_logs 
                
            if stage_idx == 2: # AGGREGATE
                # Check if metadata exists (need at least 95% of expected)
                exp_val = EXPECTED_COUNTS.get(uf_upper, 1)
                q = text("SELECT COUNT(*) FROM section_metadata WHERE upper(uf) = :uf")
                res = conn.execute(q, {"uf": uf_upper}).scalar()
                return res >= exp_val * 0.95 
                
            if stage_idx == 3: # ANALYZE
                # Check if UF is in analysis_results.csv (heuristic)
                # Since analysis is global, we check if the file exists and has content
                if os.path.exists("analysis_results.csv"):
                    return True 
                return False
                
            if stage_idx == 4: # SYNC
                # Check if local logs are GONE (cleaned up) AND metadata is nearly complete
                q_logs = text("SELECT COUNT(*) FROM log_eventos WHERE source_file LIKE :uf_pat")
                res_logs = conn.execute(q_logs, {"uf_pat": f"%/{uf_lower}/%"}).scalar()
                
                exp_val = EXPECTED_COUNTS.get(uf_upper, 1)
                q_meta = text("SELECT COUNT(*) FROM section_metadata WHERE upper(uf) = :uf")
                res_meta = conn.execute(q_meta, {"uf": uf_upper}).scalar()
                
                return res_logs == 0 and res_meta >= exp_val * 0.95
    except Exception as e:
        print(f"Error checking stage: {e}")
        return False
    return False

def main():
    parser = argparse.ArgumentParser(description="Brurna Forensic Funnel - Zero Touch Pipeline")
    parser.add_argument("--ufs", type=str, help="Comma separated UFs (e.g. pr,sc,rs)")
    parser.add_argument("--limit", type=int, help="Limit sections for testing")
    
    args = parser.parse_args()
    
    if args.ufs:
        target_ufs = [u.strip().lower() for u in args.ufs.split(",")]
    else:
        # Default fallback
        target_ufs = ['ac', 'ap', 'rr', 'to', 'se']
        
    print(f"=== FORENSIC FUNNEL V2: AUTOMATIC 5-STAGE PIPELINE ===")
    print(f"Targets: {', '.join(u.upper() for u in target_ufs)}")
    
    # State tracking: {uf: current_stage_index}
    uf_state = {uf: -1 for uf in target_ufs}
    
    # Initialize state from reality
    print("Pre-scanning current state status...")
    for uf in target_ufs:
        best_stage = -1
        for i in range(len(STAGES)):
            if check_stage_done(uf, i):
                best_stage = i
            else:
                break 
        uf_state[uf] = best_stage
        if best_stage >= 0:
            print(f"[{uf.upper()}] Initialized at stage: {STAGES[best_stage]}")
        else:
            print(f"[{uf.upper()}] Starting from scratch (DOWNLOAD).")
    
    # active_processes[uf][stage_idx] = proc
    active_processes = {uf: {} for uf in target_ufs}

    try:
        while any(uf_state[u] < len(STAGES) - 1 for u in target_ufs):
            # 1. Check for finished processes
            for uf in target_ufs:
                finished_stages = []
                for s_idx, proc in active_processes[uf].items():
                    if proc.poll() is not None:
                        if proc.returncode == 0:
                            print(f"[{uf.upper()}] Stage {STAGES[s_idx]} COMPLETE.")
                            if s_idx > uf_state[uf]:
                                uf_state[uf] = s_idx
                        else:
                            print(f"[{uf.upper()}] Stage {STAGES[s_idx]} FAILED (Code: {proc.returncode}).")
                        finished_stages.append(s_idx)
                
                for s_idx in finished_stages:
                    del active_processes[uf][s_idx]

                # Determine what needs to run next
                next_stage_idx = uf_state[uf] + 1
                
                if next_stage_idx >= len(STAGES):
                    continue 

                # PIPED LOGIC: Check Stage 0 (DOWNLOAD) completion for PR, SC, RS (South Region)
                # For South region, we want to stay in 0 and 1 together until ALL is done
                is_south = uf.lower() in ['pr', 'sc', 'rs']
                download_done = check_stage_done(uf, 0)
                ingest_done = check_stage_done(uf, 1)

                # ADVANCEMENT RULE:
                # If we are in Stage 0 or 1, and it's not truly done, stay there
                if next_stage_idx <= 1 and not (download_done and ingest_done):
                   # We are still in the acquisition phase
                    pass 
                elif check_stage_done(uf, next_stage_idx):
                    # For other stages, or if truly done, advance
                    print(f"[{uf.upper()}] Stage {STAGES[next_stage_idx]} ALREADY DONE. Advancing...")
                    uf_state[uf] = next_stage_idx
                    continue 

                # Funnel Constraint: Max concurrency per stage across all UFs
                total_active_this_stage = sum(1 for u in target_ufs if next_stage_idx in active_processes[u])
                if total_active_this_stage >= 1 and next_stage_idx > 0:
                    # Only one UF doing Ingest/Aggregate/etc at a time, but multiple can Download
                    if next_stage_idx != 0: 
                        continue 
                
                # PIPED LOGIC: Allow Stage 1 (INGEST) to run IF Stage 0 (DOWNLOAD) is active OR finished
                can_start = False
                if next_stage_idx == 0 and 0 not in active_processes[uf]:
                    can_start = True
                elif next_stage_idx == 1:
                    # We can start Ingest if Download is running OR if Download is done but Ingest isn't
                    if 1 not in active_processes[uf]:
                        can_start = True
                elif next_stage_idx > 1:
                    # Stages 2+ (Aggregate, Analyze, Sync) MUST wait for previous stage to be FULLY DONE
                    if not active_processes[uf]: # No stages running for this UF
                        can_start = True
                
                if can_start:
                    stage_name = STAGES[next_stage_idx]
                    limit_str = f" --limit {args.limit}" if args.limit else ""
                    
                    if stage_name == "DOWNLOAD":
                        cmd = f"python src/download/downloader.py --uf {uf}{limit_str}"
                    elif stage_name == "INGEST":
                        cmd = f"python src/data_ingestion/ingest_nuclear.py --uf {uf}"
                    elif stage_name == "AGGREGATE":
                        cmd = f"python src/analytics/process_forensic_patterns.py --uf {uf}"
                    elif stage_name == "ANALYZE":
                        cmd = f"python src/analytics/analytical_engine.py --uf {uf}"
                    elif stage_name == "SYNC":
                        cmd = f"python src/data_ingestion/sync_nuclear.py --uf {uf}"
                    
                    active_processes[uf][next_stage_idx] = run_cmd(cmd, uf, stage_name)

            time.sleep(10)
    except KeyboardInterrupt:
        print("\nStopping funnel...")
        for uf_procs in active_processes.values():
            for proc in uf_procs.values():
                proc.terminate()

    print("\n=== FORENSIC FUNNEL COMPLETE. ALL STATES PROCESSED 100% ===")

if __name__ == "__main__":
    main()
