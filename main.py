# main.py
import typer
from typing import Optional
import sys
from pathlib import Path
from config import config

# Adiciona src ao path
src_path = Path(__file__).parent / "src"
sys.path.append(str(src_path))

app = typer.Typer(help="BRURNA Analytics - Processador de Logs do TSE")

@app.command()
def download(
    uf: str = typer.Option(..., help="UF para download (ex: ac, sp)"),
    limit: Optional[int] = typer.Option(None, help="Limitar número de seções a baixar"),
    turno: int = typer.Option(1, help="Turno da eleição (1 ou 2)")
):
    """Baixa logs do TSE (1º ou 2º Turno)"""
    print(f"📥 Iniciando download - UF: {uf.upper()} (Turno {turno})")
    
    try:
        from download.downloader import TSEDownloader
        downloader = TSEDownloader(turno=turno)
        
        if limit:
            print(f"⚠️  Limitado às primeiras {limit} seções")
        
        # Baixa os arquivos
        resultados = downloader.download_uf(uf, limit=limit)
        
        if resultados is not None and not resultados.empty:
            secoes_baixadas = resultados['baixado'].sum()
            print(f"✅ Download concluído para UF {uf.upper()} T{turno}")
            print(f"   Seções baixadas: {secoes_baixadas}/{len(resultados)}")
        else:
            print("⚠️  Nenhuma seção foi baixada")
            
    except Exception as e:
        print(f"❌ Erro durante o download: {e}")

@app.command()
def parse(
    uf: str = typer.Option(..., help="UF para parsear (ex: ac, sp)"),
    limit: Optional[int] = typer.Option(None, help="Limitar número de seções a processar"),
    turno: int = typer.Option(1, help="Turno da eleição (1 ou 2)"),
    output: str = typer.Option("parquet", help="Formato de saída: parquet, csv, json, all"),
    cleanup: bool = typer.Option(False, help="Limpar arquivos temporários após processamento")
):
    """Parseia logs baixados (1º ou 2º Turno)"""
    print(f"🔍 Iniciando parsing - UF: {uf.upper()} T{turno}, Limite: {limit}, Formato: {output}")
    
    try:
        from parser.log_parser import TSELogParser
        import pandas as pd
        
        # Define diretório baseado no turno
        uf_path = uf if turno == 1 else f"{uf}/t2"
        raw_dir = config.RAW_LOGS_DIR / uf_path
        
        # Lista todos os arquivos .logjez
        files = list(raw_dir.glob('*.logjez'))
        if not files:
            print(f"❌ Nenhum arquivo .logjez encontrado em: {raw_dir}")
            print("Execute primeiro: python main.py download --uf ac")
            return
        
        if limit and limit > 0:
            files = files[:limit]
            print(f"⚠️  Processando apenas {limit} arquivos (de {len(list(raw_dir.glob('*.logjez')))} totais)")
        
        print(f"📁 Encontrados {len(files)} arquivos para processar")
        
        todos_dados = []
        
        for i, file in enumerate(files, 1):
            print(f"\n[{i}/{len(files)}] Processando: {file.name}")
            
            # Extrai informações do nome do arquivo
            nome_base = file.stem  # ex: o00407-0106600040077
            if '-' in nome_base:
                partes = nome_base.split('-')
                if len(partes) > 1:
                    codigo_secao = partes[1]  # ex: 0106600040077
                    if len(codigo_secao) >= 13:
                        municipio_codigo = codigo_secao[:5]
                        zona = codigo_secao[5:9]
                        secao = codigo_secao[9:13]
                        
                        print(f"   Município: {municipio_codigo}, Zona: {zona}, Seção: {secao}")
                        
                        # Cria parser e processa
                        parser = TSELogParser(str(file))
                        df = parser.parse_file()
                        
                        if not df.empty:
                            # Adiciona metadados de identificação
                            df['uf'] = uf.upper()
                            df['turno'] = turno
                            todos_dados.append(df)
                            print(f"   ✅ Processadas {len(df)} linhas")
                        else:
                            print(f"   ⚠️  Nenhum dado extraído")
                    else:
                        print(f"   ⚠️  Nome de arquivo com formato inválido: {nome_base}")
                else:
                    print(f"   ⚠️  Não foi possível extrair informações do nome: {nome_base}")
            else:
                print(f"   ⚠️  Nome de arquivo sem formato esperado: {nome_base}")
        
        # Consolida todos os dados
        if todos_dados:
            df_final = pd.concat(todos_dados, ignore_index=True)
            print(f"\n✅ Parsing concluído para UF {uf.upper()}")
            print(f"   Seções processadas: {len(todos_dados)}")
            print(f"   Total de linhas: {len(df_final):,}")
            
            # Salva em diferentes formatos conforme solicitado
            output_dir = config.PROCESSED_DIR / uf
            output_dir.mkdir(parents=True, exist_ok=True)
            
            if output in ["parquet", "all"]:
                parquet_path = output_dir / f"logs_{uf}.parquet"
                df_final.to_parquet(parquet_path, index=False)
                print(f"   📊 Parquet salvo em: {parquet_path}")
            
            if output in ["csv", "all"]:
                csv_path = output_dir / f"logs_{uf}.csv"
                df_final.to_csv(csv_path, index=False, encoding='utf-8')
                print(f"   📄 CSV salvo em: {csv_path}")
            
            if output in ["json", "all"]:
                json_path = output_dir / f"logs_{uf}.json"
                df_final.to_json(json_path, orient='records', indent=2)
                print(f"   📋 JSON salvo em: {json_path}")
            
            # Limpeza opcional
            if cleanup:
                # Lógica para limpar arquivos temporários, se necessário
                pass
        else:
            print(f"❌ Nenhum dado foi processado para UF {uf.upper()}")
            
    except ImportError as e:
        print(f"❌ Erro ao importar módulo: {e}")
        print("Certifique-se de que os módulos parser.log_parser e database.db_writer existem.")
    except Exception as e:
        print(f"❌ Erro durante o parsing: {e}")
        import traceback
        traceback.print_exc()

@app.command()
def analyze(
    uf: str = typer.Option(..., help="UF para análise"),
    metric: str = typer.Option("temporal", help="Métrica: temporal, mesarios, eventos")
):
    """Análises específicas dos dados processados"""
    print(f"📊 Iniciando análise - UF: {uf.upper()}, Métrica: {metric}")
    
    try:
        import pandas as pd
        from pathlib import Path
        
        processed_dir = config.PROCESSED_DIR / uf
        parquet_file = processed_dir / f"logs_{uf}.parquet"
        
        if not parquet_file.exists():
            print(f"❌ Arquivo de dados não encontrado: {parquet_file}")
            print("Execute primeiro: python main.py parse --uf {uf}")
            return
        
        # Carrega os dados
        df = pd.read_parquet(parquet_file)
        print(f"✅ Dados carregados: {len(df):,} linhas")
        
        if metric == "temporal":
            # Análise temporal básica
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                print(f"\n📅 ANÁLISE TEMPORAL - UF {uf.upper()}")
                print(f"Período mais antigo: {df['timestamp'].min()}")
                print(f"Período mais recente: {df['timestamp'].max()}")
                print(f"Duração total: {df['timestamp'].max() - df['timestamp'].min()}")
                
                # Eventos por hora
                df['hora'] = df['timestamp'].dt.hour
                eventos_por_hora = df.groupby('hora').size()
                print(f"\n📈 Eventos por hora:")
                for hora, count in eventos_por_hora.items():
                    print(f"  {hora:02d}:00 - {count:6,} eventos")
        
        elif metric == "severidade":
            # Análise por severidade
            if 'severidade' in df.columns:
                print(f"\n⚠️  ANÁLISE DE SEVERIDADE - UF {uf.upper()}")
                severidades = df['severidade'].value_counts()
                for sev, count in severidades.items():
                    print(f"  {sev:10} - {count:6,} eventos ({count/len(df)*100:.1f}%)")
        
        elif metric == "aplicativo":
            # Análise por aplicativo
            if 'aplicativo' in df.columns:
                print(f"\n📱 ANÁLISE POR APLICATIVO - UF {uf.upper()}")
                apps = df['aplicativo'].value_counts().head(10)
                for app, count in apps.items():
                    print(f"  {app:15} - {count:6,} eventos")
        
        print(f"\n✅ Análise {metric} concluída para UF {uf.upper()}")
        
    except Exception as e:
        print(f"❌ Erro durante a análise: {e}")

@app.command()
def sync_results(
    uf: str = typer.Option(..., help="UF para sincronizar"),
    year: int = typer.Option(2022, help="Ano da eleição")
):
    """Sincroniza logs processados com dados oficiais do TSE (BU)"""
    print(f"⚖️ Iniciando cruzamento de auditoria - UF: {uf.upper()} ({year})")
    
    try:
        from analytics.tse_data_integrator import TSEDataIntegrator
        integrator = TSEDataIntegrator(year=year)
        
        # Realiza o merge massivo
        merged = integrator.merge_with_tse_data(uf)
        
        if not merged.empty:
            output_file = f"auditoria_cruzada_{uf.lower()}_{year}.csv"
            merged.to_csv(output_file, index=False)
            print(f"✅ Auditoria concluída. {len(merged)} seções validadas.")
            print(f"📄 Resultado salvo em: {output_file}")
            
            # Análise básica de discrepância
            merged['discrepancia_votos'] = merged['total_eventos'] - merged['QT_COMPARECIMENTO'] # Simplificado
            discrepantes = merged[merged['discrepancia_votos'].abs() > 1000] # Exemplo de threshold
            if not discrepantes.empty:
                print(f"⚠️ Alerta: {len(discrepantes)} seções com alto volume de anomalias detectadas.")
        else:
            print("❌ Falha ao cruzar dados. Verifique se a UF já foi parseada.")
            
    except Exception as e:
        print(f"❌ Erro durante a sincronização: {e}")

@app.command()
def test():
    """Testa a configuração do projeto"""
    print("🧪 Testando configuração do projeto...")
    
    # Testar imports básicos
    try:
        import pandas as pd
        import requests
        import py7zr
        import chardet
        import sqlalchemy
        print("✅ Imports básicos funcionando")
    except ImportError as e:
        print(f"❌ Erro de import: {e}")
    
    # Testar estrutura de diretórios
    if config.DATA_DIR.exists():
        print("✅ Diretório de dados existe")
        
        # Verificar espaço livre
        import shutil
        total, used, free = shutil.disk_usage(config.DATA_DIR)
        print(f"  Espaço livre: {free // (2 ** 30)} GB")
        print(f"  Espaço total: {total // (2 ** 30)} GB")
    else:
        print("❌ Diretório de dados não encontrado")
    
    # Testar conexão com banco de dados
    try:
        from database.db_writer import engine
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            print("✅ Conexão com banco de dados funcionando")
    except Exception as e:
        print(f"❌ Erro na conexão com banco de dados: {e}")
    
    # Listar UFs configuradas
    print(f"\n🗺️  UFs configuradas ({len(config.UFS)}):")
    print(f"  {', '.join(config.UFS)}")
    
    print("\n✅ Teste concluído")

@app.command()
def status():
    """Mostra status do processamento"""
    print("📊 STATUS DO PROCESSAMENTO")
    print("=" * 50)
    
    for uf in ['ac', 'sp']:  # UFs de exemplo
        raw_dir = config.RAW_LOGS_DIR / uf
        processed_dir = config.PROCESSED_DIR / uf
        
        raw_files = list(raw_dir.glob('*.logjez'))
        processed_file = processed_dir / f"logs_{uf}.parquet"
        
        print(f"\nUF: {uf.upper()}")
        print(f"  Arquivos .logjez baixados: {len(raw_files)}")
        print(f"  Dados processados: {'SIM' if processed_file.exists() else 'NÃO'}")
        
        if processed_file.exists():
            try:
                import pandas as pd
                df = pd.read_parquet(processed_file)
                print(f"    Linhas processadas: {len(df):,}")
                if 'timestamp' in df.columns:
                    print(f"    Período: {df['timestamp'].min()} a {df['timestamp'].max()}")
            except:
                print(f"    (erro ao ler arquivo)")
    
    print("\n📋 COMANDOS DISPONÍVEIS:")
    print("  python main.py download --uf ac --limit 10")
    print("  python main.py parse --uf ac --limit 5")
    print("  python main.py analyze --uf ac --metric temporal")
    print("  python main.py test")
    print("  python main.py status")

if __name__ == "__main__":
    app()
