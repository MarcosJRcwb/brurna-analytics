import py7zr
import sys
import os
import re
import shutil
from datetime import datetime
from sqlalchemy import create_engine, text
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from config import config

LOG_REGEX = re.compile(r'^(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2}:\d{2})\s+(\w+)\s+([A-Z0-9]+)?\s*(.*)$')

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

def process_single_file(filepath):
    engine = create_engine(config.POSTGRES_CONN)
    tmp_dir = f"tmp_single_ingest_{os.getpid()}"
    
    try:
        os.makedirs(tmp_dir, exist_ok=True)
        
        with py7zr.SevenZipFile(filepath, 'r') as archive:
            archive.extractall(path=tmp_dir)
        
        log_file = None
        for root, dirs, files in os.walk(tmp_dir):
            for file in files:
                if file.endswith('.dat'):
                    log_file = os.path.join(root, file)
                    break
        
        if not log_file:
            print(f"No .dat file found in {filepath}")
            return 0
        
        rows = []
        with open(log_file, 'r', encoding='latin-1', errors='ignore') as f:
            for line in f:
                parsed = parse_line(line.strip(), filepath)
                if parsed:
                    rows.append(parsed)
        
        if rows:
            with engine.connect() as conn:
                conn.execute(
                    text("""
                    INSERT INTO log_eventos (source_file, timestamp, level, code, message, original_line)
                    VALUES (:source_file, :timestamp, :level, :code, :message, :original_line)
                    """),
                    rows
                )
                conn.commit()
        
        print(f"✅ Processado: {len(rows)} linhas de {Path(filepath).name}")
        return len(rows)
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return 0
    finally:
        if os.path.exists(tmp_dir):
            try:
                shutil.rmtree(tmp_dir)
            except:
                pass

if __name__ == "__main__":
    missing_file = r"C:\Users\marco\Downloads\TSE\data\raw_logs\ap\o00407-0605000020072.logjez"
    
    if os.path.exists(missing_file):
        print(f"Processando arquivo faltante: {Path(missing_file).name}")
        count = process_single_file(missing_file)
        print(f"\n✅ Ingestão completa! Total: {count} logs adicionados")
    else:
        print(f"❌ Arquivo não encontrado: {missing_file}")
