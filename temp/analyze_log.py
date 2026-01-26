#!/usr/bin/env python3
"""
Script de análise rápida para arquivos logd.dat
"""

import sys
from pathlib import Path

# Adiciona src ao path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.append(str(src_path))

from parser.log_parser import TSELogParser


def main():
    """Função principal de análise"""

    # Caminho para o arquivo logd.dat
    log_file = r"C:\Users\marco\Downloads\TSE\data\raw_logs\exemplo\logd.dat"

    # Verifica se o arquivo existe
    if not Path(log_file).exists():
        print(f"❌ Arquivo não encontrado: {log_file}")
        print("Por favor, especifique o caminho correto para o arquivo logd.dat")
        return

    # Cria e executa o parser
    print("🔍 Iniciando análise do log do TSE...")
    parser = TSELogParser(log_file)

    # Parseia o arquivo
    data = parser.parse_file()

    # Gera relatório
    report = parser.generate_report()
    print(report)

    # Exporta dados para CSV
    output_csv = project_root / "data" / "output" / "log_parsed.csv"
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    parser.export_to_csv(str(output_csv))

    # Análise temporal detalhada
    print("\n📊 ANÁLISE TEMPORAL DETALHADA:")
    temporal = parser.analyze_temporal_patterns()

    if temporal.get('periodos_inatividade'):
        print(f"\n⏸️  Períodos de inatividade (>5 minutos):")
        for periodo in temporal['periodos_inatividade'][:5]:  # Mostra apenas os 5 primeiros
            print(f"  • {periodo['inicio']} → {periodo['fim']} "
                  f"({periodo['duracao_segundos']:.0f} segundos)")

    if temporal.get('picos_atividade'):
        print(f"\n📈 Picos de atividade (acima do normal):")
        for pico in temporal['picos_atividade'][:5]:  # Mostra apenas os 5 primeiros
            print(f"  • {pico['timestamp']}: {pico['eventos']} eventos "
                  f"(intensidade: {pico['intensidade']:.1f}x)")

    # Erros e alertas
    errors = parser.find_errors_and_alerts()
    if not errors.empty:
        print(f"\n⚠️  RESUMO DE ERROS E ALERTAS:")
        print(errors[['linha_numero', 'severidade', 'aplicativo', 'mensagem']].head(10).to_string())

    print(f"\n✅ Análise concluída!")
    print(f"   Dados parseados: {len(data):,} linhas")
    print(f"   CSV exportado: {output_csv}")


if __name__ == "__main__":
    main()