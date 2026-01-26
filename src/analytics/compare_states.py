import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine
from config import config
import os
import matplotlib.ticker as ticker

# Configurações visuais globais
plt.style.use('seaborn-v0_8-muted')
# Paleta de cores manual para garantir consistência por estado
STATE_COLORS = {
    'RR': '#3498db', # Azul
    'AP': '#2ecc71', # Verde
    'AC': '#e74c3c', # Vermelho
    'TO': '#f1c40f', # Amarelo
    'SE': '#9b59b6'  # Roxo
}

def format_millions(x, pos):
    """Formata números grandes para legibilidade (ex: 2.5M)"""
    if x >= 1e6:
        return f'{x*1e-6:.1f}M'
    return f'{x:,.0f}'

def generate_comparison_report():
    engine = create_engine(config.POSTGRES_CONN)
    output_dir = config.PROJECT_ROOT / "docs" / "img"
    output_dir.mkdir(exist_ok=True)

    print("📊 Gerando Relatório Comparativo Triple-State...")

    # 1. Comparação de Volume de Eventos (Barras Coloridas)
    query_vol = """
        SELECT uf, SUM(total_eventos) as total
        FROM section_metadata
        WHERE uf IN ('RR', 'AP', 'AC', 'TO', 'SE')
        GROUP BY uf
        ORDER BY total DESC
    """
    df_vol = pd.read_sql(query_vol, engine)
    
    plt.figure(figsize=(10, 6))
    ax = sns.barplot(data=df_vol, x='uf', y='total', palette=STATE_COLORS)
    plt.title("Volume de Logs Processados por Estado (Total de Eventos)", fontsize=14, pad=20)
    plt.ylabel("Total de Eventos", fontsize=12)
    plt.xlabel("Estado (UF)", fontsize=12)
    
    # Formatação legível
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(format_millions))
    
    # Adiciona valores no topo das barras
    for p in ax.patches:
        ax.annotate(format_millions(p.get_height(), None), 
                   (p.get_x() + p.get_width() / 2., p.get_height()), 
                   ha = 'center', va = 'center', 
                   xytext = (0, 10), 
                   textcoords = 'offset points',
                   fontsize=10, 
                   fontweight='bold')

    plt.tight_layout()
    plt.savefig(output_dir / "comparison_volume.png", dpi=150)
    print("✅ Gráfico de volume gerado.")

    # 2. Distribuição Temporal (Densidade com cores fixas)
    query_temp = """
        SELECT uf, hora, SUM(quantidade) as qtd
        FROM temporal_metrics
        WHERE uf IN ('RR', 'AP', 'AC', 'TO', 'SE')
        GROUP BY uf, hora
        ORDER BY hora
    """
    df_temp = pd.read_sql(query_temp, engine)
    
    plt.figure(figsize=(12, 6))
    sns.lineplot(data=df_temp, x='hora', y='qtd', hue='uf', palette=STATE_COLORS, marker="o", linewidth=2.5)
    plt.title("Fluxo de Votação (Densidade de Eventos/Hora)", fontsize=14, pad=20)
    plt.xlabel("Hora do Dia", fontsize=12)
    plt.ylabel("Eventos por Hora", fontsize=12)
    plt.gca().yaxis.set_major_formatter(ticker.FuncFormatter(format_millions))
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend(title="UF", title_fontsize='12', fontsize='11')
    
    plt.tight_layout()
    plt.savefig(output_dir / "comparison_temporal.png", dpi=150)
    print("✅ Gráfico temporal gerado.")

    # 3. Distribuição da Duração (Boxplot com cores e anotações)
    query_dur = """
        SELECT uf, duracao_segundos / 3600.0 as duracao_horas
        FROM section_metadata
        WHERE uf IN ('RR', 'AP', 'AC')
        AND duracao_segundos > 0 AND duracao_segundos < 5000000
    """
    df_dur = pd.read_sql(query_dur, engine)
    
    plt.figure(figsize=(10, 7))
    ax = sns.boxplot(data=df_dur, x='uf', y='duracao_horas', palette=STATE_COLORS, showfliers=False)
    sns.stripplot(data=df_dur, x='uf', y='duracao_horas', color=".3", alpha=0.1, jitter=True) # Adiciona pontos leves
    
    plt.title("Estabilidade Operacional (Mediana de Horas de Votação)", fontsize=14, pad=20)
    plt.ylabel("Horas de Operação (Total)", fontsize=12)
    plt.xlabel("Estado (UF)", fontsize=12)
    
    # Anotações de Medianas próximas às caixas
    medians = df_dur.groupby(['uf'])['duracao_horas'].median().to_dict()
    for xtick in ax.get_xticks():
        uf = ax.get_xticklabels()[xtick].get_text()
        median_val = medians[uf]
        ax.text(xtick, median_val, f'{median_val:.1f}h', 
                horizontalalignment='center', size='11', color='white', weight='semibold')

    plt.tight_layout()
    plt.savefig(output_dir / "comparison_duration.png", dpi=150)
    print("✅ Gráfico de duração gerado.")

if __name__ == "__main__":
    generate_comparison_report()
