
import sys
import os
import re
import shutil
import json
import time
import subprocess
import uuid
from datetime import datetime
from sqlalchemy import create_engine, text
from multiprocessing import Process, cpu_count

# Fix path to import config from root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
try:
    from config import config
except ImportError:
    import config

# Improved Regex to handle both Spaces (Native/Standard) and Tabs (TSE Specific Format)
LOG_REGEX = re.compile(r'^(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2}:\d{2})[\s\t]+(\w+)[\s\t]+([A-Z0-9]+)?[\s\t]*(.*)$')
STATUS_DIR = "logs/workers"
NATIVE_7Z = r"C:\Program Files\7-Zip\7z.exe"
FINAL_STATUS_FILE = "ingestion_status.json"
RUN_ID = datetime.now().strftime("%H%M%S") # Unique ID for this specific run session
MAX_WORKERS = 30

def parse_line(line, filename):
    match = LOG_REGEX.match(line)
    if match:
        date_str, time_str, level, code, msg = match.groups()
        try:
            ts = datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %H:%M:%S")
            return {
                'source_file': filename,
                'timestamp': ts,
                'level': level,
                'code': code or '',
                'message': msg,
                'original_line': line # Save original line for further forensic drill-down
            }
        except ValueError:
            return None
    return None

def worker_proc(worker_id, file_list, db_conn_str, session_id):
    """
    Persistent Worker V3:
    - Unique temp path per worker AND run session
    - Permanent DB session with synchronous_commit=off
    - Aggressive batching
    """
    # Use worker_id AND session_id to guarantee unique folder name
    cache_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../cache/workers'))
    os.makedirs(cache_root, exist_ok=True)
    
    tmp_path = os.path.join(cache_root, f"tmp_nuc_{session_id}_w{worker_id}")
    if os.path.exists(tmp_path): 
        try: shutil.rmtree(tmp_path, ignore_errors=True)
        except: pass
    os.makedirs(tmp_path, exist_ok=True)
    
    engine = create_engine(db_conn_str)
    batch_records = []
    processed_files = 0
    error_count = 0
    total_files = len(file_list)
    start_time = time.time()
    
    # Use absolute paths for diagnostics on Windows workers
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
    status_dir_abs = os.path.join(root_dir, STATUS_DIR)
    
    def save_worker_status():
        elapsed = time.time() - start_time
        rate = processed_files / elapsed if elapsed > 0 else 0
        status = {
            "worker": worker_id,
            "file": os.path.basename(file_list[min(processed_files, total_files-1)][0]),
            "progress": processed_files,
            "total": total_files,
            "rate": rate,
            "errors": error_count,
            "timestamp": datetime.now().isoformat()
        }
        try:
            with open(os.path.join(status_dir_abs, f"w{worker_id}.json"), 'w') as f:
                json.dump(status, f)
        except: pass

    try:
        with engine.connect() as conn:
            # Optimize DB session
            conn.execute(text("SET synchronous_commit TO OFF"))
            
            for i, (filepath, uf) in enumerate(file_list):
                filename = os.path.basename(filepath)
                db_source = f"{uf}/{filename}"
                
                try:
                    # Extraction with Native 7z
                    subprocess.run([NATIVE_7Z, "e", filepath, f"-o{tmp_path}", "-y"], 
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                    
                    target_file = None
                    for f in os.listdir(tmp_path):
                        if f.endswith('.dat') or 'log' in f.lower():
                            target_file = os.path.join(tmp_path, f)
                            break
                    
                    if target_file:
                        with open(target_file, 'rb') as f:
                            content = f.read()
                        
                        # Immediate cleanup of extracted file to free I/O
                        os.remove(target_file)
                        
                        try:
                            text_content = content.decode('utf-8')
                        except:
                            text_content = content.decode('latin1', errors='ignore')
                            
                        lines = text_content.splitlines()
                        for line in lines:
                            parsed = parse_line(line, db_source)
                            if parsed:
                                batch_records.append(parsed)

                    processed_files += 1
                    
                    # Batch COMMIT every 10 files for visibility
                    if processed_files % 10 == 0:
                        save_worker_status()

                    # Hyper-Agile DB batch (10 files as requested for bursts)
                    if processed_files % 10 == 0 or processed_files == total_files:
                        if batch_records:
                            print(f"[Worker {worker_id}] Committing {len(batch_records)} records to DB...")
                            conn.execute(
                                text("INSERT INTO log_eventos (source_file, timestamp, level, code, message, original_line) VALUES (:source_file, :timestamp, :level, :code, :message, :original_line)"),
                                batch_records
                            )
                            conn.commit()
                            print(f"[Worker {worker_id}] COMMIT SUCCESS.")
                            batch_records = []
                        save_worker_status()

                except Exception as e:
                    error_count += 1
                    try:
                        with open(os.path.join(status_dir_abs, f"errors_w{worker_id}.log"), "a") as ef:
                            ef.write(f"[{datetime.now().isoformat()}] Error in {filename}: {str(e)}\n")
                    except: pass
                
                # Double-check cleanup of any junk in worker tmp
                if (i % 20 == 0):
                    for f in os.listdir(tmp_path):
                        try: os.remove(os.path.join(tmp_path, f))
                        except: pass

    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)
        save_worker_status()

def aggregator_main(total_count, start_time):
    """Aggregate all 30 workers into the UI and terminal."""
    from tqdm import tqdm
    pbar = tqdm(total=total_count, desc="[Nuclear Ingestion]", unit="files", ncols=100)
    last_prog = 0
    while True:
        try:
            agg_progress = 0
            agg_errors = 0
            agg_rate = 0
            last_file = "Synchronizing..."
            
            files = [f for f in os.listdir(STATUS_DIR) if f.startswith('w') and f.endswith('.json')]
            for f in files:
                try:
                    with open(os.path.join(STATUS_DIR, f), 'r') as j:
                        data = json.load(j)
                        agg_progress += data['progress']
                        agg_errors += data['errors']
                        agg_rate += data['rate']
                        last_file = data['file']
                except: pass
            
            if agg_progress > last_prog:
                pbar.update(agg_progress - last_prog)
                last_prog = agg_progress

            elapsed = (datetime.now() - start_time).total_seconds()
            # Calculate ETA based on aggregated rate
            eta = (total_count - agg_progress) / agg_rate if agg_rate > 0 else 0
            
            status = {
                "activity": "ingestion",
                "state": "NUCLEAR (30 Real Workers)",
                "file": last_file,
                "progress": agg_progress,
                "total": total_count,
                "percentage": (agg_progress / total_count * 100) if total_count > 0 else 0,
                "rate": agg_rate,
                "eta_seconds": eta,
                "elapsed_seconds": elapsed,
                "errors": agg_errors,
                "timestamp": datetime.now().isoformat()
            }
            with open(FINAL_STATUS_FILE, 'w') as f:
                json.dump(status, f)
            
            if agg_progress + agg_errors >= total_count: break
        except Exception: pass
        time.sleep(1)
    pbar.close()

def manage_indexes(action="drop"):
    engine = create_engine(config.POSTGRES_CONN)
    queries = [
        "DROP INDEX IF EXISTS idx_log_eventos_level",
        "DROP INDEX IF EXISTS idx_log_eventos_timestamp",
        "DROP INDEX IF EXISTS idx_log_eventos_source"
    ]
    if action == "create":
        queries = [
            "CREATE INDEX idx_log_eventos_level ON public.log_eventos USING btree (level)",
            "CREATE INDEX idx_log_eventos_timestamp ON public.log_eventos USING btree (\"timestamp\")",
            "CREATE INDEX idx_log_eventos_source ON public.log_eventos USING btree (source_file)"
        ]
    with engine.connect() as conn:
        for q in queries:
            try:
                conn.execute(text(q)); conn.commit()
            except: pass

def main(target_uf=None):
    print(f"INITIALIZING NUCLEAR INGESTION V3 (Session: {RUN_ID})")
    print(f"USING LOCAL DATABASE: {config.LOCAL_POSTGRES_CONN.split('@')[-1]}") # Obfuscated but shows host/db
    if target_uf:
        print(f"Targeting specific UF: {target_uf.upper()}")
    
    if not os.path.exists(STATUS_DIR): os.makedirs(STATUS_DIR)
    # Clear old UI status files
    for f in os.listdir(STATUS_DIR): 
        try: os.remove(os.path.join(STATUS_DIR, f))
        except: pass

    manage_indexes("drop") # Keep dropped for maximum write speed
    
    # Scan all states in target (SUL)
    if target_uf:
        target_states = [target_uf.lower()]
    else:
        target_states = getattr(config, 'UF_FILTERS', ['pr', 'sc', 'rs'])
    base_dir = config.RAW_LOGS_DIR
    all_files = []
    
    print(f"Scanning states: {target_states}...")
    for state in target_states:
        state_dir = os.path.join(base_dir, state)
        if os.path.exists(state_dir):
            for root, _, files in os.walk(state_dir):
                for file in files:
                    if file.endswith('.logjez'):
                        all_files.append((os.path.join(root, file), state))
    
    total_scanned = len(all_files)
    print(f"Scanned {total_scanned} .logjez files locally.")

    # --- SMART REMOTE & LOCAL CHECK ---
    print("Checking for already processed files (Local & Remote)...")
    remote_engine = create_engine(config.REMOTE_POSTGRES_CONN)
    local_engine = create_engine(config.LOCAL_POSTGRES_CONN)
    already_done = set()
    
    # Check Local First (Fastest)
    try:
        with local_engine.connect() as l_conn:
            patterns = [f"{st}/%" for st in target_states] + [f"{st}\\%" for st in target_states]
            query = text("SELECT DISTINCT source_file FROM log_eventos WHERE " + " OR ".join(["source_file LIKE :p" + str(i) for i in range(len(patterns))]))
            params = {f"p{i}": p for i, p in enumerate(patterns)}
            res = l_conn.execute(query, params).fetchall()
            local_already = {row[0] for row in res}
            already_done.update(local_already)
        print(f"Found {len(local_already)} files already in local database.")
    except Exception as e:
        print(f"Local skip check failed: {e}")

    # Check Remote (to avoid re-syncing if already there)
    try:
        with remote_engine.connect() as r_conn:
            patterns = [f"{st}/%" for st in target_states] + [f"{st}\\%" for st in target_states]
            query = text("SELECT DISTINCT source_file FROM log_eventos WHERE " + " OR ".join(["source_file LIKE :p" + str(i) for i in range(len(patterns))]))
            params = {f"p{i}": p for i, p in enumerate(patterns)}
            res = r_conn.execute(query, params).fetchall()
            remote_already = {row[0] for row in res}
            already_done.update(remote_already)
        print(f"Found {len(already_done)} total files already processed.")
    except Exception as e:
        print(f"Remote check failed: {e}")

    # Filter files
    filtered_files = []
    for filepath, uf in all_files:
        db_source = f"{uf}/{os.path.basename(filepath)}"
        if db_source not in already_done:
            filtered_files.append((filepath, uf))
    
    total_to_process = len(filtered_files)
    skipped = total_scanned - total_to_process
    print(f"Smart Skip: {skipped} already done. {total_to_process} to go.")

    if total_to_process == 0:
        print("All files already processed on remote. Nothing to do!")
        return

    # Split files into chunks for workers
    num_workers = MAX_WORKERS
    chunks = [filtered_files[i::num_workers] for i in range(num_workers)]
    
    # Prune empty chunks if any
    chunks = [c for c in chunks if c]
    num_workers = len(chunks)

    db_str = config.LOCAL_POSTGRES_CONN
    start_time = datetime.now()
    processes = []
    
    print(f"Launching {num_workers} Persistent Real-Time Workers...")
    for wid, chunk in enumerate(chunks):
        p = Process(target=worker_proc, args=(wid, chunk, db_str, RUN_ID))
        p.start(); processes.append(p)
    
    print("Aggregator Active. Check Dashboard.")
    aggregator_main(total_to_process, start_time)

    for p in processes: p.join()
        
    print("  Recreating Indexes...")
    manage_indexes("create")
    print("\nNUCLEAR INGESTION V3 COMPLETE.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ingest RAW logs into database.")
    parser.add_argument("--uf", type=str, help="Specific UF to target (e.g., AC, AP)", default=None)
    args = parser.parse_args()
    main(target_uf=args.uf)
