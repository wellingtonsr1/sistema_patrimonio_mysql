# Implementation Plan: Adicionar Campo de Pesquisa no Fluxo Global de Movimentações

**Branch**: `049-pesquisa-movimentacoes` | **Date**: 2026-09-27 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/049-pesquisa-movimentacoes/spec.md`

---

## Summary

Adicionar um campo de pesquisa textual na página "Fluxo Global de Movimentações" (`/movements`), integrado ao formulário de filtros existente. A filtragem é executada no backend via query SQLAlchemy em `MovementService.get_all_movements`, buscando com correspondência parcial e insensível a maiúsculas/minúsculas por tombamento, nome do equipamento, nomes e matrículas de colaboradores (origem/destino), locais (origem/destino), tipo de movimentação, operador e código do termo. A alteração é estritamente cirúrgica e de leitura, preservando integralmente o RBAC, as regras patrimoniais, a paginação/limite (`limit=200`) e a suíte de testes existente.

---

## Technical Context

**Language/Version**: Python 3.10+  
**Primary Dependencies**: FastAPI, SQLAlchemy 2, Jinja2, Bootstrap 5, Pydantic v2  
**Storage**: MariaDB/MySQL (PyMySQL em produção); SQLite em testes (`sqlite:///:memory:`)  
**Testing**: pytest com `TestClient` do FastAPI  
**Target Platform**: Servidor Linux (FastAPI + Uvicorn)  
**Project Type**: Aplicação Web (FastAPI + Jinja2 + SQLAlchemy)  
**Performance Goals**: Tempo de resposta de listagem com filtro textual inferior a 500ms para bases de até 10.000 movimentações; renderização server-side direta sem sobrecarga no DOM  
**Constraints**: <500ms p95; limite padrão de 200 registros mais recentes preservado; sem consultas N+1; sem alterações em regras de movimentação ou esquema de tabelas  
**Scale/Scope**: Alteração restrita a 4 arquivos existentes (`movement.py`, `movement_service.py`, `routes.py`, `list.html`) e adição de cenários de teste em `tests/test_movements.py`  

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio Constitucional | Conformidade da Feature 049 | Status |
|---|---|---|
| **I. Preservação e Evolução Incremental** | Alteração puramente aditiva sobre a tela de listagem de movimentações. Nenhuma reescrita de módulo, nenhuma troca de tecnologia e nenhuma remoção de funcionalidade existente. | ✅ PASS |
| **II. Arquitetura em Camadas** | Respeita rigorosamente o fluxo: Rota Web (`app/web/routes.py`) → Serviço (`app/services/movement_service.py`) → Modelos SQLAlchemy (`app/models/movement.py`). | ✅ PASS |
| **III. Regras de Negócio nos Services** | Toda a lógica de filtragem e composição de query é centralizada em `MovementService.get_all_movements`. A rota apenas recebe os parâmetros e repassa ao service. | ✅ PASS |
| **IV. Integridade Patrimonial e Movimentações** | Operação estritamente de leitura (read-only). O motor de movimentações (`create_movement`), histórico e transições de status permanecem 100% inalterados. | ✅ PASS |
| **VI. Segurança por Padrão (RBAC)** | Acesso unificado sob a permissão existente `movimentacao.visualizar`. Usuários não autenticados ou sem a permissão continuam bloqueados com 403. | ✅ PASS |
| **VII. Banco de Dados e Proteção** | Nenhuma tabela criada, nenhuma coluna alterada no MariaDB, nenhuma migração destrutiva. Compatível com SQLite nos testes e MariaDB em produção. | ✅ PASS |
| **VIII. Não Regressão por Testes** | A suíte pytest existente (23 testes em `test_movements.py`) permanece verde. Novos testes unitários e de integração adicionados para cobrir a pesquisa (Testes A ao J). | ✅ PASS |
| **X. Interface Consistente** | Template Jinja2 com Bootstrap 5, ícone `bi-search`, classes e layout responsivo escopados, suporte a tema claro e escuro. | ✅ PASS |
| **XII. Orientação por Especificação** | Fluxo Spec Kit seguido à risca: especificação criada, validada em checklist, planejada e projetada antes da implementação. | ✅ PASS |

---

## Project Structure

### Documentation (this feature)

```text
specs/049-pesquisa-movimentacoes/
├── checklists/
│   └── requirements.md      # Checklist de qualidade da especificação
├── spec.md                  # Especificação funcional completa
├── plan.md                  # Este plano de implementação
├── research.md              # Decisões técnicas e arquiteturais (Phase 0)
├── data-model.md            # Modelo de dados e schemas (Phase 1)
├── quickstart.md            # Roteiro de validação e testes (Phase 1)
└── contracts/
    └── web-search-contract.md # Contrato HTTP e de interface (Phase 1)
```

### Source Code (Arquivos modificados na implementação)

```text
app/
├── schemas/
│   └── movement.py              # Adição de `search: Optional[str] = None` em MovementFilter
├── services/
│   └── movement_service.py      # Aplicação do filtro textual na query de get_all_movements
├── web/
│   ├── routes.py                # Recepção de `search` em list_movements_view e envio ao template
│   └── templates/
│       └── movements/
│           └── list.html        # Integração do input de busca, ícone, botões e estado vazio

tests/
├── test_movements_search.py     # Cobertura automatizada da pesquisa (Testes A a I)
└── test_movements.py            # Suíte de regressão de movimentações (Teste J)
```

**Structure Decision**: Utiliza o layout estabelecido do monorepo FastAPI. Sem criação de novos pacotes, diretórios ou bibliotecas.

---

## Complexity Tracking

> **Nenhuma violação constitucional.** Todos os princípios foram respeitados integralmente sem necessidade de justificativas de exceção.

| Item | Avaliação | Decisão |
|---|---|---|
| Novas dependências externas | Desnecessárias | Rejeitado (usa FastAPI, SQLAlchemy e Bootstrap já existentes) |
| Novas tabelas ou índices | Desnecessários para o volume atual | Rejeitado (consulta direta no SQLAlchemy preservando o banco) |
| JavaScript personalizado | Desnecessário | Rejeitado (submissão nativa via formulário GET) |

---

## Phase 1 Review Post-Design

Após elaboração de `research.md`, `data-model.md`, `contracts/web-search-contract.md` e `quickstart.md`, confirma-se que:
1. O escopo permaneceu estritamente restrito à adição do campo de pesquisa no fluxo global de movimentações.
2. Nenhum detalhe de implementação vazou para os requisitos de negócio.
3. Todos os gates constitucionais foram revalidados e continuam 100% satisfeitos.
4. O projeto está pronto para a fase de decomposição de tarefas (`/speckit-tasks`).
