"""
Centralized Batch Processor for Brurna Analytics (v2).

Uses parallel workers for parsing but centralized, CHUNKED DB writing 
to maximize performance and prevent deadlocks.
"""

import sys
from pathlib import Path
from multiprocessing import Pool, cpu_count
from tqdm import tqdm
import pandas as pd
from typing import List, Dict, Tuple
import time
import json

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from src.parser.log_parser import TSELogParser
from src.analytics.aggregator import aggregate_logs
from src.database.db_writer import (
    save_log_patterns,
    save_temporal_metrics,
    engine,
    text
)
from config import config

def save_metadata_batch(metadata_list: List[Dict]):
    """Optimized batch insert for section metadata."""
    if not metadata_list:
        return
    
    try:
        conn = engine.connect()
        for metadata in metadata_list:
            if not metadata: continue
            
            severidades_json = json.dumps(metadata.get('severidades', {}))
            conn.execute(text("""
                INSERT INTO section_metadata (
                    uf, turno, municipio_codigo, zona, secao,
                    total_eventos, periodo_inicio, periodo_fim, duracao_segundos,
                    modelo_urna, aplicativos_usados, severidades, hash_arquivo
                )
                VALUES (
                    :uf, :turno, :municipio_codigo, :zona, :secao,
                    :total_eventos, :periodo_inicio, :periodo_fim, :duracao_segundos,
                    :modelo_urna, :aplicativos_usados, :severidades, :hash_arquivo
                )
                ON CONFLICT (uf, turno, municipio_codigo, zona, secao)
                DO UPDATE SET
                    total_eventos = EXCLUDED.total_eventos,
                    periodo_inicio = EXCLUDED.periodo_inicio,
                    periodo_fim = EXCLUDED.periodo_fim,
                    duracao_segundos = EXCLUDED.duracao_segundos,
                    modelo_urna = EXCLUDED.modelo_urna,
                    aplicativos_usados = EXCLUDED.aplicativos_usados,
                    severidades = EXCLUDED.severidades,
                    hash_arquivo = EXCLUDED.hash_arquivo
            """), {
                'uf': metadata.get('uf'),
                'turno': metadata.get('turno'),
                'municipio_codigo': metadata.get('municipio_codigo'),
                'zona': metadata.get('zona'),
                'secao': metadata.get('secao'),
                'total_eventos': metadata.get('total_eventos'),
                'periodo_inicio': metadata.get('periodo_inicio'),
                'periodo_fim': metadata.get('periodo_fim'),
                'duracao_segundos': metadata.get('duracao_segundos'),
                'modelo_urna': metadata.get('modelo_urna'),
                'aplicativos_usados': metadata.get('aplicativos_usados', []),
                'severidades': severidades_json,
                'hash_arquivo': metadata.get('hash_arquivo')
            })
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ Error saving metadata batch: {e}")

def process_worker(args: Tuple[Path, str, int]) -> Tuple[pd.DataFrame, pd.DataFrame, Dict, bool, str]:
    """Worker function: Parses one file and aggregates locally."""
    file_path, uf, turno = args
    try:
        parser = TSELogParser(str(file_path))
        df = parser.parse_file()
        secao_info = parser._extract_section_info_from_filename()
        # Adiciona modelo extraído do parser no secao_info
        secao_info['modelo_urna'] = parser.metadata.get('modelo_urna')
        
        p, t, m = aggregate_logs(df, uf, turno, secao_info)
        return p, t, m, True, ""
    except Exception as e:
        return pd.DataFrame(), pd.DataFrame(), {}, False, str(e)

def run_pipeline(uf: str, turno: int = 1, limit: int = None, workers: int = 24):
    """Runs the full pipeline with centralized, silent batch writes."""
    uf = uf.lower()
    raw_dir = config.RAW_LOGS_DIR / uf
    
    if not raw_dir.exists():
        print(f"❌ Directory not found: {raw_dir}")
        return

    files = list(raw_dir.glob("*.logjez"))
    if limit:
        files = files[:limit]
    
    if not files:
        print(f"❌ No files found for {uf}")
        return

    print("=" * 80)
    print(f"🚀 PIPELINE V2: {uf.upper()} ({len(files)} files)")
    print(f"🔧 Workers: {workers} | Chunk Size: 500")
    print("=" * 80)

    success_count = 0
    fail_count = 0
    args_list = [(f, uf, turno) for f in files]
    
    chunk_size = 500
    for i in range(0, len(args_list), chunk_size):
        chunk = args_list[i : i + chunk_size]
        print(f"📦 Processing Files {i+1} to {min(i+chunk_size, len(args_list))}...")
        
        chunk_patterns = []
        chunk_temporal = []
        chunk_metadata = []
        
        with Pool(processes=workers) as pool:
            results = list(tqdm(
                pool.imap(process_worker, chunk),
                total=len(chunk),
                desc=f"Parsing {uf.upper()}",
                ncols=100,
                leave=False
            ))
            
            for p, t, m, success, err in results:
                if success:
                    chunk_patterns.append(p)
                    chunk_temporal.append(t)
                    chunk_metadata.append(m)
                    success_count += 1
                else:
                    fail_count += 1
        
        # Centralized Silent DB write for this chunk
        if chunk_patterns:
            print("💾 Saving Patterns...")
            merged_p = pd.concat(chunk_patterns).groupby(['mensagem_padrao', 'severidade', 'aplicativo']).agg({
                'mensagem_exemplo': 'first',
                'primeira_ocorrencia': 'min',
                'ultima_ocorrencia': 'max',
                'ocorrencias': 'sum'
            }).reset_index()
            save_log_patterns(merged_p, uf, turno)
            
        if chunk_temporal:
            print("💾 Saving Temporal Metrics...")
            merged_t = pd.concat(chunk_temporal).groupby(['data', 'hora', 'aplicativo', 'severidade']).agg({
                'quantidade': 'sum'
            }).reset_index()
            save_temporal_metrics(merged_t, uf, turno)
            
        if chunk_metadata:
            print("💾 Saving Metadata Batch...")
            save_metadata_batch(chunk_metadata)

    print("\n" + "=" * 80)
    print(f"✅ COMPLETED {uf.upper()}")
    print(f"   Success: {success_count} | Failed: {fail_count}")
    print("=" * 80)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--uf", required=True)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--workers", type=int, default=24)
    args = parser.parse_args()
    run_pipeline(args.uf, limit=args.limit, workers=args.workers)
