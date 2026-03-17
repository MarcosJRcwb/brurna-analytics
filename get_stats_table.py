
import os
import sys
import pandas as pd
from sqlalchemy import create_engine, text

# Adiciona src ao path
sys.path.append(os.path.abspath('src'))
from config import config

def get_stats():
    l_engine = create_engine(config.LOCAL_POSTGRES_CONN)
    r_engine = create_engine(config.REMOTE_POSTGRES_CONN)
    ufs = ['se', 'rr', 'to', 'ac', 'ap']
    
    # Totais conhecidos ou escaneados
    uf_totals = {}
    for uf in ufs:
        path = os.path.join(config.RAW_LOGS_DIR, uf)
        count = 0
        if os.path.exists(path):
            files = os.listdir(path)
            count = len([f for f in files if f.endswith('.logjez')])
        uf_totals[uf] = count

    results = []
    
    with l_engine.connect() as l_conn:
        # Pega estatísticas locais primeiro (Rápido)
        for uf in ufs:
            total = uf_totals.get(uf, 0)
            try:
                # Contagem direta em section_metadata (Indexada por UF)
                l_meta = l_conn.execute(text(f"SELECT COUNT(*) FROM section_metadata WHERE uf = '{uf.upper()}'")).scalar()
            except: l_meta = 0
            
            results.append({
                'UF': uf.upper(),
                'Total': total,
                'Ingest_L': l_meta,
                'Meta_L': l_meta,
                'Meta_R': 0,
                'Logs_R': 0
            })
            
    # Tenta estatísticas remotas com timeout baixo
    try:
        with r_engine.connect() as r_conn:
            r_conn.execute(text("SET statement_timeout = 5000")) # 5 seg timeout
            for res in results:
                uf = res['UF']
                try:
                    res['Meta_R'] = r_conn.execute(text(f"SELECT COUNT(*) FROM section_metadata WHERE uf = '{uf}'")).scalar()
                    # Resumo de logs remotos via estimativa se possível ou count simples
                    res['Logs_R'] = r_conn.execute(text(f"SELECT COUNT(*) FROM log_eventos WHERE source_file LIKE '{uf.lower()}/%'")).scalar()
                except:
                    pass
    except:
        print("Aviso: Banco remoto lento. Exibindo dados locais.")
            
    # Formatação da tabela
    print("\n### 📊 Evolução do Processamento (Fase 14)\n")
    print("| UF | Seções | Ingestão (L) | Forense (L) | Sincronia (Metadado) | Sincronia (Logs) | Status |")
    print("| :--- | :---: | :---: | :---: | :---: | :---: | :--- |")
    
    for r in results:
        p_ingest = (r['Ingest_L'] / r['Total'] * 100) if r['Total'] > 0 else 0
        p_meta = (r['Meta_L'] / r['Total'] * 100) if r['Total'] > 0 else 0
        p_sync_m = (r['Meta_R'] / r['Total'] * 100) if r['Total'] > 0 else 0
        p_sync_l = (r['Logs_R'] / r['Ingest_L'] * 100) if r['Ingest_L'] > 0 else 0
        
        status = "✅ Concluído" if p_sync_m >= 99 and p_ingest >= 99 else ("🔄 Processando" if p_ingest > 0 else "⏳ Aguardando")
        if r['UF'].lower() == 'rr' and p_ingest < 100: status = "🚀 **Ativo**"
        
        print(f"| {r['UF']} | {r['Total']} | {p_ingest:.1f}% | {p_meta:.1f}% | {p_sync_m:.1f}% | {p_sync_l:.1f}% | {status} |")

if __name__ == "__main__":
    get_stats()
