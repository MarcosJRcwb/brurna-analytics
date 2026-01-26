# Plano de Implementação: Validação de Hash Chain + Monitoramento Real-time

## I. Problemas Identificados

### 1. Loop Duplicado na Ingestão ❌
**Linhas 154-162** do `ingest_logs.py` contêm código morto que reprocessa os últimos 50 arquivos de SE.

**Impacto**:
- Processo "trava" reprocessando arquivos já inseridos
- Tempo desperdiçado (~30min extras)
- Confusão no progresso (mostra "46/50" quando deveria estar em "1000/1000")

**Solução**: Remover linhas 151-162 (código legacy de teste)

### 2. Limite de 200 Arquivos/Estado
**Contexto**: Não é "processamento excessivo" - foi limite de segurança para piloto.

**Realidade**:
- Total no disco: 14.587 arquivos
- Limite atual: 1.000 arquivos (200 × 5 estados)
- Processamento: ~13h para 1.000 arquivos
- **Tempo para 14.587**: ~7,5 dias contínuos

**Decisão**: Manter limite de 200/estado para análise piloto. Aumentar apenas se necessário.

### 3. Ausência de Monitoramento Real-time
**Problema**: Usuário não vê progresso em tempo real.

**Solução**: Implementar dashboard de ingestão com:
- Progress bar por estado
- Taxa de processamento (arquivos/min)
- ETA por estado
- Logs em tempo real (últimos 10)

## II. Descoberta Crítica: Hash Chain (Blockchain-like)

### Análise do Formato
```
22/09/2022 09:53:32	INFO	67305985	LOGD	Início das operações do logd	DB7EE73F0522CA89
22/09/2022 09:53:32	INFO	67305985	LOGD	Urna ligada em 22/09/2022 às 09:52:18	FCF600E38FEA52F5
```

**Última coluna**: Hash hexadecimal (16 caracteres = 64 bits)

**Hipótese**: SipHash-2-4 (algoritmo usado pelo TSE)
- Entrada: Linha anterior completa (ou campos específicos)
- Saída: 64-bit hash
- Propósito: Cadeia de integridade (blockchain-like)

### Validação Proposta

#### Hipótese H501: Validação de Hash Chain
**Descrição**: Cada linha de log contém hash da linha anterior, formando cadeia de integridade.

**Metodologia**:
1. Extrair hash da última coluna
2. Calcular SipHash da linha anterior
3. Comparar hash calculado vs. hash registrado
4. Detectar quebras na cadeia (possível adulteração)

**Implementação**:
```python
import siphash

def validate_hash_chain(log_lines):
    """
    Valida cadeia de hashes em logs de urna.
    Retorna: (válido, índice_quebra, hash_esperado, hash_encontrado)
    """
    key = b'\x00' * 16  # Chave padrão (descobrir a real)
    
    for i in range(1, len(log_lines)):
        prev_line = log_lines[i-1]
        curr_hash = extract_hash(log_lines[i])
        
        # Calcular hash da linha anterior
        expected_hash = siphash.SipHash_2_4(key, prev_line.encode()).hexdigest()
        
        if expected_hash != curr_hash:
            return (False, i, expected_hash, curr_hash)
    
    return (True, -1, None, None)
```

**Desafios**:
1. **Chave secreta**: TSE pode usar chave específica (não pública)
2. **Formato de entrada**: Linha completa? Apenas campos específicos?
3. **Algoritmo exato**: SipHash-2-4? Outra variante?

**Estratégia de Descoberta**:
1. Testar com chave zero (`\x00` × 16)
2. Testar variações de entrada (linha completa, sem timestamp, etc.)
3. Reverter engenharia com amostra conhecida

## III. Proposta de Implementação

### Fase 1: Correção Urgente (Agora)
- [x] Identificar loop duplicado
- [ ] Remover linhas 151-162 de `ingest_logs.py`
- [ ] Reiniciar processo (ou aguardar conclusão do loop atual)

### Fase 2: Monitoramento Real-time (2h)
- [ ] Criar `src/dashboard/ingestion_monitor.py`
- [ ] Streamlit page com:
  - Progress por estado (5 barras)
  - Logs em tempo real (tail -f like)
  - Estatísticas (taxa, ETA, erros)
- [ ] Integrar com processo via arquivo de status

### Fase 3: Hash Chain Validation (4h)
- [ ] Criar `src/analytics/h501_hash_chain.py`
- [ ] Implementar extração de hash da última coluna
- [ ] Testar SipHash com diferentes chaves/formatos
- [ ] Adicionar ao `analytical_engine.py`
- [ ] Documentar em `plano_analise_500_final.md`

### Fase 4: Relatório de Integridade (2h)
- [ ] Adicionar seção "Integridade Criptográfica" nos relatórios
- [ ] Mostrar % de logs com hash válido
- [ ] Destacar quebras de cadeia (se houver)
- [ ] Fundamentação jurídica via TSE Justice

## IV. Decisões Pendentes

### 1. Processar Todos os 14.587 Arquivos?
**Prós**:
- Análise completa de todos os estados
- Maior confiabilidade estatística

**Contras**:
- ~7,5 dias de processamento
- ~6 GB de banco de dados (estimado)
- Custo computacional

**Recomendação**: Manter 200/estado para piloto. Expandir apenas se análise exigir.

### 2. Implementar Monitoramento Agora ou Após Conclusão?
**Opções**:
- **Agora**: Interromper ingestão, implementar, reiniciar
- **Depois**: Aguardar conclusão (~30min), implementar para próxima rodada

**Recomendação**: Aguardar conclusão (já está em 99,9%).

### 3. Prioridade da Hash Chain Validation
**Importância**: ALTA
- Adiciona camada crítica de validação forense
- Diferencial técnico-jurídico
- Prova de integridade dos logs

**Urgência**: MÉDIA
- Não bloqueia análises atuais
- Pode ser implementado em paralelo

## V. Próximos Passos Imediatos

1. **Aguardar conclusão** do loop duplicado (~20-30min)
2. **Corrigir** `ingest_logs.py` (remover linhas 151-162)
3. **Implementar** H501 (Hash Chain Validation)
4. **Adicionar** ao relatório de integridade
5. **Documentar** descoberta no README

---

**Status**: Aguardando aprovação do usuário
**Prioridade**: P0 (Correção de bug) + P1 (Hash validation)
