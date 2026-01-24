# Brurna Analytics 🗳️ 🇧🇷

![Status](https://img.shields.io/badge/Status-Ativo-success)
![Python](https://img.shields.io/badge/Python-3.13-blue)
![Banco de Dados](https://img.shields.io/badge/PostgreSQL-15-blue)
![Licença](https://img.shields.io/badge/License-MIT-green)
![Privacidade de Dados](https://img.shields.io/badge/LGPD-Conforme-brightgreen)

**Brurna Analytics** é um sistema especializado de alto desempenho para análise forense de Urnas Eletrônicas Brasileiras. Ele processa, agrega e analisa arquivos de log (`logd.dat`) de milhares de máquinas para garantir integridade, detectar anomalias e fornecer insights transparentes sobre o processo eleitoral.

---

## 🚀 Principais Funcionalidades

*   **Motor de Agregação Inteligente**: Converte terabytes de logs brutos em padrões concisos e significativos, reduzindo os requisitos de armazenamento do banco de dados em **99,98%**.
*   **Pipeline de Alto Desempenho**: Utiliza `multiprocessing` para processar milhares de arquivos de log em paralelo, otimizado para sistemas multi-core (testado em CPUs de 32 núcleos).
*   **Detecção Forense de Anomalias**:
    *   **Guarda de Privacidade**: Varredura automática para PII sensível (CPFs, Títulos de Eleitor) para garantir conformidade com a LGPD.
    *   **Verificações de Integridade**: Valida encodings de arquivo (Linux/Windows) para detectar potenciais adulterações.
    *   **Anomalias Operacionais**: Identifica seções com durações de votação incomuns, erros ou atividade fora do horário.
*   **Integração de Dados**: Cruza logs internos das máquinas com resultados eleitorais públicos do TSE (comparecimento, votos nulos, modelos de urna).

---

## 🏗️ Arquitetura e Fluxo

![Arquitetura do Projeto](docs/img/project_structure.jpg)

O sistema é construído sobre uma arquitetura modular projetada para escalabilidade e transparência:

### 1. Ingestão e Análise de Dados
*   **Log Parser**: Um parser robusto que lida com arquivos compactados `.logjez` (7-zip) e extrai conteúdo bruto `logd.dat`.
*   **Normalização de Formato**: Padroniza timestamps e tratamento de encoding (Latin-1/UTF-8).

### 2. Núcleo Analítico
*   **Agregador de Padrões**: Substitui valores dinâmicos (timestamps, caminhos de arquivo) por placeholders para identificar comportamentos recorrentes do sistema.
    *   *Exemplo*: `Erro ao abrir arquivo /dev/sda1` -> `Erro ao abrir arquivo {}`
*   **Métricas Temporais**: Agrega densidade de eventos por hora para visualizar fluxo de votação/tráfego.

### 3. Módulos Forenses
*   **Detector de Anomalias Críticas**: Varredura baseada em Regex para CPFs e padrões de acesso não autorizados.
*   **Detector de Outliers**: Análise estatística (Z-Score/IQR) para sinalizar máquinas que se desviam da norma.

### 4. Armazenamento
*   **PostgreSQL**: Armazena padrões agregados e metadados. Otimizado com restrições únicas para عمليات UPSERT eficientes.

---

## 📊 Status Atual (2026)

```mermaid
gantt
    title Cronograma de Execução Forense
    dateFormat  YYYY-MM-DD
    section Infraestrutura
    Arquitetura de Agregação       :done,    des1, 2026-01-20, 2026-01-22
    Otimização 32-core (V2)        :done,    des2, 2026-01-23, 2026-01-24
    section Piloto (RR + AP)
    Download & Ingestão            :done,    pil1, 2026-01-24, 1d
    Análise Forense                :done,    pil2, 2026-01-24, 1d
    Relatório de Integridade       :done,    pil3, 2026-01-24, 1d
    section Escala (AC, TO, SE)
    Processamento em Massa         :active,  esc1, 2026-01-25, 3d
    Análise Comparativa            :         esc2, after esc1, 2d
    section Segundo Turno
    Ingestão Turno 2               :         t2_1, after esc2, 3d
```

### Progresso por Estado

| Estado | Status | Seções | Anomalias |
| :--- | :---: | :---: | :---: |
| **Amapá (AP)** | ![Concluído](https://img.shields.io/badge/CONCLUÍDO-brightgreen?style=for-the-badge) | 1.740 | 0 |
| **Roraima (RR)** | ![Concluído](https://img.shields.io/badge/CONCLUÍDO-brightgreen?style=for-the-badge) | 1.268 | 0 |
| **Acre (AC)** | ![Planejado](https://img.shields.io/badge/PLANEJADO-blue?style=for-the-badge) | ~2.100 | - |
| **Tocantins (TO)** | ![Planejado](https://img.shields.io/badge/PLANEJADO-blue?style=for-the-badge) | ~4.000 | - |

**Última Conquista**:
Processamento bem-sucedido de 100% de Roraima e Amapá usando o novo Pipeline V2. O tamanho do banco de dados para esses estados é inferior a 50MB (agregado), provando a eficiência do motor de reconhecimento de padrões.

---

## 🛠️ Instalação e Uso

1.  **Clonar o repositório**:
    ```bash
    git clone https://github.com/MarcosJRcwb/brurna-analytics.git
    cd brurna-analytics
    ```

2.  **Configurar ambiente**:
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # Linux/Mac
    .venv\Scripts\activate     # Windows
    pip install -r requirements.txt
    ```

3.  **Configurar Credenciais**:
    Crie um arquivo `.env` com sua conexão de banco de dados:
    ```ini
    DATABASE_URL=postgresql://usuario:senha@host:porta/nomedobanco
    ```

4.  **Executar Pipeline**:
    ```bash
    # Baixar logs de um estado
    python main.py download --uf rr

    # Processar logs em lote (Otimizado V2)
    python batch_process.py --uf rr --workers 24
    ```

5.  **Executar Análise Forense**:
    ```bash
    python src/analytics/critical_anomaly_detector.py --dir caminho/para/logs
    ```

---

## 🤝 Contribuição

Contribuições são bem-vindas! Por favor, certifique-se de que quaisquer alterações de código mantenham a estrita adesão do projeto aos padrões de privacidade da LGPD.

## 📄 Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo LICENSE para detalhes.