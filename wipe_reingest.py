"""
WIPE & RE-INGEST SCRIPT v2
1. Conta arquivos em disco (cache)
2. Apaga TUDO das tabelas agregadas E log_eventos (local + remoto)
3. Re-ingere cada UF do disco
"""
import sys, os, time
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from pathlib import Path
from sqlalchemy import create_engine, text
from config import config

RAW = Path(r"C:\Users\marco\Downloads\TSE\data\raw_logs")

def count_files():
    print("=== INVENTARIO DE ARQUIVOS EM DISCO ===")
    ufs = sorted([p.name for p in RAW.iterdir() if p.is_dir()])
    counts = {}
    for uf in ufs:
        n = len(list((RAW / uf).glob("*.logjez")))
        if n > 0:
            counts[uf] = n
            print(f"  {uf.upper()}: {n} arquivos .logjez")
    print(f"\nTotal UFs com dados: {len(counts)}")
    print(f"Total arquivos: {sum(counts.values())}")
    return counts

def wipe_all():
    # Incluindo log_eventos que é usado pelo Smart Skip
    tables = ["log_exceptions", "log_patterns", "temporal_metrics", "section_metadata", "mesarios", "log_eventos"]
    
    for label, conn_str in [("LOCAL", config.LOCAL_POSTGRES_CONN), ("REMOTO", config.REMOTE_POSTGRES_CONN)]:
        print(f"\n=== LIMPANDO BANCO {label} ===")
        eng = create_engine(conn_str)
        with eng.begin() as conn:
            for t in tables:
                try:
                    cnt = conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
                    conn.execute(text(f"TRUNCATE TABLE {t} CASCADE"))
                    print(f"  {t}: {cnt} registros apagados")
                except Exception as e:
                    print(f"  {t}: {e}")
        eng.dispose()
    
    print("\nTODOS os bancos limpos (incluindo log_eventos)!")

def reingest(counts):
    import subprocess
    ordered = sorted(counts.keys(), key=lambda k: counts[k])
    print(f"\n=== INGESTAO LIMPA: {len(ordered)} UFs ===")
    print(f"Ordem: {[u.upper() for u in ordered]}")
    
    for uf in ordered:
        print(f"\n--- {uf.upper()} ({counts[uf]} arquivos) ---")
        t0 = time.time()
        result = subprocess.run(
            ["python", "src/data_ingestion/ingest_nuclear.py", "--uf", uf.upper()],
            cwd=str(Path(__file__).parent)
        )
        elapsed = time.time() - t0
        status = "OK" if result.returncode == 0 else f"ERRO (code {result.returncode})"
        print(f"  {uf.upper()}: {status} ({elapsed:.0f}s)")
    
    print("\n=== INGESTAO COMPLETA ===")

def verify():
    print("\n=== VERIFICACAO FINAL ===")
    engine = create_engine(config.POSTGRES_CONN)
    with engine.connect() as conn:
        for t in ["section_metadata", "temporal_metrics", "log_patterns", "log_exceptions", "mesarios"]:
            cnt = conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
            ufs = conn.execute(text(f"SELECT DISTINCT uf FROM {t} ORDER BY uf")).fetchall()
            uf_list = ", ".join([r[0] for r in ufs]) if ufs else "nenhuma"
            print(f"  {t}: {cnt} registros, UFs: {uf_list}")
    engine.dispose()

if __name__ == "__main__":
    counts = count_files()
    if not counts:
        print("Nenhum arquivo encontrado!")
        sys.exit(1)
    
    wipe_all()
    reingest(counts)
    verify()
