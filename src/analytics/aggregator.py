# aggregator.py
# -*- coding: utf-8 -*-
"""
Módulo de agregação de logs para o sistema Brurna Analytics.

Este módulo transforma logs brutos em padrões agregados, reduzindo
drasticamente o volume de dados armazenados no banco de dados.

Exemplo:
    79.720 linhas brutas → ~500 padrões únicos (redução de 99%)

Changelog:
    v3.0 - Regras específicas para logs eleitorais TSE
         - Preserva números de mesário para vínculo
         - Mantém N3api bruto (códigos de erro)
         - Remove hash final das linhas
         - Normaliza identificadores de mídia/MR/serial
"""

import pandas as pd
import re
from typing import Dict, List, Tuple, Any
from datetime import datetime


# =============================================================================
# CONSTANTES - Padrões que devem ser mantidos BRUTOS
# =============================================================================

# Prefixos que indicam que a linha NÃO deve ser normalizada
KEEP_RAW_PREFIXES = (
    'N3api',  # Códigos de erro importantes para mineração
)


def remove_trailing_hash(msg: str) -> str:
    """
    Remove hash hexadecimal no final da linha de log.
    
    O TSE adiciona um hash de 16 caracteres hex no final de cada linha
    que não pode ser validado (chave privada do TSE).
    
    Args:
        msg: Mensagem do log
        
    Returns:
        Mensagem sem o hash final
    """
    if not msg or not isinstance(msg, str):
        return msg
    
    # Remove hash de 16 caracteres hex no final (pode ter tab ou espaços antes)
    msg = re.sub(r'[\t\s]+[0-9A-Fa-f]{16}\s*$', '', msg)
    
    return msg.strip()


def normalize_message(msg: str) -> str:
    """
    Normaliza mensagens de log para identificar padrões.
    """
    if not msg or not isinstance(msg, str):
        return msg
    
    # ETAPA 0: Remove hash final
    msg = remove_trailing_hash(msg)
    
    # ETAPA 1: Verifica se deve manter BRUTO
    if msg.startswith(KEEP_RAW_PREFIXES):
        return re.sub(r'\s+', ' ', msg).strip()
    
    # ETAPA 2: PADRÕES ESPECÍFICOS DO CONTEXTO ELEITORAL
    # Identificadores de mídia e MR
    msg = re.sub(r'(Identificador da mídia de carga:\s*)[0-9A-Fa-f]+', r'\1{}', msg)
    msg = re.sub(r'(Número de série da MR:\s*)[0-9A-Fa-f]+', r'\1{}', msg)
    msg = re.sub(r'(Serial da MI copiada da MV da urna original:\s*)[0-9A-Fa-f]+', r'\1{}', msg)
    
    # Computadores e estações (RACWSED01, etc)
    msg = re.sub(r'(gerada pelo computador:\s*)[A-Z0-9]+', r'\1{}', msg)
    msg = re.sub(r'(MR gerada pelo computador:\s*)[A-Z0-9]+', r'\1{}', msg)
    msg = re.sub(r'\bem\s+[A-Z][A-Z0-9]+\b', 'em {}', msg)
    
    # Serial de votação
    msg = re.sub(r'(Serial de votação da MV:\s*)[0-9A-Fa-f]+', r'\1{}', msg)
    
    # Biometria do mesário com arquivo
    msg = re.sub(r'(arquivos coletados\s*)\((\d+)\)', r'\1({})', msg)
    
    # Aplicativos na MR
    msg = re.sub(r'\[([A-Z]{2,10})\]', '[{}]', msg)
    
    # ETAPA 3: PADRÕES GENÉRICOS
    # Hashes
    msg = re.sub(r'\b[0-9a-fA-F]{64}\b', '{}', msg)
    msg = re.sub(r'\b[0-9a-fA-F]{40}\b', '{}', msg)
    msg = re.sub(r'\b[0-9a-fA-F]{32}\b', '{}', msg)
    msg = re.sub(r'(?<![:\s])\b[0-9A-Fa-f]{8}\b(?!\s*$)', '{}', msg)
    msg = re.sub(r'0x[0-9a-fA-F]+', '{}', msg)
    
    # UUIDs, IPs, MACs
    msg = re.sub(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}', '{}', msg)
    msg = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '{}', msg)
    msg = re.sub(r'([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}', '{}', msg)
    
    # Caminhos e Datas
    msg = re.sub(r'/[\w/\-\.]+', '{}', msg)
    msg = re.sub(r'[A-Z]:\\[\w\\\-\.]+', '{}', msg)
    msg = re.sub(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}', '{}', msg)
    msg = re.sub(r'\b\d{2}/\d{2}/\d{4}\b', '{}', msg)
    msg = re.sub(r'\b\d{2}:\d{2}(:\d{2})?\b', '{}', msg)
    
    # Números com unidades
    msg = re.sub(r'\b\d+(\.\d+)?\s*(MB|GB|KB|TB|ms|s|Hz|%)\b', '{}', msg, flags=re.IGNORECASE)
    
    # Números genéricos (preservando mesário de 12 dígitos)
    msg = re.sub(r'\b\d+\.\d+\b', '{}', msg)
    msg = re.sub(r'(?<!mesário\s)(?<!Município:\s)(?<!Eleitoral:\s)\b\d{1,6}\b(?!\d)', 
                 lambda m: '{}' if not re.search(r'(mesário|Município|Zona|Seção)', msg[:m.start()]) else m.group(), 
                 msg)
    
    # ETAPA 4: LIMPEZA FINAL
    msg = re.sub(r'\s+', ' ', msg).strip()
    msg = re.sub(r'(\{\}\s*){2,}', '{} ', msg)
    msg = re.sub(r'\s+([,.\)\]:])', r'\1', msg)
    msg = re.sub(r'\s+$', '', msg)
    
    return msg


def extract_section_key(df: pd.DataFrame) -> Dict:
    """Extrai chave primária composta (Município-Zona-Seção)"""
    result = {'municipio': None, 'zona': None, 'secao': None, 'pk': None}
    if df.empty or 'mensagem' not in df.columns: return result
    for _, row in df.iterrows():
        msg = str(row.get('mensagem', ''))
        m_mu = re.search(r'Município:\s*(\d+)', msg)
        if m_mu: result['municipio'] = m_mu.group(1)
        m_zo = re.search(r'Zona Eleitoral:\s*(\d+)', msg)
        if m_zo: result['zona'] = m_zo.group(1)
        m_se = re.search(r'Seção Eleitoral:\s*(\d+)', msg)
        if m_se: result['secao'] = m_se.group(1)
        if all([result['municipio'], result['zona'], result['secao']]): break
    if all([result['municipio'], result['zona'], result['secao']]):
        result['pk'] = f"{result['municipio']}-{result['zona']}-{result['secao']}"
    return result


def extract_mesarios(df: pd.DataFrame) -> List[Dict]:
    """Extrai informações dos mesários"""
    mesarios = {}
    if df.empty or 'mensagem' not in df.columns: return []
    for _, row in df.iterrows():
        msg = str(row.get('mensagem', ''))
        timestamp = row.get('timestamp')
        patterns = [
            (r'mesário\s+(\d{12})\s+registrado', 'registrado'),
            (r'mesário\s+(\d{12})\s+não é eleitor da seção', 'nao_eleitor_secao'),
            (r'mesário\s+(\d{12})\s+é eleitor da seção', 'eleitor_secao'),
            (r'biometria do mesário\s+(\d{12})', 'biometria_lida'),
            (r'Biometria do mesário\s+(\d{12})\s+encontrada.*\((\d+)\)', 'biometria_arquivo'),
            (r'identificação\s+do\s+mesário:?\s+(\d{12})', 'identificado'),
            (r'membro\s+de\s+mesa\s+:?\s+(\d{12})', 'identificado'),
            (r'título\s+do\s+mesário\s+:?\s+(\d{12})', 'identificado'),
        ]
        for pattern, tipo in patterns:
            match = re.search(pattern, msg, re.IGNORECASE)
            if match:
                numero = match.group(1)
                if numero not in mesarios:
                    mesarios[numero] = {'numero': numero, 'eventos': [], 'eleitor_secao': None, 'arquivo_biometria': None}
                ts_val = timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp)
                mesarios[numero]['eventos'].append({'tipo': tipo, 'timestamp': ts_val})
                if tipo == 'biometria_arquivo' and len(match.groups()) > 1: mesarios[numero]['arquivo_biometria'] = match.group(2)
                if tipo == 'eleitor_secao': mesarios[numero]['eleitor_secao'] = True
                elif tipo == 'nao_eleitor_secao': mesarios[numero]['eleitor_secao'] = False
    return list(mesarios.values())


def analyze_biometria_distribution(df: pd.DataFrame) -> Dict:
    """Analisa a distribuição temporal de 'O eleitor não possui biometria'"""
    if df.empty or 'mensagem' not in df.columns or 'timestamp' not in df.columns: return {}
    mask = df['mensagem'].str.contains('eleitor não possui biometria', case=False, na=False)
    eventos = df[mask].copy()
    if eventos.empty: return {'total': 0}
    eventos['timestamp'] = pd.to_datetime(eventos['timestamp'])
    inicio = df['timestamp'].min()
    fim = df['timestamp'].max()
    if pd.isna(inicio) or pd.isna(fim): return {'total': len(eventos)}
    duracao = (fim - inicio).total_seconds()
    if duracao <= 0: return {'total': len(eventos)}
    terco = duracao / 3
    i_c = len(eventos[eventos['timestamp'] < inicio + pd.Timedelta(seconds=terco)])
    m_c = len(eventos[(eventos['timestamp'] >= inicio + pd.Timedelta(seconds=terco)) & (eventos['timestamp'] < inicio + pd.Timedelta(seconds=2*terco))])
    f_c = len(eventos[eventos['timestamp'] >= inicio + pd.Timedelta(seconds=2*terco)])
    eventos['hora'] = eventos['timestamp'].dt.hour
    p_h = eventos['hora'].value_counts().sort_index().to_dict()
    return {
        'total': len(eventos), 'inicio_votacao': i_c, 'meio_votacao': m_c, 'fim_votacao': f_c,
        'distribuicao_hora': {str(k): int(v) for k, v in p_h.items()},
        'predominante': 'inicio' if i_c > f_c else ('fim' if f_c > i_c else 'uniforme')
    }


def aggregate_patterns(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega mensagens de log por padrão"""
    if 'mensagem' not in df.columns:
        if df.empty: return pd.DataFrame()
        raise KeyError(f"Coluna 'mensagem' não encontrada. Colunas disponíveis: {df.columns.tolist()}")
    df['mensagem_padrao'] = df['mensagem'].apply(normalize_message)
    aggregated = df.groupby(['mensagem_padrao', 'severidade', 'aplicativo']).agg({
        'mensagem': 'first', 'timestamp': ['min', 'max', 'count']
    }).reset_index()
    aggregated.columns = ['mensagem_padrao', 'severidade', 'aplicativo', 'mensagem_exemplo', 'primeira_ocorrencia', 'ultima_ocorrencia', 'ocorrencias']
    return aggregated.sort_values('ocorrencias', ascending=False)


def aggregate_temporal(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega eventos por intervalos temporais"""
    if df.empty or 'timestamp' not in df.columns: return pd.DataFrame()
    df_v = df[df['timestamp'].notna()].copy()
    if df_v.empty: return pd.DataFrame()
    df_v['data'] = pd.to_datetime(df_v['timestamp']).dt.date
    df_v['hora'] = pd.to_datetime(df_v['timestamp']).dt.hour
    return df_v.groupby(['data', 'hora', 'aplicativo', 'severidade']).size().reset_index(name='quantidade')


def extract_section_metadata(df: pd.DataFrame, uf: str, turno: int, municipio_codigo: str = None, zona: str = None, secao: str = None, hash_arquivo: str = None, secao_info: Dict = None) -> Dict:
    """Extrai metadados resumidos de uma seção"""
    if df.empty: return {}
    df_v = df[df['severidade'] != 'INVALID'].copy()
    if df_v.empty: return {}
    if not all([municipio_codigo, zona, secao]):
        sk = extract_section_key(df_v)
        municipio_codigo = municipio_codigo or sk.get('municipio')
        zona = zona or sk.get('zona')
        secao = secao or sk.get('secao')
    p_i, p_f = df_v['timestamp'].min(), df_v['timestamp'].max()
    dur = int((p_f - p_i).total_seconds()) if pd.notna(p_i) and pd.notna(p_f) else 0
    v_c = len(df_v[df_v['mensagem'].str.contains('voto do eleitor foi computado', case=False, na=False)])
    e_h = len(df_v[df_v['mensagem'].str.contains('Eleitor foi habilitado', case=False, na=False)])
    e_s_b = len(df_v[df_v['mensagem'].str.contains('eleitor não possui biometria', case=False, na=False)])
    pk = f"{municipio_codigo}-{zona}-{secao}" if all([municipio_codigo, zona, secao]) else None
    return {
        'uf': uf.upper(), 'turno': turno, 'municipio_codigo': municipio_codigo, 'zona': zona, 'secao': secao, 'pk': pk,
        'total_eventos': len(df_v), 'periodo_inicio': p_i, 'periodo_fim': p_f, 'duracao_segundos': dur,
        'modelo_urna': secao_info.get('modelo_urna') if secao_info else None,
        'votos_computados': v_c, 'eleitores_habilitados': e_h, 'eleitores_sem_biometria': e_s_b,
        'aplicativos_usados': df_v['aplicativo'].dropna().unique().tolist(),
        'severidades': df_v['severidade'].value_counts().to_dict(),
        'hash_arquivo': hash_arquivo, 'mesarios': extract_mesarios(df_v),
        'biometria_analysis': analyze_biometria_distribution(df_v)
    }


def aggregate_logs(df: pd.DataFrame, uf: str, turno: int, secao_info: Dict = None) -> Tuple[pd.DataFrame, pd.DataFrame, Dict]:
    """Agrega logs em todas as dimensões"""
    secao_info = secao_info or {}
    patterns = aggregate_patterns(df)
    temporal = aggregate_temporal(df)
    metadata = extract_section_metadata(df, uf=uf, turno=turno, municipio_codigo=secao_info.get('municipio_codigo'), zona=secao_info.get('zona'), secao=secao_info.get('secao'), hash_arquivo=secao_info.get('hash_arquivo'), secao_info=secao_info)
    if 'modelo_urna' in secao_info and not metadata.get('modelo_urna'): metadata['modelo_urna'] = secao_info['modelo_urna']
    return patterns, temporal, metadata


def get_top_errors(patterns_df: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    errors = patterns_df[patterns_df['severidade'].isin(['ERRO', 'CRITICO', 'FATAL', 'ERROR'])].copy()
    return errors.nlargest(top_n, 'ocorrencias')


def get_n3api_errors(patterns_df: pd.DataFrame) -> pd.DataFrame:
    return patterns_df[patterns_df['mensagem_padrao'].str.startswith('N3api', na=False)].copy()


def get_temporal_summary(temporal_df: pd.DataFrame) -> Dict:
    if temporal_df.empty: return {}
    return {
        'total_eventos': temporal_df['quantidade'].sum(),
        'hora_pico': temporal_df.groupby('hora')['quantidade'].sum().idxmax(),
        'eventos_hora_pico': temporal_df.groupby('hora')['quantidade'].sum().max(),
        'periodo_inicio': temporal_df['data'].min(), 'periodo_fim': temporal_df['data'].max(), 'dias_cobertos': temporal_df['data'].nunique()
    }