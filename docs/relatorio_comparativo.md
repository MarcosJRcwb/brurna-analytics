# ⚔️ Relatório Comparativo: Amapá vs Roraima

**Objetivo**: Analisar similaridades, diferenças e padrões operacionais entre os dois estados piloto para validar a consistência do processo eleitoral em regiões distintas.

---

## 📊 1. Volume de Dados

**Amapá (AP)** vs **Roraima (RR)**

![Comparação de Volume](img/comparison_volume.png)

- **Análise**: O volume de eventos é proporcional ao número de seções e eleitores. Amapá (1.740 seções) gerou significativamente mais logs que Roraima (1.268 seções), mantendo uma média de eventos por urna consistente (~2.000 a 3.000 eventos/urna).
- **Conclusão**: A "densidade de log" (eventos por eleitor) é estável entre os estados, indicando que o software da urna (UE20xx) se comporta de maneira idêntica independente da geografia.

---

## ⏳ 2. Fluxo Temporal de Votação

**Densidade de Eventos por Hora do Dia**

![Fluxo Temporal](img/comparison_temporal.png)

- **Padrão Encontrado**: Ambos os estados exibem a clássica "Curva de Gauss Eleitoral":
    1.  **Pico Inicial (07h-08h)**: Abertura das urnas e zerésima (alto volume técnico).
    2.  **Platô da Manhã (08h-12h)**: Fluxo intenso de eleitores.
    3.  **Queda do Almoço (12h-13h)**: Leve redução no fluxo.
    4.  **Pico da Tarde e Encerramento (16h-17h)**: Corrida final e procedimentos de encerramento.
- **Anomalias**: Nenhuma divergência temporal significativa foi observada. Não houve picos fora do horário de votação (ex: madrugada).

---

## ⏱️ 3. Performance e Duração

**Tempo de Operação da Urna (Ligada até Desligada)**

![Duração das Seções](img/comparison_duration.png)

- **Média**: A maioria das seções operou por aproximadamente 10 a 11 horas (abertura às 07h, encerramento às 17h + transmissão).
- **Outliers**: Pontos fora da curva (seções com 12h+) indicam filas no encerramento, o que é esperado em zonas mais densas, mas não indicam fraude técnica.
- **Comparação**: Roraima e Amapá apresentam medianas de tempo quase idênticas, reforçando a padronização dos procedimentos dos mesários.

---

## 🏆 Conclusão Final

A comparação cruzada entre **RR** e **AP** comprova a **estabilidade sistêmica** das urnas eletrônicas.
1.  O software gera logs com o mesmo padrão de densidade.
2.  O comportamento temporal é idêntico e previsível.
3.  A duração das seções segue as normas do TSE.

**Veredito**: O sistema de votação demonstrou **alta confiabilidade e reprodutibilidade** nos dois cenários de teste.
