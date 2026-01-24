"""
Módulo de agregação de logs para o sistema Brurna Analytics.

Este módulo transforma logs brutos em padrões agregados, reduzindo
drasticamente o volume de dados armazenados no banco de dados.

Exemplo:
    79.720 linhas brutas → ~500 padrões únicos (redução de 99%)
"""

import pandas as pd
import re
from typing import Dict, List, Tuple
from datetime import datetime


def normalize_message(msg: str) -> str:
    """
    Normaliza mensagens de log para identificar padrões.
    
    Converte mensagens específicas em padrões genéricos substituindo
    valores variáveis por placeholders.
    
    Args:
        msg: Mensagem original do log
        
    Returns:
        Mensagem normalizada com placeholders
        
    Exemplos:
        >>> normalize_message("Erro ao abrir /dev/sda1")
        'Erro ao abrir {}'
        
        >>> normalize_message("Timeout após 30 segundos")
        'Timeout após {} segundos'
        
        >>> normalize_message("Memória: 0x7F3A2B1C")
        'Memória: {}'
    """
    if not msg or not isinstance(msg, str):
        return msg
    
    # Substitui caminhos de arquivo (Unix e Windows)
    msg = re.sub(r'/[\w/\-\.]+', '{}', msg)
    msg = re.sub(r'[A-Z]:\\[\w\\\-\.]+', '{}', msg)
    
    # Substitui números (inteiros e decimais)
    msg = re.sub(r'\b\d+\.?\d*\b', '{}', msg)
    
    # Substitui endereços hexadecimais
    msg = re.sub(r'0x[0-9a-fA-F]+', '{}', msg)
    
    # Substitui IPs
    msg = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '{}', msg)
    
    # Substitui UUIDs
    msg = re.sub(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '{}', msg)
    
    # Remove espaços duplicados
    msg = re.sub(r'\s+', ' ', msg).strip()
    
    return msg


def aggregate_patterns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega mensagens de log por padrão.
    
    Agrupa mensagens similares e conta suas ocorrências, mantendo
    um exemplo de cada padrão para referência.
    
    Args:
        df: DataFrame com colunas: timestamp, severidade, aplicativo, mensagem
        
    Returns:
        DataFrame agregado com colunas:
        - mensagem_padrao: Mensagem normalizada
        - mensagem_exemplo: Exemplo real da mensagem
        - ocorrencias: Número de vezes que o padrão apareceu
        - primeira_ocorrencia: Timestamp da primeira ocorrência
        - ultima_ocorrencia: Timestamp da última ocorrência
        - severidade: Severidade do log
        - aplicativo: Aplicativo que gerou o log
    """
    if df.empty:
        return pd.DataFrame()
    
    # Cria coluna com mensagem normalizada
    df['mensagem_padrao'] = df['mensagem'].apply(normalize_message)
    
    # Agrupa por padrão
    aggregated = df.groupby(['mensagem_padrao', 'severidade', 'aplicativo']).agg({
        'mensagem': 'first',  # Pega primeira mensagem como exemplo
        'timestamp': ['min', 'max', 'count']
    }).reset_index()
    
    # Renomeia colunas
    aggregated.columns = [
        'mensagem_padrao',
        'severidade',
        'aplicativo',
        'mensagem_exemplo',
        'primeira_ocorrencia',
        'ultima_ocorrencia',
        'ocorrencias'
    ]
    
    # Ordena por número de ocorrências (mais frequentes primeiro)
    aggregated = aggregated.sort_values('ocorrencias', ascending=False)
    
    return aggregated


def aggregate_temporal(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega eventos por intervalos temporais (hora do dia).
    
    Args:
        df: DataFrame com colunas: timestamp, severidade, aplicativo
        
    Returns:
        DataFrame com métricas temporais:
        - data: Data do evento
        - hora: Hora do dia (0-23)
        - aplicativo: Aplicativo
        - severidade: Severidade
        - quantidade: Número de eventos nesse intervalo
    """
    if df.empty or 'timestamp' not in df.columns:
        return pd.DataFrame()
    
    # Remove linhas sem timestamp
    df_valid = df[df['timestamp'].notna()].copy()
    
    if df_valid.empty:
        return pd.DataFrame()
    
    # Extrai data e hora
    df_valid['data'] = pd.to_datetime(df_valid['timestamp']).dt.date
    df_valid['hora'] = pd.to_datetime(df_valid['timestamp']).dt.hour
    
    # Agrupa por data, hora, aplicativo e severidade
    temporal = df_valid.groupby(['data', 'hora', 'aplicativo', 'severidade']).size().reset_index(name='quantidade')
    
    return temporal


def extract_section_metadata(
    df: pd.DataFrame,
    uf: str,
    turno: int,
    municipio_codigo: str = None,
    zona: str = None,
    secao: str = None,
    hash_arquivo: str = None
) -> Dict:
    """
    Extrai metadados resumidos de uma seção eleitoral.
    
    Args:
        df: DataFrame com logs da seção
        uf: Unidade Federativa
        turno: Número do turno (1 ou 2)
        municipio_codigo: Código do município
        zona: Código da zona eleitoral
        secao: Código da seção eleitoral
        hash_arquivo: Hash SHA256 do arquivo original
        
    Returns:
        Dicionário com metadados da seção
    """
    if df.empty:
        return {}
    
    # Remove linhas inválidas
    df_valid = df[df['severidade'] != 'INVALID'].copy()
    
    if df_valid.empty:
        return {}
    
    # Calcula duração
    periodo_inicio = df_valid['timestamp'].min()
    periodo_fim = df_valid['timestamp'].max()
    duracao_segundos = int((periodo_fim - periodo_inicio).total_seconds()) if pd.notna(periodo_inicio) and pd.notna(periodo_fim) else 0
    
    # Lista de aplicativos usados
    aplicativos_usados = df_valid['aplicativo'].dropna().unique().tolist()
    
    # Distribuição de severidades
    severidades = df_valid['severidade'].value_counts().to_dict()
    
    metadata = {
        'uf': uf.upper(),
        'turno': turno,
        'municipio_codigo': municipio_codigo,
        'zona': zona,
        'secao': secao,
        'total_eventos': len(df_valid),
        'periodo_inicio': periodo_inicio,
        'periodo_fim': periodo_fim,
        'duracao_segundos': duracao_segundos,
        'aplicativos_usados': aplicativos_usados,
        'severidades': severidades,
        'hash_arquivo': hash_arquivo
    }
    
    return metadata


def aggregate_logs(
    df: pd.DataFrame,
    uf: str,
    turno: int,
    secao_info: Dict = None
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict]:
    """
    Função principal que agrega logs em todas as dimensões.
    
    Args:
        df: DataFrame com logs brutos
        uf: Unidade Federativa
        turno: Número do turno
        secao_info: Dicionário com informações da seção (municipio, zona, secao, hash)
        
    Returns:
        Tupla com:
        - DataFrame de padrões agregados
        - DataFrame de métricas temporais
        - Dicionário com metadados da seção
    """
    secao_info = secao_info or {}
    
    # Agrega padrões
    patterns = aggregate_patterns(df)
    
    # Agrega métricas temporais
    temporal = aggregate_temporal(df)
    
    # Extrai metadados
    metadata = extract_section_metadata(
        df,
        uf=uf,
        turno=turno,
        municipio_codigo=secao_info.get('municipio_codigo'),
        zona=secao_info.get('zona'),
        secao=secao_info.get('secao'),
        hash_arquivo=secao_info.get('hash_arquivo')
    )
    
    return patterns, temporal, metadata


# Funções auxiliares para análise

def get_top_errors(patterns_df: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    """
    Retorna os erros mais frequentes.
    
    Args:
        patterns_df: DataFrame de padrões agregados
        top_n: Número de erros a retornar
        
    Returns:
        DataFrame com top N erros
    """
    errors = patterns_df[
        patterns_df['severidade'].isin(['ERRO', 'CRITICO', 'FATAL', 'ERROR'])
    ].copy()
    
    return errors.nlargest(top_n, 'ocorrencias')


def get_temporal_summary(temporal_df: pd.DataFrame) -> Dict:
    """
    Gera resumo das métricas temporais.
    
    Args:
        temporal_df: DataFrame de métricas temporais
        
    Returns:
        Dicionário com estatísticas temporais
    """
    if temporal_df.empty:
        return {}
    
    summary = {
        'total_eventos': temporal_df['quantidade'].sum(),
        'hora_pico': temporal_df.groupby('hora')['quantidade'].sum().idxmax(),
        'eventos_hora_pico': temporal_df.groupby('hora')['quantidade'].sum().max(),
        'periodo_inicio': temporal_df['data'].min(),
        'periodo_fim': temporal_df['data'].max(),
        'dias_cobertos': temporal_df['data'].nunique()
    }
    
    return summary
