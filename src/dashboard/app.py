import streamlit as st
import pandas as pd
import plotly.express as px
import os
from sqlalchemy import create_engine, text
import sys
from datetime import datetime, timedelta
import locale
from pathlib import Path

# Add root to path for config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from config import config

# --- Authentication gate (must run before any page render) ---
from auth.auth_gate import require_auth
require_auth()


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
def get_db(use_local=True):
    if use_local:
        return create_engine(config.LOCAL_POSTGRES_CONN)
    return create_engine(config.REMOTE_POSTGRES_CONN)

# Iniciar state do DB
if 'db_mode' not in st.session_state:
    st.session_state.db_mode = 'Local (Ryzen 🚀)'

def get_current_engine():
    return get_db(use_local=st.session_state.db_mode == 'Local (Ryzen 🚀)')

def get_download_status():
    """Read live download status from JSON file."""
    import json
    import time
    status_path = Path("download_status.json")
    
    # Only return if recently updated (last 30s) to avoid stale data
    if status_path.exists():
        try:
            if time.time() - status_path.stat().st_mtime < 60:
                with open(status_path, 'r') as f:
                    return json.load(f)
        except:
            return None
    return None

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

def get_ingestion_status():
    """Read live ingestion status from JSON file."""
    import json
    import time
    status_path = Path("ingestion_status.json")
    
    if status_path.exists():

        try:
            # Removed time limit to show stale status with warning in UI
            with open(status_path, 'r') as f:
                return json.load(f)
        except:
            return None
    return None

def get_ingestion_stats():
    """Query live row counts per state based on source_file path/name."""
    try:
        engine = get_current_engine()
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

@st.cache_data(ttl=2)
def get_dual_sync_status():
    """Fetch counts from both Local and Remote DB for comparative Sync Status."""
    ufs_target = ['SE', 'RR', 'TO', 'AC', 'AP']
    
    def fetch_data(conn_str):
        from sqlalchemy.pool import NullPool
        try:
            eng = create_engine(conn_str, poolclass=NullPool)
            with eng.connect() as conn:
                q_meta = text("SELECT upper(uf) as uf, COUNT(*) as meta_total FROM section_metadata GROUP BY 1")
                df_meta = pd.read_sql(q_meta, conn)
                q_logs = text("""
                    SELECT 
                        CASE 
                            WHEN source_file LIKE '%/ac/%' OR source_file LIKE '%\\ac\\%' THEN 'AC'
                            WHEN source_file LIKE '%/ap/%' OR source_file LIKE '%\\ap\\%' THEN 'AP'
                            WHEN source_file LIKE '%/rr/%' OR source_file LIKE '%\\rr\\%' THEN 'RR'
                            WHEN source_file LIKE '%/to/%' OR source_file LIKE '%\\to\\%' THEN 'TO'
                            WHEN source_file LIKE '%/se/%' OR source_file LIKE '%\\se\\%' THEN 'SE'
                            ELSE 'Outros'
                        END as uf,
                        COUNT(*) as raw_total
                    FROM log_eventos
                    GROUP BY 1
                """)
                df_logs = pd.read_sql(q_logs, conn)
                return df_meta, df_logs
        except Exception:
            return pd.DataFrame(), pd.DataFrame()

    loc_meta, loc_logs = fetch_data(config.LOCAL_POSTGRES_CONN)
    rem_meta, rem_logs = fetch_data(config.REMOTE_POSTGRES_CONN)
    
    # Expected approx file counts per state
    expected = {'SE': 4207, 'RR': 1124, 'TO': 3593, 'AC': 2118, 'AP': 1740}
    avg_logs_per_urn = 7500
    
    rows = []
    for uf in ufs_target:
        # Extract Local data
        l_meta_val = loc_meta.loc[loc_meta['uf'] == uf, 'meta_total'].values[0] if (not loc_meta.empty and uf in loc_meta['uf'].values) else 0
        l_logs_val = loc_logs.loc[loc_logs['uf'] == uf, 'raw_total'].values[0] if (not loc_logs.empty and uf in loc_logs['uf'].values) else 0
        
        # Extract Remote data
        r_meta_val = rem_meta.loc[rem_meta['uf'] == uf, 'meta_total'].values[0] if (not rem_meta.empty and uf in rem_meta['uf'].values) else 0
        
        exp_urnas = expected.get(uf, 1)
        exp_logs = exp_urnas * avg_logs_per_urn
        
        phase = "Aguardando"
        progress_pct = 0.0
        details = "0"
        
        # Analysis status check
        analysis_done = os.path.exists("analysis_results.csv")
        
        if l_meta_val >= exp_urnas * 0.95:
            if r_meta_val >= exp_urnas * 0.95:
                phase = "🌟 Concluído"
                progress_pct = 100.0
            elif analysis_done:
                phase = "✅ Fase 4: Sinc. Remoto"
                progress_pct = (r_meta_val / exp_urnas) * 100
                progress_pct = min(100.0, progress_pct)
            else:
                phase = "🧠 Fase 3: Motor Analítico"
                progress_pct = 80.0 # Heuristic for analysis starting
            details = f"{l_meta_val} Seções"
        elif l_meta_val > 0:
            phase = "🕵️ Fase 2: Agregador"
            progress_pct = (l_meta_val / exp_urnas) * 100
            details = f"{l_meta_val} / {exp_urnas} Seções"
        elif l_logs_val > 0:
            phase = "☢️ Fase 1: Ingestão Bruta"
            progress_pct = (l_logs_val / exp_logs) * 100
            progress_pct = min(99.9, progress_pct)
            details = f"{format_number(l_logs_val)} / ~{format_number(exp_logs)} logs"
            
        sync_pct_str = f"{min(100, (r_meta_val / exp_urnas) * 100):.1f}%" if r_meta_val > 0 else "0.0%"
        
        # Create visual progress bar (ASCII style for columns)
        bar_len = 15
        filled = int(bar_len * (progress_pct / 100))
        bar = "█" * filled + "░" * (bar_len - filled)
        
        rows.append({
            "UF": uf,
            "Alvo Estimado": format_number(exp_urnas),
            "Fase Atual": phase,
            "Progresso Visual": f"{bar} {progress_pct:.1f}%",
            "Detalhes do Proc.": details,
            "Remoto (Sincronizado)": format_number(r_meta_val),
            "Cloud Sync %": sync_pct_str
        })
    return pd.DataFrame(rows)


def get_temporal_data():
    try:
        engine = get_current_engine()
        q = text("SELECT hora, SUM(quantidade) as vol FROM temporal_metrics GROUP BY 1 ORDER BY 1")
        with engine.connect() as conn:
            return pd.read_sql(q, conn)
    except:
        return pd.DataFrame()

st.title("🗳️ Brurna Analytics: Painel de Inteligência Eleitoral")

# --- INGESTION STATUS (LIVE) ---
st.subheader("🔄 Status do Banco: Sincronismo Nuclear")
sync_df = get_dual_sync_status()
st.dataframe(sync_df, width="stretch", hide_index=True)
st.caption("A tabela acima monitora os logs brutos nos dois ambientes (Ryzen Local vs AWS/Remoto).")

# Monitoramento de Operações em Background
st.subheader("⚙️ Monitor de Background")
col_ops1, col_ops2 = st.columns(2)

with col_ops1:
    st.caption("**Última atualização:** " + datetime.now().strftime("%H:%M:%S"))
    st.info("✅ Sistema operando normalmente")

with col_ops2:
    st.caption("**Auto-refresh:** A cada 5 minutos")
    if st.button("🔄 Forçar Atualização Agora"):
        st.session_state.last_refresh = time.time()
        st.rerun()



st.markdown("---")

# Load Analysis Data
@st.cache_data(ttl=60) # Refresh every minute
def load_data():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
    path = os.path.join(project_root, "analysis_results.csv")
    
    if not os.path.exists(path):
        return pd.DataFrame()
        
    try:
        df = pd.read_csv(path)
        return df
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.info("ℹ️ Nenhum dado analítico encontrado. O Motor Analítico precisa rodar para gerar os resultados das 500 hipóteses.")
    st.caption(f"Procurando em: {os.path.abspath(os.path.join(os.path.dirname(__file__), '../../analysis_results.csv'))}")
    st.stop()

# Sidebar
st.sidebar.header("🔌 Conectividade")
db_mode = st.sidebar.radio(
    "Fonte de Dados",
    options=['Local (Ryzen 🚀)', 'Remoto (Cloud ☁️)'],
    index=0,
    key="db_mode_radio"
)

if db_mode != st.session_state.db_mode:
    st.session_state.db_mode = db_mode
    st.cache_resource.clear()
    st.rerun()

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
    
    # Check Download Status First
    dl_status = get_download_status()
    
    if dl_status and dl_status.get("activity") == "download":
        st.info("📥 Download de Dados em Andamento (Região SUL)")
        
        # Clamp progress to 0-1 range to avoid Streamlit errors
        raw_pct = dl_status["percentage"] / 100
        safe_pct = min(max(raw_pct, 0.0), 1.0)
        
        st.progress(safe_pct, 
                   text=f"Baixando: {format_number(dl_status['progress'])} / {format_number(dl_status['total'])} arquivos ({dl_status['percentage']:.1f}%)")
        st.caption(f"Último arquivo: {dl_status['file']}")
        st.divider()
    
    # Check Ingestion Status
    ing_status = get_ingestion_status()
    if ing_status:
        # Check staleness
        import time
        last_update = datetime.fromisoformat(ing_status['timestamp'])
        seconds_ago = (datetime.now() - last_update).total_seconds()
        is_stale = seconds_ago > 120
        
        status_color = "red" if is_stale else "blue"
        status_text = f"⚠️ Ingestão Parada/Estagnada (Último sinal: {int(seconds_ago/60)} min atrás)" if is_stale else f"⚡ Monitoramento de Ingestão (Tempo Real) - {ing_status.get('state', 'Unknown').upper()}"
        
        if is_stale:
            st.error(status_text)
        else:
            st.info(status_text)
        
        # Calculate Rates from JSON
        rate = ing_status.get("rate", 0) * 60 # logs/min (assuming rate is files/sec? no, rate is files/sec in backend)
        # Actually rate in backend is files/sec. Let's show files/min or logs/min? 
        # User asked for "783 logs/min". We track files processed. 
        # Let's show Files/min to be accurate to what we count.
        files_per_min = rate 
        
        eta_seconds = ing_status.get("eta_seconds", 0)
        eta_h = int(eta_seconds // 3600)
        eta_m = int((eta_seconds % 3600) // 60)
        
        elapsed_seconds = ing_status.get("elapsed_seconds", 0)
        el_h = elapsed_seconds / 3600
        
        raw_pct = ing_status["percentage"] / 100
        safe_pct = min(max(raw_pct, 0.0), 1.0)
        
        # Display Bar
        st.progress(safe_pct, 
                   text=f"Progresso: {format_number(ing_status['progress'])} / {format_number(ing_status['total'])} arquivos ({ing_status['percentage']:.1f}%)")
        
        # Custom Portuguese Day of Week
        days_map = {0: "SEG", 1: "TER", 2: "QUA", 3: "QUI", 4: "SEX", 5: "SAB", 6: "DOM"}
        
        # Calculate Projected Finish
        finish_time = datetime.now() + timedelta(seconds=eta_seconds)
        day_str = days_map[finish_time.weekday()]
        finish_str = finish_time.strftime("%d/%m %H:%M")
        
        # Metrics Row
        col_i1, col_i2, col_i3 = st.columns(3)
        col_i1.metric("Rítmo", f"{format_number(files_per_min, 1)} arq/min")
        col_i2.metric("⏱️ ETA", f"{eta_h}h {eta_m}min", help=f"Previsão: {day_str} {finish_str}")
        col_i3.metric("Conclusão", f"{day_str} {finish_str}")
        
        # Details
        st.caption(f"Arquivo Atual: {ing_status['file']}")
        if ing_status['errors'] > 0:
            st.error(f"Erros Totais: {ing_status['errors']}")
        
        st.divider()

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


