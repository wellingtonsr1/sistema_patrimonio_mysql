# Feature Specification: Correção do Ciclo de Backup, Restauração e Agendamento Automático

**Feature Branch**: `028-correcao-ciclo-backup`

**Created**: 2026-09-18

**Status**: Draft

**Input**: Corrigir três comportamentos observados no módulo de Backup, de forma cirúrgica, sem refatorações: (A) coluna "Tipo" da tela de backups exibe "—" para backups de tipo conhecido após uma restauração; (B) o backup automático agendado não executa no horário configurado; (C) a tela `/admin/backups` recebe HTTP 503 durante a restauração em segundo plano, impedindo o acompanhamento prometido ao operador.

---

## Análise do estado atual (fatos verificados no código, 2026-09-18)

Esta spec é de **correção em sistema existente**. Os três problemas foram localizados por leitura do código atual; a spec exige que o planejamento/confirmação partam destes fatos:

- **Problema A — tipo perdido após restauração**: os registros de backup (`BackupRecord`) são criados nos fluxos manual, automático e pré-restauração. Durante a restauração, o ciclo cria o registro do backup de pré-restauração **antes** do import e, em seguida, o import substitui o conteúdo do banco pelo snapshot do dump restaurado — que não contém registros criados após a sua geração. Os arquivos continuam no disco, mas sem registro associado; a tela cruza arquivos × registros e exibe "—" quando não encontra registro. Não existe nenhum passo de reconciliação de registros após o import.
- **Problema B — agendador não dispara**: o loop do agendador (verificação a cada 30 s) decide o disparo comparando o momento atual com a **próxima ocorrência futura** do horário configurado — valor recalculado a cada tick e por definição estritamente posterior ao agora, tornando a condição de disparo impossível de satisfazer. O catch-up de inicialização usa um critério correto ("o horário do ciclo corrente já passou sem sucesso?") e por isso funciona — o disparo normal do horário é que nunca ocorre.
- **Problema C — 503 na tela de acompanhamento**: durante a restauração em segundo plano, o modo de manutenção bloqueia com 503 todos os caminhos fora de uma whitelist mínima. A whitelist inclui o endpoint de status da restauração, mas **não** inclui a própria tela `/admin/backups` — que é exatamente a tela para onde o operador é redirecionado com a mensagem "acompanhe o resultado nesta tela".

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Tipo dos backups preservado após a restauração (Priority: P1)

Um administrador gera backups (manual e automático) e executa uma restauração. Ao retornar à tela de backups, cada arquivo presente no disco continua exibindo seu tipo correto — MANUAL, AUTOMÁTICO ou PRÉ-RESTAURAÇÃO — porque o sistema preserva a associação entre arquivo e tipo, e o próprio ciclo de restauração garante que o backup de segurança que ele criou permanece identificado como PRÉ-RESTAURAÇÃO.

**Why this priority**: a tela de backups é o instrumento de confiança do operador para decidir restaurações; um tipo perdido (—) torna o histórico inconfiável e pode induzir decisões erradas em cenário de recuperação.

**Independent Test**: pode ser testado criando um backup manual, executando uma restauração válida e conferindo a tela de backups — entrega valor mesmo sem mexer no agendador.

**Acceptance Scenarios**:

1. **Given** um backup manual existente com registro e tipo MANUAL, **When** uma restauração válida é concluída e o arquivo continua presente, **Then** a tela de backups exibe MANUAL para esse arquivo.
2. **Given** uma restauração válida concluída, **When** a tela de backups é consultada, **Then** o backup de segurança criado pelo próprio ciclo aparece como PRÉ-RESTAURAÇÃO (nunca reinterpretado como MANUAL).
3. **Given** um backup automático existente com registro e tipo AUTOMATICO, **When** uma restauração válida é concluída e o arquivo continua presente, **Then** a tela exibe AUTOMÁTICO.
4. **Given** qualquer arquivo de backup presente no disco que possuía registro com tipo conhecido antes da restauração, **When** a restauração é concluída, **Then** o arquivo nunca é exibido como "—" por perda do registro.
5. **Given** um arquivo de backup legado anterior à existência de registros (sem registro algum), **When** a tela é exibida, **Then** o comportamento atual para arquivo sem registro é preservado (o "—" legítimo para tipo genuinamente desconhecido não é preenchido com suposição).
6. **Given** a conclusão da restauração, **When** os registros são consultados, **Then** os valores persistidos continuam sendo MANUAL / AUTOMATICO / PRE_RESTAURACAO (a apresentação "MANUAL/AUTOMÁTICO/PRÉ-RESTAURAÇÃO" é apenas visual).

---

### User Story 2 — Backup automático executa no horário configurado (Priority: P1)

Um administrador configura o backup automático (diário ou semanal, horário configurável). Quando o horário configurado chega, o backup é gerado exatamente uma vez no ciclo; os ticks seguintes do verificador não geram duplicidade; a proteção contra execução durante restauração e o catch-up de inicialização continuam funcionando como hoje.

**Why this priority**: o backup automático é a proteção de dados do sistema; hoje o disparo por horário simplesmente nunca ocorre, o que é uma lacuna silenciosa de proteção.

**Independent Test**: pode ser testado com o agendador e um relógio simulado, sem envolver restauração nem tela — entrega valor isolado.

**Acceptance Scenarios**:

1. **Given** o backup automático habilitado com horário configurado, **When** o horário configurado é alcançado/passado dentro do ciclo corrente sem sucesso anterior no ciclo, **Then** um backup com tipo AUTOMATICO e status de sucesso é gerado.
2. **Given** um backup automático bem-sucedido no ciclo corrente, **When** o verificador volta a avaliar (tick seguinte de 30 s), **Then** nenhum segundo backup é gerado no mesmo ciclo.
3. **Given** o agendamento semanal configurado para um dia da semana, **When** o verificador avalia em dias que não o configurado, **Then** nenhum backup é disparado; no dia configurado, aplica-se o cenário 1.
4. **Given** o sistema iniciado após o horário configurado do ciclo corrente sem sucesso no ciclo, **When** o catch-up de inicialização avalia, **Then** ocorre no máximo uma execução de recuperação, sem duplicar com o disparo normal corrigido.
5. **Given** o backup automático desabilitado na configuração efetiva, **When** o verificador avalia, **Then** nenhum backup é disparado.
6. **Given** uma restauração em andamento, **When** o horário do backup automático chega, **Then** a execução é adiada/descartada conforme a proteção existente e nenhuma operação de backup concorre com a restauração.
7. **Given** uma execução automática ainda em andamento, **When** um novo tick avalia o disparo, **Then** a sobreposição é descartada (proteção existente preservada).

---

### User Story 3 — Acompanhamento seguro da restauração sem 503 indevido (Priority: P2)

Um administrador inicia uma restauração que executa em segundo plano em modo de manutenção. Enquanto o ciclo está em andamento, ele consegue acompanhar o estado (fase, mensagem, término) na tela de backups — a mesma tela prometida na mensagem de redirecionamento — sem que isso libere qualquer operação de escrita; ao término, a tela volta ao comportamento normal.

**Why this priority**: é experiência do operador e fidelidade do contrato da restauração assíncrona; não impede a proteção dos dados, mas elimina um bloqueio que contradiz a própria mensagem exibida ao operador.

**Independent Test**: pode ser testado iniciando uma restauração (com executor de import simulado) e consultando a tela durante o ciclo, verificando os bloqueios de escrita — independente das stories 1 e 2.

**Acceptance Scenarios**:

1. **Given** uma restauração em andamento com modo de manutenção ativo, **When** o administrador acessa a tela de backups, **Then** consegue visualizar o estado da restauração (acompanhamento) em vez de receber o 503 indevido.
2. **Given** o modo de manutenção ativo durante a restauração, **When** qualquer endpoint de escrita é acionado (gerar backup, iniciar restauração, salvar configurações, operações de patrimônio/usuários), **Then** continua bloqueado conforme o comportamento atual de manutenção.
3. **Given** o modo de manutenção ativo, **When** a tela de acompanhamento é acessada, **Then** a autenticação e a permissão existentes continuam exigidas (o acompanhamento não concede acesso a quem não as possui).
4. **Given** dados momentaneamente indisponíveis para consulta durante o ciclo (import em curso), **When** a tela de acompanhamento é acessada, **Then** ela degrada de forma controlada (exibe o estado da operação) em vez de falhar com página de erro.
5. **Given** a restauração concluída (sucesso ou falha), **When** a tela é acessada, **Then** o modo de manutenção está encerrado e a tela volta ao comportamento normal completo.
6. **Given** páginas fora do fluxo de acompanhamento, **When** acessadas durante a manutenção, **Then** continuam recebendo a página de manutenção (o 503 legítimo é preservado).

---

### Edge Cases

- **Restauração que falha no meio do ciclo**: o registro do pré-restauração e os tipos dos demais backups existentes no disco permanecem corretos; o modo de manutenção é encerrado e a tela volta ao normal.
- **Registro cujo arquivo não existe mais** (removido pela retenção ou manualmente): comportamento atual de listagem/cruzamento é preservado — a correção não pode ressuscitar arquivos nem inventar registros para arquivos inexistentes.
- **Arquivos legados sem registro**: continuam exibindo "—" (não há inferência de tipo por nome de arquivo).
- **Configuração alterada pela tela durante a execução do agendador**: o comportamento atual (configuração efetiva relida sem reinício) é preservado.
- **Tick do verificador durante backup automático longo**: proteção contra sobreposição descarta a avaliação concorrente.
- **Catch-up e disparo normal no mesmo ciclo**: no máximo uma execução por ciclo (a recuperação de inicialização não pode coexistir com um disparo duplicado corrigido).

## Requirements *(mandatory)*

### Problema A — Integridade do tipo dos backups

- **FR-001**: O sistema MUST preservar, após uma restauração concluída, a associação entre cada arquivo de backup presente no disco e o tipo registrado (MANUAL, AUTOMATICO, PRE_RESTAURACAO) que ele possuía.
- **FR-002**: A restauração MUST NOT destruir ou perder o tipo dos registros de backups cujos arquivos continuam presentes no disco, incluindo os backups criados após a geração do dump restaurado.
- **FR-003**: O backup de segurança criado pelo próprio ciclo de restauração MUST permanecer registrado e identificado como PRE_RESTAURACAO após a conclusão do ciclo (sucesso ou falha).
- **FR-004**: A recuperação de tipos perdidos MUST partir de estado capturado/registrado pelo próprio sistema antes da substituição do banco pelo dump (decisão de mecanismo cabendo ao planejamento), NÃO podendo inferir tipo pelo nome do arquivo nem aplicar fallback para MANUAL.
- **FR-005**: A tela MUST exibir os rótulos MANUAL / AUTOMÁTICO / PRÉ-RESTAURAÇÃO para tipos conhecidos e "—" apenas para arquivo genuinamente sem registro (legado), mantendo os valores persistidos intocados.
- **FR-006**: A correção MUST ocorrer no ponto real da causa: se o banco perde o tipo, a correção é na preservação dos dados; se o problema for apenas de associação/apresentação, não deve haver alteração de banco. NÃO é aceitável mascarar perda real de dados somente na camada de apresentação.
- **FR-007**: Os fluxos de criação de backup (manual, automático, pré-restauração), seus registros, hashes e validações de integridade MUST permanecer funcionando como hoje.
- **FR-008**: A correção MUST NOT criar registros duplicados, criar registros para arquivos inexistentes ou alterar a política de retenção.

### Problema B — Disparo do backup automático

- **FR-009**: O agendador MUST disparar o backup automático quando o horário configurado for alcançado/passado dentro do ciclo corrente sem backup automático bem-sucedido nesse ciclo (semântica de "execução devida"), para agendamento diário e semanal.
- **FR-010**: O agendador MUST NOT usar a "próxima ocorrência futura" como condição de disparo (condição impossível); essa informação, quando existir, fica restrita a exibição/monitoramento.
- **FR-011**: A arquitetura atual MUST ser preservada: verificação periódica de 30 s, thread agendadora única interna ao processo, worker de disparo em thread própria — sem segundo agendador, sem polling agressivo, sem processos externos.
- **FR-012**: As proteções existentes MUST continuar ativas: descarte de sobreposição de execuções automáticas, adiamento quando há restauração em andamento e não duplicação dentro do mesmo ciclo (guarda por sucesso do ciclo).
- **FR-013**: O catch-up de inicialização existente MUST continuar funcionando, com no máximo uma execução de recuperação por inicialização, sem gerar duplicidade com o disparo normal corrigido.
- **FR-014**: A configuração efetiva existente (persistido → env → default) MUST continuar sendo a única fonte de parâmetros do agendador; a lógica de configuração não deve ser duplicada, e alterações pela tela continuam aplicando sem reinício.
- **FR-015**: Se o aviso de análise estática sobre a referência de tipagem da configuração efetiva for tratado, a correção MUST ser restrita à referência de tipo (mecanismo seguro equivalente a importação condicional de tipos), sem alterar a arquitetura de imports.

### Problema C — Acompanhamento da restauração durante manutenção

- **FR-016**: Durante uma restauração em andamento, a tela de acompanhamento (lista de backups) MUST permanecer acessível ao operador para exibir o estado da operação (fase/mensagem/término), reutilizando o mecanismo existente de consulta do estado da restauração — sem criar um segundo mecanismo de status.
- **FR-017**: O modo de manutenção MUST continuar existindo e bloqueando operações incompatíveis durante a restauração; a exceção de acompanhamento é somente leitura e restrita ao fluxo de restauração.
- **FR-018**: Nenhuma operação de escrita MAY ser liberada pela exceção de acompanhamento: geração de backup, execução de restauração, salvamento de configurações e demais operações de dados continuam bloqueadas durante o ciclo.
- **FR-019**: A exceção de acompanhamento MUST ser específica, explícita, documentada e testada; é proibido bypass global de manutenção, desabilitar autenticação, ignorar autorização (a tela mantém autenticação e permissão existentes) ou liberar endpoints administrativos indevidamente.
- **FR-020**: A tela de acompanhamento MUST degradar de forma controlada quando dados de listagem estiverem momentaneamente indisponíveis durante o ciclo (exibir o estado da operação em vez de página de erro).
- **FR-021**: Após a conclusão da restauração (sucesso ou falha), o modo de manutenção MUST ser encerrado automaticamente e a tela voltar ao comportamento normal completo.
- **FR-022**: Endpoints que hoje devem permanecer bloqueados durante a manutenção MUST continuar retornando o comportamento atual de manutenção.

### Segurança e auditoria (transversal)

- **FR-023**: Nenhuma senha, segredo, credencial ou caminho com credencial MAY ser registrado em logs, auditoria ou mensagens como consequência desta correção.
- **FR-024**: Os eventos de auditoria existentes de backup manual, automático, falha, retenção, pré-restauração e restauração MUST permanecer sendo emitidos pela trilha existente, sem novo mecanismo de auditoria.
- **FR-025**: Nenhuma alteração de RBAC, autenticação, schema de banco, integração AD ou layout global MAY ser feita além do estritamente necessário para as correções.

### Key Entities

- **BackupRecord** (existente): registro determinístico por tentativa de geração — arquivo (único), tipo (MANUAL/AUTOMATICO/PRE_RESTAURACAO), status, timestamp UTC, tamanho, hash, motivo de remoção pela retenção. É a fonte da coluna "Tipo".
- **Configuração efetiva de backup** (existente): parâmetros correntes do agendador/retenção com precedência persistido → env → default, relida periodicamente.
- **Estado de manutenção/restauração em memória** (existente): indicador de ciclo em andamento, fase corrente, horário de início e resultado — consumido pelo acompanhamento e pelas proteções do agendador.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Após uma restauração concluída, 100% dos arquivos de backup presentes no disco que possuíam registro com tipo conhecido exibem o tipo correto na tela — zero ocorrências de "—" por perda de registro (verificável pelo cenário de teste da Story 1).
- **SC-002**: Com o backup automático habilitado e o horário configurado alcançado, o backup é gerado exatamente 1 vez por ciclo: 1 registro AUTOMATICO com status de sucesso no ciclo corrente e nenhum adicional nos ticks seguintes (verificável com relógio simulado nos cenários 1, 2 e 3 da Story 2).
- **SC-003**: Durante uma restauração em andamento, a tela de acompanhamento responde com sucesso ao operador autenticado e autorizado, enquanto os endpoints de escrita permanecem bloqueados; após o término, a tela volta ao normal sem intervenção (cenários da Story 3).
- **SC-004**: A suíte de testes existente completa permanece verde (exceto testes diretamente ligados aos comportamentos alterados por esta spec), sem regressão em funcionalidades não relacionadas.
- **SC-005**: Nenhuma alteração fora do escopo dos três problemas: os fluxos de criação de backup, retenção, auditoria, permissões e demais módulos permanecem intocados.

## Assumptions

- Deploy de processo único (um processo de aplicação), como o sistema opera hoje — as proteções em memória continuam válidas sob essa premissa.
- O tipo dos registros perdidos pelo import é recuperável a partir do próprio sistema (estado existente antes da substituição do banco, capturado pelo ciclo), sem inferência por nome de arquivo — todos os tipos compartilham o mesmo padrão de nome.
- Arquivos de backup anteriores à existência de registros não têm tipo recuperável e continuam exibindo "—" (comportamento atual, não é regressão).
- A política de fuso existente (persistência em UTC, exibição local) e o padrão de nome dos arquivos permanecem inalterados.
- As features 015–022 (backup/restauração/configuração/retenção) representam o comportamento-base a preservar; esta spec corrige desvios pontuais sobre esse comportamento, não os redesenha.
