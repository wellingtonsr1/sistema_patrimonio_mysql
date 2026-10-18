# Research — 074 Dropdown de Locais na Conferência Offline

**Data**: 2026-10-18 | **Base**: inspeção direta do código (nenhum arquivo alterado nesta fase)

## Parte A — Diagnóstico técnico obrigatório (FR-013 / §8 da spec)

### A.1 Arquivos responsáveis pela Conferência **Online**

| Arquivo | Papel (verificado) |
|---|---|
| `app/web/routers/inventario.py` | `view_inventario` (L142, `all_locations` em L197), `conferir_asset_page` (L279, `all_locations` em L295) e os POSTs de conferência (L317 e L381) que recebem `found_location_id: Optional[int] = Form(None)` e delegam a `InventarioService` |
| `app/web/templates/inventarios/detail.html` | Modal de conferência: `<select name="found_location_id" id="modalloc-{{ item.id }}">` iterando `{% for loc in all_locations %}` (L370–455) |
| `app/web/templates/inventarios/conferir.html` | Página de conferência por bem, mesmo padrão de `<select>` (L90–122) |
| `app/services/inventario_service.py` | `record_check` (L262–315): `LOCAL_DIFERENTE` **exige** `found_location_id` válido (`db.get(Location, ...)`); grava `item.found_location_id` + snapshot textual `item.found_location_name` |

Fonte dos locais no online: **`LocationService.get_all(db)`** — todos os locais, ordenados por `branch, department, name` (sem filtro de status: o modelo não possui flag de ativo).

### A.2 Arquivos responsáveis pela Conferência **Offline**

| Arquivo | Papel (verificado) |
|---|---|
| `app/web/routers/inventario.py` | `view_inventario_offline` (L474): serve a **shell** `inventarios/offline.html` com permissão `inventario.visualizar`; a coleta acontece 100% no client |
| `app/web/templates/inventarios/offline.html` | Modal de coleta: **`<input type="text" id="mFoundLocationName">`** (L328–331, "Digite o nome do local — o servidor valida na sincronização"); submit grava coleta em IDB com `found_location_id: null, found_location_name: <texto>` (L600–621) |
| `app/web/static/js/inventario_offline.js` | Núcleo client (432 linhas): IndexedDB `sispatrimonio_offline` v1 com stores `packages`/`coletas`/`sync_queue`/`device_info`; migração `onupgradeneeded` **apenas cria** (FR-038); `savePackage` grava o pacote inteiro; `registrarColeta` já aceita `foundLocationId`; `sincronizar` **já envia `found_location_id` E `found_location_name`** (L203–207) |
| `app/web/static/js/sw.js` | `CACHE_VERSION = "inventario-offline-v34"`; casco offline cache-first; `inventario_offline.js` está no `PRECACHE_URLS` |
| `app/api/inventario_offline_api.py` | `POST .../offline/package` (permissão `inventario.conferir`), `GET .../offline/ping`, `POST .../offline/sync` — **contrato intocado** |

### A.3 Mecanismo de armazenamento local do inventário (o que será reutilizado)

- **IndexedDB `sispatrimonio_offline`, versão 1**, stores: `packages` (keyPath `inventory_id`), `coletas` (keyPath `client_operation_id`), `sync_queue`, `device_info`.
- Ciclo de vida do pacote: `POST .../offline/package` → `savePackage(pkg)` → record completo persistido em `packages` (inclui `status: READY|EXPIRED`, `snapshot_version`, `items[]`); `getPackage(invId)` recupera; re-preparo substitui o pacote preservando `coletas`; `limparDispositivo` só remove após sync confirmado (FR-040).
- **O pacote hoje NÃO contém catálogo de locais** — apenas `expected_location_id`/`expected_location_name` por item (comentário em `process_sync`: "o pacote não carrega catálogo de locais — FR-003" da spec 033).

### A.4 Fluxo de sincronização (formato atual)

`InventarioOfflineService.process_sync` (L159–400): por operação —
1. idempotência por `client_operation_id`; 2. inventário aberto; 3. `snapshot_version` confere; 4. **validação de local**: se `found_location_id` vier, valida `db.get(Location, id)` (rejeita `local_inexistente`); senão, resolve `found_location_name` por **match exato único** em `Location.name` (constraint `unique`); sem match → rejeição estável `local_nao_resolvido` **preservando a coleta**; 5. gravação oficial única via `InventarioService.record_check`.

**Conclusão-chave: o contrato de sync já aceita `found_location_id` do cliente offline hoje — zero mudança de servidor para o transporte.**

### A.5 Cadastro de locais (estrutura real)

`app/models/location.py`: `Location` — `id` (Integer PK, estável e único), **`name` (String(100), `unique=True`, `index=True`)**, `branch`, `building`, `floor`, `room`, `department`, `manager_name`, `description`, `created_at`. **Não existe flag de ativo/inativo** — "local removido" é o único cenário de descontinuidade; "local desativado" não é um conceito do modelo atual.

`LocationService.get_all` ordena por `branch, department, name`; é a mesma fonte exibida pela Conferência Online.

### A.6 Testes existentes relacionados

| Arquivo | Cobre |
|---|---|
| `tests/test_inventario_offline.py` | Pacote (§2), sync (§3) incluindo `found_location_id` (L128, L349, L483–489), conflitos/reconciliação, UI da shell offline |
| `tests/test_inventario.py` | `record_check` com `found_location_id` (L110–190, L378–486) |
| `tests/test_inventario_reconferencia_ui.py` | UI online com `found_location_id` |
| `tests/test_acessibilidade_estatica_069.py` | Acessibilidade da página offline (`/offline` sem controles sem nome) |
| `tests/test_sw_service_worker.py` | `CACHE_VERSION` e estrutura do SW (bump esperado v32+; v35 é aditivo) |

---

## Parte B — Decisões de design (formato Decision/Rationale/Alternatives)

### D1 — Catálogo de locais embarcado no pacote offline

- **Decision**: `generate_package` passa a incluir `"locations": [{"id": <int>, "name": <str>}, ...]` (ordenado como `get_all`: branch/department/name; payload só precisa de `id`+`name`), persistido **dentro do mesmo record** do pacote na store `packages`.
- **Rationale**: é literalmente a reutilização pedida pela RF03 — mesmo transporte (endpoint de preparação), mesmo armazenamento (IndexedDB `packages`), mesmo ciclo de atualização (preparar/re-preparar) e mesma limpeza (`limparDispositivo`). A atualização acontece exatamente quando o usuário prepara/re-prepara a coleta, que já é o momento em que os dados são renovados. Falha de rede preserva o pacote anterior porque `savePackage` só roda no `.then` do fetch com resposta OK.
- **Alternatives considered**:
  - *Novo endpoint + novo store `locations` no IndexedDB*: cria segundo mecanismo de persistência e exigiria bump de `DB_VERSION` (acoplada ao `CACHE_VERSION`, D4 da spec 033) — proibido pela RF03/restrições.
  - *Repetir local esperado por item (já existe) e inferir o catálogo dos itens*: cobre apenas locais já esperados no snapshot — viola FR-002 (mesmo conjunto do online).
  - *localStorage*: reservado a `sp_device_id`/preferências por design (FR-031 da spec 033).

### D2 — Identificação do local: `found_location_id` (PK estável)

- **Decision**: o dropdown grava o `Location.id` no campo `found_location_id` da coleta; o nome é usado só para exibição (e gravado junto apenas como snapshot de apresentação, já que `sincronizar` envia os dois campos). Servidor continua autoridade (`process_sync` valida o id).
- **Rationale**: `Location.id` é PK única e estável; `process_sync` **já valida id** e o cliente **já envia** o campo — nenhuma mudança de contrato. Resolve RF06/FR-006 com a menor alteração possível (0 mudança de modelo/sync).
- **Alternatives considered**: *só nome textual* (status quo) — mantido apenas como fallback de compatibilidade para coletas antigas; *adotar `name` como chave* — rejeitado: dependência textual é justamente a causa do problema.

### D3 — Ciclo de atualização: preparação/re-preparação do pacote (sem rotina nova)

- **Decision**: a lista é atualizada quando o pacote é (re)preparado — mesmo ciclo do inventário (RF05). Re-preparo é confirmado pela UI existente ("A nova versão substitui a anterior; as coletas pendentes são preservadas").
- **Rationale**: já é o mecanismo de atualização dos dados offline; substituição atômica e preservação de pendências já garantidas (FR-040). Sem requisições periódicas novas.
- **Alternatives considered**: *refresh automático a cada visita online* — requisições extras sem necessidade; *cron/intervalo* — mecanismo novo, proibido.

### D4 — Persistência: sem mudança de schema do IndexedDB

- **Decision**: `DB_VERSION` permanece **1**; `locations` é um campo do record de pacote. Único bump é o `CACHE_VERSION` → `inventario-offline-v35` em `sw.js`, porque `inventario_offline.js` e a shell offline são servidos cache-first e precisam atualizar nos dispositivos.
- **Rationale**: migração aditiva zero-risco; a regra do projeto (onupgradeneeded apenas cria stores) fica intacta — nenhuma criação de store é necessária.
- **Alternatives considered**: *criar store `locations` + DB_VERSION 2* — desnecessário e acoplado ao SW (D4 da spec 033).

### D5 — Retrocompatibilidade

- **Decision**:
  - **Pacote antigo** (já no dispositivo, sem `locations`): o dropdown entra no estado "lista indisponível" com orientação para reconectar e **re-preparar a coleta offline** (equivalente ao Cenário F/SC-006: bloqueio + mensagem; nada de texto livre).
  - **Coletas antigas** com `found_location_name`: permanecem intactas e sincronizáveis — `process_sync` continua resolvendo por nome exato único como até hoje.
  - **Cliente antigo com pacote novo**: ignora o campo `locations` (JSON aditivo) — sem quebra.
- **Rationale**: FR-012/SC-007: nenhum dado descartado, nenhuma migração.

### D6 — UI e acessibilidade

- **Decision**: `<select class="form-select form-select-sm">` com `label[for]`/`id` (`mFoundLocationId`), exatamente o padrão do online (`modalloc-{{ item.id }}`); opção vazia "Selecione o local…"; exibição do nome (`name` é único no cadastro — sem homônimos, RNF-003 resolvido pelo próprio modelo). Aplicável apenas quando o resultado é `LOCAL_DIFERENTE` (comportamento atual preservado).
- **Rationale**: paridade visual (RF02/RNF01), acessibilidade da spec 069 preservada (RNF04), sem bibliotecas novas.
- **Alternatives considered**: *dropdown com busca (datalist/combobox)* — condicionado pelo RNF-002/decisão de clarify: só se a investigação apurar volume; cadastro atual é de ordem de dezenas/centenas → **fora da v1**.

### D7 — Vazio × indisponível (distinção obrigatória)

- **Decision**: dois estados distintos na UI:
  1. `pkg.locations` **ausente** (pacote antigo) ou pacote inexistente → "lista indisponível — reconecte e re-prepare a coleta offline"; registro bloqueado.
  2. `pkg.locations` **presente e vazio** (nenhum local cadastrado) → "nenhum local cadastrado no sistema"; registro bloqueado.
- **Rationale**: FR-004/FR-010/SC-006: nunca inventar opções; nunca selecionar automaticamente.

### D8 — Escopo fechado de alterações

| Arquivo | Alteração |
|---|---|
| `app/services/inventario_offline_service.py` | `generate_package`: adicionar `locations` (via `LocationService.get_all`, projeção `id`+`name`) |
| `app/web/templates/inventarios/offline.html` | Trocar input por `<select>`; renderização do catálogo a partir de `pkg.locations`; estados D7; coleta grava `found_location_id` (+ snapshot name) |
| `app/web/static/js/sw.js` | `CACHE_VERSION` → `inventario-offline-v35` |
| `app/services/help_service.py` | Texto da ajuda da conferência: "informe o nome" → "selecione o local na lista" (XI) |
| `tests/test_dropdown_locais_offline_074.py` | Novos testes (ver quickstart.md) |

**NÃO alteram**: `inventario_offline.js` (já suporta o caminho), `inventario_offline_api.py`, `inventario_service.py`, `inventario.py` (rotas), models/migrations, templates da Conferência Online.

## NEEDS CLARIFICATION restantes

**Nenhum.** Todos os unknowns do Technical Context foram resolvidos pela inspeção (Parte A) e pelas decisões D1–D8.
