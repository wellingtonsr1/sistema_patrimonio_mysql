# Feature Specification: Destino Externo para Backups (Pasta de Rede/NAS)

**Feature Branch**: `045-backup-destino-externo`

**Created**: 2026-09-26

**Status**: Draft

**Input**: Implementar no SisPatrimônio Pro suporte a **cópia externa dos backups existentes**, aproveitando integralmente o mecanismo de backup já implementado (manual local, automático local, validação de integridade, histórico, restauração, pré-restauração, retenção, auditoria e configuração). A feature NÃO recria o sistema de backup: acrescenta a dimensão **DESTINO** (LOCAL | EXTERNO) à dimensão existente **TIPO** (MANUAL | AUTOMATICO). Fluxo conceitual: backup local gerado → validado → (se externo habilitado) copiar para destino externo → validar cópia (SHA-256) → registrar resultado/auditoria. Primeiro destino: **pasta de rede / NAS** montada no sistema operacional (ex.: `/mnt/backup-sispatrimonio` ou `\\servidor\Backups\SisPatrimonio`). Regras máximas: backup local permanece obrigatório e anterior à cópia; cópia atômica; falha externa nunca invalida o local; default DESABILITADO; zero segredos em logs/auditoria; alteração pequena e localizada.

## Estado atual analisado (fatos do repositório — leitura prévia)

| Fato verificado | Relevância |
|---|---|
| Serviço único `app/services/backup_service.py`: `_BACKUP_NAME_RE` (L59, `backup_YYYYMMDD_HHMMSS_microsec.sql[.gz]`), `BackupService.generate_backup` (dump → gzip → **SHA-256 calculado no streaming** L735–742 → registro `_record_backup_success` L361), validação de leitura gzip + hash (`_gzip_read_status` L831), `BackupError`, guarda de restauração (`restore_in_progress` L293, `_restore_slot` L317) | Ponto de acoplamento da cópia externa: APÓS `_record_backup_success` (arquivo final válido, com hash) |
| `BackupRecord` (`app/models/backup_record.py`): `filename` UNIQUE, `backup_type` = MANUAL \| AUTOMATICO \| PRE_RESTAURACAO (vocabulário controlado), `status` = SUCCESS \| FAILURE, `size_bytes`, `sha256`, `error_description` controlado (nunca segredos), `removed_at`/`removed_reason` preenchidos EXCLUSIVAMENTE pela retenção | Modelo local intocado; o **resultado externo por backup** vive em tabela nova aditiva (mesmo princípio zero-ALTER da configuração — clarificação) |
| Retenção: executada no `backup_scheduler.py` (GFS diário/semanal/mensal + `keep_pre_restore`; `_pre_restore_candidates` L564, `_is_anchor_*` L539/550); remoção física preenche `removed_at` sem remover registro | Retenção local intocada; política externa deve ser explicitamente definida (não presumir) |
| Scheduler: thread única com `_AUTO_LOCK = threading.Lock()` (L261), `_run_scheduled_backup` (L435), catch-up (`_should_catch_up` L244), proteção contra execução simultânea e contra restore em andamento | Nenhum scheduler novo; a cópia externa engata no fluxo existente dentro das proteções atuais |
| Configuração: `BackupConfig` singleton id=1 (`app/models/backup_config.py`) com 8 campos operacionais (agendamento + retenção); `backup_config_service.get_effective_config` (L106) resolve persistido → env → default; **docstring explicita: nenhum campo com segredo/caminho técnico** (MYSQLDUMP_PATH/BACKUP_DIR ficam em env) | Extensão de configuração segue este padrão; caminho do destino externo é dado operacional novo — decisão de armazenamento (singleton vs. estrutura aditiva) no plan, respeitando o mecanismo aditivo (`Base.metadata.create_all` em `init_db()`; **sem Alembic/ALTER** no projeto) |
| Rotas: `app/web/admin_routes.py` — GET `/admin/backups` (L816), POST `/gerar` (L884), download (L895), GET/POST `/configuracoes` (L923/L1170, evento `ACTION_BACKUP_CONFIG_UPDATED` L1222), restaurar (L1242/1277), status polling (L1297) — todas com gates `backup.gerenciar` ou `backup.restaurar` | Tela existente a estender (configuração + histórico + status do destino + botão "Testar destino"); RBAC existente reutilizado |
| Auditoria: `app/services/audit_service.py` L62–117 — eventos literais PT (`BACKUP_FALHA`, `BACKUP_RESTORE_*`, `BACKUP_CONFIGURACAO_ALTERADA`) com dicionário de labels | 4 eventos novos no mesmo padrão: configurado/testado/sucesso externo/falha externa |
| Tela: `app/web/templates/admin/backups.html` — formulário de configuração (L161), card "Gerar backup" (L238), histórico com badges por tipo incl. PRE_RESTAURACAO (L277), ações restaurar/download (L295–299) | Extensões de UI localizadas nesta tela; nenhuma tela nova |
| Testes existentes robustos: `test_backup_manual.py` (RBAC da tela L579, evento literal L600), `test_backup_automatico.py` (disparo/catch-up/exclusão mútua), `test_backup_config.py` (config intacta L772, manual intocado L494), `test_backup_records.py`, `test_backup_restore.py`, `test_backup_retencao.py` | Suíte como regressão; **o pedido EXIGE testes automatizados novos (seções 36/37, cenários A–L)** — padrão diferente das features visuais 036–044 |
| Banco em produção MariaDB; dumps via `mysqldump` binário (`_resolve_tool_executable`); sanitização de stderr e de segredos já implementada (`_sanitize_stderr` L420, `_dump_env` L84 — senha via env, nunca argv) | Cópia é de **arquivo** (`.sql.gz`), independente de banco; padrão de segredos (env, não argv/logs) já existe e será seguido |

## Decisões registradas pelo solicitante (2026-09-26)

- **C-1 (seções 2/44)**: **Extensão, não novo mecanismo** — os tipos continuam apenas MANUAL | AUTOMATICO; a nova dimensão é DESTINO: LOCAL | EXTERNO. Proibido criar "backup manual externo"/"backup automático externo" independentes, novo scheduler, novo sistema de retenção ou de auditoria.
- **C-2 (seções 3/11)**: **Local obrigatório e anterior** — a cópia externa só acontece depois de gerar → finalizar → validar → considerar válido pelo mecanismo existente; nunca copiar arquivo temporário/parcial/inválido; nunca "gerar somente externo".
- **C-3 (seção 6)**: **Primeiro destino = pasta de rede/NAS** montada no SO (ex.: `/mnt/backup-sispatrimonio`, `\\servidor\Backups\SisPatrimonio`); sem múltiplos provedores por antecipação; arquitetura preparada para extensão futura sem complexidade desnecessária.
- **C-4 (seções 7/28)**: **Sem credenciais na aplicação** — preferir pasta já montada pelo SO (sem senha armazenada); se autenticação for exigida no futuro: nada em texto puro, logs, auditoria, nome de arquivo ou argv; registrar a limitação antes de implementar armazenamento de credenciais.
- **C-5 (seção 8)**: **Configuração na tela existente** — estender "Configurações de Backup" com o mínimo: Ativado, Tipo (Pasta de rede/NAS), Destino (caminho), botão "Testar destino"; nenhuma tela nova de administração.
- **C-6 (seção 9)**: **Default DESABILITADO** — sem configuração explícita, nenhum comportamento externo acontece; o fluxo atual permanece exatamente como está.
- **C-7 (seções 12/13/33)**: **Cópia atômica + validação** — copiar para nome temporário → completar/flush → validar → renomear para o nome definitivo; validação por existência + tamanho + **SHA-256 comparado ao hash do local**; divergente = cópia inválida + falha registrada.
- **C-8 (seções 14/34)**: **Falha externa nunca afeta o local** — LOCAL = SUCESSO / EXTERNO = FALHA; não apagar, não invalidar, não restaurar, não alterar banco, não interromper a aplicação/scheduler; registrar falha + auditoria + painel + permitir nova tentativa; timeout apropriado, sem bloqueio indefinido.
- **C-9 (seção 17)**: **Dump único por execução** — o destino externo não dispara nova execução do dump; a cópia é do arquivo local já gerado.
- **C-10 (seção 18)**: **Restauração externa FORA do escopo** — o fluxo é BACKUP → CÓPIA EXTERNA, nunca RESTORE ← EXTERNO nesta feature; restauração e pré-restauração existentes intocadas.
- **C-11 (seção 19)**: **Pré-restauração É copiado** — a finalidade do mecanismo atual é intocada; todos os backups locais válidos, **incluindo PRE_RESTAURACAO**, são copiados ao destino (clarificação 2026-09-26 — proteção máxima: o destino cobre também a perda do servidor no meio de uma restauração); o acúmulo de artefatos transitórios no destino é aceito, sem exclusão automática sem regra explícita (C-12).
- **C-12 (seções 20/21/31)**: **Retenção** — a política local continua intocada e **não pode apagar a única cópia existente do backup externo**; **esta feature NÃO implementa retenção externa automática** — as cópias acumulam no destino (decorrência das clarificações: acúmulo aceito + proibição de exclusão sem regra clara), com limpeza eventualmente manual operacional; uma política externa própria fica como extensão futura explicitamente definida e auditada; sem apagar backups para liberar espaço.
- **C-13 (seção 25)**: **RBAC existente** — usuários com `backup.gerenciar` configuram/ativam/testam o destino e alteram retenção externa (se existir); nenhuma permissão nova.
- **C-14 (seção 26)**: **Auditoria existente** — registrar (nomes finais no padrão dos eventos atuais): destino configurado, destino testado, cópia externa com sucesso, cópia externa com falha; nunca registrar senha/credencial/token/segredo.
- **C-15 (seção 32)**: **Nomenclatura** — o arquivo externo mantém **o mesmo nome** do backup local (vínculo inequívoco); sem nomes que sugiram backup independente.
- **C-16 (seção 35)**: **Retry imediato limitado** — dentro do mesmo ciclo de backup, a cópia é re-tentada até um limite definido no plan (sugestão: 3 tentativas com espera curta entre elas) antes de registrar a falha externa definitiva; timeout por tentativa e tempo total limitado, sem loops infinitos e sem bloquear a thread principal além desse tempo; o resultado registrado é o **final** (um único registro externo por backup, sem duplicar registro por tentativa); após esgotar o limite, a re-tentativa volta a ocorrer apenas no próximo ciclo de backup (sem mecanismo de retry novo além disso).
- **C-17 (seções 36/37)**: **Testes automatizados obrigatórios** — cobrir os cenários A–L (manual/auto com e sem externo, destino indisponível, sem permissão, integridade adulterada, duplicidade, restauração, retenção, reinicialização, desativação) + suíte completa de regressão; em teste, o "destino externo" é um diretório temporário (comportamento de pasta idêntico).
- **C-18 (seção 38/44)**: **Alteração pequena e localizada** — proibido refatorar o sistema, trocar banco/framework/frontend ou alterar funcionalidades não relacionadas; se houver duas soluções, escolher a localizada.

## Clarifications

### Session 2026-09-26

- Q: Os backups do tipo PRE_RESTAURACAO (gerados antes de uma restauração) devem também ser copiados para o destino externo? → A: Sim — todos os backups locais válidos, incluindo PRE_RESTAURACAO, são copiados (proteção máxima: o destino cobre também a perda do servidor no meio de uma restauração); o acúmulo de artefatos transitórios no destino é aceito, sem exclusão automática sem regra explícita (C-12).
- Q: Onde a configuração do destino externo deve ser persistida? → A: Em **tabela nova aditiva** (singleton id=1, padrão BackupConfig/ADSettings), criada pelo mecanismo schema atual do projeto (create_all, idempotente, **zero ALTER** em tabelas existentes) — funciona no banco de produção sem migração manual; nenhum campo com segredo.
- Q: Qual deve ser a estratégia de nova tentativa (retry) quando a cópia externa falha? → A: **Retry imediato limitado dentro do mesmo ciclo** — re-tentar até um limite definido no plan (sugestão: 3 tentativas com espera curta), com timeout por tentativa e tempo total limitado; resultado final único registrado (sem duplicar registro por tentativa); após esgotar, nova tentativa só no próximo ciclo (C-16).
- Q (decorrência do princípio zero-ALTER): o resultado externo por backup (sucesso/falha, hash, motivo) é registrado em colunas novas de `backup_records` ou em estrutura própria? → A: Em **tabela nova aditiva** vinculada por `filename` — mesmo princípio da configuração: nenhuma coluna nova em tabelas existentes, create_all idempotente.

Demais pontos deliberadamente delegados à análise do plan: detalhes de implementação da tabela aditiva de resultados e do fluxo de acoplamento no serviço.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cópia externa opcional após backup local válido (Priority: P1)

Um administrador habilita o destino externo (pasta de rede/NAS). A partir daí, **todo backup local válido** — manual ou automático — é copiado para o destino, com validação por SHA-256 e registro do resultado; o backup local permanece intacto e obrigatório em todos os casos, e com o destino desabilitado nada muda no comportamento atual.

**Why this priority**: é o núcleo do pedido — proteção adicional dos backups contra perda do servidor.

**Independent Test**: com destino habilitado (diretório temporário em teste/NAS real em produção), gerar backup manual e automático e confirmar: arquivo externo com o mesmo nome, mesmo SHA-256, registros e auditoria corretos; desabilitar e confirmar que nenhum acesso externo ocorre.

**Acceptance Scenarios**:

1. **Given** destino externo DESABILITADO, **When** um backup manual ou automático é executado, **Then** o comportamento é idêntico ao atual (somente local) e nenhuma tentativa externa ocorre (Testes A/B/L).
2. **Given** destino externo HABILITADO, **When** um backup manual é gerado e validado, **Then** a cópia é criada atomicamente no destino com o mesmo nome, validada por SHA-256 idêntico ao local e registrada como sucesso (Teste C).
3. **Given** destino externo HABILITADO, **When** o backup automático gera um backup válido dentro das proteções existentes (lock, catch-up, restore em andamento), **Then** a cópia externa ocorre após a validação local, com dump único por execução (Testes D/H).
4. **Given** um backup inválido ou ainda temporário, **When** o ciclo de cópia avalia o arquivo, **Then** nada é copiado — somente backups válidos pelo mecanismo existente seguem para o destino (C-2).

---

### User Story 2 - Configuração, teste e monitoramento na tela existente (Priority: P2)

O administrador configura o destino externo na própria tela de Configurações de Backup (ativado, tipo pasta de rede/NAS, caminho), testa o destino com uma verificação leve (acesso, escrita, leitura, remoção de temporário) e acompanha no histórico e no painel: resultado local vs. externo por backup e status do último resultado do destino — sem segunda tela e sem quebrar a tela atual.

**Why this priority**: sem configuração/teste/visibilidade, o mecanismo do US1 não é operável de forma segura.

**Independent Test**: acessar Configurações de Backup com `backup.gerenciar`: salvar configuração, testar destino (com destino válido e inválido), verificar colunas Local/Externo no histórico e o status do destino; conferir auditoria e ausência de segredos.

**Acceptance Scenarios**:

1. **Given** um administrador com `backup.gerenciar`, **When** ele salva "Backup externo: ativado, Pasta de rede/NAS, /mnt/backup-sispatrimonio" e clica "Testar destino", **Then** o teste verifica destino configurado, acesso, permissão de escrita, criação/leitura/remoção de arquivo temporário (sem backup completo) e o resultado é exibido e auditado.
2. **Given** backups existentes no histórico, **When** a tela é exibida, **Then** cada backup mostra Local ✓/✗ e Externo ✓/✗ (com motivo quando falha), preservando todas as informações atuais (nome, data, tipo, status, integridade, tamanho).
3. **Given** o painel de status, **When** o destino está disponível ou indisponível, **Then** a tela mostra o último resultado (SUCESSO/FALHA com motivo) e a data da última cópia/tentativa — sem confundir destino indisponível com backup local inválido.
4. **Given** um usuário sem `backup.gerenciar`, **When** ele tenta configurar/testar o destino, **Then** o acesso é negado pelas regras RBAC existentes.

---

### User Story 3 - Resiliência: falhas externas não afetam o backup local (Priority: P2)

Com o destino externo habilitado mas indisponível (rede fora, sem permissão de escrita, sem espaço), o sistema mantém o backup local válido, registra a falha externa com motivo, audita o evento, exibe no painel e permite nova tentativa posteriormente — sem derrubar scheduler ou aplicação e sem bloqueios indefinidos (timeout apropriado).

**Why this priority**: garante que a extensão nunca degrade o mecanismo existente — requisito central de preservação (seção 44).

**Independent Test**: simular destino indisponível/sem permissão/arquivo adulterado e confirmar: local preservado, falha registrada + auditada, aplicação íntegra, retry possível (Testes E/F/G).

**Acceptance Scenarios**:

1. **Given** destino indisponível (ou sem permissão de escrita), **When** um backup válido é gerado, **Then** LOCAL = SUCESSO e EXTERNO = FALHA com motivo registrado; o local não é apagado, invalidado ou alterado; a aplicação e o scheduler continuam funcionando (Testes E/F).
2. **Given** uma cópia externa adulterada em teste, **When** a validação por SHA-256 compara local e externo, **Then** hashes divergentes resultam em cópia externa inválida + falha registrada (Teste G).
3. **Given** espaço insuficiente no destino (quando tecnicamente verificável), **When** a cópia é tentada, **Then** EXTERNO = FALHA com motivo, sem exclusões automáticas no destino (C-12/§31).
4. **Given** a execução repetida da mesma operação, **When** o ciclo roda novamente, **Then** nenhuma cópia indevida ou registro duplicado é criado (Teste H); restauração, pré-restauração e retenção continuam funcionando (Testes I/J); após reinicialização, a configuração persiste e o scheduler continua íntegro (Teste K).

---

### Edge Cases

- **Destino indisponível / rede fora**: até o limite de re-tentativas no ciclo (C-16); falha externa definitiva registrada com motivo; local preservado; sem derrubar scheduler/aplicação; sem bloqueio indefinido (timeout) — nova tentativa no próximo ciclo.
- **Destino sem permissão de escrita**: idem — LOCAL = SUCESSO, EXTERNO = FALHA (Teste F).
- **Hash divergente (cópia adulterada/instável)**: cópia externa considerada inválida; falha registrada; o nome definitivo externo não permanece com aparência de válido (C-7).
- **Arquivo parcial no destino**: nunca visível como backup válido — cópia atômica com nome temporário até a validação (C-7).
- **Espaço insuficiente** (quando verificável): falha externa registrada; sem exclusões automáticas para liberar espaço (C-12).
- **Restore em andamento**: proteção existente respeitada — nenhuma cópia iniciada de backup incompleto e nenhuma corrida com a restauração (§30).
- **Execução simultânea** (manual durante automático): proteções existentes (lock/catch-up) reutilizadas; nenhuma segunda execução de backup ou corrida geração/cópia/retenção (§29).
- **Reinicialização do serviço**: configuração persistida; scheduler continua; destino permanece utilizável; nenhum estado inconsistente (Teste K).
- **Desativação posterior**: volta a valer somente local — nenhuma tentativa externa (Teste L).
- **Backup de pré-restauração**: finalidade intocada; **copiado ao destino como os demais** (clarificação) — acúmulo no destino aceito, sem exclusão automática (C-12).
- **Retenção local**: execução atual preservada (Teste J); nunca apaga a única cópia externa (C-12).
- **Caminho inválido/perigoso no destino**: validado antes do uso (sem traversal, sem execução de shell com entrada do usuário — §27).
- **Segredos**: nunca em logs, auditoria, argv ou nomes de arquivo (C-4/C-14).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST tratar o destino externo como **nova dimensão de destino** (LOCAL | EXTERNO) sobre os tipos existentes (MANUAL | AUTOMATICO | PRE_RESTAURACAO), sem criar mecanismos de backup independentes, sem novo scheduler e sem novo sistema de retenção/auditoria (C-1).
- **FR-002**: O backup local MUST permanecer **obrigatório e anterior**: a cópia externa só ocorre após o backup local estar gerado, finalizado e **válido pelo mecanismo existente** (status SUCCESS com SHA-256); arquivo temporário, parcial ou inválido NUNCA é copiado (C-2).
- **FR-003**: O primeiro tipo de destino MUST ser **pasta de rede/NAS** (caminho montado no SO, ex.: `/mnt/backup-sispatrimonio` ou `\\servidor\Backups\SisPatrimonio`), sem múltiplos provedores; a arquitetura MAY ser preparada para futuros destinos sem complexidade adicional (C-3).
- **FR-004**: Por padrão o destino externo MUST estar **DESABILITADO** e, enquanto desabilitado, o comportamento atual MUST permanecer exatamente o mesmo (nenhuma tentativa externa) (C-6).
- **FR-005**: A configuração MUST ser adicionada à tela existente de Configurações de Backup com o mínimo necessário (Ativado; Tipo: Pasta de rede/NAS; Destino: caminho; "Testar destino") e MUST ser persistida em **tabela nova aditiva** (singleton id=1, padrão BackupConfig/ADSettings), criada pelo mecanismo de schema do projeto (create_all idempotente, **zero ALTER** em tabelas existentes — clarificação), sem apagar/recriar dados existentes e **sem armazenar segredos** (C-5; §39).
- **FR-006**: A operação "Testar destino" MUST verificar apenas o necessário (destino configurado; acesso; permissão de escrita; criação, leitura e remoção de arquivo temporário) e NÃO MUST executar backup completo; resultado exibido e auditado (§24).
- **FR-007**: A cópia MUST ser **atômica**: nome temporário → cópia completa (flush/fechamento) → validação → renomear para o nome definitivo; o nome definitivo externo só aparece como válido após a cópia completa (C-7).
- **FR-008**: A validação da cópia MUST confirmar existência, tamanho e **SHA-256 idêntico ao do backup local** (quando o local possuir hash — sempre possui no fluxo atual); hashes divergentes = cópia externa inválida + falha registrada (C-7/§33).
- **FR-009**: Em caso de falha externa (destino indisponível, sem permissão, sem espaço, integridade divergente, timeout), o sistema MUST: preservar o backup local (nunca apagar, invalidar, restaurar ou alterar o banco), registrar a falha com motivo controlado (nunca segredos), auditar, informar no painel e permitir nova tentativa posterior — sem interromper aplicação ou scheduler e sem bloqueio indefinido (timeout apropriado) (C-8).
- **FR-010**: O fluxo de cópia MUST valer para **manual e automático** dentro do mecanismo existente: scheduler, horário, frequência, catch-up, prevenção de execução simultânea e proteção de restore em andamento continuam funcionando intocados (C-1/§16/§29/§30).
- **FR-011**: O banco MUST ser dumpado **uma única vez por execução** — a cópia externa é do arquivo local já gerado, sem nova execução do dump (C-9).
- **FR-012**: O histórico atual MUST ser estendido (sem segunda tela, sem quebrar a tela) com o resultado externo por backup: Local ✓/✗, Externo ✓/✗ e motivo quando falha, preservando todas as informações existentes (§22).
- **FR-013**: A tela MUST apresentar, quando possível, o **status do destino externo** (disponível/indisponível, última cópia/tentativa, último resultado) sem confundir destino indisponível com backup local inválido (§23).
- **FR-014**: A política de retenção local MUST continuar intocada e NÃO pode apagar a única cópia existente do backup externo; **nenhuma retenção externa automática é implementada nesta feature** (clarificação) — as cópias acumulam no destino e a limpeza é operacional/manual; exclusões automáticas no destino ficam para extensão futura com regra explícita e auditada (C-12).
- **FR-015**: O mecanismo de pré-restauração MUST permanecer com a finalidade atual; backups **PRE_RESTAURACAO válidos MUST também ser copiados** ao destino externo, como os demais tipos (clarificação), sem alteração silenciosa de sua finalidade nem de sua retenção local (`keep_pre_restore` continua local).
- **FR-016**: As operações de configurar/ativar/desativar/testar o destino e alterar retenção externa (se existir) MUST exigir a permissão existente `backup.gerenciar` — nenhuma permissão nova (C-13).
- **FR-017**: A auditoria MUST usar o módulo existente e registrar, no padrão de eventos atual: destino externo configurado, destino testado, cópia externa com sucesso, cópia externa com falha — com usuário (quando aplicável), tipo, nome do backup, destino identificado de forma segura, resultado, motivo e data/hora; **nunca** senha/credencial/token/segredo (C-14).
- **FR-018**: O acesso ao destino MUST tratar o destino como infraestrutura não confiável: caminho validado (sem traversal), sem `shell=True`, sem segredos em argv/logs, argumentos separados quando houver comando externo, verificação de disponibilidade/permissões/espaço quando tecnicamente possível (§27/§31).
- **FR-019**: O arquivo externo MUST manter **o mesmo nome** do backup local (C-15), permanecendo identificável como o mesmo backup.
- **FR-020**: A estratégia de nova tentativa MUST ser **retry imediato limitado dentro do mesmo ciclo** (clarificação): re-tentativas até o limite definido no plan (sugestão: 3) com espera curta entre elas, timeout por tentativa e tempo total limitado; o resultado registrado MUST ser o **final** (um único registro externo por backup, sem duplicidade por tentativa); sem loops infinitos, sem bloquear a thread principal além do tempo total; após esgotar o limite, a re-tentativa ocorre apenas no próximo ciclo de backup (C-16).
- **FR-021**: Testes automatizados MUST cobrir os cenários A–L do pedido (manual/auto × externo on/off, indisponível, sem permissão, integridade adulterada, duplicidade, restauração, retenção, reinicialização, desativação) usando diretório temporário como destino, e a suíte existente MUST permanecer 100% verde (C-17; §37).
- **FR-022**: A implementação MUST ser pequena e localizada: somente alterações indispensáveis para "copiar backups locais válidos para um destino externo configurável"; na dúvida entre soluções, a localizada (C-18).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Com o destino desabilitado, o comportamento é **idêntico ao atual** — comprovado pelos testes A/B/L automatizados (somente local, zero tentativas externas) e pela suíte existente 100% verde.
- **SC-002**: Com o destino habilitado, 100% dos backups locais válidos (manual e automático) geram cópia externa com **mesmo nome e SHA-256 idêntico** ao local (testes C/D), com dump único por execução.
- **SC-003**: Em todos os cenários de falha (indisponível, sem permissão, hash divergente, sem espaço, timeout), o backup local permanece SUCCESS/íntegro e a falha externa é registrada com motivo controlado e auditada — 100% dos testes E/F/G verificando preservação do local (testes E/F/G).
- **SC-004**: Zero duplicidade: execuções repetidas não criam cópias indevidas nem registros duplicados (teste H); zero segundo scheduler/serviço de backup/novo mecanismo de retenção (inspeção de código).
- **SC-005**: Restauração, pré-restauração e retenção existentes permanecem funcionais e intocadas nos testes I/J; a retenção local nunca remove a única cópia externa.
- **SC-006**: Após reinicialização (teste K), a configuração externa persiste e o scheduler/destino permanecem íntegros, sem estado inconsistente.
- **SC-007**: Zero segredos em logs/auditoria/argv/nomes de arquivo (verificação dos eventos e capturas de log nos testes).
- **SC-008**: Suíte completa pytest 100% verde com os novos testes incluídos; cenários manuais do pedido executados quando aplicável (NAS real não existe em dev — limitação registrada).
- **SC-009**: Validação registrada em `specs/045-backup-destino-externo/validacao.md`: resultado de cada teste A–L, suíte final, auditoria verificada e relatório final obrigatório da seção 43 do pedido (arquivos alterados/novos, configuração, fluxos, integridade, falhas, auditoria, testes, limitações — sem inventar resultados).

## Assumptions

- O ambiente alvo possui a pasta de rede/NAS **já montada no sistema operacional** — a aplicação usa o caminho montado e não gerencia credenciais de rede (C-4); credenciais próprias ficam fora desta feature (limitação registrada se um dia forem exigidas).
- Em testes automatizados, o "destino externo" é um **diretório temporário local** — o comportamento de pasta montada é equivalente para cópia/validação/atomicidade; NAS real só no aceite de produção.
- O mecanismo de schema do projeto é `Base.metadata.create_all` **aditivo** (sem Alembic): **tabelas novas** são criadas idempotentemente; a configuração do destino externo vive em **tabela nova aditiva** (clarificação) — nenhuma coluna nova é adicionada a tabelas existentes.
- O SHA-256 já é calculado no fluxo local atual e armazenado em `BackupRecord.sha256` — a comparação da cópia usa esse hash.
- A aplicação roda com permissão de escrita na pasta montada quando o destino está corretamente provisionado (prerrogativa operacional do ambiente).
- Terminologia: "destino externo" = destino configurável de cópia; "backup externo" = cópia validada no destino; o backup **local** permanece a fonte da verdade.

## Fora de escopo

- **Restaurar a partir do destino externo** (fluxo RESTORE ← EXTERNO) — apenas BACKUP → CÓPIA EXTERNA nesta feature (C-10).
- Múltiplos destinos/provedores (S3, nuvem, FTP etc.) — apenas o primeiro destino (pasta de rede/NAS) (C-3).
- Gestão de credenciais de rede pela aplicação (C-4).
- Nova tela de administração, novo scheduler, novo sistema de retenção, novo sistema de auditoria, segunda listagem de histórico (C-1/C-5).
- Refatoração do serviço de backup, troca de banco/framework/frontend, alterações em usuários, RBAC, movimentações, inventário, manutenção, relatórios, autenticação AD ou remoção de funcionalidades (§38).
- Retenção externa automática — as cópias acumulam no destino; limpeza é operacional/manual; política própria fica como extensão futura (C-12, clarificações).
