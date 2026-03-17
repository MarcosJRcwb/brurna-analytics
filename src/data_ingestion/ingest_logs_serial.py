
import py7zr
import sys
import os
import re
import shutil
import json
import time
from datetime import datetime
from sqlalchemy import create_engine, text

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

def update_status_json(current, total, current_file, state, start_time, errors=0):
    """Updates the JSON status file for the Dashboard."""
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

def process_file_single(filepath, engine):
    tmp_base = f"tmp_serial_{os.getpid()}_{int(time.time()*1000)}"
    filename = os.path.basename(filepath)
    batch = []
    
    try:
        # Check valid 7z
        if not py7zr.is_7zfile(filepath):
            return 0

        if not os.path.exists(tmp_base):
            os.makedirs(tmp_base)

        with py7zr.SevenZipFile(filepath, mode='r') as z:
            target = next((f for f in z.getnames() if f.endswith('.dat') or 'log' in f.lower()), None)
            if not target:
                shutil.rmtree(tmp_base, ignore_errors=True)
                return 0
            
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
                    batch.append(parsed)
            
            if os.path.exists(extracted_path):
                os.remove(extracted_path)

        if batch:
            with engine.connect() as conn:
                conn.execute(
                    text("INSERT INTO log_eventos (source_file, timestamp, level, code, message, original_line) VALUES (:source_file, :timestamp, :level, :code, :message, :original_line)"),
                    batch
                )
                conn.commit()
            return 1 # Success
            
    except Exception as e:
        print(f"Error on {filename}: {e}")
        return -1 # Error
    finally:
        if os.path.exists(tmp_base):
            try:
                shutil.rmtree(tmp_base, ignore_errors=True)
            except:
                pass
    return 0

def main():
    print("Initializing SERIAL (Reliable) Ingestion Engine...")
    base_dir = r"C:\Users\marco\Downloads\TSE\data\raw_logs"
    target_states = ['pr', 'sc', 'rs']

    import logging
    
    # Setup Internal Logging (Avoids Shell Locks)
    log_dir = os.path.join(os.path.dirname(base_dir), "logs") # Try to save near data or project root
    if not os.path.exists(log_dir):
        # Fallback to project root logs if data/logs doesn't exist
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"ingestion_serial_{timestamp}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout) # Keep printing to console too
        ]
    )
    
    print(f"🚀 Initializing SERIAL Engine. Logs: {log_file}")
    logging.info("Starting ingestion process...")
    
    start_time = datetime.now()
    
    # Reset status file immediately
    update_status_json(0, 0, "Initializing Serial Engine...", "STARTUP", start_time)
    
    # 1. Discover 
    print("Scanning files...")
    logging.info("Scanning directories for .logjez files...")
    update_status_json(0, 0, "Scanning files...", "SCANNING", start_time)
    
    all_files = []
    for state in target_states:
        state_dir = os.path.join(base_dir, state)
        if os.path.exists(state_dir):
            for root, _, files in os.walk(state_dir):
                for file in files:
                    if file.endswith('.logjez'):
                        all_files.append(os.path.join(root, file))
                        # Report scan progress every 1000 files
                        if len(all_files) % 2000 == 0:
                             update_status_json(0, 0, f"Found {len(all_files)} files...", "SCANNING", start_time)
                             print(f"Found {len(all_files)}...", end='\r')

    total_files = len(all_files)
    print(f"\nTotal files: {total_files}")
    
    # 2. Process
    engine = setup_db()
    processed_count = 0
    error_count = 0
    
    for i, filepath in enumerate(all_files):
        fname = os.path.basename(filepath)
        
        # Show activity immediately even if slow
        if i % 10 == 0:
            update_status_json(i, total_files, fname, "SUL (Serial)", start_time, error_count)
            msg = f"Processing {i}/{total_files}: {fname}..."
            print(msg, end='\r')
            if i % 100 == 0: logging.info(msg) # Log every 100th to avoid huge log files
            
        res = process_file_single(filepath, engine)
        
        if res == -1:
            error_count += 1
        
        processed_count += 1
        
    update_status_json(total_files, total_files, "DONE", "COMPLETED", start_time, error_count)
    print("\nDone.")

if __name__ == "__main__":
    main()
