# Implementation Plan: Identificador Provisório de Colaborador (PROV-*)

**Branch**: `010-matricula-provisoria` | **Date**: 2026-09-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/010-matricula-provisoria/spec.md`

## Summary

Permitir o cadastro de colaborador **sem matrícula funcional**, gerando automaticamente um identificador provisório `PROV-000001` (prefixo `PROV-` + 6 dígitos, sequencial, não escolhível, único), sem bloquear qualquer operação patrimonial do colaborador provisório, e permitindo depois a **substituição** `PROV-*` → matrícula oficial **no mesmo registro** (mesmo `id` — bens, movimentações, termos e histórico preservados por FK). O **prefixo é o marcador** da condição provisória (sem coluna nova e **zero DDL** — a coluna `custodians.registration_code` já é `String(50)` `UNIQUE NOT NULL` e comporta o formato). Nenhuma regra nova de restrição patrimonial; nenhuma mudança em autenticação, AD, RBAC, movimentações ou inventário.

## Technical Context

**Language/Version**: Python 3.10+ (stack existente — Constitution §Restrições)

**Primary Dependencies**: Nenhuma nova — SQLAlchemy 2 (session/constraints existentes), FastAPI (Form/Pydantic), Jinja2 (marcação visual)

**Storage**: MariaDB/MySQL em produção via `DATABASE_URL`; **nenhuma alteração de schema** (zero DDL/migration — SC-007). A constraint `UNIQUE` existente em `registration_code` é a garantia final da unicidade

**Testing**: pytest — novo arquivo `tests/test_custodian_provisional.py` (TDD: vermelho antes da implementação, Constitution VIII); suíte existente 281 passed / 1 failed (lockout defasado) como baseline de não-regressão; SQLite em memória como na suíte

**Target Platform**: Aplicação web existente (FastAPI + Jinja2 server-side) + API REST `/api/v1`

**Performance Goals**: N/A (geração local = consulta `MAX` indexada; custo desprezível)

**Constraints**:
- Zero DDL: nenhuma coluna/tabela nova; o prefixo `PROV-` É o marcador da condição provisória.
- Geração exclusivamente no service (Constitution III) — rotas delegam.
- Trilha imutável (Constitution IV): snapshots de movimentações e documentos emitidos NÃO são reescritos pela substituição.
- Comportamento existente preservado: cadastro com matrícula informada, validações atuais ("Matrícula já cadastrada", e-mail duplicado), importação CSV (matrícula obrigatória), casamento AD (`registration_code == username AD`), bloqueio de edição de matrícula oficial na interface web.
- Anti-fabricação em TODOS os caminhos de escrita (web e API): usuário nunca grava `PROV-*` digitado (criação ou atualização).
- Sem nova permissão: reuso de `colaboradores.criar` / `colaboradores.editar` (Constitution VI).

**Scale/Scope**: 1 service + 1 schema + 1 rota web alterada (+ contextos de exibição) + ~6 templates com marcação visual + 1 arquivo de testes novo + docs (ajuda embutida + README) — escopo mínimo.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Princípio | Status | Evidência |
|---|---|---|---|
| I | Preservação do sistema existente | ✅ PASS | Extensão aditiva (geração + marcação + edição condicional); nenhum módulo reescrito; comportamentos atuais preservados por requisito (FR-015) |
| II | Arquitetura em camadas | ✅ PASS | Geração, validação anti-fabricação e guard de substituição no `CustodianService`; rotas delegam; templates apenas exibem |
| III | Regras de negócio nos services | ✅ PASS | Regras novas (geração `PROV-*`, unicidade, substituição) vivem no service; nenhum caminho de escrita fora dele |
| IV | Integridade patrimonial e movimentações | ✅ PASS | Nenhuma movimentação alterada; snapshots históricos imutáveis (FR-011); vínculo por FK por `id` preserva custódia na substituição |
| V | Integridade do inventário | ✅ PASS | Inventário intocado (usa snapshot de nome — sem matrícula) |
| VI | Segurança (auth, RBAC, AD) | ✅ PASS | Nenhuma permissão nova/alterada; `PROV-*` nunca é credencial nem deriva de dado pessoal (FR-004/FR-012); AD intocado (`PROV-*` não casa com username de domínio) |
| VII | Banco MariaDB e proteção dos dados | ✅ PASS | **Zero DDL** (SC-007); nenhum dado existente alterado; a `UNIQUE` existente garante unicidade; geração compatível com MariaDB e com SQLite dos testes |
| VIII | Testes como não regressão | ✅ PASS | Novos testes (TDD vermelho primeiro) + suíte existente no patamar atual; nenhum teste existente editado |
| IX | Auditoria | ✅ PASS | Substituição auditada pelo mecanismo EXISTENTE (`write_change_audit` before/after já presente nos caminhos de alteração de colaborador); sem credenciais |
| X | Interface consistente | ✅ PASS | Marcação "provisória" com o padrão visual existente (badge Bootstrap); formulário segue o padrão atual |
| XI | Documentação fiel | ✅ PASS | Ajuda embutida (`cadastrar-colaboradores`) e README atualizados na MESMA tarefa de implementação |
| XII | Spec-driven + validação | ✅ PASS | Fluxo Spec Kit em curso; validação = TDD + suíte + quickstart + `git status` com escopo fechado |

**Post-design re-check**: sem violações — o desenho não introduz camada, permissão, tabela, comportamento novo de escrita fora do service, nem altera regras existentes (Complexity Tracking vazio).

## Project Structure

### Documentation (this feature)

```text
specs/010-matricula-provisoria/
├── plan.md              # This file
├── research.md          # Phase 0 — decisões R1–R6
├── data-model.md        # Phase 1 — semântica estendida de registration_code (sem DDL)
├── contracts/
│   └── custodian-identifier-contract.md   # Contrato API/web do identificador
└── quickstart.md        # Phase 1 — protocolo de validação
```

### Source Code (repository root)

```text
app/schemas/custodian.py          # ALTERAR: registration_code opcional na CRIAÇÃO
                                  #   (Optional[str] = None; update já é opcional)
app/services/custodian_service.py # ALTERAR: geração PROV-* no create (padrão
                                  #   max+1 + retry apoiado na UNIQUE), anti-fabricação
                                  #   (create/update), guard de substituição no update,
                                  #   helper is_provisional()
app/web/routes.py                 # ALTERAR: POST /custodians/new com matrícula opcional;
                                  #   POST /custodians/{id}/edit aceita matrícula APENAS
                                  #   quando a atual for PROV-*; contextos de exibição
app/web/templates/custodians/form.html   # ALTERAR: campo opcional na criação (dica
                                  #   "deixe em branco..."), editável só quando PROV-*
app/web/templates/custodians/list.html, custodians/detail.html,
app/web/templates/assets/detail.html, assets/form.html, assets/list.html,
app/web/templates/movements/new.html, movements/term.html   # ALTERAR (apenas
                                  #   apresentação): marcação "provisória" onde a
                                  #   matrícula viva é exibida
tests/test_custodian_provisional.py  # CRIAR: testes US1–US4 + não-regressão
app/services/help_service.py      # ALTERAR (doc): seção de cadastro de colaboradores
                                  #   cobre identificador provisório e substituição
README.md                         # ALTERAR (doc): seção de colaboradores menciona PROV-*
```

**Nenhum outro arquivo** é alterado: zero models (sem DDL), zero `movement_service.py`, `inventario_service.py`, `ad_service.py`, `custodian_import_service.py`, APIs de relatórios, autenticação, RBAC, configuração.

**Structure Decision**: feature de escopo mínimo sobre a arquitetura existente — a única lógica nova fica no `CustodianService`; a apresentação usa o padrão visual de badge já existente.

## Implementation Flow (ordem de integração)

1. **Schema** (`app/schemas/custodian.py`): `CustodianCreate.registration_code: Optional[str] = None` (criação sem matrícula passa a ser representável; `CustodianUpdate` já é opcional — inalterado). Retrocompatível: chamadores que enviam matrícula continuam funcionando idênticos.
2. **Service** (`app/services/custodian_service.py`) — a lógica nova toda:
   a. **Geração** (padrão do precedente `InventarioService.next_code`): se `registration_code` vem vazio/ausente (após `strip()`), gerar `PROV-%06d` com próximo número = maior `PROV-` existente + 1; **loop curto de retentativa (limitado)** apoiado na constraint `UNIQUE` para o caso de colisão concorrente (rollback → regenerar → inserir), mantendo o `db.commit()` no service como hoje.
   b. **Anti-fabricação** (create e update): valor fornecido pelo usuário que case com o padrão `PROV-` + 6 dígitos → `ValueError` (a web redireciona com o erro existente; a API responde 400 — padrão atual).
   c. **Substituição guard** (update): mudança de matrícula é permitida quando (i) a atual é `PROV-*` (a feature) ou (ii) trata-se do comportamento atual da API (oficial → oficial segue as validações existentes, conforme a spec); matrícula `PROV-*` **digitada** como novo valor é sempre rejeitada (fabricação). Unicidade validada como hoje ("Matrícula já cadastrada").
   d. **Helper** `is_provisional(registration_code) -> bool` (`startswith("PROV-")`) para os contextos de template.
3. **Rotas web** (`app/web/routes.py`): `create_custodian_form` passa a receber `registration_code: Optional[str] = Form(None)` (dica no template); `update_custodian_form` ganha `registration_code: Optional[str] = Form(None)` aplicado **somente** quando a matrícula atual é `PROV-*` (a rota valida antes de chamar o service; a auditoria `write_change_audit` do caminho JÁ registra before/after — confirmado em `routes.py` ~L977, apenas testado em T012e). Expor `is_provisional` aos templates via `context_processors` existente (precedente: `can`, L110) — nenhuma mudança de contexto por rota (helper d).
4. **Templates**: `custodians/form.html` (campo opcional na criação; em edição, editável apenas se `PROV-*`, readonly caso contrário — estado atual preservado) e a marcação "provisória" (badge do padrão visual existente) nas exibições de matrícula viva listadas na estrutura acima. Termo (`movements/term.html`) exibe a marcação quando o colaborador é provisório (FR-006).
5. **API REST**: `POST /api/v1/custodians` — criação sem `registration_code` passa a funcionar (schema opcional; service gera); `PUT` — guard do service aplica anti-fabricação; demais contratos inalterados (`CustodianRead` continua devolvendo `registration_code` — agora podendo ser `PROV-*`).
6. **Testes** (`tests/test_custodian_provisional.py`, TDD — escritos ANTES dos passos 1–4 e confirmados vermelhos): geração automática e sequencial; unicidade; colisão tratada (pré-inserir `PROV-000001` e criar sem matrícula → recebe o próximo); anti-fabricação (web/API, create/update); uso patrimonial sem bloqueio (alocação/cautela com colaborador provisório via `MovementService` — comportamento existente); substituição preservando `id`, vínculos e histórico (snapshot antigo intacto; termo novo mostra oficial); auditoria da substituição; não-regressão (cadastro com matrícula informada; duplicidade atual; AD intocado via mocks existentes; importação CSV exige matrícula como antes).
7. **Documentação** (Constitution XI, mesma tarefa): `help_service.py` artigo `cadastrar-colaboradores` (identificador provisório: quando é gerado, como aparece, como substituir) + README (seção de colaboradores: `PROV-*`, marcador, substituição preservando vínculos).
8. **Validação** (quickstart): `pytest tests/test_custodian_provisional.py` verde → suíte completa no patamar 281/1 → percorrida manual (§3 do quickstart) → `git status` com escopo fechado.

## Error Handling

| Cenário | Comportamento |
|---|---|
| Usuário digita `PROV-000123` na criação (web ou API) | `ValueError` → web: redirect com mensagem no padrão atual (`?error=...`); API: `400` com detail — sem gravar |
| Usuário digita `PROV-*` no update (web ou API) | Mesmo tratamento de fabricação — rejeitado |
| Matrícula oficial duplicada | Erro existente "Matrícula já cadastrada" (web redirect / API 400) |
| Colisão concorrente na geração (`UNIQUE` dispara) | Rollback → regenera próximo número → tenta novamente (loop limitado); se persistir, erro padrão do sistema sem registro parcial |
| Falha de banco na geração | Erro padrão do sistema (web: mensagem atual de erro; API: 500 pelo handler existente) — sem detalhe técnico sensível |
| Tentativa web de trocar matrícula oficial | Bloqueada na rota (o campo nem chega a ser aplicado; template readonly) — comportamento atual |
| Edição com matrícula atual `PROV-*` e nova oficial duplicada | Erro existente "Matrícula já cadastrada"; `PROV-*` permanece (nada é perdido) |
| E-mail duplicado no cadastro | Erro existente "E-mail já cadastrado" — inalterado |

## Security & Permissions

- **Nenhuma permissão nova ou alterada**: `colaboradores.criar` (cadastro) e `colaboradores.editar` (substituição) — as mesmas de hoje (Constitution VI).
- **`PROV-*` nunca é credencial**: não entra em login, senha, CPF ou username AD; nenhuma relação nova `User`↔`Custodian`.
- **Anti-fabricação** evita que alguém "planeje" identificadores provisórios para simular registros.
- **Auditoria**: substituição via caminhos existentes de `write_change_audit` (before/after) — sem dado sensível; geração de `PROV-*` fica registrada na auditoria de criação já existente (`resource_ref` conterá o `PROV-*` gerado).
- **Dados pessoais**: a geração não usa CPF, telefone, nome, e-mail, username AD nem qualquer dado pessoal (FR-004).

## Testing Strategy

1. **Baseline** antes da edição: `python -m pytest tests/ -q --tb=no` → patamar atual (**281 passed / 1 failed** — lockout defasado conhecido).
2. **TDD (Constitution VIII)**: criar `tests/test_custodian_provisional.py` ANTES da implementação e confirmar **vermelho**; padrões das fixtures existentes (`client`, `db_session`, `unauth_client`).
3. **Cobertura nova** (mapeada às US/SC da spec):
   - US1: cadastro sem matrícula → `PROV-000001`/sequencial; campo reposto; marcado como provisório na UI; pesquisa por `PROV-` (006) funciona.
   - US2: alocação/cautela com colaborador provisório via `MovementService` (comportamento existente, sem bloqueio); termo gerado; inventário (snapshot de nome) inalterado.
   - US3: substituição `PROV-*` → oficial preserva `id`, bens vinculados, movimentações (snapshot antigo intacto), auditoria before/after; termo novo exibe oficial.
   - US4: unicidade em sequência de cadastros; colisão com `PROV-000001` pré-existente → próximo número; fabricação rejeitada (web/API, create/update).
   - Não-regressão: cadastro com matrícula informada idêntico ao atual; duplicidades atuais; importação CSV exige matrícula; casamento AD (mock existente) intocado.
4. **Após implementação**: suíte completa no patamar da baseline (+ testes novos, nenhum failure novo) e validação manual do quickstart (§3).

## Risks & Mitigations

| Risco | Mitigação |
|---|---|
| Colisão concorrente na geração (max+1) | Loop limitado de retentativa com rollback apoiado na `UNIQUE` (garantia final do banco); testes cobrem colisão com código pré-existente |
| Quebrar chamadores do schema (`registration_code` obrigatório) | Mudança aditiva (optional com default); retrocompatibilidade testada (API e web com matrícula informada) |
| Vazamento da edição de matrícula para oficiais via API | Guard no service (único ponto de escrita); testes de API com oficial → comportamento atual preservado conforme spec |
| Marcação visual inconsistente entre telas | Helper único (`is_provisional`) + padrão de badge existente; lista fechada de templates no plan; validação manual §3 |
| Escopo vazar (DDL, auth, AD) | Constraints na spec (SC-007, FR-012/FR-015) + verificação de `git status` no fechamento |

## Complexity Tracking

> Sem violações de Constitution — tabela vazia por design.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
