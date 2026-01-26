# Brurna Analytics

**Sistema de Auditoria Forense e Inteligência Eleitoral em Larga Escala**

> 🗳️ **Status**: Piloto Completo (99,9% Ingestão) | 🔎 **Motor Analítico**: Ativo (500 Hipóteses)

---

## 📊 Visão Geral

O **Brurna Analytics** é uma plataforma avançada de inteligência eleitoral desenvolvida para auditar, analisar e visualizar logs de urnas eletrônicas brasileiras. O sistema processa arquivos brutos (`.logjez`), extrai metadados, executa testes forenses automatizados e gera relatórios fundamentados juridicamente.

### 🎯 Objetivos
1. **Auditoria Técnica**: Verificar integridade, hardware e padrões temporais.
2. **Fundamentação Jurídica**: Produzir relatórios alinhados com a legislação do TSE.
3. **Transparência**: Visualização clara de dados complexos para auditoria pública.

---

## 📚 Documentação do Projeto

A documentação detalhada foi migrada para a pasta `docs/`. Recomendamos a leitura na seguinte ordem:

### 1. Metodologia Científica
- **[Plano de Análise - 500 Hipóteses](docs/plano_analise_500_final.md)**
  - Detalhamento completo dos 4 grupos de análise (Temporal, Hardware, Forense, Cruzamento).
  - Explicação teórica de cada teste.
  - Critérios de aceitação (PASS/FAIL).

### 2. Relatórios de Resultados
- **[Relatório Piloto Completo (Nacional)](docs/relatorio_piloto_completo.md)**
  - Análise consolidada dos 5 estados (AC, AP, RR, TO, SE).
  - Estrutura hierárquica (Nacional → Regional → UF).
  - Parecer jurídico do agente **TSE Justice**.

### 3. Implementações Futuras
- **[Validação de Hash Chain (Blockchain)](docs/implementation_plan_hash_validation.md)**
  - Plano para validação criptográfica da integridade dos logs.
  - Implementação do algoritmo SipHash.

---

## 🏗️ Arquitetura do Sistema

```bash
brurna-analytics/
├── .agent/                    # Inteligência Artificial (Agentes + Skills)
├── src/
│   ├── analytics/            # Motor Analítico (500 Hipóteses)
│   ├── dashboard/            # Interface Visual (Streamlit)
│   ├── data_ingestion/       # ETL de Logs (.logjez)
│   └── reports/              # Gerador de Relatórios (ABNT)
├── docs/                     # 📚 Documentação Técnica (NOVOS ARQUIVOS)
├── reports/                  # Saída dos Relatórios Gerados
│   ├── html/                # Relatórios HTML
│   └── por_hipotese/        # Resultados Individuais
└── analysis_results.csv      # Dataset final das hipóteses
```

---

## 🚀 Guia de Uso

### Pré-requisitos
- Python 3.11+
- PostgreSQL
- Bibliotecas: `pip install -r requirements.txt`

### Comandos Principais

1. **Ingestão de Dados**
   ```bash
   python src/data_ingestion/ingest_logs.py
   ```

2. **Executar Todas as Análises**
   ```bash
   python src/analytics/analytical_engine.py
   ```

3. **Executar Hipótese Individual**
   ```bash
   python run_hypothesis.py H001
   python run_hypothesis.py H501 --save
   ```

4. **Iniciar Dashboard**
   ```bash
   streamlit run src/dashboard/app.py
   ```

---

## 🏛️ Agentes e Governança

O projeto é gerenciado por agentes especializados definidos em `.agent/`:

- **TSE Justice**: Ministro virtual para fundamentação jurídica.
- **Report Generator**: Skill de geração de relatórios forenses.
- **Backend Specialist**: Arquitetura e performance.

---

**Desenvolvido por**: MarcosJRcwb | **Licença**: Uso restrito para auditoria.