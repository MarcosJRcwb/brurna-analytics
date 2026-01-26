import streamlit as st
import pandas as pd
import plotly.express as px
import os
from sqlalchemy import create_engine, text
import sys

# Add root to path for config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from config import config

st.set_page_config(page_title="Brurna Analytics", page_icon="🗳️", layout="wide")

# --- SQL CONNECTION ---
@st.cache_resource
def get_db():
    return create_engine(config.POSTGRES_CONN)

def get_ingestion_stats():
    """Query live row counts per state based on source_file path/name."""
    try:
        engine = get_db()
        # heuristic: filename usually starts with state or we assume folder structure
        # actually log_eventos has source_file which is full path.
        query = text("""
        SELECT 
            CASE 
                WHEN source_file LIKE '%/ac/%' OR source_file LIKE '%\\ac\\%' THEN 'AC'
                WHEN source_file LIKE '%/ap/%' OR source_file LIKE '%\\ap\\%' THEN 'AP'
                WHEN source_file LIKE '%/rr/%' OR source_file LIKE '%\\rr\\%' THEN 'RR'
                WHEN source_file LIKE '%/to/%' OR source_file LIKE '%\\to\\%' THEN 'TO'
                WHEN source_file LIKE '%/se/%' OR source_file LIKE '%\\se\\%' THEN 'SE'
                ELSE 'Outros'
            END as uf,
            COUNT(*) as total
        FROM log_eventos
        GROUP BY 1
        ORDER BY 2 DESC
        """)
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
        return df
    except:
        return pd.DataFrame()

def get_temporal_data():
    try:
        engine = get_db()
        q = text("SELECT hora, SUM(quantidade) as vol FROM temporal_metrics GROUP BY 1 ORDER BY 1")
        with engine.connect() as conn:
            return pd.read_sql(q, conn)
    except:
        return pd.DataFrame()

st.title("🗳️ Brurna Analytics: Painel de Inteligência Eleitoral")

# --- INGESTION STATUS (LIVE) ---
st.subheader("⚡ Monitoramento de Ingestão (Tempo Real)")
stats_df = get_ingestion_stats()
if not stats_df.empty:
    # Estimativa: 200 arquivos por estado × 5 estados = 1000 arquivos
    # Média de ~400 linhas por arquivo = 400.000 linhas esperadas
    total_logs = stats_df['total'].sum()
    expected_total = 400000
    progress_pct = min(total_logs / expected_total, 1.0)
    
    col_prog1, col_prog2 = st.columns([3, 1])
    with col_prog1:
        st.progress(progress_pct, text=f"Progresso: {total_logs:,} / ~{expected_total:,} logs ({progress_pct*100:.1f}%)")
    with col_prog2:
        st.metric("Taxa", f"{total_logs/37:.0f} logs/min" if total_logs > 0 else "Calculando...")
    
    # Detalhamento por estado
    cols = st.columns(len(stats_df))
    for i, row in stats_df.iterrows():
        with cols[i]:
            delta = f"+{row['total']}" if i == 0 else None
            cols[i].metric(f"🗳️ {row['uf']}", f"{row['total']:,}", delta=delta)
else:
    st.info("Conectando ao Banco de Dados...")

st.markdown("---")

# Load Analysis Data
@st.cache_data
def load_data():
    try:
        path = "analysis_results.csv"
        if not os.path.exists(path):
            path = r"C:\Users\marco\OneDrive\Projetos\brurna-analytics\analysis_results.csv"
        df = pd.read_csv(path)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.warning("Nenhum dado analítico encontrado. O motor ainda está rodando?")
    st.stop()

# Sidebar
st.sidebar.header("Filtros")
if st.sidebar.button("🔄 Atualizar Dados (F5)"):
    st.rerun()

group_filter = st.sidebar.multiselect(
    "Filtrar por Grupo",
    options=["G1 (H001-H125)", "G2 (H126-H250)", "G3 (H251-H375)", "G4 (H376-H500)"],
    default=["G1 (H001-H125)", "G2 (H126-H250)", "G3 (H251-H375)", "G4 (H376-H500)"]
)

status_filter = st.sidebar.multiselect(
    "Filtrar por Status",
    options=df["Status"].unique(),
    default=df["Status"].unique()
)

# Metrics
col1, col2, col3, col4 = st.columns(4)
total = len(df)
covered = len(df[df["Status"].isin(["PASS", "INFO", "FAIL", "FAIL (Anomaly)"])])
pct = (covered / 500) * 100
anomalies = len(df[df["Status"].str.contains("FAIL") | df["Status"].str.contains("Anomaly")])

col1.metric("Total Hipóteses", total)
col2.metric("Cobertura Atual", f"{pct:.1f}%")
col3.metric("Hipóteses Ativas", covered)
col4.metric("Anomalias Detectadas", anomalies, delta_color="inverse")

st.markdown("---")

# --- TABS PARA ORGANIZAÇÃO ---
tab1, tab2, tab3 = st.tabs(["📊 Visão Geral", "🔍 Análise Profunda", "📋 Detalhamento"])

with tab1:
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    total = len(df)
    covered = len(df[df["Status"].isin(["PASS", "INFO", "FAIL", "FAIL (Anomaly)"])])
    pct = (covered / 500) * 100
    anomalies = len(df[df["Status"].str.contains("FAIL") | df["Status"].str.contains("Anomaly")])
    
    col1.metric("Total Hipóteses", total)
    col2.metric("Cobertura Atual", f"{pct:.1f}%")
    col3.metric("Hipóteses Ativas", covered)
    col4.metric("Anomalias Detectadas", anomalies, delta_color="inverse")
    
    # Charts
    col_charts_1, col_charts_2 = st.columns(2)
    
    with col_charts_1:
        st.subheader("📉 Dinâmica Temporal (H001)")
        temp_df = get_temporal_data()
        if not temp_df.empty:
            fig_temp = px.line(temp_df, x='hora', y='vol', title='Volume de Votos por Hora', markers=True)
            fig_temp.update_layout(hovermode='x unified')
            st.plotly_chart(fig_temp, use_container_width=True)
        else:
            st.info("Sem dados temporais.")
    
    with col_charts_2:
        st.subheader("📊 Distribuição de Resultados")
        fig_pie = px.pie(df, names="Status", title="Status das Hipóteses", hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)

with tab2:
    st.subheader("🔍 Análises Profundas por Grupo")
    
    # Análise por grupo
    df['Grupo'] = df['ID'].apply(lambda x: 
        'G1: Temporal' if int(x[1:]) <= 125 else
        'G2: Hardware' if int(x[1:]) <= 250 else
        'G3: Forense' if int(x[1:]) <= 375 else
        'G4: Cruzamento'
    )
    
    grupo_stats = df.groupby('Grupo').agg({
        'Status': lambda x: (x.isin(['PASS', 'INFO', 'FAIL', 'FAIL (Anomaly)'])).sum(),
        'ID': 'count'
    }).reset_index()
    grupo_stats.columns = ['Grupo', 'Executadas', 'Total']
    grupo_stats['Cobertura %'] = (grupo_stats['Executadas'] / grupo_stats['Total'] * 100).round(1)
    
    st.dataframe(grupo_stats, use_container_width=True, hide_index=True)
    
    # Top 10 Anomalias
    st.subheader("⚠️ Top 10 Anomalias Detectadas")
    anomalias_df = df[df['Status'].str.contains('FAIL|Anomaly', na=False)].head(10)
    if not anomalias_df.empty:
        st.dataframe(
            anomalias_df[['ID', 'Description', 'Status', 'Observation']],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.success("✅ Nenhuma anomalia crítica detectada!")

with tab3:
    st.subheader("📋 Detalhamento Completo das Hipóteses")
    
    # Filtros na própria tab
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        grupo_filter_tab = st.multiselect(
            "Filtrar por Grupo",
            options=['G1: Temporal', 'G2: Hardware', 'G3: Forense', 'G4: Cruzamento'],
            default=['G1: Temporal', 'G2: Hardware', 'G3: Forense', 'G4: Cruzamento'],
            key="grupo_tab3"
        )
    with col_f2:
        status_filter_tab = st.multiselect(
            "Filtrar por Status",
            options=df["Status"].unique(),
            default=df["Status"].unique(),
            key="status_tab3"
        )
    
    # Aplicar filtros
    mask = df["Status"].isin(status_filter_tab) & df["Grupo"].isin(grupo_filter_tab)
    filtered_df = df[mask]
    
    st.caption(f"Mostrando {len(filtered_df)} de {len(df)} hipóteses")
    
    # Show Table
    st.dataframe(
        filtered_df[["ID", "Description", "Status", "Observation"]],
        column_config={
            "Status": st.column_config.TextColumn(
                "Status",
                help="Resultado da Análise",
                width="medium",
            ),
            "Observation": st.column_config.TextColumn(
                "Obs",
                width="large",
            ),
        },
        use_container_width=True,
        hide_index=True
    )

# Auto-refresh note
st.caption("💡 Dados atualizados automaticamente. Use o botão '🔄 Atualizar' na barra lateral para forçar refresh.")

