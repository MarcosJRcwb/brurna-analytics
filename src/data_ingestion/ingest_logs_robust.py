
import py7zr
import sys
import os
import re
import shutil
import json
import time
from datetime import datetime
from sqlalchemy import create_engine, text
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing

# Fix path to import config from root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
try:
    from config import config
except ImportError:
    import config

LOG_REGEX = re.compile(r'^(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2}:\d{2})\s+(\w+)\s+([A-Z0-9]+)?\s*(.*)$')
STATUS_FILE = "ingestion_status.json"

def setup_db():
    return create_engine(config.POSTGRES_CONN)

def update_status(current, total, current_file, state, start_time, errors=0):
    """Updates the JSON status file for the Dashboard."""
    try:
        elapsed = (datetime.now() - start_time).total_seconds()
        rate = current / elapsed if elapsed > 0 else 0 # files per second
        eta = (total - current) / rate if rate > 0 else 0
        
        status = {
            "activity": "ingestion",
            "state": state,
            "file": current_file,
            "progress": current,
            "total": total,
            "percentage": (current / total * 100) if total > 0 else 0,
            "rate": rate,
            "eta_seconds": eta,
            "elapsed_seconds": elapsed,
            "errors": errors,
            "timestamp": datetime.now().isoformat()
        }
        with open(STATUS_FILE, 'w') as f:
            json.dump(status, f)
    except Exception:
        pass

def parse_line(line, filename):
    match = LOG_REGEX.match(line)
    if match:
        date_str, time_str, level, code, msg = match.groups()
        is_critical = level != "INFO"
        if not is_critical:
            keywords = ["bateria", "reboot", "inicializa", "boot", "desliga", "hash", "assinatura", "lacre", "viol", "erro", "falha"]
            if any(k in msg.lower() for k in keywords):
                is_critical = True
        
        if is_critical:
            try:
                ts = datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %H:%M:%S")
                return {
                    'source_file': filename,
                    'timestamp': ts,
                    'level': level,
                    'code': code or '',
                    'message': msg,
                    'original_line': "" 
                }
            except ValueError:
                return None
    return None

def process_file_batch(args):
    """Worker function to process a BATCH of files."""
    file_list, db_url = args
    batch_records = []
    
    processed_count = 0
    error_count = 0
    last_file = ""
    
    # Process all files in batch first
    for filepath in file_list:
        filename = os.path.basename(filepath)
        last_file = filename
        tmp_base = f"tmp_ingest_{os.getpid()}_{int(time.time()*1000)}_{hash(filename)}"
        
        try:
            if not py7zr.is_7zfile(filepath):
                continue

            if not os.path.exists(tmp_base):
                os.makedirs(tmp_base)

            with py7zr.SevenZipFile(filepath, mode='r') as z:
                target = next((f for f in z.getnames() if f.endswith('.dat') or 'log' in f.lower()), None)
                if not target:
                    shutil.rmtree(tmp_base, ignore_errors=True)
                    continue
                
                z.extract(path=tmp_base, targets=[target])
                extracted_path = os.path.join(tmp_base, target)
                
                with open(extracted_path, 'rb') as f:
                    content = f.read()
                    
                try:
                    text_content = content.decode('utf-8')
                except:
                    text_content = content.decode('latin1', errors='ignore')
                    
                lines = text_content.splitlines()
                for line in lines:
                    parsed = parse_line(line, filename)
                    if parsed:
                        batch_records.append(parsed)
                
                # Cleanup
                if os.path.exists(extracted_path):
                    os.remove(extracted_path)
            
            processed_count += 1
            
        except Exception:
            error_count += 1
        finally:
            if os.path.exists(tmp_base):
                try:
                    shutil.rmtree(tmp_base, ignore_errors=True)
                except:
                    pass

    # Batch Insert into DB (One transaction per file batch)
    if batch_records:
        try:
            engine = create_engine(db_url)
            with engine.connect() as conn:
                conn.execute(
                    text("INSERT INTO log_eventos (source_file, timestamp, level, code, message, original_line) VALUES (:source_file, :timestamp, :level, :code, :message, :original_line)"),
                    batch_records
                )
                conn.commit()
        except Exception as e:
            print(f"DB Error: {e}")
            pass
            
    return (last_file, processed_count, error_count)

def main():
    base_dir = r"C:\Users\marco\Downloads\TSE\data\raw_logs"
    target_states = ['pr', 'sc', 'rs'] 
    
    print("Initializing HIGH-PERFORMANCE BATCHED Parallel Ingestion...")
    
    # 1. Discover all files
    all_files = []
    print("Scanning directories...")
    for state in target_states:
        state_dir = os.path.join(base_dir, state)
        if os.path.exists(state_dir):
            for root, _, files in os.walk(state_dir):
                for file in files:
                    if file.endswith('.logjez'):
                        all_files.append(os.path.join(root, file))
    
    total_files = len(all_files)
    print(f"Found {total_files} files.")
    
    # 2. Config parallel processing
    # Reduced to 4 workers and 20 files per batch to prevent BrokenProcessPool (Memory/Stability)
    max_workers = 4
    print(f"Starting Pool with {max_workers} workers...")
    
    BATCH_SIZE = 5
    
    batches = [all_files[i:i + BATCH_SIZE] for i in range(0, total_files, BATCH_SIZE)]
    print(f"Created {len(batches)} batches of {BATCH_SIZE} files.")
    
    processed_count = 0
    error_count = 0
    start_time = datetime.now()
    
    # Write initial status IMMEDIATELY so Dashboard isn't empty
    update_status(0, total_files, "Starting Workers...", "SUL (Safe Batch)", start_time, 0)
    
    db_url = config.POSTGRES_CONN
    
    # Use spawn context for Windows stability if possible, but default is usually spawn/forkserver on 3.14? 
    # Standard ProcessPoolExecutor uses default.
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_file_batch, (batch, db_url)): batch for batch in batches}
        
        for future in as_completed(futures):
            fname, count, err = future.result()
            
            processed_count += count
            error_count += err
            
            # Update status
            update_status(processed_count, total_files, fname, "SUL (Turbo Batch)", start_time, error_count)
            print(f"[{processed_count}/{total_files}] Batch done. Last: {fname} ", end='\r')

    # Final Status
    update_status(total_files, total_files, "COMPLETED", "ALL", start_time, error_count)
    print(f"\nIngestion Finished. Errors: {error_count}")

if __name__ == "__main__":
    main()
