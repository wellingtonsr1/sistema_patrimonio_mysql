# Implementation Plan: 071-separar-cadastrais-fluxo

**Branch**: `071-separar-cadastrais-fluxo` | **Date**: 2026-10-12 | **Spec**: `specs/071-separar-cadastrais-fluxo/spec.md`

**Input**: Feature specification from `/specs/071-separar-cadastrais-fluxo/spec.md`

> **Remediação do /speckit-analyze (2026-10-13)**: rótulos da Constitution Check corrigidos para os números reais dos artigos (C1); Storage corrigido para MariaDB/MySQL conforme Constitution VII (C2); nota de estado atualizada — a 070 **já está commitada** (`5b3f71f`) (I1); referência de artigos nas Data Model Notes corrigida (I/IX).

## Summary

Separação de apresentação na tela de detalhes do Equipamento (`view_asset_detail` → `assets/detail.html`): os eventos de auditoria de natureza cadastral (`action == "ALTERACAO"`, mesmo filtro exato do painel `get_cadastral_history`) deixam de ser renderizados como cartões na seção "Trilha de Fluxo & Movimentações". O restante da trilha (movimentações e eventos não cadastrais atípicos) mantém o comportamento atual, incluindo o fallback legível da 070.

Nesta etapa (implementação): o serviço `MovementService.get_timeline_for_asset`, a API `GET /api/v1/assets/{id}/timeline`, a gravação de auditoria, o banco e as migrações **não** são tocados. A filtragem fica na camada de apresentação, na própria rota, antes do `TemplateResponse`.

## Technical Context

**Language/Version**: Python 3.10+ (por Constitution VII; rodando atualmente em Python 3.10 no ambiente)

**Primary Dependencies**: FastAPI (web), SQLAlchemy 2 (ORM), Jinja2 templates, pytest (+ TestClient). `alembic` é apenas infraestrutura de migrações existente — não usada pela 071.

**Storage**: MariaDB/MySQL (PyMySQL) em produção — **não é alterado pela 071**; SQLite é restrito à suíte de testes (Constitution VII).

**Testing**: pytest; suíte base ativa: 1059 passed, 3 skipped, 3 failures (as 3 falhas são `tests/test_migrations_052.py` por ausência de `alembic`, infraestrutura não relacionada à 071).

**Target Platform**: Servidor web (SisPatrimônio Pro), módulo Equipamentos.

**Project Type**: Web application (backend Python + templates Jinja2).

**Performance Goals**: Sem requisito de latência novo. Impacto mensurável: menos cartões de auditoria cadastral na trilha (rolagem da página mais curta, SC-007).

**Constraints**: Nenhum além da Constitution — somente apresentação na tela de detalhes.

**Scale/Scope**: 1 tela afetada; 2–3 arquivos de código candidatos: `app/web/routers/assets.py`, `app/web/templates/assets/detail.html` (provavelmente intocado, PD-1(a)), `app/services/asset_service.py` (helper de classificação opcional). Novos testes: `tests/test_separacao_cadastral_fluxo_071.py`.

## Constitution Check

*GATE: deve passar antes da implementação. Números dos artigos conforme `.specify/memory/constitution.md` v1.0.0.*

- **Constitution I (Preservação do Sistema Existente)**: nenhum registro de auditoria apagado/alterado/inacessível — preservação garantida pelo painel + `/admin/audit` + API; comportamento existente preservado exceto o previsto na especificação.
- **Constitution II/III (Arquitetura em Camadas / Regras nos Services)**: a filtragem é de **apresentação** (classificação de renderização), não regra de negócio nova; `MovementService.get_timeline_for_asset` e `get_cadastral_history` permanecem intocados — não há duplicação de regra em rota.
- **Constitution IV (Integridade Patrimonial e Movimentações)**: movimentações e trilha histórica imutáveis — nenhum registro é editável ou apagável pela 071.
- **Constitution VII (Banco)**: zero alteração em banco, colunas ou migrações.
- **Constitution VIII (Testes)**: suíte verde; os asserts de `tests/test_legibilidade_trilha_070.py` que validam presença de `ALTERACAO` **na trilha** podem ser ajustados (documentado), pois estão diretamente ligados ao comportamento especificamente alterado pela 071 — nunca enfraquecidos; guardas `TestUS3Preservacao` intactas.
- **Constitution IX (Auditoria)**: a trilha `audit_logs` permanece íntegra e acessível (painel, `/admin/audit`, API `/timeline` inalterada).
- **Constitution XI (Documentação)**: nenhum artigo da central de ajuda descreve a duplicação atual — revalidar durante a implementação.
- **Estado de dependência (spec §6)**: a 070 **já está commitada** (`5b3f71f "Implementação da spec 070"`). O commit da 071 deve vir depois dele (não é preciso recommitar a 070).

## Project Structure

### Documentation (this feature)

```text
specs/071-separar-cadastrais-fluxo/
├── checklists/requirements.md   # checklist de qualidade da spec (pronto)
├── plan.md                      # este arquivo
├── spec.md                      # estado Definitive
└── tasks.md                     # gerado por /speckit-tasks (20+1 tasks)
```

### Source Code (repository root)

```text
app/web/routers/assets.py       # view_asset_detail: filtro na apresentação
app/web/templates/assets/detail.html  # provavelmente intocado (PD-1(a))
app/services/asset_service.py   # opcional: helper/predicado de classificação
tests/test_separacao_cadastral_fluxo_071.py  # novos testes da separação
tests/test_legibilidade_trilha_070.py  # ajuste pontual e documentado (FR-010)
```

## Complexity Tracking

> Sem violações da Constitution que exijam justificativa.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| — | — | Filtrar no template duplicaria a lógica de renderização de `audit` (resumo/detalhes 070), aumentando acoplamento e risco de regressão; a proposta mantém o template intocado e filtra a lista antes do `TemplateResponse`. |

## Flow do Código (análise verificada)

1. `GET /assets/{asset_id}` → `view_asset_detail` (`app/web/routers/assets.py` L489–530), permissão `patrimonio.visualizar`.
2. A rota monta o contexto do template:
   - `timeline`: resultado de `MovementService.get_timeline_for_asset(db, asset_id)` (intocado, contratos C1/C2) + enriquecimento 070 (`audit_summary`);
   - `cadastral_history`: `AssetService.get_cadastral_history(db, asset_id)` (filtro `resource='Asset'` AND `resource_id` AND `action == ACTION_UPDATE`, limite 50 + flag `truncado`).
3. `assets/detail.html` L217–263: painel `#historico-cadastral` (fonte `cadastral_history`).
4. L265+: trilha — ramo `item.type == 'audit'` renderiza cartões 070 + detalhes técnicos; ramo `else`, movimentações (padrão 063/064).
5. **Duplicação atual**: eventos `ALTERACAO` chegam aos dois ramos.
6. **Nova ordem (PD-1(a))**: filtragem no controller, antes do `TemplateResponse` — itens `audit` cuja ação seja `ALTERACAO` são removidos da lista apresentada; itens não classificáveis permanecem (fallback R-C2); o restante passa igual.
7. O template continua renderizando a variável `timeline` (agora já filtrada pela rota) e `cadastral_history`.

## Implementation Strategy

1. **Setup**: confirmar que HEAD contém a implementação da 070 (`5b3f71f`) e capturar o baseline da suíte (1059 passed, 3 skipped, 3 failures = infraestrutura `alembic`, fora do escopo).
2. **Filtro na rota**: em `view_asset_detail`, antes do `TemplateResponse`, aplicar o predicado de apresentação (dicts Python: `item.get("type") == "audit"` e `(item.get("data") or {}).get("action") == "ALTERACAO"`), sem mudar `MovementService.get_timeline_for_asset` nem o service de auditoria.
3. **Template**: intocado (PD-1(a) — filtro na rota).
4. **Testes**: `tests/test_separacao_cadastral_fluxo_071.py` — US1 (separação), US2 (preservação + truncamento), US3 (fallback), guardas 070 US3 verdes sem edição; payload da API idêntico.
5. **Ajuste documentado de testes 070 (FR-010)**: apenas os asserts de presença de `ALTERACAO` na trilha, com comentário de contexto; guardas `TestUS3Preservacao` intactas.
6. **Verificação**: suíte completa com status explícito (3 falhas = `alembic`, infraestrutura); smoke antes/depois para SC-007.
7. **Commit auditável único da 071** (a 070 já está em `5b3f71f`).

## Data Model Notes

Nenhum campo no banco é alterado. `AuditLog` permanece idêntico; a filtragem é um predicado em memória sobre a lista já carregada por `get_timeline_for_asset` (Constitution I/IX — preservação e imutabilidade da trilha).

## Reference Artifacts

| Arquivo | Estado |
|---|---|
| `specs/071-separar-cadastrais-fluxo/spec.md` | Status: Definitive (fechada) |
| `specs/071-separar-cadastrais-fluxo/checklists/requirements.md` | 16/16 aprovados |
| `app/web/routers/assets.py` | Alvo da 071 (rota) |
| `app/web/templates/assets/detail.html` | Manter intocado |
| `app/services/asset_service.py` | `get_cadastral_history` intocado |
| `app/services/movement_service.py` | `get_timeline_for_asset` intocado |
| `tests/test_legibilidade_trilha_070.py` | Apenas asserts de presença na trilha ajustados, documentados |
