import streamlit as st
import pandas as pd
import plotly.express as px
import os
from sqlalchemy import create_engine, text
import sys
from datetime import datetime
import locale
from pathlib import Path

# Add root to path for config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from config import config

# Configurar locale para PT-BR
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    except:
        pass  # Fallback se não conseguir configurar

def format_number(num, decimals=0):
    """Formata número no padrão PT-BR (1.234.567,89)"""
    if decimals == 0:
        return f"{num:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
    else:
        return f"{num:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")

st.set_page_config(page_title="Brurna Analytics", page_icon="🗳️", layout="wide")

# Auto-refresh a cada 5 minutos (300 segundos)
import time
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()

elapsed = time.time() - st.session_state.last_refresh
if elapsed > 300:  # 5 minutos
    st.session_state.last_refresh = time.time()
    st.rerun()

# --- SQL CONNECTION ---
@st.cache_resource
def get_db():
    return create_engine(config.POSTGRES_CONN)

def get_execution_status():
    """Read live status from JSON file."""
    import json
    status_path = Path("execution_status.json")
    if status_path.exists():
        try:
            with open(status_path, 'r') as f:
                return json.load(f)
        except:
            return None
    return None

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
    # Calcular estimativa realista baseada em dados reais
    total_logs = stats_df['total'].sum()
    
    # Consultar média real de logs por arquivo
    engine = get_db()
    with engine.connect() as conn:
        total_files = conn.execute(text("SELECT COUNT(DISTINCT source_file) FROM log_eventos")).scalar()
        avg_logs_per_file = total_logs / total_files if total_files > 0 else 400
    
    # Estimativa: 200 arquivos por estado × 5 estados = 1000 arquivos
    expected_files = 1000
    expected_total = int(avg_logs_per_file * expected_files)
    
    progress_pct = min(total_logs / expected_total, 1.0) if expected_total > 0 else 0
    
    # Debug: mostrar valores para diagnóstico
    # st.write(f"DEBUG: total_logs={total_logs}, expected_total={expected_total}, avg={avg_logs_per_file}")
    
    import psutil
    
    col_prog1, col_prog2, col_prog3 = st.columns([3, 1, 2])
    with col_prog1:
        st.progress(progress_pct, text=f"Progresso: {format_number(int(total_logs))} / ~{format_number(int(expected_total))} logs ({format_number(progress_pct*100, 1)}%)")
    with col_prog2:
        # Calcular tempo decorrido real buscando processo ingest_logs.py
        elapsed_minutes = 0
        try:
            for p in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
                try:
                    cmd = p.info['cmdline']
                    if cmd and 'python' in p.info['name'] and any('ingest_logs.py' in c for c in cmd):
                        create_time = datetime.fromtimestamp(p.info['create_time'])
                        elapsed = datetime.now() - create_time
                        elapsed_minutes = elapsed.total_seconds() / 60
                        break
                except:
                    continue
        except:
            pass
            
        # Fallback se não encontrar processo (ex: finalizado ou erro)
        if elapsed_minutes == 0:
             # Fallback estimado (9h = 540min) se não conseguir detectar
             elapsed_minutes = 540

        # Garantir que total_logs é numérico
        total_logs_num = int(total_logs) if total_logs else 0
        rate_per_min = total_logs_num / elapsed_minutes if elapsed_minutes > 0 else 0
        st.metric("Taxa", f"{format_number(int(rate_per_min))} logs/min" if rate_per_min > 0 else "Calculando...")
    with col_prog3:
        # Estimativa de conclusão
        if rate_per_min > 0:
            remaining_logs = expected_total - total_logs
            remaining_minutes = remaining_logs / rate_per_min
            remaining_hours = remaining_minutes / 60
            
            if remaining_hours >= 24:
                days = int(remaining_hours // 24)
                hours = int(remaining_hours % 24)
                eta_text = f"{days}d {hours}h ({format_number(remaining_hours, 1)}h total)"
            else:
                hours = int(remaining_hours)
                minutes = int((remaining_hours - hours) * 60)
                eta_text = f"{hours}h {minutes}min ({format_number(remaining_hours, 1)}h total)"
            
            st.metric("⏱️ ETA", eta_text)
        else:
            st.metric("⏱️ ETA", "Calculando...")
    
    # Detalhamento por estado
    cols = st.columns(len(stats_df))
    for i, row in stats_df.iterrows():
        with cols[i]:
            delta = f"+{format_number(row['total'])}" if i == 0 else None
            cols[i].metric(f"🗳️ {row['uf']}", format_number(row['total']), delta=delta)
    
    # Monitoramento de Operações em Background
    st.subheader("🔄 Operações em Andamento")
    col_ops1, col_ops2 = st.columns(2)
    
    with col_ops1:
        st.caption("**Última atualização:** " + datetime.now().strftime("%H:%M:%S"))
        if total_logs >= expected_total:
            st.success("✅ Ingestão completa!")
        else:
            remaining = expected_total - total_logs
            st.info(f"⏳ Processando... Faltam ~{format_number(int(remaining))} logs")
    
    with col_ops2:
        st.caption("**Auto-refresh:** A cada 5 minutos")
        if st.button("🔄 Forçar Atualização Agora"):
            st.rerun()

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
tab1, tab2, tab3, tab4 = st.tabs(["📊 Visão Geral", "🔍 Análise Profunda", "📋 Detalhamento", "🚀 Monitor de Execução"])

with tab1:
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    total = len(df)
    covered = len(df[df["Status"].isin(["PASS", "INFO", "FAIL", "FAIL (Anomaly)"])])
    pct = (covered / 500) * 100
    anomalies = len(df[df["Status"].str.contains("FAIL") | df["Status"].str.contains("Anomaly")])
    
    col1.metric("Total Hipóteses", format_number(total))
    col2.metric("Cobertura Atual", f"{format_number(pct, 1)}%")
    col3.metric("Hipóteses Ativas", format_number(covered))
    col4.metric("Anomalias Detectadas", format_number(anomalies), delta_color="inverse")
    
    # Charts
    col_charts_1, col_charts_2 = st.columns(2)
    
    with col_charts_1:
        st.subheader("📉 Dinâmica Temporal (H001)")
        temp_df = get_temporal_data()
        if not temp_df.empty:
            # Criar gráfico de linha com melhorias
            fig_temp = px.line(temp_df, x='hora', y='vol', 
                              title='Volume de Votos por Hora',
                              markers=True)
            
            # Configurar eixo X para mostrar todas as horas (0-23)
            fig_temp.update_xaxes(
                dtick=1,  # Intervalo de 1 hora
                range=[-0.5, 23.5],
                title="Hora do Dia"
            )
            
            # Configurar eixo Y
            fig_temp.update_yaxes(title="Volume de Votos")
            
            # Adicionar valores nos pontos (formato PT-BR)
            # Converter valores para formato brasileiro antes de exibir
            temp_df['vol_formatted'] = temp_df['vol'].apply(lambda x: format_number(x))
            
            fig_temp.update_traces(
                textposition='top center',
                text=temp_df['vol_formatted'],
                mode='lines+markers+text',
                line=dict(color='#0066cc', width=3),
                marker=dict(size=8, color='#ff6600')
            )
            
            # Melhorar layout
            fig_temp.update_layout(
                hovermode='x unified',
                showlegend=False,
                height=400
            )
            
            st.plotly_chart(fig_temp, use_container_width=True)
        else:
            st.info("Sem dados temporais.")
    
    with col_charts_2:
        st.subheader("📊 Distribuição de Resultados")
        
        # Criar gráfico de pizza com cores vibrantes
        status_counts = df['Status'].value_counts()
        
        # Paleta de cores personalizada
        colors = ['#00cc66', '#0099ff', '#ff9900', '#ff3366', '#9933ff', '#ffcc00']
        
        fig_pie = px.pie(
            values=status_counts.values,
            names=status_counts.index,
            title="Status das Hipóteses",
            hole=0.4,
            color_discrete_sequence=colors
        )
        
        # Adicionar percentuais nos labels
        fig_pie.update_traces(
            textposition='inside',
            textinfo='percent+label',
            textfont_size=12
        )
        
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
    
    # Calcular cobertura como número primeiro
    grupo_stats['Cobertura_num'] = (grupo_stats['Executadas'] / grupo_stats['Total'] * 100)
    
    # Criar cópia para exibição com formatação PT-BR
    grupo_stats_display = grupo_stats.copy()
    grupo_stats_display['Executadas'] = grupo_stats['Executadas'].apply(lambda x: format_number(int(x)))
    grupo_stats_display['Total'] = grupo_stats['Total'].apply(lambda x: format_number(int(x)))
    grupo_stats_display['Cobertura %'] = grupo_stats['Cobertura_num'].apply(lambda x: f"{format_number(x, 1)}%")
    
    # Remover coluna auxiliar
    grupo_stats_display = grupo_stats_display.drop('Cobertura_num', axis=1)
    
    st.dataframe(grupo_stats_display, use_container_width=True, hide_index=True)
    
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

with tab4:
    st.subheader("🚀 Monitor de Execução em Tempo Real")
    
    status = get_execution_status()
    if status:
        # Progress Bar
        st.progress(status["percentage"] / 100, 
                   text=f"Progresso: {status['progress']} / {status['total']} hipóteses ({format_number(status['percentage'], 1)}%)")
        
        m_col1, m_col2, m_col3 = st.columns(3)
        m_col1.metric("Hipótese Atual", status["current_id"])
        
        avg_step = status["avg_step_seconds"]
        m_col2.metric("Tempo Médio/Teste", f"{format_number(avg_step, 2)}s")
        
        eta = status["eta_seconds"]
        eta_h = eta / 3600
        m_col3.metric("⏱️ ETA Restante", f"{format_number(eta_h, 1)}h" if eta_h >= 1 else f"{format_number(eta/60, 0)}min")
        
        st.divider()
        
        # Last Result Preview
        if status.get("last_result"):
            lr = status["last_result"]
            st.write("### 🆕 Último Resultado:")
            res_col1, res_col2 = st.columns([1, 4])
            with res_col1:
                st.info(f"**{lr['ID']}**")
                if "FAIL" in lr['Status']:
                    st.error(lr['Status'])
                elif "PASS" in lr['Status']:
                    st.success(lr['Status'])
                else:
                    st.warning(lr['Status'])
            with res_col2:
                st.write(f"**Descrição**: {lr['Description']}")
                st.write(f"**Observação**: {lr['Observation']}")
                
        st.divider()
        
        # Live Anomaly Detector
        st.write("### ⚠️ Anomalias Detectadas Recentemente")
        if os.path.exists("analysis_results.csv"):
            res_df = pd.read_csv("analysis_results.csv")
            anomalies = res_df[res_df["Status"].str.contains("FAIL") | res_df["Status"].str.contains("Anomaly")].tail(5)
            if not anomalies.empty:
                st.table(anomalies[["ID", "Status", "Observation"]])
            else:
                st.success("Nenhuma anomalia detectada até o momento.")
    else:
        st.info("Aguardando início do motor analítico...")
        if st.button("▶️ Iniciar Motor em Background"):
            import subprocess
            subprocess.Popen([sys.executable, "src/analytics/analytical_engine.py"], 
                             stdout=open("logs/analytical_engine.out", "a"),
                             stderr=open("logs/analytical_engine.err", "a"),
                             creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0)
            st.success("Motor disparado! O monitor atualizará em instantes.")
            time.sleep(2)
            st.rerun()

# Auto-refresh note
st.caption("💡 Dados atualizados automaticamente a cada 5 min. Use 'F5' ou o botão na sidebar para atualizar o monitor instantaneamente.")


