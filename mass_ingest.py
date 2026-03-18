import subprocess
import sys
import time

def run_cmd(cmd):
    print(f"\n🚀 Running: {cmd}")
    process = subprocess.Popen(cmd, shell=True)
    process.wait()
    return process.returncode

def main():
    # Ordered by size
    ordered_ufs = ['rr', 'ap', 'ac', 'to', 'se']
    
    print(f"=== STARTING NON-STOP MASS INGESTION WITH PIPELINED SYNC ===")
    
    for uf in ordered_ufs:
        print(f"\n{'='*40}")
        print(f" UF: {uf.upper()}")
        print(f"{'='*40}")
        
        # 1. Ingest Raw Logs (Using Nuclear Speed)
        print(f"[{uf.upper()}] ☢️ Phase 1: Nuclear Ingestion...")
        ing_code = run_cmd(f"python src/data_ingestion/ingest_nuclear.py --uf {uf}")
        if ing_code != 0:
            print(f"❌ Error: Ingestion for {uf} failed.")
            continue
            
        # 2. Forensic Aggregation (Populates metadata/patterns/mesarios)
        print(f"\n[{uf.upper()}] 🕵️ Phase 2: Forensic Aggregation...")
        agg_code = run_cmd(f"{sys.executable} src/analytics/process_forensic_patterns.py --uf {uf}")
        if agg_code != 0:
            print(f"❌ Error: Aggregation for {uf} failed.")
            
        # 3. Parallel Sync & Cleanup (Runs in background while next UF ingests!)
        print(f"\n[{uf.upper()}] ☁️ Phase 3: Parallel Remote Sync & Local Cleanup...")
        subprocess.Popen(["powershell", "-c", f"{sys.executable} src/data_ingestion/sync_nuclear.py --uf {uf} >> logs/workers/sync_{uf}.log 2>&1"])
        
        print(f"\n✅ Finished {uf.upper()} - Next phase starting...")
        time.sleep(2)

    print("\n=== ALL STATES PROCESSED ===")
    print("Wait 60s for final background syncs to complete...")
    time.sleep(60)

if __name__ == "__main__":
    main()
