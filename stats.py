#!/usr/bin/env python3
"""
Script para gerar estatísticas do banco de dados BRURNA
"""

import pandas as pd
from sqlalchemy import create_engine, text, inspect
from config import config
from datetime import datetime
import matplotlib.pyplot as plt
import sys
import typer
from typing import Optional


def get_db_engine():
    """Retorna engine de conexão com o banco"""
    return create_engine(config.POSTGRES_CONN)


def get_connection():
    """Retorna uma conexão com o banco"""
    engine = get_db_engine()
    return engine.connect()


def get_table_columns(conn, table_name='logs'):
    """Retorna as colunas existentes na tabela"""
    inspector = inspect(conn.engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return columns


def estatisticas_gerais(conn, uf=None):
    """Gera estatísticas gerais dos logs"""

    # Primeiro, verifica quais colunas existem
    columns = get_table_columns(conn)

    # Base da query com apenas colunas que existem
    query_base = """
                 SELECT COUNT(*)                   as total_registros, \
                        COUNT(DISTINCT aplicativo) as aplicativos_distintos, \
                        COUNT(DISTINCT severidade) as severidades_distintas, \
                        MIN(timestamp)             as data_minima, \
                        MAX(timestamp)             as data_maxima
                 FROM logs \
                 """

    params = {}
    if uf:
        query_base += " WHERE uf = :uf"
        params['uf'] = uf.upper()

    try:
        result = conn.execute(text(query_base), params)
        row = result.fetchone()

        stats = {
            'total_registros': row[0] if row[0] is not None else 0,
            'aplicativos_distintos': row[1] if row[1] is not None else 0,
            'severidades_distintas': row[2] if row[2] is not None else 0,
            'data_minima': row[3],
            'data_maxima': row[4]
        }

        # Adiciona colunas adicionais se existirem
        if 'municipio_codigo' in columns:
            query_mun = "SELECT COUNT(DISTINCT municipio_codigo) FROM logs"
            if uf:
                query_mun += " WHERE uf = :uf"
                result_mun = conn.execute(text(query_mun), params)
            else:
                result_mun = conn.execute(text(query_mun))
            stats['municipios_distintos'] = result_mun.scalar() or 0

        if 'zona' in columns:
            query_zona = "SELECT COUNT(DISTINCT zona) FROM logs"
            if uf:
                query_zona += " WHERE uf = :uf"
                result_zona = conn.execute(text(query_zona), params)
            else:
                result_zona = conn.execute(text(query_zona))
            stats['zonas_distintas'] = result_zona.scalar() or 0

        if 'secao' in columns:
            query_secao = "SELECT COUNT(DISTINCT secao) FROM logs"
            if uf:
                query_secao += " WHERE uf = :uf"
                result_secao = conn.execute(text(query_secao), params)
            else:
                result_secao = conn.execute(text(query_secao))
            stats['secoes_distintas'] = result_secao.scalar() or 0

        return stats

    except Exception as e:
        print(f"Erro ao obter estatísticas gerais: {e}")
        return None


def estatisticas_por_aplicativo(conn, uf=None, top_n=10):
    """Estatísticas por aplicativo"""
    try:
        if uf:
            query = text("""
                         SELECT COALESCE(aplicativo, 'DESCONHECIDO')                                               as aplicativo,
                                COUNT(*)                                                                           as quantidade,
                                ROUND(COUNT(*) * 100.0 / NULLIF((SELECT COUNT(*) FROM logs WHERE uf = :uf), 0),
                                      2)                                                                           as porcentagem
                         FROM logs
                         WHERE uf = :uf
                         GROUP BY COALESCE(aplicativo, 'DESCONHECIDO')
                         ORDER BY quantidade DESC LIMIT :top_n
                         """)

            result = conn.execute(query, {'uf': uf.upper(), 'top_n': top_n})
        else:
            query = text("""
                         SELECT COALESCE(aplicativo, 'DESCONHECIDO')                                as aplicativo,
                                COUNT(*)                                                            as quantidade,
                                ROUND(COUNT(*) * 100.0 / NULLIF((SELECT COUNT(*) FROM logs), 0), 2) as porcentagem
                         FROM logs
                         GROUP BY COALESCE(aplicativo, 'DESCONHECIDO')
                         ORDER BY quantidade DESC LIMIT :top_n
                         """)

            result = conn.execute(query, {'top_n': top_n})

        apps = []
        for row in result:
            apps.append({
                'aplicativo': row[0],
                'quantidade': row[1],
                'porcentagem': row[2] if row[2] is not None else 0
            })

        return apps

    except Exception as e:
        print(f"Erro ao obter estatísticas por aplicativo: {e}")
        return []


def estatisticas_por_severidade(conn, uf=None):
    """Estatísticas por severidade"""
    try:
        if uf:
            query = text("""
                         SELECT COALESCE(severidade, 'DESCONHECIDO')                                               as severidade,
                                COUNT(*)                                                                           as quantidade,
                                ROUND(COUNT(*) * 100.0 / NULLIF((SELECT COUNT(*) FROM logs WHERE uf = :uf), 0),
                                      2)                                                                           as porcentagem
                         FROM logs
                         WHERE uf = :uf
                         GROUP BY COALESCE(severidade, 'DESCONHECIDO')
                         ORDER BY quantidade DESC
                         """)

            result = conn.execute(query, {'uf': uf.upper()})
        else:
            query = text("""
                         SELECT COALESCE(severidade, 'DESCONHECIDO')                                as severidade,
                                COUNT(*)                                                            as quantidade,
                                ROUND(COUNT(*) * 100.0 / NULLIF((SELECT COUNT(*) FROM logs), 0), 2) as porcentagem
                         FROM logs
                         GROUP BY COALESCE(severidade, 'DESCONHECIDO')
                         ORDER BY quantidade DESC
                         """)

            result = conn.execute(query)

        sevs = []
        for row in result:
            sevs.append({
                'severidade': row[0],
                'quantidade': row[1],
                'porcentagem': row[2] if row[2] is not None else 0
            })

        return sevs

    except Exception as e:
        print(f"Erro ao obter estatísticas por severidade: {e}")
        return []


def estatisticas_por_hora(conn, uf=None):
    """Estatísticas por hora do dia"""
    try:
        if uf:
            query = text("""
                         SELECT EXTRACT(HOUR FROM timestamp) as hora,
                                COUNT(*)                     as quantidade,
                                ROUND(COUNT(*) * 100.0 /
                                      NULLIF((SELECT COUNT(*) FROM logs WHERE uf = :uf AND timestamp IS NOT NULL), 0),
                                      2)                     as porcentagem
                         FROM logs
                         WHERE uf = :uf
                           AND timestamp IS NOT NULL
                         GROUP BY EXTRACT (HOUR FROM timestamp)
                         ORDER BY hora
                         """)

            result = conn.execute(query, {'uf': uf.upper()})
        else:
            query = text("""
                         SELECT EXTRACT(HOUR FROM timestamp)                                                 as hora,
                                COUNT(*)                                                                     as quantidade,
                                ROUND(COUNT(*) * 100.0 /
                                      NULLIF((SELECT COUNT(*) FROM logs WHERE timestamp IS NOT NULL), 0),
                                      2)                                                                     as porcentagem
                         FROM logs
                         WHERE timestamp IS NOT NULL
                         GROUP BY EXTRACT (HOUR FROM timestamp)
                         ORDER BY hora
                         """)

            result = conn.execute(query)

        horas = []
        for row in result:
            hora_val = row[0]
            if hora_val is not None:
                try:
                    horas.append({
                        'hora': int(float(hora_val)),
                        'quantidade': row[1],
                        'porcentagem': row[2] if row[2] is not None else 0
                    })
                except (ValueError, TypeError):
                    continue

        return horas

    except Exception as e:
        print(f"Erro ao obter estatísticas por hora: {e}")
        return []


def estatisticas_por_dia(conn, uf=None):
    """Estatísticas por dia"""
    try:
        if uf:
            query_base = """
                         SELECT
                             DATE (timestamp) as dia, COUNT (*) as quantidade
                         FROM logs
                         WHERE timestamp IS NOT NULL
                           AND uf = :uf
                         GROUP BY DATE (timestamp) \
                         ORDER BY dia
                         """

            result = conn.execute(text(query_base), {'uf': uf.upper()})
        else:
            query_base = """
                         SELECT
                             DATE (timestamp) as dia, COUNT (*) as quantidade
                         FROM logs
                         WHERE timestamp IS NOT NULL
                         GROUP BY DATE (timestamp) \
                         ORDER BY dia
                         """

            result = conn.execute(text(query_base))

        dias = []
        for row in result:
            dias.append({
                'dia': row[0],
                'quantidade': row[1]
            })

        return dias

    except Exception as e:
        print(f"Erro ao obter estatísticas por dia: {e}")
        return []


def estatisticas_por_municipio(conn, uf=None, top_n=10):
    """Estatísticas por município (se a informação estiver disponível)"""
    try:
        # Verifica se a coluna existe
        columns = get_table_columns(conn)
        if 'municipio_codigo' not in columns:
            return []

        if uf:
            query_base = """
                         SELECT COALESCE(municipio_codigo, 'DESCONHECIDO') as municipio_codigo, \
                                COUNT(*)                                   as quantidade
                         FROM logs
                         WHERE municipio_codigo IS NOT NULL
                           AND uf = :uf
                         GROUP BY COALESCE(municipio_codigo, 'DESCONHECIDO') \
                         ORDER BY quantidade DESC
                         """

            result = conn.execute(text(query_base), {'uf': uf.upper()})
        else:
            query_base = """
                         SELECT COALESCE(municipio_codigo, 'DESCONHECIDO') as municipio_codigo, \
                                COUNT(*)                                   as quantidade
                         FROM logs
                         WHERE municipio_codigo IS NOT NULL
                         GROUP BY COALESCE(municipio_codigo, 'DESCONHECIDO') \
                         ORDER BY quantidade DESC
                         """

            result = conn.execute(text(query_base))

        municipios = []
        for row in result.fetchmany(top_n):
            municipios.append({
                'municipio_codigo': row[0],
                'quantidade': row[1]
            })

        return municipios

    except Exception as e:
        print(f"Erro ao obter estatísticas por município: {e}")
        return []


def top_erros(conn, uf=None, top_n=20):
    """Encontra os erros mais frequentes"""
    try:
        if uf:
            query = text("""
                         SELECT mensagem,
                                COUNT(*) as quantidade
                         FROM logs
                         WHERE uf = :uf
                           AND (severidade LIKE '%ERRO%' OR severidade LIKE '%ALERTA%' OR
                                severidade IN ('CRITICO', 'FATAL', 'ERROR'))
                           AND mensagem IS NOT NULL
                         GROUP BY mensagem
                         ORDER BY quantidade DESC LIMIT :top_n
                         """)

            result = conn.execute(query, {'uf': uf.upper(), 'top_n': top_n})
        else:
            query = text("""
                         SELECT mensagem,
                                COUNT(*) as quantidade
                         FROM logs
                         WHERE (severidade LIKE '%ERRO%' OR severidade LIKE '%ALERTA%' OR
                                severidade IN ('CRITICO', 'FATAL', 'ERROR'))
                           AND mensagem IS NOT NULL
                         GROUP BY mensagem
                         ORDER BY quantidade DESC LIMIT :top_n
                         """)

            result = conn.execute(query, {'top_n': top_n})

        erros = []
        for row in result:
            erros.append({
                'mensagem': row[0] or "MENSAGEM VAZIA",
                'quantidade': row[1]
            })

        return erros

    except Exception as e:
        print(f"Erro ao obter top erros: {e}")
        return []


def gerar_relatorio_txt(conn, uf=None, saida=None):
    """Gera um relatório em formato de texto"""
    try:
        if saida is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"relatorio_{uf if uf else 'geral'}_{timestamp}.txt"
        else:
            output_file = saida

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write(f"RELATÓRIO DE ESTATÍSTICAS - BRURNA Analytics\n")
            f.write(f"UF: {uf.upper() if uf else 'TODAS'}\n")
            f.write(f"Data de geração: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")

            # Estatísticas gerais
            f.write("1. ESTATÍSTICAS GERAIS\n")
            f.write("-" * 40 + "\n")

            stats_gerais = estatisticas_gerais(conn, uf)
            if stats_gerais:
                f.write(f"Total de registros: {stats_gerais.get('total_registros', 0):,}\n")
                f.write(f"Aplicativos distintos: {stats_gerais.get('aplicativos_distintos', 0)}\n")
                f.write(f"Severidades distintas: {stats_gerais.get('severidades_distintas', 0)}\n")

                if 'municipios_distintos' in stats_gerais:
                    f.write(f"Municípios distintos: {stats_gerais.get('municipios_distintos', 0)}\n")
                if 'zonas_distintas' in stats_gerais:
                    f.write(f"Zonas distintas: {stats_gerais.get('zonas_distintas', 0)}\n")
                if 'secoes_distintas' in stats_gerais:
                    f.write(f"Seções distintas: {stats_gerais.get('secoes_distintas', 0)}\n")

                f.write(
                    f"Período coberto: {stats_gerais.get('data_minima', 'N/A')} a {stats_gerais.get('data_maxima', 'N/A')}\n")
            else:
                f.write("Não foi possível obter estatísticas gerais\n")

            f.write("\n")

            # Por aplicativo
            f.write("2. POR APLICATIVO (TOP 10)\n")
            f.write("-" * 40 + "\n")
            apps = estatisticas_por_aplicativo(conn, uf, top_n=10)
            if apps:
                for app in apps:
                    app_nome = str(app['aplicativo']) if app['aplicativo'] is not None else "DESCONHECIDO"
                    f.write(f"{app_nome:<20} {app['quantidade']:>10,} ({app['porcentagem']:.2f}%)\n")
            else:
                f.write("Nenhum dado de aplicativo disponível\n")
            f.write("\n")

            # Por severidade
            f.write("3. POR SEVERIDADE\n")
            f.write("-" * 40 + "\n")
            sevs = estatisticas_por_severidade(conn, uf)
            if sevs:
                for sev in sevs:
                    sev_nome = str(sev['severidade']) if sev['severidade'] is not None else "DESCONHECIDO"
                    f.write(f"{sev_nome:<10} {sev['quantidade']:>10,} ({sev['porcentagem']:.2f}%)\n")
            else:
                f.write("Nenhum dado de severidade disponível\n")
            f.write("\n")

            # Por hora do dia
            f.write("4. POR HORA DO DIA\n")
            f.write("-" * 40 + "\n")
            horas = estatisticas_por_hora(conn, uf)
            if horas:
                for hora in horas:
                    hora_val = str(hora['hora']) if hora['hora'] is not None else "N/A"
                    f.write(f"{hora_val:<5} {hora['quantidade']:>10,} ({hora['porcentagem']:.2f}%)\n")
            else:
                f.write("Nenhum dado por hora disponível\n")
            f.write("\n")

            # Por município
            municipios = estatisticas_por_municipio(conn, uf, top_n=10)
            if municipios:
                f.write("5. TOP 10 MUNICÍPIOS\n")
                f.write("-" * 40 + "\n")
                for mun in municipios:
                    mun_cod = str(mun['municipio_codigo']) if mun['municipio_codigo'] is not None else "DESCONHECIDO"
                    f.write(f"{mun_cod:<10} {mun['quantidade']:>10,}\n")
                f.write("\n")

            # Erros e alertas
            f.write("6. ERROS E ALERTAS (TOP 20)\n")
            f.write("-" * 40 + "\n")
            erros = top_erros(conn, uf, top_n=20)
            if erros:
                for i, erro in enumerate(erros, 1):
                    mensagem = erro['mensagem']
                    if len(mensagem) > 80:
                        mensagem = mensagem[:77] + "..."
                    f.write(f"{i:2}. {mensagem:<80} (x{erro['quantidade']:,})\n")
            else:
                f.write("Nenhum erro ou alerta encontrado.\n")

            f.write("\n" + "=" * 60 + "\n")
            f.write("Fim do relatório\n")
            f.write("=" * 60 + "\n")

        print(f"✅ Relatório salvo em: {output_file}")
        return output_file

    except Exception as e:
        print(f"❌ Erro ao gerar relatório TXT: {e}")
        raise


def gerar_graficos(conn, uf=None, prefixo=None):
    """Gera gráficos das estatísticas"""
    try:
        if prefixo is None:
            prefixo = f"graficos_{uf if uf else 'geral'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Gráfico 1: Top aplicativos
        apps = estatisticas_por_aplicativo(conn, uf, top_n=10)
        if apps:
            df_apps = pd.DataFrame(apps)
            plt.figure(figsize=(12, 6))
            bars = plt.bar(df_apps['aplicativo'], df_apps['quantidade'])
            plt.title(f'Top 10 Aplicativos - UF {uf.upper() if uf else "Todas"}')
            plt.xlabel('Aplicativo')
            plt.ylabel('Quantidade')

            # Adicionar valores nas barras
            for bar in bars:
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width() / 2., height,
                         f'{int(height):,}', ha='center', va='bottom')

            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            plt.savefig(f'{prefixo}_aplicativos.png', dpi=150)
            plt.close()
            print(f"  ✅ Gráfico de aplicativos salvo")

        # Gráfico 2: Severidade
        sevs = estatisticas_por_severidade(conn, uf)
        if sevs:
            df_sevs = pd.DataFrame(sevs)
            plt.figure(figsize=(10, 8))
            plt.pie(df_sevs['quantidade'], labels=df_sevs['severidade'], autopct='%1.1f%%')
            plt.title(f'Distribuição por Severidade - UF {uf.upper() if uf else "Todas"}')
            plt.tight_layout()
            plt.savefig(f'{prefixo}_severidade.png', dpi=150)
            plt.close()
            print(f"  ✅ Gráfico de severidade salvo")

        # Gráfico 3: Por hora
        horas = estatisticas_por_hora(conn, uf)
        if horas:
            df_horas = pd.DataFrame(horas)
            plt.figure(figsize=(12, 6))
            plt.plot(df_horas['hora'], df_horas['quantidade'], marker='o', linewidth=2)
            plt.title(f'Eventos por Hora do Dia - UF {uf.upper() if uf else "Todas"}')
            plt.xlabel('Hora')
            plt.ylabel('Quantidade de Eventos')
            plt.grid(True, alpha=0.3)
            plt.xticks(range(0, 24))

            # Adicionar valores nos pontos
            for x, y in zip(df_horas['hora'], df_horas['quantidade']):
                plt.text(x, y, f'{int(y):,}', ha='center', va='bottom')

            plt.tight_layout()
            plt.savefig(f'{prefixo}_horas.png', dpi=150)
            plt.close()
            print(f"  ✅ Gráfico por hora salvo")

        # Gráfico 4: Por dia
        dias = estatisticas_por_dia(conn, uf)
        if dias:
            df_dias = pd.DataFrame(dias)
            if not df_dias.empty:
                plt.figure(figsize=(14, 6))
                plt.plot(df_dias['dia'], df_dias['quantidade'], marker='o', linewidth=2)
                plt.title(f'Eventos por Dia - UF {uf.upper() if uf else "Todas"}')
                plt.xlabel('Data')
                plt.ylabel('Quantidade de Eventos')
                plt.grid(True, alpha=0.3)
                plt.xticks(rotation=45, ha='right')
                plt.tight_layout()
                plt.savefig(f'{prefixo}_dias.png', dpi=150)
                plt.close()
                print(f"  ✅ Gráfico por dia salvo")

        print(f"✅ Todos os gráficos salvos com prefixo: {prefixo}")

    except Exception as e:
        print(f"❌ Erro ao gerar gráficos: {e}")
        raise


def main():
    """Função principal"""
    app = typer.Typer(help="Estatísticas do BRURNA Analytics")

    @app.command(name="test-db")
    def test_db():
        """Testa a conexão com o banco de dados"""
        try:
            conn = get_connection()
            result = conn.execute(text("SELECT COUNT(*) FROM logs"))
            total = result.scalar()
            print(f"✅ Conexão bem-sucedida!")
            print(f"Total de registros no banco: {total:,}")

            # Lista UFs disponíveis
            result = conn.execute(text("SELECT DISTINCT uf FROM logs ORDER BY uf"))
            ufs = [row[0] for row in result]
            print(f"UFs disponíveis: {', '.join(ufs)}")

            # Mostra colunas da tabela
            columns = get_table_columns(conn)
            print(f"Colunas na tabela logs: {', '.join(columns)}")

            conn.close()

        except Exception as e:
            print(f"❌ Erro na conexão: {e}")

    @app.command()
    def relatorio(
            uf: Optional[str] = typer.Option(None, help="UF para filtrar (ex: ac, ap, mg)"),
            saida: Optional[str] = typer.Option(None, help="Nome do arquivo de saída"),
            graficos: bool = typer.Option(False, help="Gerar gráficos")
    ):
        """Gera um relatório de estatísticas"""
        try:
            conn = get_connection()

            # Gera relatório em texto
            output_file = gerar_relatorio_txt(conn, uf, saida)

            # Gera gráficos se solicitado
            if graficos:
                # Remove extensão .txt se existir para usar como prefixo
                if output_file.endswith('.txt'):
                    prefixo = output_file[:-4]
                else:
                    prefixo = output_file

                gerar_graficos(conn, uf, prefixo)

            print(f"\n{'=' * 60}")
            print(f"✅ PROCESSO CONCLUÍDO COM SUCESSO!")
            print(f"{'=' * 60}")

            conn.close()

        except Exception as e:
            print(f"❌ Erro ao gerar relatório: {e}")

    @app.command()
    def resumo(
            uf: Optional[str] = typer.Option(None, help="UF para filtrar (ex: ac, ap, mg)")
    ):
        """Mostra um resumo rápido das estatísticas"""
        try:
            conn = get_connection()
            stats = estatisticas_gerais(conn, uf)

            if stats:
                print("=" * 60)
                print(f"RESUMO - UF {uf.upper() if uf else 'TODAS'}")
                print("=" * 60)
                print(f"Total de registros: {stats.get('total_registros', 0):,}")
                print(f"Período coberto: {stats.get('data_minima', 'N/A')} a {stats.get('data_maxima', 'N/A')}")
                print()

                # Top 3 aplicativos
                apps = estatisticas_por_aplicativo(conn, uf, top_n=3)
                if apps:
                    print("Top 3 aplicativos:")
                    for app in apps:
                        app_nome = str(app['aplicativo']) if app['aplicativo'] is not None else "DESCONHECIDO"
                        print(f"  {app_nome}: {app['quantidade']:,} ({app['porcentagem']:.1f}%)")
                    print()

                # Distribuição por severidade
                sevs = estatisticas_por_severidade(conn, uf)
                if sevs:
                    print("Distribuição por severidade:")
                    for sev in sevs:
                        sev_nome = str(sev['severidade']) if sev['severidade'] is not None else "DESCONHECIDO"
                        print(f"  {sev_nome}: {sev['quantidade']:,} ({sev['porcentagem']:.1f}%)")
                    print()
            else:
                print("Não foi possível obter estatísticas.")

            conn.close()

        except Exception as e:
            print(f"❌ Erro ao gerar resumo: {e}")

    @app.command()
    def colunas():
        """Mostra as colunas disponíveis na tabela logs"""
        try:
            conn = get_connection()
            columns = get_table_columns(conn)
            print("Colunas na tabela 'logs':")
            for col in columns:
                print(f"  - {col}")
            conn.close()
        except Exception as e:
            print(f"❌ Erro: {e}")

    app()


if __name__ == "__main__":
    main()