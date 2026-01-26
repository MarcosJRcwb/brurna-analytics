#!/usr/bin/env python3
"""
Análise forense dos dados eleitorais de AC.
Identifica padrões, anomalias e comportamentos suspeitos.
"""

from sqlalchemy import create_engine, text
from config import config
import pandas as pd
import json

def analyze_patterns():
    """Analisa padrões de mensagens para identificar anomalias"""
    engine = create_engine(config.POSTGRES_CONN)
    conn = engine.connect()
    
    print("=" * 80)
    print("ANÁLISE FORENSE - PADRÕES DE LOG (AC)")
    print("=" * 80)
    
    # Top 20 padrões mais frequentes
    result = conn.execute(text("""
        SELECT 
            mensagem_padrao,
            mensagem_exemplo,
            aplicativo,
            severidade,
            SUM(ocorrencias) as total_ocorrencias,
            COUNT(DISTINCT CONCAT(municipio_codigo, zona, secao)) as secoes_afetadas
        FROM log_patterns lp
        LEFT JOIN section_metadata sm ON lp.uf = sm.uf AND lp.turno = sm.turno
        WHERE lp.uf = 'AC'
        GROUP BY mensagem_padrao, mensagem_exemplo, aplicativo, severidade
        ORDER BY total_ocorrencias DESC
        LIMIT 20
    """))
    
    print("\n📊 TOP 20 PADRÕES MAIS FREQUENTES:\n")
    for i, row in enumerate(result, 1):
        print(f"{i}. [{row[3]}] {row[2]}")
        print(f"   Padrão: {row[0]}")
        print(f"   Exemplo: {row[1]}")
        print(f"   Ocorrências: {row[4]:,} | Seções: {row[5] or 'N/A'}")
        print()
    
    # Erros críticos
    result = conn.execute(text("""
        SELECT 
            mensagem_padrao,
            mensagem_exemplo,
            aplicativo,
            SUM(ocorrencias) as total
        FROM log_patterns
        WHERE uf = 'AC' 
        AND severidade IN ('ERRO', 'CRITICO', 'FATAL')
        GROUP BY mensagem_padrao, mensagem_exemplo, aplicativo
        ORDER BY total DESC
        LIMIT 10
    """))
    
    print("\n🔴 TOP 10 ERROS CRÍTICOS:\n")
    for i, row in enumerate(result, 1):
        print(f"{i}. {row[2]}: {row[0]}")
        print(f"   Exemplo: {row[1]}")
        print(f"   Ocorrências: {row[3]:,}")
        print()
    
    conn.close()


def analyze_temporal():
    """Analisa distribuição temporal dos eventos"""
    engine = create_engine(config.POSTGRES_CONN)
    conn = engine.connect()
    
    print("=" * 80)
    print("ANÁLISE TEMPORAL - RITMO DE VOTAÇÃO")
    print("=" * 80)
    
    # Eventos por hora
    result = conn.execute(text("""
        SELECT 
            hora,
            SUM(quantidade) as total_eventos,
            COUNT(DISTINCT data) as dias
        FROM temporal_metrics
        WHERE uf = 'AC'
        GROUP BY hora
        ORDER BY hora
    """))
    
    print("\n⏰ DISTRIBUIÇÃO POR HORA DO DIA:\n")
    horas_data = []
    for row in result:
        horas_data.append((row[0], row[1], row[2]))
        bar = "█" * int(row[1] / 1000)
        print(f"{row[0]:02d}:00 | {bar} {row[1]:6,} eventos ({row[2]} dias)")
    
    # Identifica picos anormais
    if horas_data:
        eventos_por_hora = [h[1] for h in horas_data]
        media = sum(eventos_por_hora) / len(eventos_por_hora)
        import statistics
        desvio = statistics.stdev(eventos_por_hora) if len(eventos_por_hora) > 1 else 0
        
        print(f"\n📈 ESTATÍSTICAS:")
        print(f"   Média: {media:,.0f} eventos/hora")
        print(f"   Desvio padrão: {desvio:,.0f}")
        
        print(f"\n⚠️  PICOS ANORMAIS (>2σ acima da média):")
        for hora, eventos, dias in horas_data:
            if eventos > media + 2 * desvio:
                print(f"   {hora:02d}:00 - {eventos:,} eventos ({(eventos/media - 1)*100:.1f}% acima da média)")
    
    # Eventos por dia
    result = conn.execute(text("""
        SELECT 
            data,
            SUM(quantidade) as total_eventos
        FROM temporal_metrics
        WHERE uf = 'AC'
        GROUP BY data
        ORDER BY data
    """))
    
    print(f"\n📅 DISTRIBUIÇÃO POR DIA:\n")
    for row in result:
        print(f"{row[0]} | {row[1]:,} eventos")
    
    conn.close()


def analyze_sections():
    """Analisa metadados das seções"""
    engine = create_engine(config.POSTGRES_CONN)
    conn = engine.connect()
    
    print("=" * 80)
    print("ANÁLISE DE SEÇÕES ELEITORAIS")
    print("=" * 80)
    
    # Estatísticas gerais
    result = conn.execute(text("""
        SELECT 
            COUNT(*) as total_secoes,
            AVG(total_eventos) as media_eventos,
            MIN(total_eventos) as min_eventos,
            MAX(total_eventos) as max_eventos,
            AVG(duracao_segundos) as duracao_media
        FROM section_metadata
        WHERE uf = 'AC'
    """))
    
    row = result.fetchone()
    print(f"\n📊 ESTATÍSTICAS GERAIS:")
    print(f"   Total de seções: {row[0]}")
    print(f"   Média de eventos/seção: {row[1]:,.0f}")
    print(f"   Mín/Máx eventos: {row[2]:,} / {row[3]:,}")
    print(f"   Duração média: {row[4]/3600:.1f} horas" if row[4] else "   Duração média: N/A")
    
    # Seções com comportamento anômalo
    result = conn.execute(text("""
        SELECT 
            municipio_codigo,
            zona,
            secao,
            total_eventos,
            duracao_segundos,
            severidades
        FROM section_metadata
        WHERE uf = 'AC'
        ORDER BY total_eventos DESC
        LIMIT 10
    """))
    
    print(f"\n🔍 TOP 10 SEÇÕES COM MAIS EVENTOS:\n")
    for i, row in enumerate(result, 1):
        severidades = json.loads(row[5]) if row[5] else {}
        print(f"{i}. Seção {row[0]}-{row[1]}-{row[2]}")
        print(f"   Eventos: {row[3]:,} | Duração: {row[4]/3600:.1f}h" if row[4] else f"   Eventos: {row[3]:,}")
        print(f"   Severidades: {severidades}")
        print()
    
    # Aplicativos mais usados
    result = conn.execute(text("""
        SELECT 
            UNNEST(aplicativos_usados) as app,
            COUNT(*) as secoes
        FROM section_metadata
        WHERE uf = 'AC'
        GROUP BY app
        ORDER BY secoes DESC
    """))
    
    print(f"\n📱 APLICATIVOS MAIS USADOS:\n")
    for row in result:
        print(f"   {row[0]}: {row[1]} seções")
    
    conn.close()


def analyze_voting_sequence():
    """Analisa se há padrões relacionados à sequência de votação"""
    engine = create_engine(config.POSTGRES_CONN)
    conn = engine.connect()
    
    print("=" * 80)
    print("ANÁLISE DA SEQUÊNCIA DE VOTAÇÃO")
    print("=" * 80)
    print("\nSequência esperada:")
    print("1. Deputado Estadual (5 dígitos)")
    print("2. Deputado Federal (5 dígitos)")
    print("3. Senador (3 dígitos)")
    print("4. Governador (2 dígitos)")
    print("5. Presidente (2 dígitos)")
    
    # Busca padrões relacionados a votação
    result = conn.execute(text("""
        SELECT 
            mensagem_padrao,
            mensagem_exemplo,
            aplicativo,
            SUM(ocorrencias) as total
        FROM log_patterns
        WHERE uf = 'AC'
        AND (
            mensagem_padrao LIKE '%voto%'
            OR mensagem_padrao LIKE '%votação%'
            OR mensagem_padrao LIKE '%candidato%'
            OR mensagem_padrao LIKE '%digito%'
            OR mensagem_padrao LIKE '%dígito%'
            OR mensagem_padrao LIKE '%cargo%'
        )
        GROUP BY mensagem_padrao, mensagem_exemplo, aplicativo
        ORDER BY total DESC
        LIMIT 20
    """))
    
    print(f"\n🗳️  PADRÕES RELACIONADOS À VOTAÇÃO:\n")
    found = False
    for row in result:
        found = True
        print(f"   {row[2]}: {row[0]}")
        print(f"   Exemplo: {row[1]}")
        print(f"   Ocorrências: {row[3]:,}")
        print()
    
    if not found:
        print("   ⚠️  Nenhum padrão explícito de votação encontrado nos logs.")
        print("   (Logs podem não registrar ações de votação por segurança)")
    
    conn.close()


if __name__ == "__main__":
    analyze_patterns()
    print("\n" + "=" * 80 + "\n")
    analyze_temporal()
    print("\n" + "=" * 80 + "\n")
    analyze_sections()
    print("\n" + "=" * 80 + "\n")
    analyze_voting_sequence()
