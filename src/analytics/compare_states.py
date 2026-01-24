
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine
from config import config
import os

# Configurações visuais
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("viridis")

def generate_comparison_report():
    engine = create_engine(config.POSTGRES_CONN)
    output_dir = config.PROJECT_ROOT / "docs" / "img"
    output_dir.mkdir(exist_ok=True)

    print("📊 Gerando Relatório Comparativo (RR vs AP)...")

    # 1. Comparação de Volume de Eventos
    query_vol = """
        SELECT uf, SUM(total_eventos) as total
        FROM section_metadata
        WHERE uf IN ('RR', 'AP')
        GROUP BY uf
    """
    df_vol = pd.read_sql(query_vol, engine)
    
    plt.figure(figsize=(8, 6))
    sns.barplot(data=df_vol, x='uf', y='total')
    plt.title("Total de Eventos Processados por Estado")
    plt.ylabel("Eventos (Milhões)")
    plt.savefig(output_dir / "comparison_volume.png")
    print("✅ Gráfico de volume gerado.")

    # 2. Distribuição Temporal (Densidade)
    query_temp = """
        SELECT uf, hora, SUM(quantidade) as qtd
        FROM temporal_metrics
        WHERE uf IN ('RR', 'AP')
        GROUP BY uf, hora
        ORDER BY hora
    """
    df_temp = pd.read_sql(query_temp, engine)
    
    plt.figure(figsize=(12, 6))
    sns.lineplot(data=df_temp, x='hora', y='qtd', hue='uf', marker="o")
    plt.title("Densidade Temporal de Eventos (Fluxo de Votação)")
    plt.xlabel("Hora do Dia")
    plt.ylabel("Eventos por Hora")
    plt.grid(True, which='minor', linestyle='--', alpha=0.7)
    plt.savefig(output_dir / "comparison_temporal.png")
    print("✅ Gráfico temporal gerado.")

    # 3. Modelos de Urna (Estimado via Patterns)
    # Nota: Como não temos modelo na metadata, usamos uma query aproximada nos patterns se possível,
    # mas para este gráfico vamos focar na duração média da sessão que é um bom proxy de performance.
    query_dur = """
        SELECT uf, duracao_segundos / 3600.0 as duracao_horas
        FROM section_metadata
        WHERE uf IN ('RR', 'AP')
        AND duracao_segundos > 0 AND duracao_segundos < 50000
    """
    df_dur = pd.read_sql(query_dur, engine)
    
    plt.figure(figsize=(10, 6))
    sns.boxplot(data=df_dur, x='uf', y='duracao_horas')
    plt.title("Distribuição da Duração das Seções (Horas)")
    plt.ylabel("Horas de Operação")
    plt.savefig(output_dir / "comparison_duration.png")
    print("✅ Gráfico de duração gerado.")

if __name__ == "__main__":
    generate_comparison_report()
