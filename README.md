# Brurna Analytics

Sistema de análise forense de logs eleitorais do TSE com fundamentação jurídica automatizada.

## 📊 Visão Geral

O Brurna Analytics é uma plataforma de auditoria eleitoral que processa logs de urnas eletrônicas, executa 500 hipóteses de análise (temporal, hardware, forense e cruzamento de dados) e gera relatórios técnico-jurídicos fundamentados.

## 🎯 Funcionalidades

- **Ingestão de Dados**: Processamento de arquivos `.logjez` (logs compactados de urnas)
- **Motor Analítico**: 500 hipóteses automatizadas (99.8% de cobertura)
- **Machine Learning**: Detecção de anomalias via Isolation Forest
- **Dashboard Interativo**: Visualização em tempo real (Streamlit)
- **Relatórios Forenses**: Geração automática com formatação ABNT A4
- **Fundamentação Jurídica**: Agente TSE Justice com base legal completa

## 🚀 Quick Start

```bash
# 1. Ativar ambiente virtual
.venv\Scripts\activate

# 2. Executar ingestão de dados
python src/data_ingestion/ingest_logs.py

# 3. Executar análises
python src/analytics/analytical_engine.py

# 4. Iniciar dashboard
streamlit run src/dashboard/app.py

# 5. Gerar relatórios
python src/reports/generator.py
```

## 📁 Estrutura do Projeto

```
brurna-analytics/
├── .agent/                    # Agentes e Skills
│   ├── agents/
│   │   └── tse-justice.md    # Agente de fundamentação jurídica
│   └── skills/
│       └── report-forense-TSE-generation/
├── src/
│   ├── analytics/            # Motor analítico
│   │   ├── analytical_engine.py
│   │   ├── g1_temporal.py
│   │   └── g4_crosscheck.py
│   ├── dashboard/            # Interface Streamlit
│   │   └── app.py
│   ├── data_ingestion/       # Processamento de logs
│   │   └── ingest_logs.py
│   └── reports/              # Geração de relatórios
│       └── generator.py
├── reports/                  # Relatórios gerados (HTML)
└── analysis_results.csv      # Resultados das 500 hipóteses
```

## 🔬 Metodologia

### Grupos de Hipóteses

1. **G1 - Dinâmica Temporal (H001-H125)**: Padrões de votação ao longo do dia
2. **G2 - Hardware/Operacional (H126-H250)**: Funcionamento de componentes
3. **G3 - Forense/Segurança (H251-H375)**: Integridade e assinaturas
4. **G4 - Cruzamento de Dados (H376-H500)**: Machine Learning e correlações

### Tecnologias

- **Backend**: Python 3.11, SQLAlchemy, Pandas
- **Banco de Dados**: PostgreSQL
- **Machine Learning**: scikit-learn 1.8.0 (Isolation Forest)
- **Frontend**: Streamlit, Plotly
- **Relatórios**: HTML com CSS ABNT A4

## 📄 Relatórios

Os relatórios são gerados em `reports/` com:
- Formatação ABNT A4 (margens 3cm/2cm/2cm/3cm)
- Detalhamento completo de anomalias
- Rastreabilidade por urna/seção
- Trechos de logs originais
- Fundamentação jurídica (Res. TSE 23.603/2019)

## 🏛️ Agente TSE Justice

Ministro/Desembargador virtual com:
- Formação: USP, FGV, PUC-SP, Mackenzie, UNICAMP
- Especialização: Direito Eleitoral + Perícia Forense Digital
- 20 casos de uso documentados
- Linguagem técnico-jurídica rigorosa

## 📊 Status Atual

- ✅ **Cobertura**: 99.8% (499/500 hipóteses)
- ✅ **Estados**: AC, AP, RR, TO, SE
- ✅ **Logs Processados**: ~98.000+
- ✅ **Dashboard**: http://localhost:8501

## 🔐 Segurança e Compliance

- ✅ Sigilo do voto preservado (apenas dados agregados)
- ✅ Análises estatísticas como indícios (não provas definitivas)
- ✅ Presunção de lisura do processo eleitoral
- ✅ Conformidade com legislação eleitoral brasileira

## 📚 Documentação

- [Agente TSE Justice](.agent/agents/tse-justice.md)
- [Skill de Relatórios](.agent/skills/report-forense-TSE-generation/SKILL.md)
- [Task List](../.gemini/antigravity/brain/823a5e8b-dcb0-4e8e-84b0-5afb5d3b200b/task.md)

## 🤝 Contribuindo

Este é um projeto de auditoria eleitoral. Contribuições devem seguir:
1. Rigor técnico-científico
2. Fundamentação jurídica
3. Transparência e rastreabilidade
4. Respeito ao sigilo do voto

## 📝 Licença

Uso restrito para fins de auditoria interna e transparência eleitoral.

---

**Desenvolvido com**: Python, PostgreSQL, Streamlit, scikit-learn
**Fundamentação**: Código Eleitoral, CF/88, Resoluções TSE