# Protocolo de Inteligência Avançada: 500 Hipóteses (Restaurado e Estruturado)

Este documento recupera as 500 hipóteses originais detalhadas (sem placeholders genéricos) e as organiza pela estrutura de complexidade solicitada para execução em lotes.

---

## 🎯 1. Dinâmica Temporal (Hipóteses H001 - H125)

### 1.1 Complexidade Baixa (Métricas Diretas)
*Dados já disponíveis na tabela `temporal_metrics`.*

- **H001**: A velocidade média de votos por hora (VPH) no período matutino (08h-12h) é estatisticamente superior ao vespertino (13h-17h).
- **H002**: Seções com mais de 400 eleitores apresentam VPH > 60 nos últimos 60 minutos de votação.
- **H003**: A variância do tempo entre votos (Inter-arrival time) é menor em seções de capitais vs. interior.
- **H004**: Existe correlação positiva entre a densidade demográfica do município e a taxa de votos por minuto no pico.
- **H005**: O intervalo de almoço (12h-13h) apresenta queda de volume superior a 40% em relação à média do dia.
- **H006**: Seções rurais apresentam início de votação (primeiro voto) mais tardio que seções urbanas.
- **H007**: A taxa de votos nulos aumenta conforme a hora do dia avança (fadiga do eleitor).
- **H008**: Seções com biometria habilitada têm VPH 15% menor que seções sem biometria.
- **H009**: O tempo médio de votação (duração da sessão do eleitor) é constante independente do modelo da urna.
- **H010**: O desvio padrão dos timestamps de log é uniforme entre seções do mesmo local de votação.
- **H011**: Picos de votação acima de 3 sigma (Desvio Padrão) ocorrem apenas e exclusivamente em horários de pico conhecidos (10h-11h).
- **H012**: Não existem votos registrados com timestamp futuro (Clock Drift > 0).
- **H013**: Não existem votos registrados com timestamp anterior à abertura da urna (08:00 oficial).
- **H014**: O tempo de encerramento da urna (comando de fim) ocorre em média 30 minutos após o último voto.
- **H015**: Seções com filas reportadas (via app e-Título, se dados disponíveis) correlacionam com VPH máximo sustentado.
- **H016**: A distribuição de votos por minuto segue uma Distribuição de Poisson em 95% das seções.
- **H017**: Seções com comparecimento > 90% não apresentam "buracos" (gaps) de votação maiores que 10 minutos.
- **H018**: O tempo de inicialização (Boot) da urna não influencia o horário do primeiro voto.
- **H019**: A frequência de eventos de sistema (não-voto) é constante ao longo do dia.
- **H020**: O volume de logs de erro temporal é menor que 0.1% do total de logs.
- **H021**: A correlação entre o horário de pico de votos e a longitude da cidade é significativa (fuso horário solar).
- **H022**: Seções em cidades universitárias têm curva de votação deslocada para a tarde.
- **H023**: Dias de chuva (dados metrológicos cruzados) deslocam a curva de votação para horários de estiagem.
- **H024**: O tempo de habilitação do eleitor pelo mesário é constante ao longo do dia.
- **H025**: A relação Votos/Hora é linear em seções com menos de 100 eleitores.
- **H026**: O "rush final" (16:30-17:00) representa mais de 10% dos votos totais em grandes centros.
- **H027**: Seções com maior taxa de abstenção têm curva de votação mais achatada (curtose menor).
- **H028**: O tempo médio entre a habilitação do mesário e o voto do eleitor é menor em urnas modelo 2020.
- **H029**: Não há duplicidade de timestamps de voto na mesma urna (colisão de hash temporal).
- **H030**: A sequência de logs de votação é monotonicamente crescente em 100% dos casos.
- **H031**: O tempo de impressão da zerésima não impacta o início da votação.
- **H032**: Seções com troca de bateria registram "buracos" temporais compatíveis com a manutenção.
- **H033**: A taxa de eventos por segundo no log não excede a capacidade de gravação do hardware.
- **H034**: Logs noturnos (pós-encerramento) são restritos a eventos de sistema e transmissão.
- **H035**: O tempo de geração do BU é proporcional ao número de votos computados.
- **H036**: A latência de gravação de log não aumenta com o tempo de uso contínuo (fragmentação).
- **H037**: Seções com 2º turno têm VPH maior que no 1º turno (menos cargos para votar).
- **H038**: A média móvel de 15 minutos de votos é estável em seções padronizadas.
- **H039**: O tempo de "urna ociosa" (sem eleitor) é maior em bairros de alta renda.
- **H040**: A duração total da carga da urna (ligada) não excede 14 horas em condições normais.

### 1.2 Complexidade Média (Inferências e Correlações)
*Requer cálculo de gaps, sessões e joins simples.*

- **H041**: O tempo de resposta da interface gráfica não degrada ao longo do dia logado.
- **H042**: Eventos de "Voto Confirmado" têm duração de processamento uniforme.
- **H043**: O intervalo entre "Habilitação" e "Voto" não é inferior a 3 segundos (tempo físico mínimo).
- **H044**: Seções com muitos idosos (demografia) têm VPH 20% menor.
- **H045**: A taxa de eventos de "Tecla Pressionada" é compatível com o número de dígitos dos cargos.
- **H046**: Não há registro de votos durante períodos de reinicialização da urna.
- **H047**: O tempo de auditoria pós-votação correlaciona com a complexidade do pleito.
- **H048**: A data de criação do arquivo de log corresponde ao dia da eleição.
- **H049**: O fuso horário registrado no log corresponde ao fuso da UF.
- **H050**: A sincronização de horário (NTP ou similar, se houver) não causa saltos negativos no tempo.
- **H051**: O tempo de visualização da foto do candidato é maior para cargos majoritários.
- **H052**: A taxa de correção de voto (tecla CORRIGE) é maior no período da manhã.
- **H053**: O tempo médio de voto para Governador é maior que para Senador.
- **H054**: Seções com acessibilidade têm tempos de ciclo de voto 30% maiores.
- **H055**: O uso de fones de ouvido (acessibilidade) correlaciona com maior tempo de voto.
- **H056**: A taxa de votos brancos é constante temporalmente.
- **H057**: Picos de votação não coincidem com picos de temperatura ambiente da urna.
- **H058**: A distribuição de chegada dos eleitores é Bimodal (pico manhã e pico tarde).
- **H059**: Seções em áreas comerciais têm pico acentuado na hora do almoço.
- **H060**: A variabilidade do VPH é baixa em seções com fila constante.
- **H061**: O tempo de "Voto em Branco" é significativamente menor que "Voto Nominal".
- **H062**: O tempo de "Voto de Legenda" é menor que "Voto Nominal Completo".
- **H063**: A densidade de logs por voto é constante (não há verbose logging ativado aleatoriamente).
- **H064**: O tempo de recuperação após falha de energia é menor que 5 minutos.
- **H065**: A sequência de eventos de inicialização é idêntica em 99% das urnas.
- **H066**: O tempo de validação de assinaturas digitais é constante.
- **H067**: Não há eventos de log "Órfãos" (sem thread/processo pai identificado).
- **H068**: A rotação de logs (se houver) não perde eventos na transição.
- **H069**: O tempo de carga da bateria interna correlaciona com o tempo de operação na bateria externa.
- **H070**: Urnas que trocaram bateria não apresentam reset de relógio (RTC).
- **H071**: O tempo de resposta do touchscreen não varia com a temperatura da CPU.
- **H072**: A taxa de erro de leitura biométrica é maior nas primeiras horas (dedos frios/secos).
- **H073**: O tempo de identificação por títulonet é maior que por biometria.
- **H074**: A taxa de substituição de urnas é maior no período da tarde (falhas acumuladas).
- **H075**: Seções agregadas (junção de seções) têm VPH proporcionalmente maior.
- **H076**: O tempo de espera na fila (inferido por gaps) aumenta linearmente com o comparecimento.
- **H077**: Não há correlação entre a velocidade do voto e o partido escolhido (voto rápido x demorado).
- **H078**: O tempo de permanência na cabine é menor para eleitores jovens (16-24 anos).
- **H079**: A taxa de toques inválidos na tela é maior em urnas antigas (calibração).
- **H080**: O tempo de exibição da mensagem "FIM" é constante.

### 1.3 Complexidade Alta (Anomalias Sutis e Externas)
*Requer cruzamento com dados climáticos, geográficos e processamento pesado.*

- **H081**: A gravação em mídia redundante (MR) ocorre sincronicamente com a mídia interna.
- **H082**: Não há logs de "Debug" em urnas de produção.
- **H083**: O tempo total de log ativo corresponde exatamente ao período de votação legal.
- **H084**: Seções em fronteiras de fuso horário respeitam o horário local de fechamento.
- **H085**: A taxa de eventos de "Bateria Fraca" aumenta exponencialmente após 10h de uso.
- **H086**: O tempo de boot é menor em urnas que não precisaram de carga inicial.
- **H087**: A verificação de integridade inicial (hash check) leva o mesmo tempo em todos os modelos.
- **H088**: Não há eventos de mouse ou teclado externo registrados.
- **H089**: A taxa de atualização da tela do mesário é síncrona com a ação do eleitor.
- **H090**: O tempo de transmissão do BU (se logado) depende da qualidade da rede local.
- **H091**: Seções offline não apresentam logs de tentativa de conexão.
- **H092**: O número de tentativas de biometria por eleitor segue uma distribuição normal.
- **H093**: Eleitores com 4 tentativas de biometria falhas recorrem à habilitação manual em 100% dos casos.
- **H094**: O tempo de habilitação manual é 3x maior que a biométrica.
- **H095**: A taxa de falha biométrica não aumenta no fim do dia (sujeira no sensor).
- **H096**: O tempo de limpeza do sensor biométrico (se registrado) impacta o VPH.
- **H097**: A taxa de votos nulos não se correlaciona com a velocidade de votação.
- **H098**: Seções com muitos votos de legenda têm tempo médio de voto menor.
- **H099**: A distribuição temporal de votos nulos é uniforme.
- **H100**: O tempo de encerramento não é afetado pelo número de votos nulos.
- **H101**: A verificação de chaves RSA na inicialização é bem-sucedida em 100% dos logs.
- **H102**: O tempo de carregamento da lista de candidatos é imperceptível (< 100ms).
- **H103**: A taxa de eventos de áudio (bips) corresponde ao número de teclas + confirmações.
- **H104**: O ajuste de volume do áudio não impacta a performance da votação.
- **H105**: O uso de fones de ouvido não gera ruído no log de eventos.
- **H106**: A inicialização da impressora térmica é registrada antes do primeiro voto.
- **H107**: O tempo de corte do papel da zerésima é constante.
- **H108**: Eventos de "Papel Acabou" correlacionam com paradas na votação.
- **H109**: A troca de bobina de papel leva em média 2 minutos.
- **H110**: Não há logs de impressão durante o voto (segredo do voto).
- **H111**: A assinatura digital do log é gerada apenas no encerramento.
- **H112**: O tempo de geração da assinatura digital depende do tamanho do log.
- **H113**: A verificação de espaço em disco é feita periodicamente.
- **H114**: Não há logs de "Disco Cheio" em eleições normais.
- **H115**: A temperatura da urna (se logada) sobe até um platô e estabiliza.
- **H116**: A variação de tensão da bateria externa está dentro dos limites nominais.
- **H117**: A comutação para bateria interna gera um evento de log de alta prioridade.
- **H118**: O retorno da energia externa é logado imediatamente.
- **H119**: Flutuações de energia não corrompem o evento de log atual.
- **H120**: O desligamento forçado gera um log de "Dirty Shutdown" na próxima inicialização.
- **H121**: O tempo de recuperação de crash é inferior ao tempo de boot frio.
- **H122**: Logs recuperados de crash mantêm a integridade sequencial.
- **H123**: A taxa de crashes é menor que 0.01% das urnas.
- **H124**: Crashes recorrentes na mesma urna indicam falha de hardware.
- **H125**: O padrão temporal de crashes é aleatório (não sistêmico).

---

## 💻 2. Hardware e Operacional (Hipóteses H126 - H250)

### 2.1 Complexidade Baixa (Comparação de Modelos)
*Disponível via agregação simples por `DS_MODELO_URNA`.*

- **H126**: O modelo UE2020 tem tempo de boot 20% mais rápido que o UE2009.
- **H127**: A taxa de falhas de biometria é menor no modelo UE2020.
- **H128**: O modelo UE2010 apresenta maior incidência de troca de bateria.
- **H129**: A temperatura média de operação é menor nas urnas modelo UE2020.
- **H130**: Urnas do modelo UE2013 têm maior variância no tempo de resposta do touch.
- **H131**: A taxa de reinicialização espontânea é maior em modelos anteriores a 2015.
- **H132**: O consumo de papel (comprimento do log impresso) é igual em todos os modelos.
- **H133**: A frequência de calibração de tela é maior em urnas UE2009.
- **H134**: O tempo de acesso à mídia flash é mais rápido nos modelos novos.
- **H135**: A taxa de erro de leitura de mídia é nula em urnas novas.
- **H136**: Urnas com mais de 3 eleições de uso têm maior latência de I/O.
- **H137**: A vida útil da bateria é consistente entre urnas do mesmo lote.
- **H138**: Falhas de impressora são mais comuns no modelo UE2011.
- **H139**: O tempo de resposta do terminal do mesário é uniforme entre modelos.
- **H140**: A detecção de mídia USB é instantânea em 100% dos casos.
- **H141**: A taxa de falha de pixels na tela é monitorada e nula.
- **H142**: O brilho da tela não degrada a ponto de impedir a votação.
- **H143**: O teclado numérico não apresenta "bouncing" (registros duplos) em modelos novos.
- **H144**: A tecla "CONFIRMA" tem a mesma sensibilidade em todos os modelos.
- **H145**: O feedback sonoro tem volume padronizado entre modelos.
- **H146**: A dissipação térmica é eficiente em todos os modelos (sem superaquecimento).
- **H147**: A vedação contra poeira (inferida por sensores/falhas) é eficaz.
- **H148**: A resistência à umidade (inferida por logs regionais) é consistente.
- **H149**: Conectores de fone de ouvido não apresentam falha de detecção.
- **H150**: A porta de conexão da bateria externa não apresenta oxidação lógica (falha intermitente).
- **H151**: O relógio de tempo real (RTC) mantém precisão (<1s drift) em 24h.
- **H152**: A bateria do RTC não falha durante a votação.
- **H153**: A integridade da BIOS/Firmware é verificada a cada boot.
- **H154**: Não há execução de código não assinado na urna.
- **H155**: Periféricos não autorizados não são reconhecidos pelo kernel.
- **H156**: A tentativa de conexão de dispositivos USB não autorizados gera log de alerta.
- **H157**: O bloqueio físico de portas não utilizadas é respeitado (sem logs de inserção).
- **H158**: A tampa do compartimento de mídia não é aberta durante a votação (sensor de intrusão).
- **H159**: A remoção da mídia flash gera parada imediata e log crítico.
- **H160**: O lacre eletrônico (se houver) não é violado.
- **H161**: A remoção do cabo de força gera comutação imediata sem reset.
- **H162**: O alerta de bateria fraca ocorre com antecedência suficiente (>30min).
- **H163**: A substituição da bateria recupera o status de energia imediatamente.
- **H164**: Não há perda de dados durante a troca de bateria (memória não volátil).
- **H165**: O ciclo de carga/descarga da bateria é monitorado.

### 2.2 Complexidade Média (Performance de Componentes)
*Requer parsing detalhado de logs de hardware.*

- **H166**: Baterias com falha de carga são identificadas no teste inicial.
- **H167**: O consumo de energia em standby é desprezível.
- **H168**: O pico de corrente na impressão não derruba a tensão da urna.
- **H169**: A fonte de alimentação externa suporta variações da rede elétrica local.
- **H170**: Filtros de linha (se logados) atuam corretamente.
- **H171**: A temperatura da bateria não excede limites de segurança.
- **H172**: O armazenamento interno tem espaço suficiente para logs de 3 dias.
- **H173**: Não há fragmentação excessiva do sistema de arquivos.
- **H174**: O tempo de montagem do sistema de arquivos é rápido.
- **H175**: Erros de CRC na leitura de arquivos são raros (<0.001%).
- **H176**: Blocos defeituosos na memória flash são marcados e isolados.
- **H177**: O desgaste da memória flash (write cycles) está dentro do limite.
- **H178**: A velocidade de escrita é consistente ao longo do tempo.
- **H179**: Arquivos corrompidos são detectados e restaurados do backup.
- **H180**: O sistema operacional (Linux) não apresenta kernel panics.
- **H181**: Drivers de dispositivos não falham durante a operação.
- **H182**: O gerenciamento de memória não apresenta leaks (vazamentos).
- **H183**: A carga de CPU permanece baixa (<50%) na maior parte do tempo.
- **H184**: Picos de CPU coincidem com criptografia/assinatura.
- **H185**: Processos zumbis não são criados.
- **H186**: O scheduler do SO garante prioridade ao processo de votação.
- **H187**: Interrupções de hardware são tratadas em tempo real.
- **H188**: O watchdog de hardware reinicia a urna em caso de travamento.
- **H189**: Logs de watchdog são gravados após o reboot.
- **H190**: A taxa de falsos positivos do watchdog é zero.
- **H191**: O display não apresenta "burn-in" ou fantasmas.
- **H192**: A legibilidade da tela é mantida sob luz ambiente variada (se sensor existir).
- **H193**: O contraste da tela é ajustado corretamente.
- **H194**: A tela sensível ao toque responde apenas a toques intencionais.
- **H195**: Toques múltiplos (multitouch) não travam a interface.
- **H196**: A calibração do touch é persistente entre reboots.
- **H197**: O teclado do mesário é resistente a múltiplos pressionamentos.
- **H198**: O leitor de biometria detecta "dedo vivo" (liveness).
- **H199**: A qualidade da imagem biométrica é verificada antes do aceite.
- **H200**: O tempo de processamento do matching biométrico é < 1s.
- **H201**: Falhas de comunicação entre terminal do mesário e do eleitor são raras.
- **H202**: O cabo de conexão entre terminais é monitorado quanto a desconexões.
- **H203**: Ruído eletromagnético não interfere na comunicação interna.
- **H204**: A blindagem da urna é efetiva.
- **H205**: A integridade física da urna (case) não afeta a eletrônica.

### 2.3 Complexidade Alta (Engenharia e Stress)
*Testes de stress, drivers e falhas raras.*

- **H206**: Vibrações de transporte não soltam componentes internos.
- **H207**: Conectores internos têm travas de segurança.
- **H208**: A montagem da urna segue padrão de qualidade industrial.
- **H209**: Componentes não apresentam oxidação precoce.
- **H210**: A vida útil estimada dos capacitores é respeitada.
- **H211**: A ventilação passiva é suficiente para resfriamento.
- **H212**: A entrada de insetos/poeira é mitigada.
- **H213**: O peso da urna está dentro da especificação.
- **H214**: A ergonomia da urna facilita o voto.
- **H215**: O ângulo de visão da tele protege o sigilo.
- **H216**: Barreiras laterais visuais são eficazes.
- **H217**: O teclado em Braille é funcional e padronizado.
- **H218**: A saída de áudio para fones é estéreo ou mono limpo.
- **H219**: O conector de fone é padrão P2.
- **H220**: O volume máximo de áudio não causa distorção.
- **H221**: A impressora tem resolução suficiente para leitura humana e OCR.
- **H222**: O papel térmico tem durabilidade conforme especificação.
- **H223**: O mecanismo de tracionamento de papel não atola.
- **H224**: A guilhotina de papel funciona sem falhas.
- **H225**: A tampa da impressora tem sensor de abertura.
- **H226**: A troca de papel é registrada como evento de manutenção.
- **H227**: O teste de impressão inicial valida todo o mecanismo.
- **H228**: A tinta/térmica da impressão é legível por anos (exigência legal).
- **H229**: O QR Code impresso no BU é legível por apps padrão.
- **H230**: O conteúdo do QR Code bate com os dados impressos.
- **H231**: A assinatura digital no BU impresso é válida.
- **H232**: A compactação dos logs não corrompe dados.
- **H233**: A descompactação é determinística.
- **H234**: Algoritmos de criptografia são acelerados por hardware onde possível.
- **H235**: A geração de números aleatórios (RNG) é de alta entropia.
- **H236**: As chaves criptográficas são armazenadas em área segura (TPM/HSM).
- **H237**: O acesso às chaves exige autenticação forte.
- **H238**: Tentativas de violação física apagam as chaves (tamper detection).
- **H239**: O boot seguro impede carregamento de SO adulterado.
- **H240**: A cadeia de confiança (Chain of Trust) é validada no boot.
- **H241**: Logs de auditoria interna do hardware são acessíveis.
- **H242**: Testes de fábrica (burn-in) foram realizados e logados.
- **H243**: O número de série do hardware bate com o registro lógico.
- **H244**: A identificação da seção eleitoral é gravada na mídia de carga.
- **H245**: A urna recusa funcionar se a seção/zona não conferir com a mídia.
- **H246**: A data/hora local deve bater com a configuração da eleição.
- **H247**: O fuso horário configurado deve ser o local da seção.
- **H248**: Logs de auditoria não podem ser apagados pelo usuário.
- **H249**: A capacidade de armazenamento de logs excede o pior caso previsto.
- **H250**: A performance do hardware é suficiente para não causar filas.

---

## 🕵️ 3. Forense e Segurança (Hipóteses H251 - H375)

### 3.1 Complexidade Baixa (Integridade Estática)
*Checks de hash e estrutura básica.*

- **H251**: O hash SHA-512 de todos os arquivos de log é válido e verificável.
- **H252**: A cadeia de assinaturas digitais do TSE é válida para 100% das urnas.
- **H253**: Não existem arquivos de log com tamanho zero bytes.
- **H254**: Não existem arquivos de log com conteúdo binário inválido (corrompido).
- **H255**: A estrutura interna do formato de log (LogJEZ/LogD) está 100% conforme a especificação.
- **H256**: Todos os eventos possuem um timestamp sequencial e lógico.
- **H257**: Não há saltos de numeração sequencial de eventos (event IDs).
- **H258**: O identificador da urna no log corresponde ao nome do arquivo.
- **H259**: Os metadados de município e zona no log batem com a estrutura de diretórios.
- **H260**: Não há logs duplicados (conteúdo idêntico) em seções diferentes (clonagem).
- **H261**: Não há logs compartilhando a mesma assinatura digital em seções diferentes.
- **H262**: O certificado digital utilizado para assinar pertence à autoridade certificadora do TSE.
- **H263**: O certificado digital estava válido na data da eleição.
- **H264**: A lista de revogação de certificados (CRL) foi consultada (ou é estática e válida).
- **H265**: Chaves privadas de assinatura não vazaram (inferido por unicidade).
- **H266**: A entropia dos logs criptografados é alta (indica boa encriptação).
- **H267**: Padrões repetitivos de "ruído" não são detectados nos dados encriptados.
- **H268**: Logs de falha de autenticação de mesários são inferiores a 5% do total de autenticações.
- **H269**: Não há registros de "Superusuário" ou "Admin" acessando a urna durante a votação.
- **H270**: O modo de manutenção só é acessado fora do horário de votação.
- **H271**: A inserção de mídia de carga após o início da votação gera alerta crítico.
- **H272**: A tentativa de atualização de software durante a votação é bloqueada e logada.
- **H273**: Não há execução de scripts de shell (.sh) registrados nos logs.
- **H274**: Variáveis de ambiente do SO não são alteradas durante a execução.
- **H275**: O espaço de endereçamento de memória é protegido (sem logs de segfault por buffer overflow).
- **H276**: Bibliotecas dinâmicas carregadas são apenas as assinadas e autorizadas.
- **H277**: O hash do binário do software de votação é constante em todas as urnas.
- **H278**: Versões de software divergentes entre urnas da mesma UF são detectadas.
- **H279**: A tabela de candidatos carregada é íntegra e autêntica.
- **H280**: Fotos de candidatos não foram alteradas (verificação de hash).
- **H281**: Dados de eleitores (Caderno de Votação digital) estão íntegros.
- **H282**: Não há acesso não autorizado aos dados do eleitor.
- **H283**: Logs de votação não contêm identificação do eleitor (anonimização).
- **H284**: A ordem dos votos no RDV (Registro Digital do Voto) é embaralhada (shuffled).
- **H285**: O embaralhamento do RDV é estatisticamente aleatório.
- **H286**: Não é possível correlacionar a ordem do log de eventos com a ordem do RDV.
- **H287**: Ataques de canal lateral (timing analysis) não revelam o voto.
- **H288**: Emissões eletromagnéticas (se medidas) não revelam o voto (TEMPEST).
- **H289**: A urna opera em modo "air-gapped" (sem rede externa) real.
- **H290**: Não há logs de drivers de rede (Wi-Fi/Bluetooth) ativos.

### 3.2 Complexidade Média (Padrões de Ataque)
*Regex complexos e correlação de eventos.*

- **H291**: Portas de comunicação não utilizadas estão desabilitadas logicamente.
- **H292**: A porta USB para mídia de resultados só aceita pen-drives específicos.
- **H293**: Tentativas de explorar vulnerabilidades de USB stack são logadas.
- **H294**: A montagem de sistemas de arquivos externos é restrita.
- **H295**: Logs de sistema (syslog) são consistentes com os logs da aplicação.
- **H296**: Não há lacunas temporais inexplicáveis nos logs de sistema.
- **H297**: A correlação entre eventos de aplicação e kernel é perfeita.
- **H298**: Anomalias de I/O de disco indicam tentativa de acesso físico ou falha.
- **H299**: A estrutura de diretórios da mídia de resultados é padrão.
- **H300**: Arquivos ocultos ou estranhos não existem na mídia de resultados.
- **H301**: O BU (Boletim de Urna) digital corresponde exatamente aos votos computados.
- **H302**: O BU impresso corresponde ao digital.
- **H303**: O QR Code do BU contêm os dados autênticos.
- **H304**: A assinatura do BU é válida.
- **H305**: Não há BUs duplicados para a mesma seção.
- **H306**: O número de votos no BU não excede o número de eleitores aptos.
- **H307**: A soma de votos nominais, brancos e nulos fecha com o total.
- **H308**: O comparecimento no BU bate com o número de "comparecimentos" no log de eventos.
- **H309**: O número de justificativas (se houver) bate com os logs.
- **H310**: A complexidade da senha do mesário atende aos requisitos.
- **H311**: Tentativas de força bruta na senha do mesário são bloqueadas.
- **H312**: O bloqueio após N tentativas falhas de senha funciona.
- **H313**: Senhas padrão ou de fábrica não são aceitas.
- **H314**: A troca de senha obrigatória é forçada pelo sistema.
- **H315**: Logs de auditoria registram o usuário responsável por cada ação administrativa.
- **H316**: A rastreabilidade das ações do mesário é completa.
- **H317**: Comandos administrativos críticos exigem dupla autenticação ou senha especial.
- **H318**: A reinicialização da urna exige senha.
- **H319**: O encerramento da votação é irreversível na mesma mídia.
- **H320**: A reabertura da votação (se permitida legalmente) deixa trilha auditável clara.
- **H321**: Logs de eventos anômalos (ex: erro desconhecido) são destacados.
- **H322**: Padrões de ataque conhecidos (ex: buffer overflow strings) não aparecem nos inputs.
- **H323**: Inputs do usuário (teclado) são sanitizados.
- **H324**: Não há injeção de código via campos de texto (se houver).
- **H325**: O sistema é robusto a entradas aleatórias (fuzzing manual).
- **H326**: A integridade dos dados em memória RAM é protegida (ECC).
- **H327**: O dump de memória (em crash) não expõe o voto unificado.
- **H328**: A exclusão segura de dados temporários é realizada.
- **H329**: Arquivos temporários não permissionados permancem no disco.
- **H330**: Permissões de arquivo no SO são restritivas (princípio do menor privilégio).

### 3.3 Complexidade Alta (Deep Inspection)
*Requer ferramentas forenses externas e análise de binários.*

- **H331**: O usuário executando a aplicação de votação não é root.
- **H332**: Ferramentas de desenvolvimento/debug não estão instaladas.
- **H333**: Portas de console serial/JTAG estão desativadas ou protegidas.
- **H334**: O gabinete da urna dificulta o acesso físico às portas internas.
- **H335**: Sensores de violação de gabinete funcionam e logaram se houvesse abertura.
- **H336**: A integridade das etiquetas de segurança físicas é verificada procedimentalmente (logs de 'Lacre Confere').
- **H337**: Relatórios de anomalias forenses são gerados automaticamente.
- **H338**: A consistência dos metadados de seção/zona/município é total.
- **H339**: Logs de diferentes turnos não se misturam na mesma estrutura de dados ativa.
- **H340**: O arquivamento de logs antigos é seguro.
- **H341**: A transmissão de resultados utiliza canal criptografado (VPN/TLS) - verificação indireta via log de sucesso.
- **H342**: A autenticação mútua urna-servidor na transmissão é bem-sucedida.
- **H343**: Não há logs de "Certificado de Servidor Inválido" na transmissão.
- **H344**: Ataques de Man-in-the-Middle (MitM) na transmissão seriam detectados por falha de handshake.
- **H345**: A integridade do pacote de transmissão é verificada no destino (ACK recebido).
- **H346**: Retentativas de transmissão seguem backoff exponencial.
- **H347**: Logs de transmissão falha indicam o motivo (rede, timeout, auth).
- **H348**: A recuperação de transmissão interrompida funciona sem duplicidade.
- **H349**: A mídia de resultados pode ser lida em qualquer computador autorizado para contingência.
- **H350**: A leitura da mídia em sistema não autorizado não executa código (autorun desativado).
- **H351**: Vírus ou malware de PC não infectam a urna via mídia.
- **H352**: A urna não infecta PCs via mídia.
- **H353**: A formatação da mídia segue padrão proprietário ou seguro.
- **H354**: Mídias não reconhecidas são rejeitadas.
- **H355**: A urna não monta partições desconhecidas.
- **H356**: O sistema de arquivos é somente leitura (Read-Only) onde possível.
- **H357**: A partição de dados é montada como "noexec".
- **H358**: Logs de auditoria são imutáveis (append-only).
- **H359**: A integridade referencial do banco de dados interno (se houver) é mantida.
- **H360**: Transações de voto são atômicas (tudo ou nada).
- **H361**: Falta de energia durante o voto não gera estado inconsistente.
- **H362**: O estado da urna é recuperado perfeitamente após reboot.
- **H363**: Não há "votos fantasmas" após recuperação de falha.
- **H364**: O número de eleitores que votaram é preservado.
- **H365**: A lista de eleitores que já votaram não é perdida.
- **H366**: Não é possível um eleitor votar duas vezes (mesmo após reboot).
- **H367**: O status de "Habilitado para Votar" é limpo após o voto.
- **H368**: O timeout de habilitação (eleitor não comparece) funciona e cancela a habilitação.
- **H369**: Cancelamento de habilitação é logado corretamente.
- **H370**: Tentativas sucessivas de habilitação/cancelamento são detectadas como anomalia.
- **H371**: A urna não entra em loop de reinicialização.
- **H372**: Logs de erro de hardware não são suprimidos.
- **H373**: A verbosidade do log é adequada para auditoria forense.
- **H374**: Não há logs criptografados com chaves desconhecidas pelo TSE.
- **H375**: A "Unicidade do Voto" é garantida logicamente.

---

## 🔗 4. Cruzamento de Dados e Resultado (Hipóteses H376 - H500)

### 4.1 Complexidade Baixa (Consistência Interna)
*Validações que não exigem dados externos ao pacote da urna (Log + BU).*

- **H376**: A proporção de votos no candidato vencedor na seção não correlaciona com o modelo da urna (Ex: UE2020 não favorece X).
- **H377**: A taxa de falha biométrica não correlaciona com a vitória de determinado partido.
- **H378**: O volume de votos nulos não correlaciona com o modelo de hardware da urna.
- **H379**: Seções com encerramento tardio (após 17h) não mostram tendência de voto divergente da média local.
- **H380**: A velocidade de votação (segundos por voto) não prediz o vencedor da seção.
- **H381**: Interrupções de energia não alteram a tendência de voto antes e após a falha.
- **H382**: Seções com troca de urna (contingência) mantêm o perfil de votação da urna original.
- **H383**: A densidade de votos por minuto não afeta a distribuição partidária (voto rápido x lento).
- **H384**: Não há correlação entre a hora do dia e a preferência partidária (viés temporal de voto).
- **H385**: O comparecimento em seções biométricas é estatisticamente igual ao de seções híbridas.
- **H386**: A taxa de abstenção não correlaciona com falhas técnicas registradas no log.
- **H387**: Zonas eleitorais com mais urnas novas não têm resultados divergentes de zonas com urnas antigas vizinhas.
- **H388**: O tempo médio de voto no 2º turno é significativamente menor (confirmação da hipótese de eficiência).
- **H389**: Votos de legenda são mais frequentes em seções com maior escolaridade (inferida por local).
- **H390**: A taxa de anulação de voto não aumenta em urnas com tela pequena (biometria antiga).
- **H391**: Padrões de Benford são respeitados nos dígitos iniciais dos totais de votos por seção.
- **H392**: A distribuição dos últimos dígitos dos totais de votos é uniforme (0-9).
- **H393**: Não há clusters geográficos anômalos de votos 100% para um candidato (unanimidade suspeita).
- **H394**: Seções "gêmeas" (mesmo local) apresentam correlação alta de resultados (>0.9).
- **H395**: A variância dos votos dentro de um local de votação é baixa.
- **H396**: Outliers de votação (Z-Score > 3) são explicáveis por demografia ou localidade específica.
- **H397**: A curva de acumulação de votos ao longo da apuração (tse) segue padrão logístico.
- **H398**: Resultados de Urnas com LOG quebrado/ilegível (zero bytes) devem ser auditados manualmente.
- **H399**: A proporção de votos conferidos no BU bate com a média histórica da seção (se dados disponíveis).
- **H400**: O número de inscritos na seção bate com o teto do BU.
- **H401**: Seções com alto índice de "Voto em Branco" não possuem viés de hardware.
- **H402**: A taxa de comparecimento é uniforme entre urnas do mesmo local.
- **H403**: Não há correlação entre ID da urna e resultados (randomização do hardware).
- **H404**: A versão do software da urna (se múltipla) não influencia o resultado.
- **H405**: O tempo de exibição da foto do candidato vice não altera a confirmação do voto.
- **H406**: A taxa de votos em candidatos indeferidos (sub judice) é monitorada.
- **H407**: Seções que sofreram carga de mídia ou flash extra não desviam da média.
- **H408**: A presença de mesários substitutos (log de login) não altera padrões.
- **H409**: O horário de chegada dos mesários não correlaciona com eficiência ou resultado.
- **H410**: Seções com muitas justificativas de ausência têm perfil distinto de votação.
- **H411**: A taxa de falha de leitura de QR Code do título não impacta o fluxo.
- **H412**: O número de eleitores habilitados por ano de nascimento (se logado) segue a pirâmide etária.
- **H413**: Votos computados nos últimos 5 minutos não têm viés estatístico.
- **H414**: A ordem dos candidatos na tela (se rotativa em legislativo) não induz voto.
- **H415**: A luminosidade da tela (brilho) não correlaciona com taxa de branco/nulo.
- **H416**: O tempo de operação em bateria não afeta a contagem de votos.
- **H417**: A temperatura da CPU não se correlaciona com um partido específico (carga de processamento gráfica).
- **H418**: O número de reinicializações da urna não altera a tendência de votos acumulada.
- **H419**: Seções que fecharam exatamente às 17:00 têm o mesmo perfil das que estenderam.
- **H420**: A taxa de votos nominais vs. legenda é consistente com a média estadual.
- **H421**: Não há "votos negativos" ou contadores estourados (overflow integers).
- **H422**: A soma dos BUs de uma Zona bate com a totalização da Zona.
- **H423**: A soma dos votos de todos os candidatos + brancos + nulos = Total Comparecimento.
- **H424**: O número de votos nominais não excede o total de votos válidos.
- **H425**: Logs de BUs emitidos antes das 17h (em fuso Brasília) são alertas críticos.

### 4.2 Complexidade Média (Cruzamento Geográfico/Demográfico)
*Requer join com bases do IBGE, Clima ou Perfil do Eleitorado.*

- **H426**: A geolocalização da seção (metadados) bate com a zona eleitoral esperada.
- **H427**: Seções rurais vs urbanas mostram perfis de nulos distintos mas consistentes internamente.
- **H428**: A taxa de abstenção em seções com transporte público difícil é maior.
- **H429**: O impacto de chuvas (metereologia) na abstenção é quantificável.
- **H430**: Seções com histórico de violência (metadados segurança) têm horários de pico diferentes.
- **H431**: A curva de chegada de eleitores correlaciona com horários de ônibus locais.
- **H432**: A velocidade de votação aumenta em seções com mesários experientes (recorrentes).
- **H433**: A idade média dos mesários (se disponível) impacta a velocidade da fila.
- **H434**: Mesários que votam na própria seção o fazem em horários de vale.
- **H435**: O voto do mesário é indistinguível dos demais no RDV.
- **H436**: A presença de fiscais de partido (registro em log/ata) não altera o resultado da seção.
- **H437**: O número de boletins de urna impressos (cópias) é registrado.
- **H438**: A reimpressão do BU não altera os dados.
- **H439**: A transmissão de dados via satélite (locais remotos) tem latência maior mas integridade igual.
- **H440**: Seções indígenas têm padrões temporais e de resultado específicos e consistentes.
- **H441**: Seções em presídios (se houver) têm padrões de segurança reforçados.
- **H442**: Votos em trânsito são contabilizados corretamente na urna específica.
- **H443**: A urna de justificativa não aceita votos normais.
- **H444**: Transferência de eleitores reflete-se no caderno de votação digital.
- **H445**: Eleitores falecidos (caderno desatualizado) são impedidos de votar (habilitação falha).
- **H446**: Tentativas de voto com título cancelado geram log de impedimento.
- **H447**: O sistema de áudio para cegos é ativado corretamente quando solicitado.
- **H448**: O uso de fones não altera o sigilo do voto no log.
- **H449**: A votação assistida (registrada em ata/log) segue o protocolo.
- **H450**: O tempo de voto assistido é estatisticamente maior.
- **H451**: A taxa de renovação política (novos candidatos) correlaciona com demografia jovem da seção.
- **H452**: Votos em candidatos "famosos" (celebridades) independem de modelo de urna.
- **H453**: A fidelidade partidária (voto em chapa completa) é consistente na seção.
- **H454**: O "voto cruzado" (presidente de um partido, governador de oposto) é detectável estatisticamente.
- **H455**: A polarização política (concentração em 2 candidatos) é visível em nível de seção.
- **H456**: Seções com biometria 100% (cidades recadastradas) têm fraudes de identidade próximas de zero.
- **H457**: A divergência entre pesquisas eleitorais locais e resultado da urna está na margem de erro.
- **H458**: O "efeito manada" (votos influenciados pela fila) não é detectado.
- **H459**: A boca de urna (crime) não gera padrão de votação concentrado em horário específico.
- **H460**: A distribuição de votos segue a Lei de Benford para o segundo dígito também.
- **H461**: Testes de Qui-Quadrado confirmam a independência entre variáveis aleatórias no RDV.
- **H462**: A entropia de Shannon dos resultados é consistente com a complexidade do pleito.
- **H463**: Análise de Componentes Principais (PCA) agrupa seções por perfil socioeconômico, não por hardware.
- **H464**: Detecção de anomalias via Isolation Forest não aponta fraude sistêmica.
- **H465**: O coeficiente de Gini dos votos na seção reflete a desigualdade local.
- **H466**: A autocorrelação espacial (I de Moran) dos resultados mostra clusters naturais, não artificiais.
- **H467**: A análise de regressão confirma que "Modelo da Urna" não é preditor significativo de votos.
- **H468**: O "efeito vizinhança" explica 80% da variância entre seções próximas.
- **H469**: A abstenção é maior em zonas com transporte precário (cruzamento com dados de mobilidade se houver).
- **H470**: A taxa de votos nulos é maior em eleições municipais complexas.
- **H471**: A curva de aprendizado do eleitor (tempo de voto) melhora ao longo do dia? (H: Não, fadiga piora).
- **H472**: O primeiro eleitor do dia tende a ser idoso (padrão cultural).
- **H473**: O pico de jovens votantes é no final da tarde.
- **H474**: Famílias votando juntas (sequência de sobrenomes no caderno, se disponível) votam em horários próximos.
- **H475**: A taxa de sucesso de leitura biométrica correlaciona com a idade do eleitor.

### 4.3 Complexidade Alta (Inferência Causal e Múltiplas Fontes)
*Exige modelagem estatística avançada e cruzamento de 3+ dimensões.*

- **H476**: Biometria de idosos falha mais que de jovens.
- **H477**: Eleitores com deficiência têm prioridade na fila (fluxo de atendimento no log).
- **H478**: O tempo de atendimento preferencial é otimizado.
- **H479**: A taxa de troca de bobina de papel aumenta com o número de eleitores na seção.
- **H480**: Urnas com bobina mau colocada geram logs de erro de impressora recorrentes.
- **H481**: A nitidez da impressão (se sensor existir) degrada com a bateria fraca (H: Não, regulado).
- **H482**: O consumo de bateria é linear com o número de votos.
- **H483**: O aquecimento da bateria é proporcional à carga de trabalho.
- **H484**: Baterias antigas aquecem mais.
- **H485**: Seções com ar condicionado (frias) têm melhor performance de bateria.
- **H486**: A umidade relativa do ar (metadados) afeta a condutividade do touch (H: Não deve afetar).
- **H487**: Tempestades elétricas (raios) não causam reboots em urnas na bateria.
- **H488**: Seções em ilhas ou locais isolados funcionam com a mesma confiabilidade.
- **H489**: O transporte fluvial das urnas não causa danos físicos (logs de shock sensor, se houver).
- **H490**: Urnas de contingência ativadas têm logs de "Troca de Urna".
- **H491**: A migração de votos para urna de contingência é íntegra.
- **H492**: Não há perda de votos na troca por contingência.
- **H493**: A urna de contingência inicia com zero votos.
- **H494**: O Flash Card da urna quebrada é lido com sucesso na contingência.
- **H495**: A urna de contingência assume a identidade da seção corretamente.
- **H496**: O tempo de parada para troca de urna é registrado.
- **H497**: A troca de urna não afeta a tendência de votos da seção (antes vs depois).
- **H498**: A urna defeituosa é lacrada e auditada posteriormente.
- **H499**: O motivo da falha da urna original é diagnosticado nos logs.
- **H500**: **Conclusão Geral**: A integridade do processo eleitoral é mantida independente das falhas pontuais de hardware, variações temporais ou características demográficas, com rastreabilidade total de ponta a ponta.
