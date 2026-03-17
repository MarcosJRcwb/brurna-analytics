
import py7zr
import sys
import os
import re
import shutil
import json
import time
import subprocess
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
NATIVE_7Z = r"C:\Program Files\7-Zip\7z.exe"

def update_status_json(current, total, current_file, state, start_time, errors=0, rate_fixed=None):
    """Simple JSON status update."""
    try:
        elapsed = (datetime.now() - start_time).total_seconds()
        rate = rate_fixed if rate_fixed else (current / elapsed if elapsed > 0 else 0)
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

def process_file_universal(args):
    """
    Worker function: Extract (Library or Native) -> Parse -> DB Insert
    """
    filepath, db_conn_str, method = args
    filename = os.path.basename(filepath)
    tmp_dir = f"tmp_bench_{os.getpid()}_{hash(filename)}"
    records = []
    
    try:
        if not os.path.exists(tmp_dir):
            os.makedirs(tmp_dir)

        target_file = None
        
        # 1. Extraction Phase
        if method == "native":
            # Use 7z.exe l (list) to find the file
            # Actually we usually know it starts with 'log' or '.dat'
            # Simpler: just extract everything to tmp_dir
            # cmd: 7z e <archive> -o<dir> -y
            subprocess.run([NATIVE_7Z, "e", filepath, f"-o{tmp_dir}", "-y"], 
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            # Find the log file in tmp_dir
            for f in os.listdir(tmp_dir):
                if f.endswith('.dat') or 'log' in f.lower():
                    target_file = os.path.join(tmp_dir, f)
                    break
        else:
            # py7zr method
            with py7zr.SevenZipFile(filepath, mode='r') as z:
                target = next((f for f in z.getnames() if f.endswith('.dat') or 'log' in f.lower()), None)
                if target:
                    z.extract(path=tmp_dir, targets=[target])
                    target_file = os.path.join(tmp_dir, target)

        if not target_file or not os.path.exists(target_file):
            shutil.rmtree(tmp_dir, ignore_errors=True)
            return (filename, 0, 0)

        # 2. Read & Parse
        with open(target_file, 'rb') as f:
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

        # 3. DB Insert
        if records:
            engine = create_engine(db_conn_str)
            with engine.connect() as conn:
                conn.execute(
                    text("INSERT INTO log_eventos (source_file, timestamp, level, code, message, original_line) VALUES (:source_file, :timestamp, :level, :code, :message, :original_line)"),
                    records
                )
                conn.commit()
            return (filename, len(records), 0)
            
    except Exception:
        return (filename, 0, 1)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    return (filename, 0, 0)

def run_bench(files, db_str, method, workers):
    print(f"--- Benchmarking METHOD: {method} ---")
    start = time.time()
    results_count = 0
    err_count = 0
    
    with ProcessPoolExecutor(max_workers=workers) as executor:
        args = [(f, db_str, method) for f in files]
        futures = {executor.submit(process_file_universal, arg): arg[0] for arg in args}
        for future in as_completed(futures):
            _, count, err = future.result()
            results_count += 1
            err_count += err
            print(f"[{results_count}/{len(files)}] {method}...", end='\r')
            
    duration = time.time() - start
    rate = len(files) / duration if duration > 0 else 0
    print(f"\nMethod {method} finished in {duration:.2f}s (Rate: {rate:.2f} files/sec)")
    return rate

def main():
    print("🚀 Initializing SELF-OPTIMIZING Ingestion Engine...")
    base_dir = r"C:\Users\marco\Downloads\TSE\data\raw_logs"
    target_states = ['pr', 'sc', 'rs']
    
    # Discovery
    all_files = []
    for state in target_states:
        state_dir = os.path.join(base_dir, state)
        if os.path.exists(state_dir):
            for root, _, files in os.walk(state_dir):
                for file in files:
                    if file.endswith('.logjez'):
                        all_files.append(os.path.join(root, file))
    
    total = len(all_files)
    print(f"Found {total} files.")
    
    db_str = config.POSTGRES_CONN
    MAX_WORKERS = 30
    BENCH_SIZE = 100
    
    if total < BENCH_SIZE * 2:
        print("Not enough files for benchmark. Using library.")
        best_method = "library"
    else:
        # Phase 1: Benchmark
        update_status_json(0, total, "Benchmarking Library...", "PILOT_PY7ZR", datetime.now())
        rate_lib = run_bench(all_files[:BENCH_SIZE], db_str, "library", MAX_WORKERS)
        
        update_status_json(BENCH_SIZE, total, "Benchmarking Native...", "PILOT_NATIVE", datetime.now())
        rate_native = run_bench(all_files[BENCH_SIZE:BENCH_SIZE*2], db_str, "native", MAX_WORKERS)
        
        if rate_native > rate_lib:
            print(f"🏆 NATIVE 7z is faster ({rate_native:.2f} vs {rate_lib:.2f})")
            best_method = "native"
        else:
            print(f"🏆 LIBRARY py7zr is faster ({rate_lib:.2f} vs {rate_native:.2f})")
            best_method = "library"

    # Phase 2: Mass Processing
    start_mass = datetime.now()
    processed = BENCH_SIZE * 2
    error_count = 0
    
    print(f"🔥 Starting Mass Ingestion using {best_method} with {MAX_WORKERS} workers...")
    
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        mass_args = [(f, db_str, best_method) for f in all_files[processed:]]
        futures = {executor.submit(process_file_universal, arg): arg[0] for arg in mass_args}
        
        for future in as_completed(futures):
            fname = os.path.basename(futures[future])
            _, count, err = future.result()
            processed += 1
            error_count += err
            
            if processed % 20 == 0:
                update_status_json(processed, total, fname, f"SUL ({best_method.upper()})", start_mass, error_count)
                print(f"[{processed}/{total}] {best_method} ingesting...", end='\r')

    print("\n✅ Ingestion complete.")

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
