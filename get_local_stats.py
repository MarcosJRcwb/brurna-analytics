
import os
import sys
from sqlalchemy import create_engine, text

# Adiciona src ao path
sys.path.append(os.path.abspath('src'))
from config import config

def get_local_stats():
    l_engine = create_engine(config.LOCAL_POSTGRES_CONN)
    ufs = ['se', 'rr', 'to', 'ac', 'ap']
    
    uf_totals = {}
    for uf in ufs:
        path = os.path.join(config.RAW_LOGS_DIR, uf)
        count = 0
        if os.path.exists(path):
            files = os.listdir(path)
            count = len([f for f in files if f.endswith('.logjez')])
        uf_totals[uf] = count

    print("\n### 📊 Evolução do Processamento LOCAL (Fase 14)\n")
    print("| UF | Seções | Ingestão (L) | Forense (L) | Status |")
    print("| :--- | :---: | :---: | :---: | :--- |")
    
    with l_engine.connect() as l_conn:
        for uf in ufs:
            total = uf_totals.get(uf, 0)
            try:
                l_meta = l_conn.execute(text(f"SELECT COUNT(*) FROM section_metadata WHERE uf = '{uf.upper()}'")).scalar()
            except: l_meta = 0
            
            p_ingest = (l_meta / total * 100) if total > 0 else 0
            
            status = "✅ Concluído" if p_ingest >= 99 else ("🚀 **Ativo**" if p_ingest > 0 else "⏳ Aguardando")
            
            print(f"| {uf.upper()} | {total} | {p_ingest:.1f}% | {p_ingest:.1f}% | {status} |")

if __name__ == "__main__":
    get_local_stats()
