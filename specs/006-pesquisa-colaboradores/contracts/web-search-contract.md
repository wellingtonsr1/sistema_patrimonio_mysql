# Contract — Pesquisa na tela de Colaboradores (`GET /custodians`) — feature 006

**Base**: extensão da rota existente `list_custodians_view` (`app/web/routes.py`), seguindo o
precedente da pesquisa de bens. Este contrato define a interface web para implementação,
testes e validação.

## Requisição

```text
GET /custodians                    → listagem completa (comportamento atual)
GET /custodians?search=<termo>     → listagem filtrada (novo)
```

| Elemento | Regra |
|---|---|
| Método/rota | `GET /custodians` (existente, inalterada) |
| Permissão | `colaboradores.visualizar` (existente, inalterada) |
| `search` | Opcional. Texto livre do operador. Normalização: `strip()`; vazio/ausente = sem filtro |
| Campos filtrados | `registration_code`, `name`, `role`, `department`, `email` |
| Correspondência | Parcial (`%termo%`) e case-insensitive (`ILIKE`) — combinada via `OR` entre os 5 campos |
| Filtro executado em | `CustodianService.get_all(db, search=...)` — única lógica (sem duplicação) |

## Comportamentos de saída

| Situação | Resposta |
|---|---|
| Sem `search` (ou só espaços) | Tabela completa, igual à atual — sem mensagem de busca |
| `search` com correspondências | Tabela com somente os colaboradores correspondentes; mesmas colunas (Matrícula, Nome, Cargo, Departamento, E-mail, Bens, Ações), links (`/custodians/{id}`, `/custodians/{id}/edit` conforme permissão) e contagem de bens idênticos |
| `search` sem correspondência | HTTP 200 + mensagem "Nenhum colaborador encontrado." (sem erro de aplicação) |
| Lista vazia sem busca | "Nenhum colaborador cadastrado" (estado atual preservado) |
| Campo repopulado | O input volta preenchido com o termo pesquisado (`value="{{ search }}"`) |

## UI (padrão visual da pesquisa de bens — `assets/list.html`)

```text
[form GET /custodians]
  input-group: ícone bi-search + input name="search" com placeholder
  "Pesquisar por matrícula, nome, cargo, departamento ou e-mail..."
  + botão/ação de submit; limpar o campo e submeter = listagem completa
```

## Regras de não-regressão do contrato

1. `GET /custodians` sem `search` renderiza exatamente a tela atual (mesmos dados, ordem por nome, contagens).
2. `CustodianService.get_all` sem `search` comporta-se byte-idêntico ao atual (API REST `/api/v1/custodians` e chamadores `active_only=True` intactos).
3. A pesquisa não cria, altera ou exclui colaborador (operação read-only).
4. A pesquisa não expõe colaborador além do universo já visível (permissão da rota intacta).
5. Links, ações e contagem de bens nos resultados funcionam como antes (CA-010/CA-011).
6. Nenhum teste existente é editado; nova cobertura em `tests/test_custodians_search.py`.
