# Implementation Plan: Pesquisa de Locais

**Branch**: `007-pesquisa-locais` | **Date**: 2026-09-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/007-pesquisa-locais/spec.md`

## Summary

Adicionar pesquisa server-side por **Nome / Identificação** à tela existente de Locais (`GET /locations`), replicando o padrão já estabelecido nas telas de Bens e Colaboradores (feature 006): parâmetro GET `search` processado na camada de serviço (`LocationService.get_all` ganha parâmetro aditivo e retrocompatível), card de filtros separado com o par de botões **Filtrar** (com ícone) e **Limpar** (somente texto), estados vazios distintos ("Nenhum local encontrado." para pesquisa sem resultado; "Nenhum local cadastrado" preservado) e testes TDD em arquivo novo. Diferença essencial em relação à 006: o filtro é **mono-campo** — exclusivamente `Location.name` (FR-002), não uma busca combinada `or_` por vários campos.

## Technical Context

**Language/Version**: Python 3.10+ (stack existente, Constitution §Restrições)

**Primary Dependencies**: FastAPI + Uvicorn, SQLAlchemy 2, Jinja2 + Bootstrap 5, Pydantic v2 (todos existentes — nenhuma dependência nova)

**Storage**: MariaDB/MySQL via `DATABASE_URL` (PyMySQL) — **zero DDL** nesta feature; SQLite restrito à suíte de testes (já é o padrão)

**Testing**: pytest + TestClient do FastAPI (padrão existente); novo arquivo `tests/test_locations_search.py`

**Target Platform**: Servidor web local/Windows (existente), navegadores já suportados pelo sistema

**Project Type**: Aplicação web monolítica existente (FastAPI + Jinja2 server-side)

**Performance Goals**: SC-006 — pesquisa < 2s com o volume atual de locais; consulta `ilike` indexável sobre tabela pequena (mesmo padrão das pesquisas de bens/colaboradores)

**Constraints**:
- Filtro exclusivamente no campo `Location.name` ("Nome / Identificação") — FR-002.
- Compatibilidade de comportamento: sem `search`, `get_all` retorna exatamente o resultado de hoje (API REST de locais e demais chamadores intactos) — FR-011.
- Permissão `locais.visualizar` intocada; nenhum gate novo — FR-012.
- Botões: Filtrar com ícone (`bi-funnel`), Limpar somente texto sem ícone, ambos sempre visíveis no card de filtros — FR-014 (padrão vigente da tela de colaboradores, corrigido nesta conversa).
- Mensagem exata "Nenhum local encontrado." — FR-007.
- Nenhuma alteração fora do escopo (Constitution I): sem refatoração da rota, sem paginação, sem autocomplete.

**Scale/Scope**: 1 rota web alterada (assinatura + passagem de parâmetro), 1 service alterado (parâmetro aditivo), 1 template alterado (card de filtros + estados vazios), 1 arquivo de testes novo, 2 artefatos de documentação. Sem alteração de models, schemas, API REST, permissões ou banco.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Princípio | Status | Evidência |
|---|---|---|---|
| I | Preservação do sistema existente | ✅ PASS | Alteração incremental: parâmetro aditivo em service existente; comportamento sem `search` idêntico ao atual; nenhum módulo reescrito; API REST não expõe o filtro |
| II | Arquitetura em camadas | ✅ PASS | Regra do filtro no service (`LocationService`); rota apenas recebe `search`, delega e repõe o termo no template |
| III | Regras de negócio nos services | ✅ PASS | Normalização (`strip`) + condição `ilike` concentradas no service; nenhuma lógica de filtro em rota/template |
| IV | Integridade patrimonial | ✅ PASS | Operação de consulta; nenhum estado/localização/custódia alterado; nenhum caminho paralelo ao motor de movimentações |
| V | Integridade do inventário | ✅ PASS | Nenhum fluxo de inventário tocado |
| VI | Segurança (auth, RBAC, AD) | ✅ PASS | Rota existente mantém `locais.visualizar`; pesquisa revela apenas o universo já visível; nenhum dado sensível em logs |
| VII | Banco MariaDB e proteção dos dados | ✅ PASS | Zero DDL, zero migração; somente `SELECT` com filtro opcional |
| VIII | Testes como não regressão | ✅ PASS | TDD: testes novos em `tests/test_locations_search.py` escritos **antes** da implementação; nenhum teste existente editado; suíte completa verde ao final |
| IX | Auditoria | ✅ PASS/N-A | Operação de consulta sem mutação — não se enquadra nas operações relevantes auditadas; nenhum evento novo necessário |
| X | Interface consistente | ✅ PASS | Card de filtros, ícone, classes e estados vazios replicam o padrão vigente de colaboradores/bens; ajuda embutida atualizada |
| XI | Documentação fiel | ✅ PASS | Atualização na mesma tarefa: artigo "cadastrar-locais" da central de ajuda + §12.4 do `ARQUITETURA_E_MANUTENCAO.md` |
| XII | Spec-driven + validação | ✅ PASS | Fluxo Spec Kit em curso; validação final = suíte + quickstart (T-ui manual para SC-001) |

**Post-design re-check**: sem violações — o desenho não introduz nova camada, novo endpoint, novo modelo nem novo padrão visual (ver Complexity Tracking: vazio).

## Project Structure

### Documentation (this feature)

```text
specs/007-pesquisa-locais/
├── plan.md              # This file
├── research.md          # Phase 0 — decisões R1–R6
├── data-model.md        # Phase 1 — entidade consultada (read-only)
├── contracts/
│   └── web-search-contract.md   # Phase 1 — contrato GET /locations?search=
├── quickstart.md        # Phase 1 — protocolo de validação
└── tasks.md             # Phase 2 (/speckit-tasks) — NÃO criado aqui
```

### Source Code (repository root)

```text
app/
├── services/
│   └── location_service.py      # ALTERAR: get_all ganha search: Optional[str] = None
├── web/
│   ├── routes.py                # ALTERAR: list_locations_view recebe/repassa search
│   └── templates/
│       └── locations/
│           └── list.html        # ALTERAR: card de filtros + estados vazios
tests/
└── test_locations_search.py     # CRIAR: suíte TDD da feature
app/services/help_service.py     # ALTERAR (docs XI): seção "Pesquisar locais" no artigo
docs/ARQUITETURA_E_MANUTENCAO.md # ALTERAR (docs XI): nota no §12.4
```

**Structure Decision**: Estrutura monolítica existente mantida; alterações restritas ao trio service → rota → template (mesma sequência de integração da feature 006), testes em arquivo novo por analogia a `tests/test_custodians_search.py`.

## Implementation Flow (ordem de integração)

1. **Service** (`location_service.py`): assinatura `get_all(db, search: Optional[str] = None)`.
   - `search` é normalizado: `termo = (search or "").strip()`.
   - Se `termo` vazio → consulta **byte-idêntica** à atual (`order_by(branch, department, name)`).
   - Se `termo` presente → `.filter(Location.name.ilike(f"%{termo}%"))` aplicado **antes** do `order_by`, mantendo a ordenação atual com e sem filtro (Assumption 3 da spec).
   - Mono-campo: **somente** `Location.name` (diferença deliberada da 006, que usa `or_` multi-campo).
2. **Rota** (`routes.py::list_locations_view`): recebe `search: Optional[str] = None`, passa ao service e repõe no template (`"search": search or ""`); permissão e contagem de bens (`count_assets` por local exibido) inalteradas.
3. **Template** (`locations/list.html`):
   - Card de filtros separado **antes** do card da tabela: `<div class="card p-3 mb-4">` com `<form method="get" action="/locations" class="row g-2 align-items-center">` (padrão de `assets/list.html`/`custodians/list.html`).
   - Campo: `input-group` + ícone `bi-search` + `placeholder` orientativo + `value="{{ search }}"` (FR-009).
   - Botões (FR-014): `<button type="submit" class="btn btn-primary"><i class="bi bi-funnel me-1"></i> Filtrar</button>` + `<a href="/locations" class="btn btn-ghost">Limpar</a>` — Limpar **somente texto, sem ícone**, sempre visível (padrão vigente de colaboradores).
   - Estados vazios: `{% elif search %}` → `Nenhum local encontrado.` (FR-007, texto exato); `{% else %}` → "Nenhum local cadastrado" preservado como estado distinto.
4. **Testes** (`tests/test_locations_search.py`, arquivo novo, TDD — vermelho antes do verde):
   - US1: pesquisa por nome completo; parcial (`Controle` → "IPMJP – Acessoria de Controle Interno"); sigla (`IPMJP` → todos os locais do exemplo); termo reposto no campo.
   - US2: case-insensitive (`CONTROLE`/`controle`/`Controle` equivalentes); parcial em qualquer posição (`gabinete`); termo com espaços nas extremidades aparado; vazio/só espaços → lista completa; nenhum resultado → "Nenhum local encontrado." exato e HTTP 200; limpar → lista completa; **contratesta mono-campo**: termo que casa só com Filial/Departamento/Gestor **não** retorna registro.
   - US3 (não regressão): colunas da tabela preservadas; link "Ver Bens" com `location_id` correto; contagem de bens idêntica com e sem pesquisa; retrocompatibilidade do `get_all` sem `search` (chamada direta = mesma lista de hoje); tela sem `search` idêntica ao estado atual; read-only (nenhuma mutação após pesquisa).
5. **Documentação** (Constitution XI, mesma tarefa): artigo `cadastrar-locais` da ajuda ganha seção "Pesquisar locais" (alvo único: Nome / Identificação; Filtrar/Limpar); §12.4 do doc de arquitetura registra a pesquisa server-side mono-campo.

## Error Handling

| Cenário | Comportamento |
|---|---|
| Termo vazio/só espaços | Lista completa (normalização no service) |
| Termo sem correspondência | HTTP 200 + "Nenhum local encontrado." (estado vazio, sem erro) |
| Caracteres especiais (`%`, `_`, aspas, acentos) | Segue o precedente aceito de bens/colaboradores (R6): a página não falha; comportamento de curinga do `ilike` é aceito como padrão do sistema; teste confirma ausência de erro |
| Falha de banco | Comportamento existente (exceção propagada pelo handler global) — nenhum tratamento novo inventado |
| Acesso sem permissão | Inalterado: gate `locais.visualizar` bloqueia antes da rota (403 existente) |

## Security & Permissions

- Nenhum gate novo nem alteração de RBAC: a pesquisa opera dentro do universo já autorizado pela rota (FR-012/RN da spec).
- O termo pesquisado via GET aparece na URL (decisão explícita da spec/RF) — nenhum dado sensível é pesquisável por esse campo (nomes de locais); sem exposição de credenciais (Constitution VI).
- Sem escrita: operação read-only; trilha de auditoria não se aplica (IX).

## Testing Strategy

- **Arquivo novo** `tests/test_locations_search.py` (fixtures `client`/`db_session` existentes), seguindo o padrão de `tests/test_custodians_search.py`.
- **TDD por história** (lições 005/006): testes escritos e executados **vermelhos** antes da implementação; marcador `[P]` nas tasks de teste significa independência de arquivo, nunca execução concorrente com a implementação.
- **Regressão**: suíte completa `python -m pytest tests/ -q` verde ao final (baseline atual: 245 passed / 1 failed conhecido — lockout defasado; a mesma exceção pré-existente é aceita).
- **Retrocompatibilidade comprovada por teste**: chamada direta `LocationService.get_all(db)` (sem `search`) e a API REST `/api/v1/locations` inalteradas.

## Risks & Mitigations

| Risco | Mitigação |
|---|---|
| Chamadores da API REST de `get_all` receberem comportamento alterado | Parâmetro com default `None` e branch de consulta idêntica quando ausente; teste de retrocompatibilidade |
| Duplicação do padrão de filtro (rota vs service) | Regra 100% no service (Constitution III); rota só repassa |
| Divergência visual do par Filtrar/Limpar entre telas | Copiar o markup vigente de `custodians/list.html` (corrigido nesta conversa); nada de estilo novo |
| Expectativa de busca multi-campo | Contratesta explícito na suíte (FR-002) + nota na ajuda embutida |

## Complexity Tracking

> Sem violações de Constitution — tabela vazia por design.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
