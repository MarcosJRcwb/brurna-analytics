
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

def get_db_engine():
    """Create a new engine for each process/call to avoid sharing issues."""
    return create_engine(config.POSTGRES_CONN)

def update_status_json(current, total, current_file, state, start_time, errors=0):
    """Simple JSON status update."""
    try:
        elapsed = (datetime.now() - start_time).total_seconds()
        rate = current / elapsed if elapsed > 0 else 0 
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

def process_single_file_safe(args):
    """
    Worker function: Extract -> Parse -> DB Insert
    """
    filepath, db_conn_str = args
    filename = os.path.basename(filepath)
    
    # Unique temp folder for this process/file
    tmp_dir = f"tmp_p_{os.getpid()}_{hash(filename)}"
    records = []
    
    try:
        if not py7zr.is_7zfile(filepath):
            return (filename, 0, 0) # Ignored

        if not os.path.exists(tmp_dir):
            os.makedirs(tmp_dir)

        # 1. Extract
        with py7zr.SevenZipFile(filepath, mode='r') as z:
            target = next((f for f in z.getnames() if f.endswith('.dat') or 'log' in f.lower()), None)
            if not target:
                shutil.rmtree(tmp_dir, ignore_errors=True)
                return (filename, 0, 0)
            
            z.extract(path=tmp_dir, targets=[target])
            extracted_path = os.path.join(tmp_dir, target)
            
            # 2. Read & Parse
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
                    records.append(parsed)
            
            if os.path.exists(extracted_path):
                os.remove(extracted_path)

        # 3. Insert into DB (Worker specific connection)
        if records:
            engine = create_engine(db_conn_str)
            with engine.connect() as conn:
                conn.execute(
                    text("INSERT INTO log_eventos (source_file, timestamp, level, code, message, original_line) VALUES (:source_file, :timestamp, :level, :code, :message, :original_line)"),
                    records
                )
                conn.commit()
            return (filename, len(records), 0) # Success
            
    except Exception as e:
        # print(f"Error {filename}: {e}") # keep console clean
        return (filename, 0, 1) # Error
    finally:
        if os.path.exists(tmp_dir):
            try:
                shutil.rmtree(tmp_dir, ignore_errors=True)
            except:
                pass
    return (filename, 0, 0)

def main():
    print("🚀 Initializing SIMPLE PARALLEL Engine (No Batching)...")
    
    base_dir = r"C:\Users\marco\Downloads\TSE\data\raw_logs"
    target_states = ['pr', 'sc', 'rs']
    
    start_time = datetime.now()
    
    # 1. Discover files
    print("Scanning files...")
    all_files = []
    
    # Use config from parent to avoid path issues
    for state in target_states:
        state_dir = os.path.join(base_dir, state)
        if os.path.exists(state_dir):
            for root, _, files in os.walk(state_dir):
                for file in files:
                    if file.endswith('.logjez'):
                        all_files.append(os.path.join(root, file))
    
    total_files = len(all_files)
    print(f"✅ Found {total_files} files.")
    
    # Prepare for Processing
    db_str = config.POSTGRES_CONN
    
    # Use 30 workers for high-performance (Ryzen 9 7950x)
    MAX_WORKERS = 30
    process_args = [(f, db_str) for f in all_files]
    
    processed_count = 0
    error_count = 0
    
    update_status_json(0, total_files, "Starting Pool...", "STARTING", start_time)
    
    # 2. Execute Parallel
    print(f"🔥 Starting Pool with {MAX_WORKERS} workers...")
    
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all tasks mapped 1:1
        futures = {executor.submit(process_single_file_safe, arg): arg[0] for arg in process_args}
        
        for future in as_completed(futures):
            fname = os.path.basename(futures[future])
            try:
                _, count, err = future.result()
                processed_count += 1
                error_count += err
                
                # Update status every 10 files to keep UI responsive but not flooded
                if processed_count % 10 == 0:
                    update_status_json(processed_count, total_files, fname, "SUL (Parallel Simple)", start_time, error_count)
                    print(f"[{processed_count}/{total_files}] Done: {fname}...", end='\r')
            except Exception as e:
                error_count += 1
                print(f"Task Failed: {e}")

    update_status_json(total_files, total_files, "DONE", "COMPLETED", start_time, error_count)
    print("\n✅ Ingestion Finished.")

if __name__ == "__main__":
    multiprocessing.freeze_support() # Crucial for Windows
    main()
