# Contract: Pesquisa web de locais (`GET /locations?search=`)

**Feature**: 007-pesquisa-locais · **Tipo**: contrato de interface web (rota + service) · **Base**: `app/web/routes.py::list_locations_view`, `app/services/location_service.py::get_all`, `app/web/templates/locations/list.html`

## 1. Requisição

```
GET /locations                      → listagem completa (comportamento atual, inalterado)
GET /locations?search=<termo>       → listagem filtrada pelo Nome / Identificação
```

| Parâmetro | Onde | Tipo | Default | Semântica |
|---|---|---|---|---|
| `search` | Query string | texto livre | ausente/`None` | Termo aparado (`strip`); vazio ou só espaços ⇒ **sem filtro** (lista completa). Filtro: `Location.name` contém o termo, case-insensitive, parcial em qualquer posição. **Mono-campo** — Filial/Departamento/Gestor/Prédio-Andar-Sala NÃO são pesquisados |
| — permissão | — | — | — | `locais.visualizar` (gate existente, inalterado) |

## 2. Comportamento do service (`LocationService.get_all`)

```
get_all(db)                     → todos os locais, order_by(branch, department, name)   [idêntico a hoje]
get_all(db, search=None)        → idem (None ≡ sem filtro)
get_all(db, search="  Gabinete ")→ strip() → "Gabinete" → locais cujo name contém "Gabinete", mesma ordenação
```

- **Retrocompatibilidade obrigatória**: chamadores existentes (API REST `GET /api/v1/locations`, formulários web, seletores) continuam chamando `get_all(db)` — resultado byte-idêntico ao atual. A API REST **não** expõe o parâmetro `search` nesta feature.

## 3. Resposta (HTML da tela)

| Condição | Renderização |
|---|---|
| Com ou sem pesquisa, há resultados | Card de filtros (sempre presente) + tabela com as 7 colunas atuais: Nome / Identificação, Filial, Departamento, Prédio / Andar / Sala, Gestor, Bens, Ações |
| `search` presente sem correspondência | Estado vazio com texto **exato**: `Nenhum local encontrado.` (HTTP 200, sem erro) |
| Sem registros no banco e sem `search` | Estado vazio existente: `Nenhum local cadastrado` (preservado, distinto do anterior) |
| Após qualquer pesquisa | Campo `search` reposto com o termo (FR-009); ordenação dos resultados = ordenação atual da listagem |

## 4. Elementos de UI do card de filtros (padrão vigente — FR-014)

| Elemento | Especificação |
|---|---|
| Container | `<div class="card p-3 mb-4">` próprio, separado do card da tabela (padrão `assets/list.html`, ajustado em colaboradores nesta conversa) |
| Form | `method="get" action="/locations" class="row g-2 align-items-center"` |
| Campo | `input-group`: ícone `bi-search` + input com placeholder orientativo e `value="{{ search }}"` |
| **Filtrar** | `<button type="submit" class="btn btn-primary"><i class="bi bi-funnel me-1"></i> Filtrar</button>` — **com ícone** |
| **Limpar** | `<a href="/locations" class="btn btn-ghost">Limpar</a>` — **somente texto, sem ícone**, sempre visível |
| Estados vazios | Ícone `bi-search` + título "Nenhum local encontrado." no estado de pesquisa (padrão `empty-state` existente) |

## 5. Regras de não regressão (verificáveis por teste)

1. `GET /locations` sem `search` retorna **exatamente** o mesmo HTML de dados que antes da feature (mesmos locais, mesma ordem, mesmas contagens).
2. `LocationService.get_all(db)` direto = lista completa (retrocompatibilidade de assinatura).
3. API REST `GET /api/v1/locations` inalterada (sem `search` exposto; resposta idêntica).
4. Colunas, links (`Ver Bens` com `location_id`), contagem de bens e ordenação idênticos nos resultados filtrados.
5. A pesquisa não cria, altera ou exclui locais (read-only — nenhuma mutação no banco durante a requisição).
6. Permissão: usuário sem `locais.visualizar` continua bloqueado (403), com ou sem `search`.
7. Termo que casa somente com Filial/Departamento/Gestor **não** retorna o registro (contratesta mono-campo).
8. Termo com caracteres especiais (`%`, `_`, aspas) não gera erro 500.

## 6. Fora do contrato

- Autocomplete, paginação, filtros por outros campos, seletor de campo, pesquisa client-side, alteração da API REST, alteração de permissões ou de CRUD de locais.
