# Inventário do Projeto Brurna Analytics
**Data da Análise**: 2026-01-24
**Status**: Ativo / Em Retomada

## 1. Status do Processamento

| UF  | Download | Processado | Notas |
| --- | :---: | :---: | --- |
| **AC** | ✅ (2124 arquivos) | ✅ (79,720 linhas) | Dados completos do 1º turno |
| **SP** | ❌ (0 arquivos) | ❌ | Aguardando processamento |
| **Outros** | ❌ | ❌ | Aguardando |

## 2. Estrutura de Diretórios Atual

### Código Fonte (`src/`)
*   **`src/parser/log_parser.py`**: Parser principal (funcional).
*   **`src/download/downloader.py`**: Módulo de download do TSE.
*   **`src/database`**: Persistência de dados.
*   **`src/analytics`**: Análise de métricas.

### Raiz
*   **`main.py`**: CLI principal (Typer). Comandos: `download`, `parse`, `analyze`, `status`.
*   **`config.py`**: Configurações de caminhos e banco de dados.
*   **`.venv/`**: Ambiente virtual Python (Ativo e com dependências).

### Pastas Temporárias (Para Revisão)
*   **`z_Deepseek_upload/`**: Cópia de backup/upload de arquivos do projeto.
*   **`z_ajustes/`**: Scripts de correção (`fix_parser.py`, etc). Provavelmente já integrados.

## 3. Próximos Passos Recomendados
1.  **Limpeza**: Arquivar ou remover `z_Deepseek_upload` e `z_ajustes`.
2.  **Escala**: Iniciar download/processamento de um estado médio (ex: AL ou AM) antes de SP.
3.  **Análise**: Gerar visões agregadas dos dados do AC para validar métricas.
