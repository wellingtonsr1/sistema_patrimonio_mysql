---

description: "Tasks for feature 022 — Configurações de Backup em Modal"
---

# Tasks: Configurações de Backup em Modal (022)

**Input**: Design documents from `/specs/022-modal-configuracoes-backup/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md (R1–R6) ✅, data-model.md ✅, contracts/service-contract.md ✅, quickstart.md ✅

**Tests**: incluídos conforme briefing §28 (Testes A–H) e Constitution VIII. Estruturais automatizáveis via TestClient; interação visual (abrir/fechar real, temas, larguras) segue validação manual no quickstart.

**Organization**: agrupadas por user story (spec: US1 ⚙+modal · US2 cancelar/salvar · US3 fidelidade visual · US4 preservação).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência)
- **[Story]**: user story à qual a task pertence
- Caminhos exatos em cada descrição

## Path Conventions

Projeto único: `app/`, `tests/` na raiz. Feature toca: `app/services/backup_config_service.py`, `app/web/admin_routes.py`, `app/web/templates/admin/backups.html`, `tests/test_backup_config.py`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: estado inicial verificado antes de qualquer mudança

- [x] T001 Baseline: rodar `python3 -m pytest -q` e confirmar **522 passed, 0 failed**; ler o estado atual de `app/web/templates/admin/backups.html` (header, botão "Configurar" do card, card "Configurações de Backup" com `{% if config_form %}`) e de `app/web/admin_routes.py` (contexto das 2 rotas GET + redirect do POST) — registrar como referência do "antes"

**Checkpoint**: baseline verde + "antes" mapeado.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: leitura sem efeito colateral (R1) e ajustes de rota (R4) — pré-requisito de TODAS as stories

**⚠️ CRITICAL**: nenhuma story começa antes desta fase (US1 depende do `config_form` na listagem)

- [x] T002 [Fundação] `app/services/backup_config_service.py`: adicionar parâmetro **aditivo** `create: bool = True` em `get_backup_config(db, create=True)` e `get_effective_config(db, create=True)`; com `create=False`, consulta a linha e, se ausente, retorna `BackupConfig(id=1, auto_enabled=False)` **não persistido** — NUNCA `add`/`commit`/`flush` (resolução da efetiva segue igual: None → env → default); default `True` preserva o comportamento de TODOS os chamadores existentes (verificar que rota dedicada, POST e scheduler não mudam). Testes em `tests/test_backup_config.py`: (a) `create=False` em banco SEM linha → nenhuma escrita (`BackupConfig` count == 0 após a chamada) e efetiva = defaults; (b) `create=False` com linha existente → retorna os valores persistidos; (c) `create=True` mantém a criação lazy (comportamento atual, anti-regressão)
- [x] T003 [Fundação] `app/web/admin_routes.py` (depends T002): (1) `GET /admin/backups` ganha `"config_form": backup_config_service.get_effective_config(db, create=False)` no contexto (NÃO chamar `get_backup_config` — listagem permanece somente-leitura); (2) `POST /admin/backups/configuracoes` redireciona para **`/admin/backups?success=…`** e **`/admin/backups?error=…`** (303 — mensagens no alerta do topo da página principal); (3) `GET /admin/backups/configuracoes` MANTIDO com comportamento atual (compatibilidade). Adaptar em `tests/test_backup_config.py` os asserts de `location` afetados (substring `success=`/`error=` continua batendo; trocar asserts de `resp_get` de `/configuracoes` para `/admin/backups` onde o HTML esperado era o formulário)
- [x] T004 [Fundação] Checkpoint: `python3 -m pytest tests/test_backup_config.py tests/test_backup_monitoramento.py tests/test_backup_manual.py -q` verde; `GET /admin/backups` continua 200 sem INSERTs em estado sem linha (testes T002 cobrem)

**Checkpoint**: fundação pronta — US1 pode começar.

---

## Phase 3: User Story 1 — Acessar as configurações pela engrenagem (Priority: P1) 🎯 MVP

**Goal**: ⚙ (somente ícone) no topo direito alinhado ao título "Backups" abre o Modal de Configurações de Backup com os valores atuais; a seção sai da página.

**Independent Test**: `GET /admin/backups` (admin) contém botão ⚙ com `data-bs-target="#modalBackupConfig"` e o modal com os 8 campos pré-preenchidos; seção antiga fora do modal não existe.

### Tests for User Story 1 ⚠️ (escrever primeiro, ver FALHAR)

- [x] T005 [US1] Testes de estrutura em `tests/test_backup_config.py`: `GET /admin/backups` (client admin) contém (1) botão com `aria-label="Configurações de Backup"`, `title="Configurações de Backup"`, `data-bs-target="#modalBackupConfig"`, `data-bs-toggle="modal"` e ícone `bi bi-gear` **sem texto** permanente; (2) header com `page-header` + flex (`justify-content-between`) e o botão **após** o bloco do título; (3) `id="modalBackupConfig"` com classes `modal`/`modal-content`/`modal-header`/`btn-close`/`modal-body`/`modal-footer` (estrutura modalConferir — contract §3); (4) os 8 `name=` (`auto_enabled`, `schedule`, `time`, `weekday`, `keep_pre_restore`, `retention_daily_days`, `retention_weekly_weeks`, `retention_monthly_months`) aparecem **exatamente 1 vez** no HTML da página; (5) o texto "Salvar configuração" NÃO aparece fora do modal (seção antiga removida); (6) botão "Configurar" do card "Backup Automático" **não** existe mais (`>Configurar<` ausente)

### Implementation for User Story 1

- [x] T006 [US1] `app/web/templates/admin/backups.html` (depends T003/T005): (1) header → `page-header d-flex justify-content-between align-items-start flex-wrap gap-2` com o botão ⚙ (`btn btn-sm btn-outline-primary`, somente `<i class="bi bi-gear"></i>`, `aria-label`/`title`, `data-bs-toggle`/`data-bs-target`); (2) converter o card "Configurações de Backup" em `<div class="modal fade" id="modalBackupConfig" tabindex="-1" aria-hidden="true" aria-labelledby="modalBackupConfigLabel">` → `modal-dialog modal-lg modal-dialog-centered` → `modal-content` → `form method="post" action="/admin/backups/configuracoes"` → `modal-header` (`<h5 class="modal-title" id="modalBackupConfigLabel"><i class="bi bi-gear me-1"></i>Configurações de Backup</h5>` + `btn-close` `data-bs-dismiss` `aria-label="Fechar"`) → `modal-body` com os campos atuais **intactos** (mesmos `name=`/`value=`/labels/`form-text` da pré-restauração; grade `row g-3` com `col-sm-6`/`col-12`) → `modal-footer` (**Cancelar**: `btn-outline-secondary`, `type="button"`, `data-bs-dismiss="modal"`; **Salvar configuração**: `btn-primary`, `type="submit"`); (3) remover o botão "Configurar" do card "Backup Automático"; (4) manter `{% if config_form %}` guardando o modal; (5) **zero** `<script>` e **zero** CSS novo
- [x] T007 [US1] Checkpoint US1: `python3 -m pytest tests/test_backup_config.py -q` verde (T005 passando); requisição manual `curl`/TestClient confirma valores pré-preenchidos (`value=` com a efetiva) — Teste E parcial; MVP demonstrável

**Checkpoint**: US1 funcional e testável independentemente — página limpa, ⚙ presente, modal com valores.

---

## Phase 4: User Story 2 — Cancelar e salvar pelo modal (Priority: P1)

**Goal**: Cancelar nunca persiste; Salvar usa o fluxo existente (validação → persistência → auditoria → redirect com mensagem).

**Independent Test**: alterar campo → Cancelar → reabrir mostra valor antigo; salvar horário 23:00 → 303 `/admin/backups?success=` + auditoria `BACKUP_CONFIGURACAO_ALTERADA`.

### Tests for User Story 2 ⚠️ (escrever primeiro, ver FALHAR quando aplicável)

- [x] T008 [US2] Testes de fluxo em `tests/test_backup_config.py`: (1) POST de config válida via `_post_config` → 303 com `location` começando por `/admin/backups?success=` (adaptação do `test_k` — mesma garantia, novo destino); (2) POST inválido → 303 `/admin/backups?error=` e efetiva intacta (adapta `test_f`/`test_quantidades`); (3) **Teste E completo**: após salvar 23:00, `GET /admin/backups` contém `value="23:00"` (valor atual no modal, não default); (4) estrutura do Cancelar: no HTML do modal, botão "Cancelar" tem `type="button"` + `data-bs-dismiss="modal"` e NÃO é `type="submit"` (Teste C automatizável — formulário nunca submetido pelo Cancelar); (5) auditoria (Teste H): após POST, evento `BACKUP_CONFIGURACAO_ALTERADA` com before/after — já coberto por `test_m` (verificar que continua passando; adaptar somente se o redirect afetar)

### Implementation for User Story 2

- [x] T009 [US2] Fechamento do fluxo (depends T006/T008): conferir/ajustar em `backups.html` que o footer do modal usa exatamente os botões do contract §3 (Cancelar `type="button"` — fora do submit; Salvar `type="submit"`); rodar `python3 -m pytest tests/test_backup_config.py tests/test_backup_monitoramento.py -q` e adaptar qualquer assert remanescente de 021 afetado pelo destino do redirect — **sem remover/enfraquecer teste nenhum** (adaptação legítima; Constitution VIII)

**Checkpoint**: US2 funcional — Cancelar inerte, Salvar pelo mecanismo existente com auditoria.

---

## Phase 5: User Story 3 — Fidelidade visual e responsividade (Priority: P2)

**Goal**: modal idêntico ao padrão dos modais existentes (Conferência do Bem), responsivo 320–1920 px, temas claro/escuro, sem CSS/JS novo.

**Independent Test**: inspeção do HTML (classes iguais às do `modalConferir`) + diff sem `<script>`/CSS novo + validação manual de larguras/temas no quickstart §4.

### Tests for User Story 3

- [x] T010 [US3] Teste de fidelidade em `tests/test_backup_config.py`: no HTML de `GET /admin/backups`, o bloco do modal usa **somente** classes já presentes no projeto (verificar contra `app/web/templates/inventarios/detail.html`: `modal fade`, `modal-dialog`, `modal-content`, `modal-header`, `modal-title`, `btn-close`, `modal-body`, `modal-footer`) e o template de `backups.html` não contém `<script` novo nem `<style` (comparar contagem com o baseline T001); campos usam as mesmas classes de form da seção antiga (`form-select`, `form-control`, `form-check-input`, `form-label`, `form-text`)
- [x] T011 [US3] Validação visual manual (quickstart §4, depends T009/T010): navegadores Chrome/Firefox × claro/escuro × larguras 320/375/480/600/768/900/1024/1280/1366/1440/1920 — checklist: ⚙ alinhado ao título sem sobreposição (`flex-wrap` nas estreitas); modal sem scroll horizontal; campos reorganizados; botões acessíveis; ✕ visível; overlay/campos/foco herdam o tema. Registrar resultado no relatório final (briefing §29/§38.4)

**Checkpoint**: US3 verificada — visual consistente nos dois temas e todas as larguras.

---

## Phase 6: User Story 4 — Preservação total da lógica (Priority: P1)

**Goal**: provar que nada além da apresentação mudou (briefing §30/§37).

**Independent Test**: diff limitado (template + rotas mínimas + service aditivo); suíte 020/021 completa verde; 403 sem permissão.

- [x] T012 [US4] Auditoria de escopo do diff (`git diff --stat` + revisão): alterações SOMENTE em `backups.html`, `admin_routes.py` (contexto/redirect), `backup_config_service.py` (parâmetro aditivo) e `tests/`; confirmar NENHUMA mudança em: `backup_scheduler.py`, lógica GFS da retenção, `backup_service.py`, `audit_service.py`, `config.py`, models, migrations, `base.html`, outros templates, RBAC/permissões, autenticação/AD (briefing §34/§37)
- [x] T013 [US4] Regressão completa (depends T009): `python3 -m pytest -q` — **suíte inteira verde** (522 baseline + novos, 0 falhas) cobrindo Testes F (backup automático) e G (retenção) do §28; confirmar Teste N 021 (POST sem permissão → 403) intacto e que o guard de `GET /admin/backups` já esconde ⚙/modal de não autorizados

**Checkpoint**: preservação provada por diff + suíte.

---

## Phase 7: Polish & Cross-Cutting

**Purpose**: docs fiéis (Constitution XI) e validação final

- [x] T014 [P] `README.md`: na seção "Configurações de Backup pela interface (feature 021)", atualizar o acesso — o formulário abre via **botão ⚙ no topo direito da página de Backups (modal)**; rota `/admin/backups/configuracoes` segue existente por compatibilidade; demais informações (precedência, aplicação sem reinício, campos técnicos fora da tela) permanecem válidas
- [x] T015 [P] `app/services/help_service.py`: no artigo de backups, ajustar a seção "Configurações de Backup (feature 021)" para descrever o acesso real (engrenagem no topo da página de Backups abre o modal; Cancelar não salva; Salvar valida/audita) — sem inventar comportamento
- [x] T016 Final (depends T012–T015): executar `specs/022-modal-configuracoes-backup/quickstart.md` end-to-end (suíte + Testes A–H + checklist visual/temas marcados); marcar todas as tasks como `[x]` neste arquivo; preparar dados do relatório final (briefing §38: arquivos alterados, o que mudou e por quê, funcionamento ⚙→modal→mecanismo existente, testes, regressão, limitações)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (T001)**: imediato
- **Foundational (T002→T003→T004)**: bloqueia TODAS as stories (US1 precisa do `config_form` na listagem)
- **US1 (T005→T006→T007)**: após fundação — MVP
- **US2 (T008→T009)**: após US1 (modal precisa existir para os testes de fluxo)
- **US3 (T010→T011)**: após US2 (valida o estado final do modal)
- **US4 (T012, T013)**: após US2 (diff e regressão sobre o resultado)
- **Polish (T014∥T015 → T016)**: após todas as stories

### Within Each User Story

- Testes escritos ANTES da implementação e vistos falhando (T005, T008)
- Template depois dos testes; checkpoint executável por story

### Parallel Opportunities

- T014 ∥ T015 (README × help_service — arquivos distintos)
- Demais tasks são sequenciais (T002 e T005 compartilham `test_backup_config.py`; T003/T006/T009 compartilham rotas/template)

---

## Implementation Strategy

### MVP First (Setup + Foundational + US1)

1. T001 → T002 → T003 → T004 (fundação: leitura sem escrita + redirect)
2. T005 → T006 → T007 (⚙ + modal com valores atuais)
3. **STOP and VALIDATE**: página limpa, ⚙ abre modal, valores corretos

### Incremental Delivery

- +US2: cancelar/salvar preservando semântica → valida fluxo ponta a ponta
- +US3: fidelidade visual/responsividade/temas
- +US4: prova de preservação (diff + suíte) → release-ready

### Notes

- Testes 021 afetados são **adaptados** (destino do redirect; referências ao botão "Configurar") — nunca removidos ou enfraquecidos (Constitution VIII)
- A rota `/admin/backups/configuracoes` permanece (compatibilidade) — NÃO é removida
- Risco conhecido: `GET /admin/backups` deve continuar sem INSERT (usar `create=False` — T002/T003); validar no checkpoint T004
