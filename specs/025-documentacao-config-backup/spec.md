# Feature Specification: Correção da Documentação da Configuração de Backup

**Feature Branch**: `feature-025-documentacao-config-backup`

**Created**: 2026-09-19

**Status**: Draft

**Input**: Auditoria da Feature 024 — Precedência da Configuração de Backup Automático e Retenção. Corrigir exclusivamente a documentação relacionada à configuração do Backup Automático e da Política de Retenção, alinhando-a ao comportamento real já existente. A implementação está funcionalmente correta; esta feature é **exclusivamente documental**.

## Regra fundamental

> **Não alterar código funcional para corrigir um problema que a auditoria confirmou não existir.** A Feature 024 concluiu: configuração da tela = fonte efetiva; `config.py` = fallback/bootstrap; **não existe dupla fonte de verdade**. Esta feature apenas torna essa realidade explícita na documentação. **Se uma alteração não for necessária para corrigir AT-1, AT-2 ou AT-3 na documentação, NÃO fazer essa alteração.** (Constitution, Princípio I — preservação e escopo; Princípio XI — documentação fiel.)

## Realidade verificada (base da correção — reconfirmar antes de editar)

*Verificado na auditoria 024 (2026-09-19) e a reconfirmar no código atual antes de qualquer edição (briefing §24 — não copiar cegamente).*

1. **Relatório-fonte**: `specs/024-auditoria-config-backup/relatorio.md` — veredito global **OK** + 3 achados **ATENÇÃO** (AT-1, AT-2, AT-3); zero INCONSISTÊNCIA/RISCO/BLOQUEADOR; as 8 constantes = "DEVE SER MANTIDA COMO FALLBACK".
2. **AT-1**: `docs/GUIA_DE_MANUTENCAO.md:113` afirma que as env `BACKUP_*` são "fallback **da primeira inicialização**" — impreciso: o fallback é **por campo, a cada resolução** da configuração efetiva enquanto o campo persistido estiver indefinido (`backup_config_service.py:122–185`, `_first_defined`/`_effective_int`), além do bootstrap/fallback de boot.
3. **AT-2**: o **fallback de boot** do scheduler (`backup_scheduler.py:107–124` — falha de leitura → mantém snapshot anterior; sem snapshot → monta bootstrap env/default) **não consta** da precedência documentada (`README.md:972–973`, comentário `app/config.py:63–66`).
4. **AT-3**: `auto_enabled` é o **único campo não-nullable** (`app/models/backup_config.py:23`); a efetiva lê direto a linha (`backup_config_service.py:155`), logo `BACKUP_AUTO_ENABLED` **nunca** é fallback dinâmico desse campo (diferente dos outros 7) — continua valendo no fallback de boot (`backup_scheduler.py:117`). Assimetria correta, não documentada.
5. **Comportamento real a documentar** (confirmado na 024): precedência por campo persistido → env → default 020 via `get_effective_config()` (`backup_config_service.py:106–198`); snapshot renovado **a cada 30 s** (`_TICK_SECONDS = 30`, `backup_scheduler.py:64,799`) — alteração pela tela aplicada **sem reinício**; retenção consome a efetiva (`:625–628`); instalação nova nasce **desativada** (`config.py:67`); defaults `false/daily/02:00/0/30/12/12/0` (`config.py:67–87` = `_DEFAULT_*` `backup_config_service.py:25–32`).
6. **Estado atual da documentação**: `README.md:972–995` — fiel na precedência, no default, no tick de 30 s, no catch-up e na retenção (preservar o que está correto); falta mencionar o fallback de boot (AT-2). `docs/ARQUITETURA_E_MANUTENCAO.md:264` e `:1215` — fiéis (preservar). `docs/GUIA_DE_MANUTENCAO.md:113` — impreciso (AT-1).
7. **Arquivos editáveis** (briefing §25): `README.md`, `docs/GUIA_DE_MANUTENCAO.md`, `docs/ARQUITETURA_E_MANUTENCAO.md` — **somente** os que contiverem documentação incorreta/incompleta; não alterar todos obrigatoriamente. `app/config.py` NÃO é alterado (briefing §26 — salvo inconsistência factual grave que impeça documentar o comportamento; preferir sempre docs; a 024 não encontrou necessidade funcional).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Corrigir o papel das variáveis de ambiente (AT-1) (Priority: P1)

Um mantenedor lê `docs/GUIA_DE_MANUTENCAO.md` e encontra a afirmação de que as env `BACKUP_*` são fallback "da primeira inicialização". A documentação é corrigida para explicar o papel real: **fallback por campo durante a resolução da configuração efetiva, enquanto o respectivo campo persistido estiver indefinido**, além da participação no **bootstrap/fallback de boot** do scheduler. Nenhuma afirmação de "somente primeira inicialização" permanece em nenhum arquivo de documentação.

**Nota (analyze-F1)**: a edição E1 (contrato §1.1) já incorpora, neste mesmo trecho, a menção da particularidade do `auto_enabled` (AT-3) — parte do US3 entregue antecipadamente; o restante do AT-3 (nota no README, edição E3) permanece no US3 (T007).

**Why this priority**: é a única afirmação hoje **incorreta** (não apenas incompleta) — pode levar um operador a acreditar que a env volta a valer ao reiniciar ou que perde o efeito após o primeiro boot.

**Independent Test**: ler a documentação corrigida e confirmar que (a) não existe mais a frase "fallback da primeira inicialização" aplicada às `BACKUP_*`, e (b) a explicação corresponde ao código (`backup_config_service.py:122–185`).

**Acceptance Scenarios**:

1. **Given** `docs/GUIA_DE_MANUTENCAO.md` corrigido, **When** a frase sobre as envs `BACKUP_*` é lida, **Then** descreve fallback por campo dinâmico + bootstrap de boot, fiel ao código.
2. **Given** qualquer outro arquivo de documentação editável, **When** procuradas afirmações equivalentes ("somente na primeira inicialização"), **Then** nenhuma permanece.
3. **Given** a documentação corrigida, **When** conferida com `backup_config_service.py`, **Then** cada afirmação tem correspondência no código.

---

### User Story 2 - Documentar o fallback de boot do scheduler (AT-2) (Priority: P1)

A precedência documentada ganha a menção explícita do caminho excepcional de boot: em caso de **falha na leitura da configuração efetiva**, o scheduler **mantém o snapshot anterior** quando disponível; **sem snapshot**, utiliza o **bootstrap** por env/default. Descrito como mecanismo de segurança/fallback — sem sugerir que seja caminho normal.

**Why this priority**: sem essa menção, a precedência documentada parece absolvida de exceções que existem no código — lacuna apontada pela auditoria.

**Independent Test**: a seção de precedência da documentação descreve os 3 níveis normais + o caminho de exceção (falha → snapshot anterior → bootstrap), correspondendo a `backup_scheduler.py:93–124`.

**Acceptance Scenarios**:

1. **Given** a documentação de precedência, **When** lida, **Then** contém o diagrama/texto do fallback de boot (falha → snapshot anterior? sim → mantém; não → env/default).
2. **Given** um operador, **When** lê "o que acontece se o banco não puder ser lido?", **Then** encontra a resposta exata do comportamento real.
3. **Given** o texto inserido, **When** conferido com `backup_scheduler.py:107–124`, **Then** condição, ordem e resultado coincidem (incluindo o log "mantendo snapshot anterior").

---

### User Story 3 - Documentar a particularidade de BACKUP_AUTO_ENABLED (AT-3) (Priority: P1)

A documentação explica, quando tecnicamente apropriado, que o campo persistido `auto_enabled` é **não nulo**: após existir a linha `backup_config`, a variável `BACKUP_AUTO_ENABLED` **não é utilizada como fallback dinâmico** desse campo na resolução normal — permanece no **bootstrap/fallback de boot** e como valor inicial de instalações novas. O texto deixa claro que esse comportamento é intencional e seguro (estado sempre conhecido, default desativado).

**Why this priority**: é a única assimetria entre os 8 campos — sem explicação, parece omissão ou bug.

**Independent Test**: a documentação menciona a particularidade do `auto_enabled` (não-nullable) sem sugerir alteração de modelo ou de lógica.

**Acceptance Scenarios**:

1. **Given** a documentação das variáveis, **When** a linha de `BACKUP_AUTO_ENABLED` é lida, **Then** registra a particularidade (env não consultada dinamicamente após a linha existir; segue valendo no bootstrap/instalação nova).
2. **Given** a explicação, **When** conferida com `app/models/backup_config.py:23` e `backup_config_service.py:155`, **Then** é factual.
3. **Given** o leitor, **When** termina a leitura, **Then** entende que não há inconsistência nem necessidade de mudança no modelo.

---

### User Story 4 - Consolidar o fluxo completo na documentação (Priority: P1)

Os documentos passam a responder explicitamente as perguntas do operador/desenvolvedor: onde configuro (tela), onde fica salvo (`backup_config`, singleton), quem resolve (`get_effective_config()` — precedência persistido → env → default com diagrama), quem usa (scheduler e retenção consomem a configuração **efetiva**, não as constantes), para que serve `config.py` (defaults/fallback/bootstrap/instalações novas/ambientes automatizados — nunca descrito como fonte efetiva normal), existe dupla fonte de verdade (não — configuração persistida ≠ configuração concorrente), precisa reiniciar (não — janela ≤ 30 s, `_TICK_SECONDS = 30`), primeiro uso (campos indefinidos → env → default; `auto_enabled` nasce desativado). As 8 variáveis são documentadas com finalidade, default, quando funcionam como fallback, relação com o valor persistido e particularidade; os defaults com seu significado (desativado, diário, 02:00 America/Recife, domingo, 30 dias, 12 semanas, 12 meses, preservar todos). A separação parâmetros operacionais × credenciais/segredos é mantida (nenhuma `BACKUP_*` apresentada como segredo; nenhuma credencial adicionada).

**Why this priority**: é a entrega central — a documentação dizendo exatamente o que o sistema já faz, nos 3 arquivos editáveis, sem contradição interna.

**Independent Test**: um leitor nova consegue responder às perguntas do briefing §38 apenas lendo a documentação, e cada resposta confere com o código atual.

**Acceptance Scenarios**:

1. **Given** a documentação atualizada, **When** as 8 variáveis são conferidas, **Then** cada uma tem finalidade + default + papel de fallback + relação com o persistido (e particularidade, quando houver).
2. **Given** a documentação atualizada, **When** os textos de scheduler e retenção são lidos, **Then** ambos são descritos como consumidores da configuração efetiva (nunca das constantes diretamente).
3. **Given** qualquer parte da documentação, **When** procuradas sugestões de dupla fonte concorrente ou de reinício obrigatório, **Then** nenhuma existe; a atualização dinâmica (≤ 30 s) está documentada.

---

### User Story 5 - Validação e relatório final (Priority: P2)

Após as edições: verificação de links internos, referências a arquivos, nomes de variáveis, defaults, exemplos, comandos e ausência de afirmações contraditórias entre os arquivos; `git status`/`git diff --stat`/`git diff` confirmam alteração **somente em documentação** (qualquer alteração em `app/`, `tests/`, `data/`, `.env` é investigada e revertida). Relatório final entrega: arquivos alterados, o que foi corrigido em cada, tratamento de AT-1/AT-2/AT-3, confirmações (config.py/scheduler/service/banco/testes intocados; 8 constantes preservadas), verificações realizadas e eventuais divergências registradas para feature futura.

**Why this priority**: garante entrega verificável e preservação comprovada do sistema.

**Independent Test**: executar o diff e o checklist de verificação; conferir o relatório contra o que foi alterado.

**Acceptance Scenarios**:

1. **Given** as edições concluídas, **When** `git diff --stat` é inspecionado, **Then** somente arquivos de documentação aparecem.
2. **Given** o relatório final, **When** lido, **Then** responde os 13 itens do briefing §39.
3. **Given** a documentação final, **When** as afirmações são cruzadas entre arquivos, **Then** não existe contradição (mesma precedência, mesmos defaults, mesmo papel do config.py em todos).

---

### Edge Cases

- **Código divergiu da auditoria 024** (briefing §24/§37): NÃO corrigir código; registrar a divergência, determinar se é documental ou funcional; se funcional, **interromper** a alteração e registrar como ponto de atenção para feature separada; se documental, documentar o **comportamento atual** (nunca copiar informação antiga).
- **Inconsistência factual grave em `app/config.py`** (briefing §26): única exceção prevista para tocar código — e ainda assim preferencialmente não alterar; a auditoria não encontrou necessidade funcional; qualquer exceção é justificada no relatório.
- **Arquivo sem informação incorreta/incompleta**: NÃO alterar (briefing §25) — se `docs/ARQUITETURA_E_MANUTENCAO.md` já estiver fiel, permanece intocado.
- **Conteúdo correto existente**: preservar — a correção é fundamentada (não é reescrita por reescrita); o README já fiel na precedência/default/tick/catch-up/retenção permanece, recebendo apenas o que falta (AT-2/AT-3).
- **Execução de testes para regressão documental** (briefing §34): opcional; se executada, registrar no relatório; nenhuma alteração de teste é permitida em qualquer hipótese.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A feature é exclusivamente documental: nenhuma alteração em scheduler, BackupService, BackupConfigService, modelo `BackupConfig`, banco, tabela `backup_config`, tela, rotas, retenção, backup manual, restore, auditoria, RBAC, autenticação, AD, configurações operacionais ou comportamento de runtime.
- **FR-002**: Somente `README.md`, `docs/GUIA_DE_MANUTENCAO.md` e `docs/ARQUITETURA_E_MANUTENCAO.md` podem ser editados — e apenas os que contiverem documentação incorreta ou incompleta quanto à configuração de backup.
- **FR-003**: As 8 constantes de `app/config.py` permanecem presentes e intactas; a documentação NÃO pode sugerir remoção, substituição por valores fixos ou alteração do service para eliminá-las.
- **FR-004 (AT-1)**: A documentação deixa de afirmar que as env `BACKUP_*` são fallback somente "da primeira inicialização" e passa a descrever: fallback **por campo** durante a resolução da configuração efetiva enquanto o campo persistido estiver indefinido + participação no **bootstrap/fallback de boot**.
- **FR-005 (AT-2)**: A documentação registra o fallback de boot do scheduler com o fluxo exato: falha na leitura → mantém snapshot anterior (se existir) → sem snapshot, usa bootstrap env/default — descrito como mecanismo de segurança, não como caminho normal.
- **FR-006 (AT-3)**: A documentação registra a particularidade do `auto_enabled` (campo não nulo → `BACKUP_AUTO_ENABLED` não é fallback dinâmico desse campo após a linha existir; segue no bootstrap e na instalação nova), sem propor alteração de modelo ou lógica.
- **FR-007**: A precedência documentada é apresentada com o diagrama persistido → env (se não definido) → default da 020, atribuída explicitamente a `get_effective_config()`.
- **FR-008**: A documentação afirma que scheduler e retenção consomem a configuração **efetiva** (`EffectiveBackupConfig` via snapshot/`get_effective_config`), nunca as constantes de `config.py` diretamente para decisões normais.
- **FR-009**: `app/config.py` é descrito apenas pelos papéis reais: default, fallback por campo, bootstrap, fallback de boot do scheduler, suporte a instalações novas e a ambientes automatizados — nunca como fonte efetiva normal.
- **FR-010**: A documentação afirma explicitamente que não existem duas fontes concorrentes de configuração (persistida = operacional administrada; env/default = fallback/bootstrap).
- **FR-011**: A atualização dinâmica sem reinício está documentada com a janela confirmada de **30 segundos** (`_TICK_SECONDS = 30`), sem sugerir alteração do mecanismo.
- **FR-012**: As 8 variáveis são documentadas cada uma com: finalidade, default, quando funciona como fallback, relação com o valor persistido e eventual particularidade — com os defaults atuais inalterados (`false`, `daily`, `02:00`, `0`, `30`, `12`, `12`, `0`) e seus significados (backup automático inicia desativado; diário; America/Recife; domingo; 30 dias; 12 semanas; 12 meses; preservar todos os pré-restauração).
- **FR-013**: O primeiro uso está documentado: instalação nova → campos não definidos → env quando disponível → default → configuração efetiva; `auto_enabled` com o comportamento real do campo não nulo e default desativado.
- **FR-014**: A separação parâmetros operacionais × credenciais/segredos é mantida: nenhuma `BACKUP_*` apresentada como segredo; nenhuma senha/credencial adicionada à documentação.
- **FR-015**: Antes de editar, o código atual é verificado (trechos existentes, nomes, precedência, defaults, comportamento do scheduler e da retenção — briefing §23/§24); o comportamento documentado é sempre o do código atual, não o da auditoria ou de specs antigas.
- **FR-016**: Divergências código × auditoria 024 encontradas durante a implementação são registradas (não corrigidas em código); divergência funcional interrompe a alteração e vira ponto de atenção para feature separada (briefing §37).
- **FR-017**: O relatório final (briefing §39) é entregue com os 13 itens: arquivos alterados, correções por arquivo, tratamento de AT-1/AT-2/AT-3, confirmações de preservação (config.py, constantes, scheduler, service, banco, testes), verificações realizadas e divergências remanescentes.
- **FR-018**: Todo conteúdo alterado é verificável no código atual; afirmações não confirmáveis não são documentadas como fato.

### Non-Functional Requirements

- **NFR-001** (Escopo): `git diff` da feature contém somente alterações de documentação nos arquivos do FR-002; nenhum arquivo em `app/`, `tests/`, `data/`, `.env`.
- **NFR-002** (Consistência interna): os 3 documentos ficam mutuamente consistentes (mesma precedência, mesmos defaults, mesmo papel do `config.py`) e sem contradição com o código.
- **NFR-003** (Minimalismo): nenhuma alteração documental além do necessário para AT-1/AT-2/AT-3 e a consolidação do fluxo; preservar o texto já correto.
- **NFR-004** (Linguagem): português técnico claro, no estilo dos docs existentes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `git diff --stat` da feature lista somente arquivos de documentação (FR-002).
- **SC-002**: O checklist de aceitação do briefing §35 está 100% cumprido (18 itens: AT-1/AT-2/AT-3 corrigidos; precedência, fallback de boot, papel das constantes, fonte efetiva, scheduler/retenção como consumidores, atualização sem reinício, 30 s documentados; nenhuma afirmação de fonte concorrente/primeira-inicialização-only/config-como-fonte-efetiva; banco/código/config intocados).
- **SC-003**: Cada afirmação nova ou alterada na documentação tem correspondência verificável no código atual (conferência um a um na US5).
- **SC-004**: Um leitor responde às 8 perguntas do briefing §38 apenas com a documentação (onde configuro / onde fica salvo / quem resolve / quem usa / para que serve config.py / dupla fonte? / reiniciar? / quanto tempo? / e se o banco falhar?).
- **SC-005**: O relatório final (FR-017) é produzido com as confirmações de preservação e as verificações realizadas.

## Assumptions

1. O relatório da Feature 024 (`specs/024-auditoria-config-backup/relatorio.md`) é a referência inicial, mas **não dispensa a re-verificação no código atual** antes de cada edição (briefing §24).
2. `app/config.py` não será alterado (a auditoria não encontrou inconsistência factual grave); o comentário interno do arquivo permanece como está.
3. Nenhuma suíte de testes precisa ser executada para esta feature; se execução de regressão documental for realizada, será registrada no relatório (briefing §34).
4. O local do relatório final (arquivo em `specs/025-documentacao-config-backup/` ou resposta na conversa) é decidido na fase de tasks — não é código de produção.
5. Nenhum novo documento é criado em `docs/` — a correção acontece nos arquivos existentes do FR-002.
