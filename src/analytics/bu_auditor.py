
import pandas as pd
from sqlalchemy import create_engine, text
from src.analytics.tse_data_integrator import TSEDataIntegrator
from config import config
from pathlib import Path

class BUAuditor:
    """Auditoria cruzada entre Logs (votos computados) e Boletins de Urna (TSE)"""
    
    def __init__(self, year: int = 2022):
        self.year = year
        self.engine = create_engine(config.POSTGRES_CONN)
        self.integrator = TSEDataIntegrator(year=year)
    
    def generate_audit_report(self, uf: str) -> pd.DataFrame:
        print(f"⚖️ Gerando Relatório de Auditoria BU para {uf.upper()}...")
        
        # 1. Obtém dados do banco (Logs)
        query = f"""
            SELECT 
                municipio_codigo, zona, secao, 
                votos_computados as votos_log,
                eleitores_habilitados as eleitores_log,
                total_eventos
            FROM section_metadata 
            WHERE uf = '{uf.upper()}'
        """
        logs_df = pd.read_sql(query, self.engine)
        
        if logs_df.empty:
            print(f"⚠️ Nenhuma seção encontrada no banco para {uf}.")
            return pd.DataFrame()
            
        print(f"   ✅ {len(logs_df)} seções carregadas do banco.")
        
        # 2. Obtém dados oficiais do TSE (BU)
        # PRIORIDADE: Usar Presidente (1) para capturar comparecimento total (incluindo trânsito)
        # Nota: Presidente reside no arquivo detalhe_votacao_secao_2022_BRASIL.csv
        detalhes_df = self.integrator.downloader.load_detalhe_votacao_secao() 
        if detalhes_df.empty:
            print("❌ Falha ao carregar detalhes do TSE.")
            return pd.DataFrame()
            
        # Filtra e padroniza
        detalhes_df = detalhes_df[detalhes_df['SG_UF'] == uf.upper()].copy()
        
        # Filtra por Presidente (CD_CARGO = 1)
        detalhes_df = detalhes_df[detalhes_df['CD_CARGO'] == 1].copy()
        
        # Agrega comparecimento (Pode haver múltiplas linhas para o mesmo cargo por seção - ex: trânsito)
        detalhes_df = detalhes_df.groupby(['CD_MUNICIPIO', 'NR_ZONA', 'NR_SECAO', 'SG_UF']).agg({
            'QT_COMPARECIMENTO': 'sum',
            'QT_APTOS': 'max'
        }).reset_index()
        
        detalhes_df['municipio_codigo'] = detalhes_df['CD_MUNICIPIO'].astype(str).str.zfill(5)
        detalhes_df['zona'] = detalhes_df['NR_ZONA'].astype(str).str.zfill(4)
        detalhes_df['secao'] = detalhes_df['NR_SECAO'].astype(str).str.zfill(4)
        
        # 3. Cruzamento (Merge)
        print(f"   🔍 Debug: Logs IDs sample: {logs_df[['municipio_codigo', 'zona', 'secao']].iloc[0].to_dict() if not logs_df.empty else 'empty'}")
        print(f"   🔍 Debug: TSE IDs sample: {detalhes_df[['municipio_codigo', 'zona', 'secao']].iloc[0].to_dict() if not detalhes_df.empty else 'empty'}")
        
        merged = logs_df.merge(
            detalhes_df[['municipio_codigo', 'zona', 'secao', 'QT_APTOS', 'QT_COMPARECIMENTO']],
            on=['municipio_codigo', 'zona', 'secao'],
            how='inner'
        )
        
        # 4. Cálculo de Discrepância
        if merged.empty:
            print("❌ Erro: O merge resultou em zero seções. Verifique os identificadores acima.")
            return pd.DataFrame()
        
        merged['discrepancia_votos'] = merged['votos_log'] - merged['QT_COMPARECIMENTO']
        merged['status_auditoria'] = merged['discrepancia_votos'].apply(lambda x: 'OK' if x == 0 else 'DIVERGENTE')
        
        # 5. Sumário (Foca apenas nas auditadas)
        auditadas_df = merged[merged['votos_log'] > 0].copy()
        total_secoes = len(merged)
        total_auditadas = len(auditadas_df)
        divergentes = len(auditadas_df[auditadas_df['status_auditoria'] != 'OK'])
        
        print(f"   🏁 Auditoria concluída: {total_auditadas} seções com votos extraídos (de {total_secoes} totais).")
        if total_auditadas > 0:
            print(f"   📊 Divergências nas auditadas: {divergentes} ({100*divergentes/total_auditadas:.2f}%)")
            if divergentes == 0:
                print("   🛡️ STATUS: CONFORMIDADE TOTAL DETECTADA (100% de match Log x TSE)")
        
        return merged

if __name__ == "__main__":
    import sys
    uf = sys.argv[1] if len(sys.argv) > 1 else 'rr'
    auditor = BUAuditor()
    report = auditor.generate_audit_report(uf)
    if not report.empty:
        report.to_csv(f"auditoria_bu_{uf}.csv", index=False)
        print(f"✅ Relatório salvo em auditoria_bu_{uf}.csv")
