# Implementation Plan: Matrícula Opcional na Importação de Colaboradores via CSV

**Branch**: `014-matricula-opcional-importacao-csv` | **Date**: 2026-09-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/014-matricula-opcional-importacao-csv/spec.md`

## Summary

Tornar a coluna `matricula` opcional no importador CSV de colaboradores, alinhando-o à regra da feature 010 (cadastro individual): matrícula informada → usada com todas as validações atuais; ausente/vazia/só espaços/coluna ausente → geração automática de `PROV-%06d` **reutilizando o mecanismo único existente** (`CustodianService._next_provisional_code`, exposto por fachada pública mínima). A correção concentra-se em `app/services/custodian_import_service.py` (remover obrigatoriedade em `_validate_row`; gerar na execução; sinalizar no preview), fachada de 1 método em `custodian_service.py`, documentação da tela `import.html` e testes. Zero DDL, zero mudança no cadastro individual, API REST, AD ou demais módulos.

## Technical Context

**Language/Version**: Python 3.10+ (stack estabelecido pela Constitution — sem novas dependências)

**Primary Dependencies**: FastAPI + SQLAlchemy 2 + Pydantic v2 + Jinja2/Bootstrap 5 (todos existentes)

**Storage**: MariaDB/MySQL via SQLAlchemy (produção) / SQLite em memória (testes) — **zero DDL**: `Custodian.registration_code` já é UNIQUE e aceita `PROV-*`

**Testing**: pytest + TestClient (padrões de `tests/test_custodian_import.py` existente)

**Target Platform**: Servidor web existente (Uvicorn) — fluxo web `/custodians/import` + endpoint REST `POST /api/v1/custodians/import/csv` (`app/api/custodians_api.py:77`, ambos verificados); nenhum dos dois é alterado — a correção vive nos services consumidos por ambos

**Project Type**: Web application monolítica (app/web + app/api + app/services + app/models)

**Performance Goals**: Sem requisito novo; geração de provisória custa 1 consulta por linha sem matrícula (mesmo custo do cadastro individual)

**Constraints**: Reutilizar o gerador único (proibido duplicar contagem); comportamento das matrículas informadas byte-a-byte igual; nenhuma alteração fora do escopo da spec

**Scale/Scope**: 1 service alterado + 1 fachada + 1 template (documentação) + testes; fluxo completo: parse → preview → confirm → execute (transporte `csv_rows` JSON já preserva célula vazia — nenhuma mudança de transporte)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Aplicação nesta feature | Status |
|---|---|---|
| I. Preservação / evolução incremental | Correção localizada em 3 pontos do importador + fachada de 1 método (delegação, lógica intocada); nenhuma refatoração; cadastro individual NÃO é tocado (FR-010) | ✅ PASS |
| II/III. Camadas e regras nos services | Toda a nova lógica fica em `custodian_import_service.py`/`custodian_service.py`; rotas web intocadas; templates não recebem regra de negócio | ✅ PASS |
| IV/V. Integridade patrimonial e de inventário | Não afetados (colaboradores ≠ bens/inventário) | ✅ PASS |
| VI. Segurança/RBAC/AD | Nenhuma rota nova; permissão `colaboradores.criar` existente mantida nas 3 rotas do fluxo | ✅ PASS |
| VII. Banco de dados | Zero DDL/migração/modelo (FR-009); UNIQUE de `registration_code` permanece a garantia final de unicidade | ✅ PASS |
| VIII. Testes | Novos testes dos 8 cenários; ajuste pontual do único teste que asserta o comportamento alterado ("matricula é obrigatória") — exceção prevista pela própria Constitution; suíte verde exigida | ✅ PASS |
| IX. Auditoria | Comportamento de auditoria do fluxo de importação permanece exatamente como está (nenhuma rota/service de auditoria tocado) | ✅ PASS |
| X. UI consistente | Somente texto de documentação e badge da tabela de colunas em `import.html`; nenhum fluxo de tela alterado | ✅ PASS |
| XI. Documentação fiel | Docstring do módulo do importador + tela de importação atualizados na mesma tarefa; README/help não documentam as colunas do importador (verificado) | ✅ PASS |
| XII. Spec-driven + validação | Fluxo Spec Kit seguido; validação via suíte + quickstart como parte do DoD | ✅ PASS |

**Conclusão**: PASS pré-design (nenhuma violação a justificar — seção Complexity Tracking não utilizada). Re-verificação pós-design no final deste documento.

## Project Structure

### Documentation (this feature)

```text
specs/014-matricula-opcional-importacao-csv/
├── plan.md                  # Este arquivo (/speckit-plan)
├── research.md              # Fase 0 — decisões R1–R11 verificadas no código
├── data-model.md            # Fase 1 — dados/estados do fluxo de importação
├── contracts/
│   └── service-contract.md  # Fase 1 — contrato dos services (importador + fachada)
├── quickstart.md            # Fase 1 — roteiro de validação
└── tasks.md                 # Fase 2 (/speckit-tasks — não criado aqui)
```

### Source Code (repository root)

```text
app/
├── services/
│   ├── custodian_import_service.py   # PRINCIPAL: _validate_row, preview, execute
│   └── custodian_service.py          # Fachada pública mínima do gerador (1 método)
├── web/
│   ├── routes.py                     # INTOCADO (fluxo de 3 estágios já consome os services)
│   └── templates/custodians/
│       └── import.html               # Documentação: badge/observação da coluna + exemplo
├── api/
│   └── custodians_api.py             # INTOCADO (endpoint REST de importação herda a correção pelos services)
tests/
└── test_custodian_import.py          # Ajuste pontual (teste do erro removido) + novos testes
```

**Structure Decision**: Projeto monolítico FastAPI existente (padrão das features 010–013). A alteração vive na camada de services (Princípio II/III); rotas e template apenas documentam/consumem o comportamento dos services — nenhuma regra nova fora de `app/services/`.

## Complexity Tracking

> Não utilizado — nenhum desvio da estrutura padrão; nenhuma violação de Constitution a justificar.

## Re-verificação da Constitution pós-design (Fase 1)

- **R1 (fachada pública `generate_available_provisional_code`)**: agrega o gerador único `_next_provisional_code` + consulta existente `get_by_registration_code` — não duplica contagem nem cria segunda implementação (atende FR-002 e Princípio III).
- **R3 (preview sem busca de duplicata por matrícula vazia)**: elimina consulta sem sentido (`code == ""`), mantendo duplicata por e-mail — refinamento dentro do comportamento previsto na spec (US4), sem alterar regra visível.
- **data-model/contracts**: nenhum novo estado, tabela ou campo; apenas a semântica "ausente → provisória" documentada. Constitution Check permanece **PASS** em todos os princípios.
