
import pandas as pd
from sqlalchemy import create_engine, text
from src.analytics.tse_data_integrator import TSEDataDownloader
from config import config
import sys

engine = create_engine(config.POSTGRES_CONN)

def sync_models(ufs=['RR', 'AP', 'AC']):
    downloader = TSEDataDownloader(year=2022)
    
    print("📥 Baixando detalhes de votação do TSE (Portal Dados Abertos)...")
    # O arquivo BRASIL é o mais garantido, mas demora. Vamos tentar baixar se não existir.
    # TSEDataDownloader.load_detalhe_votacao_secao já faz o download/extração.
    
    detalhes_df = downloader.load_detalhe_votacao_secao()
    if detalhes_df.empty:
        print("❌ Falha ao carregar detalhes do TSE.")
        return

    for uf in ufs:
        print(f"\n🔄 Sincronizando modelos para {uf}...")
        
        # Filtra detalhes por UF
        df_uf = detalhes_df[detalhes_df['SG_UF'] == uf.upper()].copy()
        
        # Padroniza chaves
        df_uf['municipio_codigo'] = df_uf['CD_MUNICIPIO'].astype(str).str.zfill(5)
        df_uf['zona'] = df_uf['NR_ZONA'].astype(str).str.zfill(4)
        df_uf['secao'] = df_uf['NR_SECAO'].astype(str).str.zfill(4)
        
        # Obtém seções do banco que estão sem modelo
        with engine.connect() as conn:
            # Drop temporary table if exists
            conn.execute(text("DROP TABLE IF EXISTS tmp_models"))
            conn.commit()
            
            # Carrega dados para tabela temporária
            df_uf[['municipio_codigo', 'zona', 'secao', 'DS_MODELO_URNA']].to_sql('tmp_models', conn, if_exists='replace', index=False)
            
            # Update massivo
            result = conn.execute(text("""
                UPDATE section_metadata m
                SET modelo_urna = t."DS_MODELO_URNA"
                FROM tmp_models t
                WHERE m.uf = :uf
                AND m.municipio_codigo = t.municipio_codigo
                AND m.zona = t.zona
                AND m.secao = t.secao
            """), {"uf": uf.upper()})
            conn.commit()
            print(f"✅ {result.rowcount} seções atualizadas para {uf}.")

if __name__ == "__main__":
    sync_models()
