# Implementation Plan: Consulta Detalhada e Edição Controlada de Bens Patrimoniais

**Branch**: `067-consulta-edicao-bens` | **Date**: 2026-10-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/067-consulta-edicao-bens/spec.md`

## Summary

Fechar a lacuna registrada em `specs/001-sistema-existente/spec.md` §11 item 3: a edição cadastral de bens existe **apenas na API** (`PUT /api/v1/assets/{id}`, permissão `patrimonio.editar`) e não há ação na interface; a tela de detalhes (`/assets/{id}`) já existe mas não mostra observações nem a última atualização, e o histórico cadastral aparece em JSON bruto misturado às movimentações.

Abordagem técnica (incremental, sem DDL e sem permissão nova):

1. **Estender** a tela de detalhes existente (`app/web/templates/assets/detail.html`) — seções completas, `notes`, `updated_at`, ação "Editar bem" condicionada por `can('patrimonio.editar')` e histórico cadastral legível **separado** das movimentações (nova leitura `AssetService.get_cadastral_history`, sem tocar em `MovementService.get_timeline_for_asset`, que serve a API).
2. **Criar o fluxo web de edição** `GET/POST /assets/{asset_id}/edit` em `app/web/routers/assets.py` (permissão `patrimonio.editar` nas duas rotas), com template novo `assets/edit.html` espelhando `assets/form.html`, e delegando toda a regra ao service (Constitution II/III).
3. **Robustecer `AssetService.update`** (fonte única): validações de nome/limites/valor ≥ 0, operador autenticado e motivo na movimentação gerada por mudança de condição (padrão da 065, aplicado nos fluxos web **e** API), detecção de "nada mudou" e de conflito de edição.
4. **Atomicidade alteração + auditoria**: `AssetService.update(..., commit=False)` e `write_change_audit(..., commit=False)` numa única transação fechada pela rota (parâmetros **aditivos** com default preservando todo comportamento existente — Constitution I).
5. **Reuso obrigatório**: `AssetUpdate` mantido como contrato da API (as novas validações vivem no service, que a API já converte em 400), `write_change_audit`/`_asset_snapshot` como trilha única, `require_permission` como autorização, `can()` na UI.
6. **Proteções preservadas**: `tag`, `status`, `location_id` e `custodian_id` continuam fora do schema de edição — nenhum caminho novo para contornar o motor de movimentações (Constitution IV).

**Decisões de negócio aprovadas em 2026-10-10** (spec §14 e Clarifications): **P1** tombamento imutável; **P2** condição editável na ficha, com o operador autenticado na movimentação; **P3** controle otimista de edição concorrente por `updated_at`; **P4** edição de bem baixado bloqueada; **P5** ata de inventário e exportações mantidas com leitura viva (dívida M-003).

## Technical Context

**Language/Version**: Python 3.10+ | Jinja2 + JavaScript vanilla (apenas o já existente nos templates)

**Primary Dependencies**: FastAPI, SQLAlchemy 2, Pydantic v2, Jinja2 + Bootstrap 5 — **nenhuma dependência nova**

**Storage**: MariaDB/MySQL via `DATABASE_URL` (produção); SQLite in-memory na suíte (`tests/conftest.py`) — **zero DDL, zero migração, zero backfill**

**Testing**: pytest + `TestClient` do FastAPI (fixtures `client`/`db_session`); obrigatório atualizar `tests/route_manifest.json` por causa de `tests/test_route_inventory.py`

**Target Platform**: aplicação web (servidor Linux/Windows suportados); navegadores desktop e mobile já suportados pelo PWA existente

**Project Type**: web application — monolito em camadas Web/API → Services → Models (Constitution II)

**Performance Goals**: consulta detalhada sem novas consultas N+1 — `AssetService.get_by_id` já carrega `location`, `custodian`, `movements` e `maintenances` por `joinedload`; o histórico cadastral é uma consulta indexada a `audit_logs` (filtro por `resource`/`resource_id`, já usada pela timeline). Nenhum impacto perceptível na edição (2 escritas: bem + trilha).

**Constraints**: preservar integralmente o contrato de `PUT /api/v1/assets/{id}`, `GET /api/v1/assets*`, importação CSV de bens, movimentações, inventário, relatórios/exportações e a trilha de auditoria; nenhum teste existente editado; campos protegidos fora do schema de edição.

**Scale/Scope**: escopo fechado em ~4 arquivos de produção + 1 template novo + 1 teste novo + manifesto de rotas + documentação (spec §11); dados reais de referência: 313 bens, 352 movimentações (base já auditada em `specs/066`).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Veredito | Justificativa |
|---|---|---|
| I — Preservação/evolução incremental | ✅ PASS | Extensão de tela existente + rota nova + endurecimento do service; nenhum módulo reescrito; parâmetros novos em funções compartilhadas são **aditivos com default** (comportamento atual intacto) |
| II — Arquitetura em camadas | ✅ PASS | Rota web autoriza/valida/delega; toda regra de edição permanece em `AssetService`; template só apresenta |
| III — Regras nos services | ✅ PASS | Validações novas e composição da movimentação de condição em `AssetService.update` (fonte única usada por web e API); nenhuma regra duplicada no router/template |
| IV — Integridade patrimonial e movimentações | ✅ PASS | `tag`/`status`/`location_id`/`custodian_id` **fora** do schema de edição; localização/custódia/situação seguem exclusivamente por `MovementService.create_movement`; a única movimentação gerada pela edição (condição) passa a gravar o operador autenticado |
| V — Integridade do inventário | ✅ PASS | Inventário intocado (nenhuma escrita em `inventarios`/`inventario_itens`); a tela exibe dados, não altera listas esperadas nem resultados |
| VI — Segurança por padrão | ✅ PASS | `require_permission("patrimonio.visualizar")` na consulta e `require_permission("patrimonio.editar")` no GET/POST de edição; autoridade no backend; botão apenas apresentação; nenhuma permissão/perfil novo; sem credenciais na trilha |
| VII — Banco de dados (MariaDB) | ✅ PASS | **Zero DDL, zero migração** — todos os campos usados já existem em `assets` (`notes`, `updated_at`) e a trilha já existe em `audit_logs` |
| VIII — Testes como não regressão | ✅ PASS | Nenhum teste editado/enfraquecido; suíte nova (`tests/test_consulta_edicao_bens_067.py`) cobrindo AC01–AC15; `route_manifest.json` atualizado (artefato de teste exigido pela feature 051) |
| IX — Auditoria das operações relevantes | ✅ PASS | Reutiliza `write_change_audit` (before/after + autor + IP); nenhum segundo mecanismo; nenhuma exclusão/edição de trilha |
| X — Interface consistente e funcional | ✅ PASS | Detalhe/edição no padrão Bootstrap e nos componentes existentes; `can()` para o botão; 403/404 amigáveis; responsivo; sem redesenho |
| XI — Documentação fiel | ✅ PASS | `docs/ARQUITETURA_E_MANUTENCAO.md` e central de ajuda (`help_service.py`) atualizados na mesma tarefa |
| XII — Spec → implementação → validação | ✅ PASS | Spec 067 **aprovada em 2026-10-10** (P1–P5 decididas), com AC01–AC15 e quickstart executável; implementação pelo `tasks.md` |

**Resultado do gate**: **PASS** — nenhuma violação a justificar (Complexity Tracking vazio). As únicas mudanças estruturais são **aditivas e com default retrocompatível** (`commit: bool = True` em `write_audit`/`write_change_audit` e em `AssetService.update`; parâmetros opcionais de operador/motivo), portanto sem alteração de comportamento existente.

## Project Structure

### Documentation (this feature)

```text
specs/067-consulta-edicao-bens/
├── plan.md              # Este arquivo (/speckit-plan)
├── research.md          # Phase 0 — decisões técnicas (R1–R10)
├── data-model.md        # Phase 1 — entidades, campos editáveis/protegidos e validações
├── quickstart.md        # Phase 1 — guia de validação executável
├── contracts/           # Phase 1 — contratos do novo fluxo + contratos preservados
│   ├── web-asset-edit-contract.md
│   └── asset-edit-preserved-contracts.md
├── checklists/
│   └── requirements.md  # Checklist de qualidade da spec
├── spec.md              # Especificação (aguardando aprovação)
└── tasks.md             # Phase 2 — /speckit-tasks (NÃO criado por /speckit-plan)
```

### Source Code (repository root)

```text
app/
├── web/
│   ├── routers/
│   │   └── assets.py            # ALTERADO: + GET/POST /assets/{asset_id}/edit (patrimonio.editar)
│   └── templates/
│       └── assets/
│           ├── detail.html      # ALTERADO: notes, updated_at, botão "Editar bem", histórico cadastral separado
│           ├── edit.html        # NOVO: formulário de edição (espelha assets/form.html)
│           ├── form.html        # INTOCADO (referência de padrão visual)
│           └── list.html        # ALTERADO (polimento opcional aprovado): ação "Editar" na linha, só com permissão e fora de bem baixado (P4)
├── services/
│   ├── asset_service.py         # ALTERADO: update com validações, operador autenticado, "nada mudou",
│   │                            #           conflito de edição, commit explícito e get_cadastral_history
│   └── audit_service.py         # ALTERADO (aditivo): parâmetro commit=True em write_audit/write_change_audit
├── api/
│   └── assets_api.py            # ALTERADO (mínimo): PUT passa o operador autenticado (mesma resposta/contrato)
├── schemas/
│   └── asset.py                 # INTOCADO — AssetUpdate sem campos nem restrições novas (validações no service)
└── (demais camadas)             # INTOCADAS: models, movement_service, inventario*, report_service,
                                 #            import_service, permission_service

docs/
└── ARQUITETURA_E_MANUTENCAO.md  # ALTERADO: seção de bens — consulta detalhada e edição controlada
app/services/help_service.py     # ALTERADO: artigo de bens na central de ajuda (/ajuda)

tests/
├── route_manifest.json                 # ALTERADO: novas rotas web de edição (exigência da feature 051)
├── test_consulta_edicao_bens_067.py    # NOVO: AC01–AC15
└── test_assets.py                      # ESTENDIDO: validações e operador autenticado no service
```

**Structure Decision**: monolito existente em camadas (opção única do projeto). A feature **não** cria diretórios, módulos, tabelas, permissões ou dependências novas: altera 4 arquivos de produção (`assets.py`, `asset_service.py`, `audit_service.py`, `help_service.py`), 1 template existente + 1 template novo, 1 arquivo de documentação, 1 manifesto de testes e cria 1 arquivo de teste — exatamente como delimita a spec §11.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

Nenhuma violação — tabela vazia por design.
