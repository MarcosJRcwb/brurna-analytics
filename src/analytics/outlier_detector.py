"""
Módulo de detecção de outliers para análise forense eleitoral.
Identifica seções com comportamento anômalo usando métodos estatísticos.
"""

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from config import config
from typing import List, Dict
import json


class OutlierDetector:
    """Detecta outliers em dados eleitorais"""
    
    def __init__(self, uf: str = None):
        self.uf = uf
        self.engine = create_engine(config.POSTGRES_CONN)
    
    def get_section_metrics(self) -> pd.DataFrame:
        """
        Obtém métricas de todas as seções para análise.
        
        Returns:
            DataFrame com métricas por seção
        """
        query = """
            SELECT 
                uf,
                municipio_codigo,
                zona,
                secao,
                total_eventos,
                duracao_segundos,
                severidades,
                aplicativos_usados
            FROM section_metadata
        """
        
        if self.uf:
            query += f" WHERE uf = '{self.uf.upper()}'"
        
        df = pd.read_sql(query, self.engine)
        
        # Parse JSON severidades
        if 'severidades' in df.columns:
            df['erros'] = df['severidades'].apply(
                lambda x: x.get('ERRO', 0) + x.get('CRITICO', 0) if isinstance(x, dict) else 0
            )
            df['alertas'] = df['severidades'].apply(
                lambda x: x.get('ALERTA', 0) if isinstance(x, dict) else 0
            )
        
        return df
    
    def detect_zscore_outliers(self, df: pd.DataFrame, column: str, threshold: float = 3.0) -> pd.DataFrame:
        """
        Detecta outliers usando Z-score.
        
        Args:
            df: DataFrame com dados
            column: Coluna para análise
            threshold: Número de desvios padrão (padrão: 3)
            
        Returns:
            DataFrame apenas com outliers
        """
        if column not in df.columns or df[column].isna().all():
            return pd.DataFrame()
        
        mean = df[column].mean()
        std = df[column].std()
        
        if std == 0:
            return pd.DataFrame()
        
        df['z_score'] = (df[column] - mean) / std
        outliers = df[abs(df['z_score']) > threshold].copy()
        
        return outliers
    
    def detect_iqr_outliers(self, df: pd.DataFrame, column: str) -> pd.DataFrame:
        """
        Detecta outliers usando IQR (Interquartile Range).
        
        Args:
            df: DataFrame com dados
            column: Coluna para análise
            
        Returns:
            DataFrame apenas com outliers
        """
        if column not in df.columns or df[column].isna().all():
            return pd.DataFrame()
        
        Q1 = df[column].quantile(0.25)
        Q3 = df[column].quantile(0.75)
        IQR = Q3 - Q1
        
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        outliers = df[(df[column] < lower_bound) | (df[column] > upper_bound)].copy()
        outliers['iqr_distance'] = outliers[column].apply(
            lambda x: max(abs(x - lower_bound), abs(x - upper_bound))
        )
        
        return outliers
    
    def detect_all_outliers(self) -> Dict[str, pd.DataFrame]:
        """
        Detecta outliers em múltiplas métricas.
        
        Returns:
            Dicionário com outliers por métrica
        """
        df = self.get_section_metrics()
        
        if df.empty:
            return {}
        
        outliers = {}
        
        # Outliers por total de eventos
        outliers['eventos_zscore'] = self.detect_zscore_outliers(df, 'total_eventos')
        outliers['eventos_iqr'] = self.detect_iqr_outliers(df, 'total_eventos')
        
        # Outliers por duração
        outliers['duracao_zscore'] = self.detect_zscore_outliers(df, 'duracao_segundos')
        outliers['duracao_iqr'] = self.detect_iqr_outliers(df, 'duracao_segundos')
        
        # Outliers por erros
        if 'erros' in df.columns:
            outliers['erros_zscore'] = self.detect_zscore_outliers(df, 'erros')
            outliers['erros_iqr'] = self.detect_iqr_outliers(df, 'erros')
        
        return outliers
    
    def generate_outlier_report(self) -> str:
        """
        Gera relatório textual de outliers detectados.
        
        Returns:
            String com relatório formatado
        """
        outliers = self.detect_all_outliers()
        
        report = []
        report.append("=" * 80)
        report.append(f"RELATÓRIO DE OUTLIERS - {self.uf.upper() if self.uf else 'TODOS OS ESTADOS'}")
        report.append("=" * 80)
        
        for metric, df_outliers in outliers.items():
            if df_outliers.empty:
                continue
            
            report.append(f"\n🔍 {metric.upper().replace('_', ' ')}")
            report.append("-" * 80)
            report.append(f"Total de outliers: {len(df_outliers)}")
            
            # Top 5 outliers mais extremos
            if 'z_score' in df_outliers.columns:
                top_outliers = df_outliers.nlargest(5, 'z_score', keep='all')
            elif 'iqr_distance' in df_outliers.columns:
                top_outliers = df_outliers.nlargest(5, 'iqr_distance', keep='all')
            else:
                top_outliers = df_outliers.head(5)
            
            report.append("\nTop 5 casos mais extremos:")
            for i, row in enumerate(top_outliers.itertuples(), 1):
                report.append(f"\n{i}. Seção {row.uf}-{row.municipio_codigo}-{row.zona}-{row.secao}")
                
                if hasattr(row, 'total_eventos'):
                    report.append(f"   Total de eventos: {row.total_eventos:,}")
                
                if hasattr(row, 'duracao_segundos') and row.duracao_segundos:
                    report.append(f"   Duração: {row.duracao_segundos/3600:.1f} horas")
                
                if hasattr(row, 'erros'):
                    report.append(f"   Erros: {row.erros}")
                
                if hasattr(row, 'z_score'):
                    report.append(f"   Z-score: {row.z_score:.2f}")
                elif hasattr(row, 'iqr_distance'):
                    report.append(f"   Distância IQR: {row.iqr_distance:.2f}")
        
        report.append("\n" + "=" * 80)
        
        return "\n".join(report)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Detecção de outliers em dados eleitorais")
    parser.add_argument("--uf", help="UF para análise (opcional)")
    parser.add_argument("--output", default="outliers_report.txt", help="Arquivo de saída")
    
    args = parser.parse_args()
    
    detector = OutlierDetector(uf=args.uf)
    report = detector.generate_outlier_report()
    
    print(report)
    
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n✅ Relatório salvo em: {args.output}")
