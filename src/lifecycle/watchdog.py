import sys
import time
import subprocess
import json
import os
from datetime import datetime
import signal

# Config
WATCH_FILE = "ingestion_status.json"
SCRIPT_PATH = "src/data_ingestion/ingest_logs_serial.py"
LOG_FILE = "logs/watchdog.log"
TIMEOUT_SECONDS = 180 # 3 minutes without update = STALE

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] [WATCHDOG] {msg}"
    try:
        print(formatted)
    except:
        pass # Ignore console print errors
        
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
    except Exception as e:
        # Fallback if logging fails
        pass

def get_last_update_time():
    if not os.path.exists(WATCH_FILE):
        return 0
    try:
        with open(WATCH_FILE, 'r') as f:
            data = json.load(f)
            # Parse timestamp if available, else use file mtime
            if 'timestamp' in data:
                return datetime.fromisoformat(data['timestamp']).timestamp()
            return os.path.getmtime(WATCH_FILE)
    except:
        return os.path.getmtime(WATCH_FILE)

def start_process():
    log(f"Launching worker: {SCRIPT_PATH}")
    # Run unbuffered (-u) to ensure logs flow
    return subprocess.Popen([sys.executable, "-u", SCRIPT_PATH], 
                            creationflags=subprocess.CREATE_NEW_CONSOLE)

def kill_process(proc):
    if proc:
        log(f"Killing PID {proc.pid}...")
        try:
            # Try graceful terminate first
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Force kill if stuck
                proc.kill()
        except Exception as e:
            log(f"Error killing process: {e}")

def main():
    if not os.path.exists("logs"):
        os.makedirs("logs")
        
    log("Starting Autonomous Supervision Mode")
    
    process = start_process()
    process_start_time = time.time()
    GRACE_PERIOD = 60 # Give the worker 60s to write the first status file
    
    while True:
        try:
            # 1. Check if process is alive
            if process.poll() is not None:
                log(f"Process died (Exit Code: {process.returncode}). Restarting in 5s...")
                time.sleep(5)
                process = start_process()
                process_start_time = time.time()
                continue
                
            # 2. Check heartbeat (Status File)
            # ONLY check if we are past the grace period
            if time.time() - process_start_time > GRACE_PERIOD:
                last_heartbeat = get_last_update_time()
                now = time.time()
                elapsed = now - last_heartbeat
                
                if elapsed > TIMEOUT_SECONDS:
                    log(f"STALE DETECTED! No heartbeat for {int(elapsed)}s. Force-restarting...")
                    kill_process(process)
                    time.sleep(2)
                    process = start_process()
                    process_start_time = time.time()
                    continue
            
            # log(f"Health OK. Last beat: {int(elapsed)}s ago.")
            time.sleep(10)
            
        except KeyboardInterrupt:
            kill_process(process)
            log("Watchdog terminated by user.")
            break
        except Exception as e:
            log(f"Watchdog internal error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
