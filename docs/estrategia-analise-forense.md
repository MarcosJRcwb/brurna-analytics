# Estratégia de Análise Forense Expandida

**Objetivo**: Análise forense completa dos logs eleitorais cruzando com dados públicos do TSE para identificar anomalias, padrões suspeitos e validar integridade do processo eleitoral.

---

## 🎯 Variáveis Críticas para Análise

### 1. Modelo da Urna (CRÍTICO)

**Por que é importante**:
- Diferentes modelos podem ter comportamentos distintos
- Bugs específicos de modelo podem causar anomalias
- Permite identificar se problemas são sistêmicos ou isolados

**Modelos Conhecidos** (Brasil):
- UE2020
- UE2015
- UE2013
- UE2011
- UE2010
- UE2009

**Análises Planejadas**:
1. Taxa de erros por modelo
2. Duração média de votação por modelo
3. Uso de biometria por modelo
4. Comparecimento vs. modelo de urna

### 2. Localização Geográfica

**Variáveis**:
- Estado (UF)
- Município
- Zona Eleitoral
- Seção

**Análises**:
- Padrões regionais
- Outliers geográficos
- Comparação urbano vs rural

### 3. Métricas de Votação

**Do TSE (Dados Públicos)**:
- Quantidade de aptos
- Comparecimento
- Abstenção
- Votos válidos/nulos/brancos

**Dos Logs**:
- Total de eventos
- Duração da votação
- Erros técnicos
- Uso de biometria

### 4. Métricas Temporais

- Hora de início/fim
- Picos de atividade
- Períodos de inatividade

---

## 📊 Datasets do TSE a Integrar

### Dataset 1: Votação por Seção
**URL**: `https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_secao/votacao_secao_2022_{UF}.zip`

**Colunas Relevantes**:
- SG_UF, CD_MUNICIPIO, NR_ZONA, NR_SECAO
- NR_TURNO
- QT_APTOS
- QT_COMPARECIMENTO
- QT_ABSTENCOES
- QT_VOTOS_NOMINAIS
- QT_VOTOS_BRANCOS
- QT_VOTOS_NULOS

**Uso**: Cruzar com logs para correlacionar eventos técnicos com resultados

---

### Dataset 2: Detalhe de Votação por Seção
**URL**: `https://cdn.tse.jus.br/estatistica/sead/odsele/detalhe_votacao_secao/detalhe_votacao_secao_2022.zip`

**Colunas Relevantes**:
- **DS_MODELO_URNA** ⭐ (CRÍTICO)
- SG_UF, CD_MUNICIPIO, NR_ZONA, NR_SECAO
- QT_APTOS
- QT_COMPARECIMENTO

**Uso**: Análise por modelo de urna

**ATENÇÃO**: Arquivo nacional (>1GB), processar em chunks

---

### Dataset 3: Votação por Candidato/Município/Zona
**URL**: `https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_candidato_munzona/votacao_candidato_munzona_2022.zip`

**Uso**: Análise de padrões de votação por região

---

## 🔬 Análises Planejadas

### Análise 1: Anomalias por Modelo de Urna

**Hipótese**: Modelos mais antigos têm mais erros técnicos

**Método**:
1. Agrupar seções por modelo de urna
2. Calcular estatísticas:
   - Taxa de erros (erros / total_eventos)
   - Duração média
   - Uso de biometria
3. Identificar modelos outliers

**Output Esperado**:
```
MODELO    | SEÇÕES | ERROS (%) | DURAÇÃO (h) | BIOMETRIA (%)
----------|--------|-----------|-------------|---------------
UE2020    | 5.000  | 0,3%      | 10,2        | 95%
UE2015    | 8.000  | 0,5%      | 10,5        | 92%
UE2013    | 3.000  | 1,2%      | 11,0        | 88%  ⚠️ OUTLIER
UE2011    | 1.500  | 2,5%      | 12,5        | 80%  🔴 CRÍTICO
```

---

### Análise 2: Correlação Erros × Votos Nulos

**Hipótese**: Seções com mais erros técnicos têm mais votos nulos

**Método**:
1. Cruzar logs (erros) com TSE (votos nulos)
2. Calcular correlação de Pearson
3. Identificar seções com alta correlação

**Interpretação**:
- Correlação alta (>0.7): Erros técnicos podem estar causando votos nulos
- Correlação baixa (<0.3): Votos nulos são independentes de erros

---

### Análise 3: Outliers Geográficos

**Método**:
1. Agrupar seções por município
2. Calcular média e desvio padrão por município
3. Identificar seções com Z-score > 3

**Casos Suspeitos**:
- Seção com 10x mais eventos que a média do município
- Seção com duração 3x maior que a média
- Seção com 100% de erros (possível falha total)

---

### Análise 4: Padrões Temporais Anômalos

**Casos a Detectar**:
1. **Votação fora do horário**: Eventos após 17h (horário de fechamento)
2. **Picos noturnos**: Atividade entre 18h-6h (suspeito)
3. **Duração excessiva**: Seção aberta >15 horas

---

### Análise 5: Biometria × Comparecimento

**Hipótese**: Seções com mais uso de biometria têm maior comparecimento

**Método**:
1. Calcular taxa de uso de biometria (verificações / aptos)
2. Cruzar com taxa de comparecimento do TSE
3. Calcular correlação

**Interpretação**:
- Correlação positiva: Biometria pode reduzir abstenção
- Correlação negativa: Biometria pode estar atrasando votação

---

## 🚨 Critérios de Alerta

### 🔴 Alerta Crítico (Investigação Imediata)

1. **Taxa de erros > 5%**
2. **Duração > 15 horas**
3. **Votação fora do horário (após 17h)**
4. **Seção com 0 eventos** (possível falha de log)
5. **Modelo de urna com >10% de erros**

### ⚠️ Alerta Moderado (Monitoramento)

1. **Taxa de erros entre 1-5%**
2. **Duração entre 12-15 horas**
3. **Uso de biometria < 50%** (abaixo da média)
4. **Outlier geográfico** (Z-score > 3)

### ✅ Normal

1. **Taxa de erros < 1%**
2. **Duração 8-12 horas**
3. **Uso de biometria > 80%**
4. **Dentro de 2σ da média**

---

## 📈 Visualizações Planejadas

### 1. Mapa de Calor: Erros por Região
- Eixo X: Municípios
- Eixo Y: Taxa de erros
- Cor: Intensidade (vermelho = mais erros)

### 2. Gráfico de Dispersão: Modelo × Erros
- Eixo X: Modelo de urna
- Eixo Y: Taxa de erros
- Tamanho do ponto: Número de seções

### 3. Linha do Tempo: Eventos por Hora
- Eixo X: Hora do dia (0-23)
- Eixo Y: Número de eventos
- Linhas: Por modelo de urna

### 4. Box Plot: Duração por Modelo
- Mostra mediana, quartis e outliers
- Identifica modelos com comportamento anômalo

---

## 🔧 Pipeline de Processamento

### Etapa 1: Ingestão de Dados ✅ EM ANDAMENTO
- [x] Processar 400 seções de AC
- [ ] Processar 400 seções de MG
- [ ] Baixar dados públicos do TSE

### Etapa 2: Integração
- [ ] Cruzar logs × votação por seção
- [ ] Adicionar modelo de urna aos metadados
- [ ] Calcular métricas derivadas

### Etapa 3: Análise
- [ ] Detectar outliers (Z-score, IQR)
- [ ] Calcular correlações
- [ ] Agrupar por modelo de urna
- [ ] Identificar padrões geográficos

### Etapa 4: Relatório
- [ ] Gerar relatório forense expandido
- [ ] Criar visualizações
- [ ] Listar alertas críticos
- [ ] Recomendar ações

---

## 💾 Estrutura de Dados Integrada

### Tabela: `integrated_analysis`

```sql
CREATE TABLE integrated_analysis (
    -- Identificação
    uf VARCHAR(2),
    municipio_codigo VARCHAR(5),
    zona VARCHAR(4),
    secao VARCHAR(4),
    
    -- Modelo de urna (NOVO)
    modelo_urna VARCHAR(20),
    
    -- Logs
    total_eventos INT,
    duracao_segundos INT,
    taxa_erros FLOAT,
    uso_biometria FLOAT,
    
    -- TSE
    qt_aptos INT,
    qt_comparecimento INT,
    qt_abstencoes INT,
    qt_votos_nulos INT,
    
    -- Métricas derivadas
    taxa_comparecimento FLOAT,
    taxa_abstencao FLOAT,
    taxa_nulos FLOAT,
    
    -- Outliers
    is_outlier_eventos BOOLEAN,
    is_outlier_duracao BOOLEAN,
    is_outlier_erros BOOLEAN,
    z_score_eventos FLOAT,
    
    -- Alertas
    nivel_alerta VARCHAR(20)  -- 'CRITICO', 'MODERADO', 'NORMAL'
);
```

---

## 🎯 Métricas de Sucesso

| Métrica | Target | Status |
|---------|--------|--------|
| **Seções processadas** | 800 (400 AC + 400 MG) | 🔄 Em andamento |
| **Dados TSE integrados** | 100% das seções | ⏳ Pendente |
| **Outliers detectados** | >10 casos | ⏳ Pendente |
| **Modelos de urna analisados** | Todos | ⏳ Pendente |
| **Correlações calculadas** | >5 análises | ⏳ Pendente |
| **Alertas gerados** | Automático | ⏳ Pendente |

---

## 📚 Próximos Passos Imediatos

1. ⏳ **Aguardar conclusão** do processamento de 400 AC (em andamento)
2. 🔄 **Baixar dados TSE** para AC (votação_secao + detalhe_votacao_secao)
3. 🔄 **Integrar dados** (logs × TSE)
4. 🔄 **Analisar por modelo de urna**
5. 🔄 **Gerar relatório expandido** com alertas

---

**Status Geral**: 🟢 No prazo | 🔄 Processamento em andamento
