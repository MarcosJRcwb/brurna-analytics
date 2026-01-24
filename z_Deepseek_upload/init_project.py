# init_project.py
# !/usr/bin/env python3
"""
Script de inicialização do projeto BRURNA Analytics
"""

from pathlib import Path
import sys
import subprocess


def setup_project():
    """Configura o projeto inicialmente"""
    print("🚀 Configurando projeto BRURNA Analytics...")

    # 1. Verifica estrutura de diretórios
    project_root = Path(__file__).parent
    required_dirs = [
        project_root / "data" / "output",
        project_root / "data" / "processed",
        project_root / "logs",
        project_root / "notebooks",
    ]

    for directory in required_dirs:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"✅ Diretório criado/verificado: {directory}")

    # 2. Cria estrutura src se não existir
    src_dir = project_root / "src"
    src_dir.mkdir(exist_ok=True)

    # 3. Cria __init__.py em subdiretórios src
    subdirs = ["analytics", "core", "database", "download", "parser", "utils", "visualization"]
    for subdir in subdirs:
        subdir_path = src_dir / subdir
        subdir_path.mkdir(exist_ok=True)
        init_file = subdir_path / "__init__.py"
        if not init_file.exists():
            init_file.write_text("# " + subdir + " module\n")
            print(f"✅ Criado: {init_file}")

    # 4. Verifica requirements
    requirements_file = project_root / "requirements.txt"
    if requirements_file.exists():
        print(f"📦 Instalando dependências de {requirements_file}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(requirements_file)])
            print("✅ Dependências instaladas com sucesso!")
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Erro ao instalar dependências: {e}")
    else:
        print("⚠️  Arquivo requirements.txt não encontrado")

    print("\n✅ Configuração concluída!")
    print("\n📋 PRÓXIMOS PASSOS:")
    print("1. Configure a senha do banco em config.py")
    print("2. Teste a conexão: python test_db_connection.py")
    print("3. Baixe dados: python main.py download --uf ac --limit 5")
    print("4. Processe dados: python main.py parse --uf ac --limit 3")
    print("5. Analise: python main.py analyze --uf ac --metric temporal")


if __name__ == "__main__":
    setup_project()c