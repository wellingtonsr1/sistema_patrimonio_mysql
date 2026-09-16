# Implementation Plan: Pesquisa de Colaboradores

**Branch**: `006-pesquisa-colaboradores` | **Date**: 2026-09-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/006-pesquisa-colaboradores/spec.md`

## Summary

Adicionar pesquisa combinada à tela existente de colaboradores (`GET /custodians`): um campo
acima da tabela filtra por matrícula, nome, cargo, departamento e e-mail, com correspondência
parcial e sem diferenciação de maiúsculas/minúsculas. A decisão central deixada para este plano
(RT-003 da spec) é resolvida pelo precedente do próprio sistema: a listagem de bens já filtra
**server-side** via `?search=` (rota → `AssetService.get_all(search=...)` com `or_` + `ilike`).
A feature 006 segue exatamente o mesmo padrão: `CustodianService.get_all` ganha o parâmetro
opcional `search` (retrocompatível) e a rota/template consomem. **Nenhuma nova tela, entidade,
coluna, permissão ou segunda lógica de consulta.** Arquivos de código modificados:
`custodian_service.py`, `app/web/routes.py` (rota da listagem) e `custodians/list.html`
(+ testes novos + doc da ajuda).

## Technical Context

**Language/Version**: Python 3.10+ (stack existente, inalterada)

**Primary Dependencies**: Nenhuma nova. Reutiliza: SQLAlchemy (`ilike`, `or_` — já usados em
`asset_service.py`), Jinja2, pytest. Stack (FastAPI/SQLAlchemy/Jinja2/pytest) intocada.

**Storage**: MariaDB (produção, via `DATABASE_URL`); SQLite in-memory na suíte. **Zero DDL** —
nenhuma tabela/coluna nova; a pesquisa consulta colunas existentes de `custodians`.

**Testing**: pytest ≥8 (padrão existente). **Novo arquivo** `tests/test_custodians_search.py`
(testes web via fixture `client` e de serviço via `db_session`). **Nenhum teste existente é
editado** — ver correção: não existe `tests/test_custodians.py` (a referência da spec foi
corrigida); testes de colaboradores vivem em `test_ad.py`/`test_rbac.py`/`test_custodian_import.py`
e permanecem intactos.

**Target Platform**: Navegador web (mesmos navegadores suportados — RT-005).

**Project Type**: Extensão de consulta em sistema web monolítico em camadas (Web → Service → Models).

**Performance Goals**: O filtro executa no banco via `ILIKE` sobre a mesma consulta única da
listagem — nenhuma consulta adicional, nenhum carregamento extra no navegador. A tela hoje já
carrega a lista completa (sem paginação); a pesquisa **não aumenta** o volume transferido
(filtra no servidor, renderiza só o resultado).

**Constraints**: Sem paginação nova (não existe hoje; introduzi-la seria expansão de escopo —
avaliada e desnecessária para o volume atual, ver R1). Senha/credenciais: n/a. Sem alteração
de permissões (`colaboradores.visualizar` permanece o gate da rota — FR-013/RN-002).
Sem alteração de cadastro/detalhes/outras telas. Comportamento de `%`/`_` idêntico ao da
pesquisa de bens (precedente, ver R6).

**Scale/Scope**: 1 parâmetro opcional no service; 1 alteração na rota; 1 alteração no template (campo de busca + estado vazio); 1 novo arquivo de testes; documentação somente nos arquivos que forem tecnicamente necessários.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio (Constitution v1.0.0) | Status | Observação |
|---|---|---|
| I. Preservação / evolução incremental | ✅ PASS | Extensão aditiva: parâmetro opcional `search` (default `None` = comportamento atual), campo no template, nada substituído |
| II. Arquitetura em camadas | ✅ PASS | Filtro na camada de serviço; rota só repassa o parâmetro; template só renderiza |
| III. Regras nos services | ✅ PASS | A filtragem (`ilike`/`or_`) vive em `CustodianService.get_all` — não duplicada em rota/template/JS (RT-002/FR-014) |
| IV. Integridade patrimonial / movimentações | ✅ PASS | Não toca bens, movimentações ou custódia (só consulta colaboradores) |
| V. Integridade do inventário | ✅ PASS | Não toca inventário |
| VI. Segurança por padrão (auth, RBAC) | ✅ PASS | Rota mantém `require_permission("colaboradores.visualizar")`; a pesquisa não expõe nada além do que a tela já expõe (RN-002) |
| VII. MariaDB / proteção de dados / DDL | ✅ PASS | **Zero DDL**; apenas `SELECT` com filtro sobre colunas existentes |
| VIII. Testes como não-regressão | ✅ PASS | Novos testes para o novo comportamento; nenhum teste existente editado; suíte intacta |
| IX. Auditoria | ✅ PASS/N-A | Consulta não é operação auditável (padrão do sistema: listagens não geram evento); nada muda |
| X. Interface consistente | ✅ PASS | Campo segue o padrão visual da pesquisa de bens (`input-group` + `bi-search` + placeholder orientativo + estado vazio) |
| XI. Documentação fiel | ✅ PASS | Artigo da central de ajuda sobre colaboradores e §12.4 do doc de arquitetura atualizados na mesma tarefa |
| XII. Especificação + validação | ✅ PASS | Spec aprovada; validação executável definida em `quickstart.md` |

**Resultado: 12/12 PASS.** Re-check pós-Phase 1: mantém-se 12/12 (design é a extensão mínima
do precedente existente).

## Project Structure

### Documentation (this feature)

```text
specs/006-pesquisa-colaboradores/
├── plan.md                         # This file
├── research.md                     # Phase 0 — decisões R1..R6
├── data-model.md                   # Phase 1 — entidade consultada (zero DDL)
├── quickstart.md                   # Phase 1 — protocolo de validação
├── contracts/
│   └── web-search-contract.md      # Phase 1 — contrato GET /custodians?search=
├── checklists/
│   └── requirements.md             # (da etapa /speckit-specify)
└── tasks.md                        # (futuro /speckit-tasks)
```

### Source Code (repository root)

```text
app/
├── services/
│   └── custodian_service.py        # MODIFICAR: get_all ganha search: Optional[str] = None
│                                   #   (filtro or_ + ilike nos 5 campos; default mantém comportamento)
├── web/
│   ├── routes.py                   # MODIFICAR: list_custodians_view recebe search: Optional[str]
│   │                               #   e repassa ao service + template
│   └── templates/custodians/
│       └── list.html               # MODIFICAR: campo de busca acima da tabela (padrão assets)
│                                   #   + linha "Nenhum colaborador encontrado." na busca sem resultado
└── (todo o restante intocado — inclusive API REST /api/v1/custodians, fora do escopo da tela)

tests/
└── test_custodians_search.py       # NOVO — testes web + serviço (§7)

docs/ARQUITETURA_E_MANUTENCAO.md    # MODIFICAR (docs): §12.4 menciona a pesquisa
app/services/help_service.py        # MODIFICAR (docs): artigo "cadastrar-colaboradores" cita a busca
```

**Structure Decision**: estrutura single-project existente mantida; a feature toca **um service**,
**uma rota**, **um template** — o mínimo para a consulta, sem refatoração (spec Out of Scope).

---

# Plano Técnico Detalhado

## 1. Fluxo da Solução (design)

```text
Operador → GET /custodians?search=amanda          (ou GET /custodians sem search)
  ↓
list_custodians_view(request, search=None, db)
  ↓  [require_permission("colaboradores.visualizar") — intacto]
CustodianService.get_all(db, search="amanda")
  ├─ search None/vazio → consulta atual, sem filtro (comportamento idêntico ao de hoje)
  └─ search com texto → termo = search.strip()
        query.filter(or_(
            Custodian.registration_code.ilike(f"%{termo}%"),
            Custodian.name.ilike(f"%{termo}%"),
            Custodian.role.ilike(f"%{termo}%"),
            Custodian.department.ilike(f"%{termo}%"),
            Custodian.email.ilike(f"%{termo}%"),
        ))   # ilike = case-insensitive (FR-009); %termo% = parcial (FR-008)
  ↓
rota: for c in custodians: c.active_assets_count = count_assigned_assets(db, c.id)
      (contagem calculada apenas para os colaboradores visíveis — mesmo mecanismo de hoje)
  ↓
custodians/list.html
  ├─ campo de busca acima da tabela (input-group + bi-search, valor repopulado)
  ├─ com resultados → tabela idêntica à atual (mesmas colunas/links/ações — FR-012)
  └─ sem resultados → "Nenhum colaborador encontrado." (linha de estado vazio — FR-010)
```

Pontos do design:
- **Uma única lógica de consulta** (RT-002): o filtro vive no `get_all` existente; a API REST
  `/api/v1/custodians` e os demais chamadores (`active_only=True`) continuam funcionando sem
  alteração, pois o parâmetro é opcional com default `None`.
- **Estado vazio duplo no template**: (a) "Nenhum colaborador cadastrado" (já existe — lista
  vazia sem busca); (b) novo "Nenhum colaborador encontrado." (busca sem correspondência).
  Distinção: `custodians` vazio **com** `search` preenchido → (b).
- **Formulário GET**: submit recarrega a página com `?search=...` — sem JavaScript novo,
  funcionando em qualquer navegador (RT-005) e repovoando o campo (`value="{{ search }}"`).

## 2. Componentes Afetados (arquivos e funções reais)

| Arquivo | Ação | O quê exatamente |
|---|---|---|
| `app/services/custodian_service.py` | **MODIFICAR** | `get_all(db, active_only=False, search: Optional[str] = None)`: quando `search` com texto após `strip()`, aplicar `or_` de 5 `ilike` (registration_code, name, role, department, email). Importar `or_` de sqlalchemy. Default `None` = comportamento atual intacto |
| `app/web/routes.py` | **MODIFICAR** | `list_custodians_view(request, search: Optional[str] = None, db)`: repassa `search` ao `get_all` e `"search": search or ""` ao template |
| `app/web/templates/custodians/list.html` | **MODIFICAR** | (a) formulário GET com campo de busca (padrão visual de `assets/list.html`: `input-group`, ícone `bi-search`, placeholder "Pesquisar por matrícula, nome, cargo, departamento ou e-mail..."); (b) bloco `{% if custodians %}` mantém a tabela; (c) novo `{% elif search %}` com "Nenhum colaborador encontrado."; (d) "Nenhum colaborador cadastrado" permanece para lista vazia sem busca |
| `tests/test_custodians_search.py` | **CRIAR** | Casos do §7; fixtures `client` e `db_session` do `conftest.py` |
| `app/services/help_service.py` | **MODIFICAR (docs)** | Artigo "cadastrar-colaboradores" (L537): mencionar o campo de busca na tela |
| `docs/ARQUITETURA_E_MANUTENCAO.md` | **MODIFICAR (docs)** | §12.4 Colaboradores: uma linha sobre a pesquisa server-side |
| `app/api/custodians_api.py`, models, schemas, permissões | **NÃO modificar** | API REST fora do escopo (a spec é a tela); o service estendido é retrocompatível |

## 3. Decisão RT-003 (onde o filtro executa) — resolvida

**Server-side**, pelos motivos de R1 (abaixo): é o padrão do sistema (pesquisa de bens),
mantém a regra na camada de serviço (Constitution III), não carrega dados além dos atuais no
navegador e funciona sem JavaScript. Client-side rejeitado: criaria um segundo padrão de busca
no sistema (o existente é server-side), drenaria a lista inteira para o DOM antes de filtrar
(vol. total no navegador ≥ atual, mesmo filtrando) e embutiria regra de negócio em JS.

## 4. Segurança e Autorização

- A rota mantém `colaboradores.visualizar`; a pesquisa apenas **reduz** o universo já visível
  — nunca amplia (RN-002/FR-013). Nenhuma permissão nova, nenhum dado novo exposto.
- Entrada do usuário: usada exclusivamente como parâmetro de filtro via SQLAlchemy (bind
  parameters — sem SQL concatenado). `%`/`_` seguem o comportamento do precedente de bens (R6).
- Nenhum segredo, log ou dado sensível envolvido.

## 5. Tratamento de Erros / Estados

| Situação | Comportamento |
|---|---|
| Sem `search` ou só espaços | Lista completa (igual a hoje) — FR-011/edge case |
| Busca com correspondências | Tabela com os colaboradores correspondentes (dados/ações idênticos) |
| Busca sem correspondência | "Nenhum colaborador encontrado." — HTTP 200, sem erro (FR-010) |
| Lista vazia sem busca | "Nenhum colaborador cadastrado" (estado atual preservado) |
| Campo limpo + submit/voltar | `?search=` vazio → lista completa |
| Caracteres especiais (`%`, `_`, aspas) | Sem erro; comportamento idêntico à pesquisa de bens (R6) |

## 6. Testes — Estratégia (§9 da spec)

**Novo `tests/test_custodians_search.py`** (pytest; `client` autenticado + `db_session` do conftest):

1. **Nome completo/parcial**: Amanda Silva Nunes + Amanda Teixeira Rodrigues; busca `Amanda` → ambos (e somente) — CA-002.
2. **Matrícula**: `MAT-1036` → colaborador correspondente — CA-003 (e parcial `1036`).
3. **Departamento**: `Comercial` → correspondentes — CA-004.
4. **Cargo**: `Gerente` → "Gerente de Contas" — CA-005.
5. **E-mail**: `amanda.nunes36` → correspondente — CA-006.
6. **Case-insensitive**: `AMANDA`/`Amanda`/`amanda` → resultados equivalentes — CA-007.
7. **Sem correspondência**: termo inexistente → 200 + "Nenhum colaborador encontrado." — CA-008.
8. **Sem search**: `GET /custodians` → lista completa, sem a mensagem de busca vazia — CA-009/FR-011.
9. **Combinada entre campos**: termo que casa no departamento de um e no nome de outro → ambos (FR-007).
10. **Não-regressão da tela**: resultados mantêm link `/custodians/{id}`, contagem de bens e ações; serviço sem `search` retorna todos (retrocompatibilidade do `get_all`) — CA-010/CA-011.
11. **Permissão**: usuário sem `colaboradores.visualizar` segue bloqueado (comportamento existente da rota, exercitado via suíte RBAC — sem novo gate).

**Nenhum teste existente é editado** (Constitution VIII); `test_ad.py`/`test_rbac.py`/
`test_custodian_import.py` permanecem intactos.

## 7. Estratégia de Migração / Compatibilidade

- **Migração**: nenhuma (zero DDL, sem env nova, sem seed).
- **Compatibilidade comportamental**: `get_all` sem `search` = exatamente o comportamento atual
  (API REST e demais chamadores intocados); a rota sem `?search=` renderiza a tela atual.
- **Baseline 001**: não editada (snapshot datado), como nas features 002/005.

## 8. Riscos

| Risco | Prob. | Impacto | Mitigação |
|---|---|---|---|
| Usuário espera busca "instantânea" (client-side) | Baixa | Baixo | Submit GET recarrega rápido (consulta única com ILIKE); padrão idêntico à tela de bens que o usuário já usa |
| Divergência de acentos ("Joao" ≠ "João") | Média | Baixo | Fora de escopo por premissa 3 da spec; melhoria futura candidata |
| `count_assigned_assets` por colaborador visível com base grande | Baixa | Baixo | Mecanismo idêntico ao atual (mesma N+1 de hoje); a pesquisa **reduz** o nº de iterações quando filtra |

## 9. Arquivos que serão modificados (resumo da entrega)

1. `app/services/custodian_service.py` — parâmetro `search` no `get_all` (única regra nova).
2. `app/web/routes.py` — rota recebe/repassa `search`.
3. `app/web/templates/custodians/list.html` — campo + estado vazio de busca.
4. `tests/test_custodians_search.py` — novo arquivo de testes.
5. `app/services/help_service.py` + `docs/ARQUITETURA_E_MANUTENCAO.md` — documentação (mesma tarefa).

## 10. Arquivos que NÃO devem ser modificados

`app/api/custodians_api.py` · `app/models/**` · `app/schemas/**` · `app/config.py` ·
`app/database.py` · demais rotas/templates · permissões/RBAC · `tests/conftest.py` e testes
existentes · `specs/001-sistema-existente/**` · banco de dados (nenhum DDL).

## 11. Estratégia de Implementação Incremental

1. **T1 — Testes (TDD)**: `tests/test_custodians_search.py` — vermelho primeiro (rota ainda não filtra).
2. **T2 — Service**: parâmetro `search` no `get_all` → testes de serviço verdes.
3. **T3 — Rota + template**: campo, repasse e estado vazio → testes web verdes.
4. **T4 — Regressão**: suíte completa (estado conhecido: 230 passed + lockout defasado conhecido).
5. **T5 — Docs**: artigo de ajuda + §12.4.
6. **Validação final**: `quickstart.md` (suíte + cenários manuais no navegador).
