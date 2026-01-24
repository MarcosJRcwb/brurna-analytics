# BRURNA Analytics - Processador de Logs TSE

Sistema de análise de logs das urnas eletrônicas do TSE (Tribunal Superior Eleitoral).

## 📊 Status do Projeto

| Estado | Download | Processamento | Linhas | Status |
|--------|:--------:|:-------------:|-------:|--------|
| **AC** | ✅ 2.124 arquivos | ✅ Completo | 79.720 | Validação OK |
| **MG** | ⏳ Pendente | ⏳ Pendente | - | **Próximo alvo** |

> **Estratégia**: Ingestão incremental (download → parse → análise) em lotes de 100 urnas para evitar consumo excessivo de tempo e espaço.

## 🏗️ Arquitetura

```
main.py (CLI)
├── download    → Baixa arquivos .logjez do TSE
├── parse       → Extrai dados dos logs (regex + pandas)
├── analyze     → Gera métricas temporais/severidade
└── status      → Exibe progresso do processamento
```

**Stack Técnica**:
- **Parser**: Regex otimizado + detecção automática de encoding
- **Storage**: Parquet (local) + PostgreSQL (opcional)
- **CLI**: Typer com comandos interativos

## 🚀 Começando

### 1. Ativar Ambiente Virtual
```powershell
# Windows
.venv\Scripts\activate
```

### 2. Comandos Principais

#### Download Incremental (Recomendado para MG)
```powershell
# Baixar apenas 100 seções de MG para teste
python main.py download --uf mg --limit 100

# Processar imediatamente após download
python main.py parse --uf mg --limit 100 --output parquet
```

#### Análise de Dados
```powershell
# Análise temporal
python main.py analyze --uf mg --metric temporal

# Análise por severidade
python main.py analyze --uf mg --metric severidade

# Análise por aplicativo
python main.py analyze --uf mg --metric aplicativo
```

#### Verificar Status
```powershell
python main.py status
```

## 📁 Estrutura de Dados

```
C:\Users\marco\Downloads\TSE\data\
├── raw_logs\
│   ├── ac\          # 2.124 arquivos .logjez (✅ completo)
│   └── mg\          # Pendente
├── processed\
│   ├── ac\
│   │   └── logs_ac.parquet  # 79.720 linhas
│   └── mg\          # Pendente
└── output\
    └── reports\     # Relatórios e gráficos
```

## 🔍 Próximos Passos

1. **Iniciar MG**: `python main.py download --uf mg --limit 100`
2. **Validar Parser**: Verificar se logs de MG seguem o mesmo padrão de AC
3. **Escalar**: Aumentar limite gradualmente (100 → 500 → 1000)
4. **Análise Comparativa**: Comparar padrões entre AC e MG

## 🛠️ Troubleshooting

### Erro de Encoding
O parser detecta automaticamente `utf-8`, `latin-1`, `iso-8859-1`, e `cp1252`. Se falhar, verifique o arquivo manualmente.

### Espaço em Disco
- **AC completo**: ~500MB (raw) + ~50MB (parquet)
- **MG estimado**: ~5GB (raw) + ~500MB (parquet)
- Verifique espaço disponível antes de escalar: `python main.py test`

### Performance
- **Download**: ~2-5 arquivos/segundo (depende da rede TSE)
- **Parse**: ~1000 linhas/segundo por arquivo
- **Lote de 100 urnas**: ~5-10 minutos (download + parse)