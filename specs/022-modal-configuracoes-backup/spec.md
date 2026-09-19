# Feature Specification: Configurações de Backup em Modal

**Feature Branch**: `feature-modal-configuracoes-backup`

**Created**: 2026-09-18

**Status**: Draft

**Input**: Transformar a seção "Configurações de Backup" existente na página de Backups em um modal aberto por um botão de engrenagem (somente ícone) no canto superior direito, alinhado ao título "Backups". Exclusivamente apresentação visual: nenhuma lógica de configuração, validação, persistência, auditoria, RBAC, scheduler ou retenção é alterada.

## Realidade verificada (análise obrigatória — briefing §17)

*Analisado antes de escrever esta spec; nada foi presumido.*

1. **Página**: rota `GET /admin/backups` (`admin_backups` em `app/web/admin_routes.py`), template `app/web/templates/admin/backups.html`.
2. **Seção atual**: card "Configurações de Backup" (linha ~148–225 do template), renderizado condicionalmente com `{% if config_form %}` (apenas na rota `/admin/backups/configuracoes` desde a correção de navegação da 021).
3. **Campos existentes** (todos com `name=` preservados): `auto_enabled` (checkbox/switch), `schedule` (select diário/semanal), `time` (input time), `weekday` (select 0=domingo..6=sábado), `keep_pre_restore` (number ≥ 0, com descrição "0 preserva todos os backups pré-restauração."), `retention_daily_days`/`retention_weekly_weeks`/`retention_monthly_months` (number ≥ 1) e submit "Salvar configuração".
4. **Endpoint de salvamento**: `POST /admin/backups/configuracoes` (`admin_backup_config_save`) — valida no backend, persiste com commit único, audita `BACKUP_CONFIGURACAO_ALTERADA` (before/after) e redireciona 303 para `?success=...`/`?error=...`. **Guard, validação, persistência e auditoria não serão alterados**; apenas o **destino do redirect** muda para `/admin/backups?success=...`/`?error=...` (o formulário passa a viver no modal na página principal).
5. **Modal de referência** ("Conferência do Bem"): `app/web/templates/inventarios/detail.html` — estrutura Bootstrap padrão: `modal fade` → `modal-dialog` → `modal-content` → `form` → `modal-header` (com `modal-title` e `btn-close` + `data-bs-dismiss="modal"`) → `modal-body` → footer com botões; acionado por `data-bs-toggle="modal"` + `data-bs-target="#modalX"`.
6. **Botão de ícone**: o projeto não possui um componente dedicado, mas usa `btn btn-sm btn-outline-primary` com ícone Bootstrap Icons e `title` (o botão "Configurar" atual em `backups.html` é o exemplo mais próximo). Bootstrap Icons (ex.: `bi bi-gear`) já é o padrão de ícones.
7. **Temas claro/escuro**: via variáveis CSS (`--green-bg`, `--green-border`, etc. — ver botão em `maintenances/list.html`) sobre Bootstrap; modais Bootstrap herdam os temas automaticamente.
8. **Header da página**: `page-header` → `page-header-title` + `page-header-subtitle` — atualmente sem flex; precisará de wrapper flex (padrão `d-flex justify-content-between` já usado no sistema) para alinhar a engrenagem à direita do título.
9. **JavaScript de modais**: **nenhum JS customizado** — o sistema usa apenas atributos `data-bs-*` do Bootstrap; nenhum `<script>` adicional será necessário.
10. **Acessibilidade**: padrão existente = `aria-label="Fechar"` no `btn-close` dos modais; labels associados via `for`/`id` no formulário de configuração atual.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Acessar as configurações pela engrenagem (Priority: P1)

Um administrador abre a página **Administração → Backups** e vê, no canto superior direito, alinhado ao título "Backup Automático", um botão contendo **somente o ícone de engrenagem** (⚙), com tooltip/rótulo acessível "Configurações de Backup". Ao clicar, abre-se o **Modal de Configurações de Backup** com todos os campos da configuração atual pré-preenchidos.

**Why this priority**: é o coração da feature — sem o botão e o modal funcional, a configuração ficaria inacessível pela interface.

**Independent Test**: acessar `/admin/backups` com permissão `backup.gerenciar`, clicar no botão ⚙ e observar o modal com os valores atuais.

**Acceptance Scenarios**:

1. **Given** administrador na página de Backups, **When** observa o topo da página, **Then** o botão ⚙ está à direita, alinhado verticalmente ao título "Backups", sem texto permanente e com tooltip/aria-label "Configurações de Backup".
2. **Given** clique no botão ⚙, **When** o modal abre, **Then** exibe todos os campos com os **valores atualmente configurados** (nunca defaults se houver valores salvos).
3. **Given** página de Backups, **When** a seção "Configurações de Backup" não está mais renderizada diretamente na página, **Then** nenhum conteúdo funcional foi perdido — tudo está no modal.

---

### User Story 2 - Cancelar e salvar pelo modal (Priority: P1)

Dentro do modal, o administrador pode **Cancelar** (nenhuma alteração persistida; ao reabrir, aparecem os valores anteriormente salvos) ou **Salvar configuração** (mesmo fluxo atual: validação backend → persistência → auditoria → redirect com mensagem de sucesso/erro).

**Why this priority**: garantir que a mudança visual não criou um caminho de salvamento alternativo — Cancelar e Salvar preservam a semântica atual.

**Independent Test**: alterar um campo, cancelar, reabrir e conferir o valor original; depois salvar uma alteração válida e conferir persistência + auditoria + mensagem.

**Acceptance Scenarios**:

1. **Given** modal aberto com retenção diária 30, **When** altera para 60 e clica Cancelar, **Then** nada é persistido; ao reabrir o modal aparece 30.
2. **Given** modal aberto, **When** altera horário para 23:00 e salva, **Then** a configuração é persistida pelo **mesmo endpoint existente**, com evento de auditoria `BACKUP_CONFIGURACAO_ALTERADA` e mensagem de sucesso.
3. **Given** modal aberto, **When** submete valor inválido (ex.: horário 25:99), **Then** o erro é tratado pelo fluxo atual (redirect com `?error=`) e a configuração vigente permanece intacta.

---

### User Story 3 - Fidelidade visual e responsividade (Priority: P2)

O modal segue o **padrão visual dos modais existentes** (referência: Modal de Conferência do Bem): cabeçalho com título "⚙ Configurações de Backup" e botão ✕, corpo com os campos no layout em duas colunas do briefing, overlay e comportamento de fechamento padrão — nos temas claro e escuro, de 320 px a 1920 px, sem scroll horizontal.

**Why this priority**: a feature É a apresentação — fidelidade visual, responsividade e temas são parte dos critérios de aceitação.

**Independent Test**: inspecionar o HTML do modal (classes idênticas às dos modais existentes) e verificar comportamento em larguras extremas e nos dois temas.

**Acceptance Scenarios**:

1. **Given** modal renderizado, **When** o HTML é inspecionado, **Then** usa as mesmas classes dos modais existentes (`modal fade`, `modal-dialog`, `modal-content`, `modal-header`, `btn-close`, `modal-body`, `modal-footer`) — sem novo CSS de modal.
2. **Given** viewport de 320 px, **When** o modal abre, **Then** cabe na viewport sem scroll horizontal, campos reorganizados e botões acessíveis.
3. **Given** tema escuro ativo, **When** o modal abre, **Then** fundo/texto/bordas/campos/overlay herdam o tema como nos demais modais.

---

### User Story 4 - Preservação total da lógica (Priority: P1)

A mudança é **somente visual**: nenhuma rota nova, nenhuma tabela, nenhum serviço, nenhuma permissão, nenhum comportamento de scheduler/retenção/auditoria é criado ou alterado. O card "Backup Automático" (com seus indicadores) e o card "Gerar backup agora" permanecem na página. O botão "Gerar backup" continua fora do modal.

**Why this priority**: regra de preservação do briefing (§36/§39) — falhar aqui invalida a feature.

**Independent Test**: diff limitado a `templates` (+ rotas somente se indispensável); suíte completa verde; testes da 020/021 sem regressão.

**Acceptance Scenarios**:

1. **Given** o diff da implementação, **When** revisado, **Then** altera apenas `app/web/templates/admin/backups.html` e `app/web/admin_routes.py` (somente se um ajuste mínimo de contexto for indispensável) — nada em models, banco ou permissões, e em services somente o parâmetro aditivo `create` em `get_backup_config`/`get_effective_config` (default `True` = comportamento atual).
2. **Given** a suíte completa, **When** executada após a mudança, **Then** todos os testes da 020/021 (agendamento, retenção, configuração, monitoramento) permanecem verdes.
3. **Given** administrador sem permissão `backup.gerenciar`, **When** acessa a página, **Then** o botão ⚙ não aparece (mesma proteção atual, agora no elemento do header) e o POST direto continua negado (403).

---

## Edge Cases

- **Modal aberto e mensagens de feedback**: as mensagens `?success=`/`?error=` do salvamento são renderizadas no **alerta do topo da página** (padrão atual). Após salvar com sucesso, o redirect recarrega a página com o modal **fechado** e a mensagem visível — comportamento natural do fluxo atual (server-rendered), sem JS extra.
- **Reabrir após erro de validação**: o valor inválido não é persistido; ao reabrir o modal, os campos mostram a configuração vigente (vinda do `config_form` da rota).
- **Usuário sem permissão**: a rota `/admin/backups` exige `backup.gerenciar`; o botão ⚙ e o modal só são renderizados para quem já passa pelo guard da página. O `POST` direto continua negado (403) — nada muda no backend.
- **Restauração em andamento**: o modal de configuração não interfere no gate de manutenção da 019; o botão ⚙ pode abrir, mas o salvamento segue o fluxo atual (que não é bloqueado pelo modo manutenção — comportamento atual preservado).
- **JS indisponível**: sem JavaScript custom, os modais dependem do Bootstrap (mesma dependência dos modais existentes — nenhum requisito novo).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O card/seção "Configurações de Backup" deixa de ser renderizado diretamente na página `/admin/backups` (remove-se também o botão "Configurar" do card "Backup Automático" introduzido como navegação — o acesso passa a ser o ⚙).
- **FR-002**: O botão ⚙ (somente o ícone `bi bi-gear`) fica no **canto superior direito, alinhado verticalmente ao título "Backups"**, dentro do bloco `page-header`, usando flexbox (padrão `d-flex justify-content-between` do projeto), sem posicionamento absoluto.
- **FR-003**: O botão ⚙ possui `aria-label="Configurações de Backup"`, `title="Configurações de Backup"` (tooltip nativo) e área de clique adequada (padrão `btn` do sistema); não exibe texto permanente.
- **FR-004**: O clique no ⚙ abre o **Modal de Configurações de Backup** via atributos `data-bs-toggle="modal"`/`data-bs-target` (mesmo mecanismo dos modais existentes — nenhum JS novo).
- **FR-005**: O modal usa a estrutura Bootstrap padrão do sistema (referência: `modalConferir` em `inventarios/detail.html`): `modal fade` → `modal-dialog` → `modal-content` → `modal-header` (título "⚙ Configurações de Backup" + `btn-close` acessível) → `modal-body` (formulário) → `modal-footer` (Cancelar + Salvar configuração).
- **FR-006**: O corpo do modal contém **exatamente os campos atuais**, com os mesmos `name=`, valores pré-preenchidos, labels e descrição "0 preserva todos os backups pré-restauração.": `auto_enabled`, `schedule`, `time`, `weekday`, `keep_pre_restore`, `retention_daily_days`, `retention_weekly_weeks`, `retention_monthly_months`.
- **FR-007**: O formulário do modal faz `POST /admin/backups/configuracoes` (rota existente) — nenhuma rota, serviço ou mecanismo de salvamento novo.
- **FR-008**: Botão **Cancelar** fecha o modal (`data-bs-dismiss="modal"`) sem submeter o formulário — nenhuma alteração persistida (formulário fora do fluxo de submit).
- **FR-009**: Botão **Salvar configuração** submete o formulário pelo fluxo atual: validação backend → persistência → auditoria `BACKUP_CONFIGURACAO_ALTERADA` → redirect 303 com mensagem.
- **FR-010**: O card "Backup Automático" (indicadores), o card "Gerar backup agora" e o botão "Gerar backup" permanecem na página, fora do modal, sem alteração de dados ou cálculo.
- **FR-011**: O modal é responsivo (320 px–1920 px, sem scroll horizontal, botões acessíveis) e respeita os temas claro/escuro via Bootstrap + variáveis CSS existentes (nenhum CSS de modal novo).
- **FR-012**: Acessibilidade: `aria-label` no ⚙, `btn-close` com `aria-label="Fechar"`, labels associados aos campos (`for`/`id`), foco gerenciado pelo Bootstrap (padrão dos modais existentes), modal identificável por leitores de tela (`role="dialog"` implícito na estrutura Bootstrap).

### Non-Functional Requirements

- **NFR-001** (Consistência visual): zero CSS novo para o modal — apenas classes e componentes já usados pelo sistema.
- **NFR-002** (Escopo): alteração limitada a `app/web/templates/admin/backups.html` e `app/web/admin_routes.py` (só se um ajuste mínimo de contexto for indispensável — ex.: renderizar o `config_form` também na rota da listagem — e o novo destino do redirect), mais **única exceção aditiva no service**: parâmetro `create: bool = True` em `get_backup_config`/`get_effective_config` (`backup_config_service.py`) para leitura sem efeito colateral em GET — o default `True` preserva o comportamento atual; nenhum outro arquivo de services.
- **NFR-003** (Performance/complexidade): nenhum JavaScript novo, nenhuma dependência nova, nenhum arquivo estático novo.
- **NFR-004** (Regressão): suíte completa verde pós-mudança; nenhum teste de 020/021 enfraquecido.

### Infraestrutura

- Sem tabelas, colunas, migrations, endpoints ou dependências novas (briefing §20/§22/§34).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A página `/admin/backups` não renderiza mais a seção "Configurações de Backup" fora do modal (HTML da página sem os campos de config fora do `modal`).
- **SC-002**: O botão ⚙ está presente, à direita e alinhado ao título; contém somente o ícone; abre o modal.
- **SC-003**: O modal contém os 8 campos com os valores atuais e `name=` preservados; Cancelar não persiste; Salvar usa o endpoint existente.
- **SC-004**: Diferença visual (HTML) entre os temas claro/escuro apenas via classes/variáveis existentes.
- **SC-005**: Suíte completa verde (baseline 522 + ajustes de teste mínimos se o botão "Configurar" for citado em teste — adaptação legítima, não enfraquecimento).
- **SC-006**: Nenhum arquivo de service/model/rota (exceto o ajuste mínimo de contexto do NFR-002 e o parâmetro aditivo `create` em `backup_config_service.py`) e nenhuma tabela alterados.

## Assumptions

1. Bootstrap já carregado na base (usado pelos modais existentes) — nenhuma dependência nova.
2. O "Modal de Conferência do Bem" é a referência visual aceita (briefing §5) — estrutura idêntica, conteúdo distinto.
3. As mensagens de sucesso/erro do salvamento continuam nos alertas do topo da página (padrão server-rendered atual); o modal fecha no redirect.
4. O botão "Configurar" adicionado no card "Backup Automático" durante a 021 será removido (substituído pelo ⚙ no header) — ajuste mínimo de layout autorizado pelo briefing §33.
5. Testes visuais em navegadores reais (Chrome/Firefox, 320–1920 px, claro/escuro) seguem validação manual per `quickstart` (como nas features anteriores) — a suíte automatizada cobre estrutura HTML, permissão e fluxos de salvamento.
6. Sem permissão nova: o ⚙ e o modal herdam o guard `backup.gerenciar` da página.

## Débitos fora de escopo (registrados, não implementados)

- Nenhum — o escopo é exclusivamente a transformação seção → modal.
