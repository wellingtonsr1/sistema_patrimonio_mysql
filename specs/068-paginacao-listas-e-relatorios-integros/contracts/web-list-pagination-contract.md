# Contract — Paginação das listas web (`?page=N`) e contadores

> Contrato de entrada/apresentação das 7 listas + tela de relatório. **Nenhuma rota nova: somente query string** (é por isso que `tests/route_manifest.json` permanece válido — feature 051).

## 1. Entrada comum

```
GET /assets?page=3
GET /movements?page=2&movement_type=TRANSFERENCIA_LOCAL&search=notebook
GET /custodians?page=2&search=ana
GET /inventarios?page=2&status_filter=EM_ANDAMENTO
GET /inventarios/12?page=2&search=notebook&status_filter=LOCAL_DIFERENTE
GET /admin/audit?page=2&start_date=2026-01-01&end_date=2026-10-31&user_id=7
GET /reports/inventory?page=2&status=EM_USO
GET /reports/movements?page=2          # P6 (2026-10-11): mesma estrutura, mesmos parâmetros
```

| Parâmetro | Tipo | Default | Normalização |
|---|---|---|---|
| `page` | inteiro | `1` | vazio, `abc`, `0`, `-1` → `1`; `> pages` → última página |
| `page_size` | — | `200` | **constante da casa**, não é parâmetro público (P3) |
| demais filtros | os atuais | os atuais | inalterados (mesmo parser de hoje) |

## 2. Regras do servidor

1. `offset = (page - 1) * 200` aplicado **no service** (`.offset().limit()`); nunca filtro/paginação em Python.
2. `total` = `count()` do **mesmo filtro** da página (I3 da data-model).
3. A ordem de paginação é a **mesma ordenação atual** da lista (ex.: bens por `created_at` desc, movimentações por `timestamp` desc, auditoria por `timestamp` desc).
4. Permissão é avaliada **antes** da página: usuário sem a permissão da rota recebe 403 + registro na trilha, com ou sem `page` (I6).
5. Resposta: sempre `200` com a página válida — **nunca** 400/404 por `page` inválida.
6. Total zero → estado vazio atual ("Nenhum registro..."), **sem** controle de página.

## 3. Contexto adicionado ao template

| Variável | Tipo | Uso |
|---|---|---|
| `total` | int | denominador do indicador |
| `page` | int | página corrente |
| `pages` | int | `ceil(total/200)` |
| `start` / `end` | int | primeiro e último índice da página (`1–200`, `201–250` …) |
| `has_prev` / `has_next` | bool | habilitam Anterior/Próxima |

## 4. Saída esperada (front-end)

- **Indicador** (em toda lista): `Mostrando 201–400 de 3.142 equipamentos` — padrão único para todas as listas (hoje há três redações diferentes).
- **Pager** (macro `templates/macros/pagination.html`, gerado apenas quando `pages > 1`):
  - `‹ Anterior` (inativo na página 1) · `Página 2 de 17 (3.142 registros)` · `Próxima ›` (inativo na última);
  - links com a **query string completa atual** + `page=N` (mesmo mecanismo de `admin/integracoes/historico.html:91-95`, que usa `{{ request.query_params }}`).
- **Contadores globais preservados** (não paginados): "Bens esperados: N", conferidas/restantes/divergências/não previstos do inventário, resumo por inventário na listagem.
- **Filtros**: o `<form method="get">` continua responsável pelos filtros; ao enviar o formulário a página volta a 1 (comportamento natural de `GET` sem `page`).

## 5. Casos de borda

| Caso | Resposta |
|---|---|
| `page=abc` / `0` / `-1` / vazia | página 1, `200` |
| `page=99999` | última página com dados, `200` |
| filtro que zera o total | estado vazio, `200`, sem pager |
| total ≤ 200 | indicador com intervalo total, **sem** pager |
| usuário sem permissão | `403` + trilha (inalterado) |
| página inexistente por id (`/inventarios/99999?page=2`) | `404` amigável (comportamento atual do id) |

## 6. O que NÃO muda

- Nenhum caminho de rota novo; nenhum método HTTP novo; nenhum cabeçalho novo.
- Permissões, busca, ordenação, conteúdo das linhas, ações por linha (Ver Detalhes, Editar, Movimentar, conferir), impressão de etiquetas e reconciliação offline.
- Contrato da API (`GET /api/v1/assets`, `/movements` com `skip/limit`; `/custodians` e `/locations` sem paginação — dívida registrada).
