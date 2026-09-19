---

description: "Tasks for feature 023 — Revisão e Melhoria do README.md"
---

# Tasks: Revisão e Melhoria do README.md (023)

**Input**: Design documents from `/specs/023-revisao-readme/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md (inventário D1–D15 + R1–R5) ✅, data-model.md ✅, contracts/readme-contract.md ✅, quickstart.md ✅

**Tests**: Nenhum teste automatizado novo — feature documental (spec FR-001). Validação = inspeção comparativa README ↔ código (quickstart §2) + verificação de escopo (`git diff` somente README.md).

**Organization**: agrupadas por user story (spec: US1 auditoria · US2 reescrita · US3 validação). A auditoria US1 já foi executada na fase de plan (research.md) — as tasks a formalizam e completam os pontos de alerta do requisitante.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (verificações sem edição de arquivo)
- **[Story]**: user story à qual a task pertence
- Caminhos exatos em cada descrição

## Path Conventions

Projeto único. Feature altera EXCLUSIVAMENTE: `README.md`. Fontes de verificação (somente leitura): `app/cli.py`, `app/config.py`, `app/main.py`, `app/web/routes.py`, `app/web/help_routes.py`, `app/web/admin_routes.py`, `app/api/reports_api.py`, `app/services/permission_service.py`, `app/services/inventario_service.py`, `app/services/report_service.py`, `app/utils/time_utils.py`, `app/database.py`, `tests/conftest.py`, `requirements.txt`, `.env.example`, `docs/`, `specs/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: estado inicial conhecido antes de qualquer edição

- [x] T001 [P] Verificar baseline: `git status --short` e `git diff --stat` limpos (nenhum arquivo pendente da 022, exceto os já commitados); registrar em anotação da tarefa a lista de arquivos alterados ANTES da edição do `README.md` (referência para o escopo-check da US3)

**Checkpoint**: baseline registrado — nenhuma edição ainda.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: mapa de trabalho consolidado — divergência → seção do README (pré-requisito de TODAS as stories)

**⚠️ CRITICAL**: nenhuma edição no `README.md` antes desta fase

- [x] T002 [P] Consolidar o mapa de trabalho no comentário de trabalho da tarefa: para cada divergência do research.md (D1–D15), registrar a seção alvo no `README.md` e o fato substituto no `specs/023-revisao-readme/data-model.md` §1 (fonte verificável); confirmar que os pontos de alerta do requisitante têm verificação citável: `/setup` (routes.py L1644/L1658), backup automático (admin_routes.py), restauração (017/019), CLI (cli.py L206–245), regras de AD (ad_service.py/ad_group_role.py)

**Checkpoint**: cada edição da US2 tem origem (D#) e destino (seção) definidos.

---

## Phase 3: User Story 1 — Auditoria documental README ↔ código (Priority: P1) 🎯 MVP

**Goal**: cada afirmação do README atual classificada (correto/obsoleto/incorreto/incompleto) com verificação citável — inventário D1–D15 formalizado e estendido aos pontos de alerta.

**Independent Test**: para cada seção do `README.md`, existe uma verificação (arquivo:linha ou arquivo real) confirmando ou refutando a afirmação; as divergências estão listadas antes de editar.

### Implementation for User Story 1

- [x] T003 [P] [US1] Auditoria da seção "Como Executar/Instalação/Primeiro administrador" do `README.md` contra `app/config.py` (`AUTH_ADMIN_*`), `app/web/routes.py` (`/setup` GET/POST L1644/L1658, `setup_claims` singleton L1625) e `app/cli.py` (`create-user` L227–235): confirmar os 3 mecanismos e a condição real do `/setup` (disponível enquanto não houver usuário cadastrado) — consolidar D2
- [x] T004 [P] [US1] Auditoria das seções de Backup/Restauração do `README.md` contra `app/web/admin_routes.py` (rotas `/admin/backups/*`, acesso ⚙/modal da 022, redirect do POST) e specs 015–022: confirmar descrição do acesso às configurações — consolidar D4
- [x] T005 [P] [US1] Auditoria das seções CLI e Autenticação do `README.md` contra `app/cli.py` (comando a comando, flags) e `app/config.py` L107–132 (`AUTH_*`, lockout 10×900, PBKDF2 600000) e `app/services/auth_service.py` (423 Locked): confirmar comandos/valores — consolidar D3/D7
- [x] T006 [P] [US1] Auditoria das seções AD/RBAC do `README.md` contra `app/services/ad_service.py`, `app/models/ad_group_role.py` (prioridade menor=maior) e `app/services/permission_service.py` (7 perfis L88–180, 36 permissões incl. `backup.gerenciar`/`backup.restaurar` L85–86): confirmar regras e levantar omissões — consolidar D5/D6
- [x] T007 [P] [US1] Auditoria das seções Banco/Testes/Estrutura/Documentação do `README.md` contra `app/database.py` (`init_db`/`_ensure_schema_migrations`), `tests/conftest.py` (SQLite/`DATABASE_URL_TEST` L26–28), raiz real do repositório e `docs/` real (4 .md + auxiliares; lista "sugestão" inexistente): consolidar D1/D10/D12/D15
- [x] T008 [US1] Fechamento da auditoria (depends T003–T007): consolidar no relatório de trabalho o inventário final de divergências do `README.md` (base: research.md D1–D15, ajustado se a auditoria detalhada revelar algo novo) — nenhuma divergência sem verificação citável; nada é preservado por inércia

**Checkpoint**: US1 completa — mapa definitivo divergência→correção pronto (MVP da auditoria demonstrável).

---

## Phase 4: User Story 2 — Reescrita do README como porta de entrada (Priority: P1)

**Goal**: `README.md` corrigido aplicando D1–D15, preservando o conteúdo verificado, na ordem de seções atual (research R2) e sob o contrato de conteúdo (contracts/readme-contract.md §2).

**Independent Test**: ler o `README.md` final e verificar cada afirmação contra a auditoria (US1); seguir a instalação passo a passo por inspeção (`pip install -r requirements.txt`, `python run.py`, CLI) sem encontrar comando/caminho inexistente.

### Implementation for User Story 2

**⚠️ Todas as tasks desta story editam o MESMO arquivo (`README.md`) — executar em sequência, sem [P]**

- [x] T009 [US2] `README.md` — Introdução/Status (depends T008): manter introdução objetiva (o que é, problema resolvido, foco no fluxo auditável, sem marketing); citar a versão `1.2.0` uma única vez, marcada "conforme `app/config.py`" (R4); manter nota de porta de entrada para `docs/`
- [x] T010 [US2] `README.md` — Funcionalidades/Modelo Conceitual/Tecnologias/Arquitetura (depends T008): conferir os 8 tipos de movimentação e os módulos listados; ajustar a precisão dos "bens não previstos" do inventário (D9: ocorrência registrada como observação complementar, `nao_previsto`, sem alterar cadastro); tabela de tecnologias = `requirements.txt` real (D11); arquitetura em camadas mantida
- [x] T011 [US2] `README.md` — Como Executar/Instalação/Primeiro administrador/Banco e migração (depends T008): manter comandos verificados (`pip install -r requirements.txt`, `python run.py`, SQL de exemplo com placeholders); explicitar a condição real do `/setup` (D2: enquanto não houver usuário — singleton `setup_claims`); manter os 3 mecanismos (env `AUTH_ADMIN_*`, `/setup`, CLI `create-user`) com quando usar cada um; `init_db()` + migração idempotente
- [x] T012 [US2] `README.md` — Autenticação/AD/RBAC/Proteções/Auditoria (depends T008): manter tabela de lockout (`AUTH_*` conferidas); reforçar regra AD → grupo mapeado → perfil → permissões (prioridade numérica); **adicionar o módulo Backup ao catálogo de permissões** (`backup.gerenciar`, `backup.restaurar` — D6); manter `movimentacao.cancelar` como reservada; auditoria sem credenciais
- [x] T013 [US2] `README.md` — Banco/CLI/Ajuda/Testes/Estrutura (depends T008): manter MariaDB/MySQL produção + SQLite só em testes; citar `backup_records`/`backup_config` nas estruturas (D15); comandos CLI conforme `cli.py` (D3); ampliar cobertura citada dos testes com backup (7 arquivos) mantendo "sem números fixos" (D12); **atualizar a árvore de estrutura** com diretórios reais (`specs/`, `TASKS/`, arquivos da raiz — D10, listagem não exaustiva)
- [x] T014 [US2] `README.md` — Segurança/Backup e Restauração/Documentação/Pontos de atenção (depends T009–T013): manter separação implementado × recomendações; atualizar o acesso às Configurações de Backup (D4: ⚙ no topo direito da página de Backups abre o modal — 021/022; rota `/admin/backups/configuracoes` mantida por compatibilidade); **substituir a lista fictícia de `docs/` pelas referências reais** (D1: `ARQUITETURA_E_MANUTENCAO.md`, `GUIA_DE_MANUTENCAO.md`, `INVENTARIO_TECNICO.md`, `AVISO_RESTORE_DEADLOCK.md` + `specs/`); ajustar "Pontos de atenção" somente com limitações reais
- [x] T015 [US2] `README.md` — Varredura de consistência final (depends T014): percorrer o arquivo inteiro garantindo FR-026 (MariaDB produção em todas as menções; AD nunca concede permissão direta; inventário nunca altera bens; sem número fixo de testes; sem segredo/valor real de `.env`; nenhum caminho/endpoint/comando inexistente remanescente — SC-002/SC-005/SC-006/SC-007)

**Checkpoint**: US2 completa — `README.md` fiel ao código, com D1–D15 aplicadas.

---

## Phase 5: User Story 3 — Validação final e relatório (Priority: P2)

**Goal**: checklist §39 executado, escopo provado (`git diff` somente README.md) e relatório §41 produzido.

**Independent Test**: conferir o relatório contra o diff e executar o checklist item a item (quickstart §2).

### Implementation for User Story 3

- [x] T016 [P] [US3] Executar o checklist de validação do `specs/023-revisao-readme/quickstart.md` §2 (17 itens: comandos, caminhos, endpoints, nomes de arquivos, tecnologias, banco, autenticação, AD, RBAC, inventário, movimentações, backup/restauração, CLI, testes, links internos, blocos de código, Markdown) sobre o `README.md` revisado — registrar cada item como ✓/✗ com a fonte de confirmação
- [x] T017 [US3] Verificação de escopo (depends T016): `git diff --stat` e `git diff --name-only` — confirmar que SOMENTE `README.md` foi alterado (SC-001); se qualquer outro arquivo aparecer, reverter a alteração indevida imediatamente (FR-001/FR-004)
- [x] T018 [US3] Relatório final (depends T017): produzir o relatório do briefing §41 conforme estrutura do `specs/023-revisao-readme/quickstart.md` §5 — arquivo alterado (`README.md`), principais melhorias mapeadas em D1–D15, verificações realizadas com fontes, confirmações (`Código alterado: NÃO`, `Banco alterado: NÃO`, `Configuração alterada: NÃO`) e limitações (informações não confirmáveis diretamente)

**Checkpoint**: US3 completa — entrega verificável e auditável.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: fechamento da feature

- [x] T019 Revisar "Pontos de atenção" do `README.md` (depends T015–T018): garantir que divergências insolúveis documentalmente (se houver) estão registradas ali com explicação — sem especulação, sem bugs corrigidos, sem lista de melhorias (FR-024); se nenhum caso existir, manter a seção enxuta ou omiti-la
- [x] T020 Marcar todas as tasks como `[x]` neste arquivo (depends T019) e validar a feature contra os critérios de aceite da spec (§40): executar varredura final e registrar resultado

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (T001)**: imediato
- **Foundational (T002)**: bloqueia TODAS as stories (mapa divergência→seção)
- **US1 (T003–T006 ∥, depois T008)**: após fundação — auditoria verificável (MVP)
- **US2 (T009→T010→T011→T012→T013→T014→T015)**: após US1 — sequencial (arquivo único)
- **US3 (T016, depois T017→T018)**: após US2
- **Polish (T019→T020)**: após todas as stories

### Parallel Opportunities

- T001, T002 e T003–T007 são verificações [P] (nenhum edita arquivo)
- Todo o trabalho de edição (T009–T015) é sequencial no `README.md` — sem paralelismo possível

### Within Each User Story

- US1: verificações independentes primeiro, fechamento consolidado depois (T008)
- US2: edições por grupo de seções, varredura de consistência por último (T015)
- US3: checklist antes do escopo antes do relatório

---

## Implementation Strategy

### MVP First (Setup + Foundational + US1)

1. T001 → T002 (mapa de trabalho)
2. T003–T007 (∥) → T008 (inventário fechado)
3. **STOP and VALIDATE**: cada divergência tem verificação citável

### Incremental Delivery

- +US2: README corrigido seção a seção (T009–T015)
- +US3: validação + relatório (T016–T018)
- +Polish: pontos de atenção + fechamento (T019–T020)

### Notes

- **Nenhuma task altera código** — violar FR-001/FR-004 invalida a feature (briefing §38/§42)
- Preservar o conteúdo já correto do README (revisão fundamentada, não reescrita por reescrita — research R1)
- Divergência nova descoberta durante a execução entra no mapa (T002) antes de ser aplicada
