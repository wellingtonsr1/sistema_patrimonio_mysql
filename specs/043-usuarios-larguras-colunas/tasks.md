---
description: "Task list for feature implementation"
---

# Tasks: Ajuste Responsivo da Tabela "Usuários do Sistema" (043)

**Input**: Design documents from `/specs/043-usuarios-larguras-colunas/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/ui-contract-tabela-usuarios.md, quickstart.md

**Tests**: NENHUM teste automatizado novo (seção 28 do pedido — sem testes artificiais; padrão 036–042). Suíte pytest existente como regressão (SC-006): baseline antes, focado durante, completo depois (`test_rbac.py` valida esta página — L213/221; `test_help.py` renderiza listagens). Validação visual do quickstart (V0–V5, **com contagem de quebras e conferência de tooltips**) é o aceite, registrada em `validacao.md` (SC-007).

**Organization**: Tasks grouped by user story (US1 linha única/aproveitamento → US2 telas menores/zoom), seguida de polish/validação final. Oitava feature da família de ajustes de tabela — mecanismo validado nas 036–042 reusado (C-1/C-5). Especificidades da 043: **linha garantida em username, full_name e e-mail** (nowrap + ellipsis + tooltip Bootstrap — clarificações da spec, FR-003/004/011); **badges sem ellipsis** (Perfis/Origem/Status — C-6), com `white-space: normal` escopado (lição da 042: `.badge` Bootstrap é nowrap e transborda células fixas); **conjunto único de colunas em px** (lição da 041); **sem bloco de impressão** (R10 — tela não-relatório); rígidas em px com folga para a Plus Jakarta Sans (lições 039/041); comentários CSS não citam controles do header (lição `b75ba99`).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Path Conventions

- **Single project (padrão do repositório)**: template Jinja2 em `app/web/templates/`, suíte pytest em `tests/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirmação do estado atual — nada de infraestrutura nova (stack intocável, Constitution).

- [x] T001 Ler/confirmar a tabela em `app/web/templates/admin/users/list.html` e os elementos protegidos do contract §1 (7 colunas simétricas thead/tbody; Usuário com `bi-person-circle` + badge condicional "ADMIN" `{% if u.is_admin %}` + 2ª linha condicional `full_name`; E-mail com fallback "-"; Origem com badge "Active Directory" + `bi-hdd-network` condicional a `{% if u.auth_provider == 'ad' %}` ou "Local"; Perfis com `d-flex flex-wrap gap-1` de badges OU "Sem perfil"; Status "Ativo"/"Bloqueado"; Último Acesso com `text-nowrap` e fallback "Nunca"; Ações `text-end text-nowrap` com Editar condicional a `usuarios.editar`) e as âncoras RBAC (`test_rbac.py:213/221` valida strings desta página) — sem alterar nada
- [x] T002 Rodar a suíte como BASELINE verde: `python -m pytest tests/ -q` (SC-006; Windows: `.venv\Scripts\python -m pytest tests/ -q`), identificar os testes do domínio admin/users para o run focado e capturar o baseline "antes" do quickstart V0 (screenshot desktop + medição das 7 colunas + **contagem de quebras de linha por célula**) para a comparação antes/depois

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Nenhuma tarefa fundacional — feature de arquivo único (plan.md/Structure Decision); pré-requisitos são T001–T002.

**⚠️ CRITICAL**: T001–T002 concluídas antes de qualquer alteração (baseline precisa existir para a comparação antes/depois).

**Checkpoint**: Estado confirmado e baseline capturado — implementação pode começar.

---

## Phase 3: User Story 1 - Linha única e aproveitamento horizontal (Priority: P1) 🎯 MVP

**Goal**: A tabela ocupa praticamente toda a largura útil do card; E-mail, Usuário (username e full_name) dominam com **linha garantida** (nowrap + ellipsis + tooltip Bootstrap); Perfis com badges íntegros sem ellipsis; Último Acesso/Origem/Status/Ações compactas sem quebra; alinhamento e funcionalidade preservados (quickstart V1–V3).

**Independent Test**: abrir `/admin/users` em desktop e inspecionar/medir o aproveitamento, a linha única e os tooltips (comparação com o baseline V0).

### Implementation for User Story 1

- [x] T003 [US1] Em `app/web/templates/admin/users/list.html`: adicionar classe de escopo à tabela (ex.: `usr-lista-table`) e bloco `<style>` embutido no topo do `{% block content %}` com comentário de rastreabilidade "Feature 043" (sem citar controles do header — lição `b75ba99`), `table-layout: fixed; width: 100%; min-width: <medido>` e as larguras por classes `col.cN` no `<colgroup>` (mecanismo das 036–042 — research R2/R3; larguras de partida do data-model: Usuário ~150 · E-mail ~200 · Origem ~120 · Perfis ~150 · Status ~90 · Último Acesso ~150 · Ações ~70, a refinar por medição — C-1; **conjunto único, sem media query de colunas** — lição da 041); rígidas em px com folga para a Plus Jakarta Sans (×1,25–1,30 — lições 039/041); nenhuma regra global (contract §5)
- [x] T004 [US1] Em `app/web/templates/admin/users/list.html`: implementar o mecanismo de **linha garantida** (research R4 — clarificações, FR-003/004/011): classe auxiliar de ellipsis (ex.: `.usr-ellip`: `nowrap + overflow:hidden + text-overflow:ellipsis + max-width:100%`) com `data-bs-toggle="tooltip" data-bs-placement="top" title="{{ ... }}"` no **username** (ícone e badge ADMIN fora do span cortável) e no **full_name** (2ª linha preservada, cada linha com seu tooltip) e no **e-mail**; `white-space: normal` escopado para os badges desta tabela (`.usr-lista-table .badge` — lição da 042: nowrap do Bootstrap transborda células fixas; badges **sem ellipsis**, FR-005/006/007); preservar `text-nowrap` existentes (Último Acesso/Ações), condições Jinja, classes funcionais e fallbacks (contract §1–§2)
- [x] T005 [US1] Validar em desktop os cenários V1 (aproveitamento ≥95% e textuais dominando — medição), V2 (**tooltips Bootstrap** com o valor completo em username/full_name/e-mail; badges íntegros: ADMIN, AD, Perfis, Status, "Sem perfil"; fallbacks "Nunca"/"-"; Editar funcional) e V3 (alinhamento 7/7; altura de linhas uniforme; distribuição estável entre buscas) do `quickstart.md` — refinar as larguras por medição se algum conteúdo estourar/quebrar (C-1), registrando os valores finais e o print antes/depois
- [x] T006 [US1] Rodar a suíte após a alteração (mínimo os arquivos que exercitam a página/domínio): `python -m pytest tests/test_help.py tests/test_rbac.py <testes admin/users identificados no T002> -q` e, na sequência, a suíte completa verde (SC-006)

**Checkpoint**: US1 entregue — linha garantida com corte controlado em desktop, tooltips acessíveis e zero regressão (MVP).

---

## Phase 4: User Story 2 - Responsividade em telas menores e zoom (Priority: P2)

**Goal**: A tabela (7 colunas) mantém a leitura prioritariamente horizontal em notebook/tablet/celular e zoom 80%–200%, com rolagem confinada quando inevitável, valores truncados consultáveis e controles acessíveis (quickstart V4).

**Independent Test**: abrir `/admin/users` em larguras variadas e níveis de zoom e verificar adaptação, legibilidade, tooltips e acessibilidade dos controles.

### Implementation for User Story 2

- [x] T007 [US2] Em `app/web/templates/admin/users/list.html` (somente se a validação mostrar necessidade — research R6): ajuste responsivo pontual no `<style>` escopado — **sem media query de colunas** (conjunto único, lição da 041); eventual refinamento do `min-width` garantindo: rolagem horizontal confinada ao `table-responsive` quando a viewport for menor que o mínimo, todas as 7 colunas acessíveis, valores truncados consultáveis via tooltip, sem sobreposição, sem reduzir fontes excessivamente (proibição da seção 16 do pedido)
- [x] T008 [US2] Validar o cenário V4 do `quickstart.md`: desktop médio/notebook (768–1399px — linha garantida mantida com corte controlado), tablet (576–767px) e celular (<576px — rolagem confinada funcional, ações acessíveis), zoom 80%–200% (precedentes 036–042) — além dos temas claro e escuro (nenhuma diferença de contraste)

**Checkpoint**: US1 + US2 funcionam — a alteração visual está completa.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Não-vazamento de escopo, registro formal e revisão final (Constitution I/XI/XII).

- [x] T009 Validar o cenário V5 do `quickstart.md` (contract §5): tabelas das specs 036 (conferência), 037 (listagem de inventários), 038 (equipamentos), 039 (movimentações), 040 (custodiantes), 041 (Relatório Contábil-Físico) e 042 (Trilha de Auditoria) e demais telas visualmente idênticas; container da tela (page header, filtro, contador, estado vazio) inalterado; **nenhuma mudança de impressão** (tela não-relatório — R10); `git diff` contendo APENAS `app/web/templates/admin/users/list.html` (nenhum asset estático, nenhum `style.css`, nenhum `sw.js`)
- [x] T010 Criar `specs/043-usuarios-larguras-colunas/validacao.md` no formato das 036–042: baseline + suíte final verde, comparação antes/depois (V0, **incluindo redução de quebras**), tabela de larguras finais adotadas (com ajustes e motivos), resultado de cada cenário V1–V5 (com medições, zoom e **verificação de tooltips**), temas, observações preexistentes fora de escopo e decisões finas (SC-007)
- [x] T011 Revisão final de documentação fiel (Princípio XI): confirmar que README/ajuda não descrevem larguras da listagem de usuários — se nada a atualizar, registrar a constatação em `validacao.md`; marcar tasks concluídas e commit do grupo lógico (template + spec/validação) no padrão do repositório

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (T001–T002)**: imediato; baseline + V0 obrigatórios antes de tocar o template
- **US1 (T003–T006)**: depende do Setup; tasks sequenciais no MESMO arquivo (nenhuma [P])
- **US2 (T007–T008)**: depende da US1 concluída (refina o que ela produziu)
- **Polish (T009–T011)**: depende de US1+US2

### User Story Dependencies

- **US1 (P1)**: independente — entrega o MVP sozinha (linha garantida + aproveitamento em desktop)
- **US2 (P2)**: refina a US1 em telas menores/zoom; não faz sentido sem ela

### Parallel Opportunities

- Nenhuma tarefa marcada [P]: todas operam o mesmo arquivo (`admin/users/list.html`) ou dependem do seu estado (validações). Fluxo sequencial por design (Princípio I — mudança cirúrgica), como nas 036–042.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Setup (T001–T002, baseline + V0)
2. US1 (T003–T006) → **STOP and VALIDATE**: quickstart V1–V3 em desktop (linha única + tooltips) + suíte verde
3. Só então US2 para telas menores/zoom

### Incremental Delivery

1. US1 → linha garantida com corte controlado + tooltips no uso principal (desktop)
2. US2 → notebook/tablet/celular/zoom/temas (rolagem confinada)
3. Polish → escopo confinado, validação registrada, docs fiéis, commit

---

## Notes

- Mudança exclusivamente de apresentação: nenhuma regra de autenticação/RBAC/AD, dado, rota, permissão ou asset estático muda (FR-013/FR-014)
- NÃO bumpar versão de `style.css?v=` nem tocar o SW — `admin/users/list.html` é server-side, nunca cacheado (research R1/R9)
- **Sem `@media print`**: tela não-relatório — nenhum bloco de impressão criado ou alterado (R10)
- Larguras NÃO são fixadas pela spec (C-1): partida no data-model, refinamento por medição na implementação (V0 antes/depois)
- Escolha de `table-layout: fixed` justificada na análise (research R2 — C-5): torna o corte previsível (linha garantida)
- **Linha garantida** (clarificações): username, full_name e e-mail com nowrap + ellipsis + tooltip Bootstrap — nunca ellipsis sem tooltip (C-4); badge ADMIN e ícone fora dos spans cortáveis
- **Badges sem ellipsis** (C-6): Perfis/Origem/Status com `white-space: normal` escopado (lição 042) — quebra apenas entre palavras
- **Conjunto único de colunas px** (lição da 041): sem media query de colunas; pisos ×1,25–1,30 da fonte real; rolagem confinada é o plano B
- Tooltips: `data-bs-toggle="tooltip" data-bs-placement="top" title="..."` — inicialização existente em `base.html`/`main.js` (sem JS novo); carregam dados das linhas, não strings de controles
- Comentários CSS/HTML NÃO citam nomes de controles do header (lição `b75ba99` — `test_rbac.py` valida strings nesta página)
- Commit após cada grupo lógico (US1; US2; polish) — mensagens no padrão do repositório
- Evitar: regras CSS globais, alteração em header/filtro/estado vazio/container, refatoração não relacionada
