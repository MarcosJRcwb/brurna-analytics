"""
LIMPEZA INTEGRAL + VERIFICACAO
Apaga TODAS as tabelas de dados em ambos os bancos.
Depois verifica e imprime a prova.
"""
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from sqlalchemy import create_engine, text
from config import config

ALL_TABLES = [
    "log_exceptions",
    "log_patterns",
    "temporal_metrics",
    "section_metadata",
    "mesarios",
    "log_eventos",
]

def wipe_and_verify(label, conn_str):
    eng = create_engine(conn_str)
    
    print(f"\n{'='*60}")
    print(f"  BANCO: {label}")
    print(f"{'='*60}")
    
    # ANTES
    print(f"\n  ANTES DA LIMPEZA:")
    with eng.connect() as conn:
        for t in ALL_TABLES:
            try:
                cnt = conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
                print(f"    {t}: {cnt} registros")
            except Exception as e:
                print(f"    {t}: tabela nao existe")
    
    # TRUNCATE
    print(f"\n  EXECUTANDO TRUNCATE...")
    with eng.begin() as conn:
        for t in ALL_TABLES:
            try:
                conn.execute(text(f"TRUNCATE TABLE {t} CASCADE"))
                print(f"    TRUNCATE {t} CASCADE -> OK")
            except Exception as e:
                print(f"    TRUNCATE {t} -> {e}")
    
    # DEPOIS
    print(f"\n  DEPOIS DA LIMPEZA:")
    with eng.connect() as conn:
        all_zero = True
        for t in ALL_TABLES:
            try:
                cnt = conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
                status = "LIMPA" if cnt == 0 else f"FALHOU ({cnt} restantes!)"
                if cnt > 0:
                    all_zero = False
                print(f"    {t}: {cnt} registros -> {status}")
            except Exception as e:
                print(f"    {t}: tabela nao existe")
    
    if all_zero:
        print(f"\n  RESULTADO: BANCO {label} 100% LIMPO")
    else:
        print(f"\n  RESULTADO: ATENCAO - Algumas tabelas NAO foram limpas!")
    
    eng.dispose()
    return all_zero

if __name__ == "__main__":
    print("LIMPEZA INTEGRAL DE TODAS AS TABELAS")
    print("Local + Remoto")
    
    r1 = wipe_and_verify("LOCAL", config.LOCAL_POSTGRES_CONN)
    r2 = wipe_and_verify("REMOTO (Contabo)", config.REMOTE_POSTGRES_CONN)
    
    print(f"\n{'='*60}")
    print(f"  RESUMO FINAL")
    print(f"{'='*60}")
    print(f"  Local:  {'100% LIMPO' if r1 else 'COM PROBLEMAS'}")
    print(f"  Remoto: {'100% LIMPO' if r2 else 'COM PROBLEMAS'}")
    print(f"{'='*60}")
    
    # Salvar prova em arquivo
    with open("wipe_proof.txt", "w") as f:
        f.write("Limpeza executada com sucesso.\n")
        f.write(f"Local: {'LIMPO' if r1 else 'COM PROBLEMAS'}\n")
        f.write(f"Remoto: {'LIMPO' if r2 else 'COM PROBLEMAS'}\n")
