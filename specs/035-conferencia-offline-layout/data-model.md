# Data Model: Conferência Offline — responsividade e padronização visual (035)

**Sem entidades de dados novas ou alteradas.** A feature é exclusivamente de apresentação: nenhum model, tabela, coluna, rota, permissão ou payload muda (FR-012/FR-013 da spec).

## Modelo de apresentação (únicas superfícies afetadas)

### 1. Template `app/web/templates/inventarios/offline.html` (autônomo, não estende base.html)

| Região | Elementos | Estado atual | Alteração prevista |
|---|---|---|---|
| `<header class="offbar">` | `.offbar-brand` (logo), `.offbar-info` (`.offbar-line1`: título "SisPatrimônio PRO" + `.offbar-code`), `#offlineModeIndicator`, `#darkToggle` | Marca lado a lado com o código (commit `30d051e`) | Marca **empilhada** (D1); ≥768px linha única; ≤767px código+status na 2ª linha (D4/C-3) |
| `<main>` | container da página | `container-fluid py-4 px-lg-4 mx-auto` + `max-width: 92%` | `container-fluid py-4 px-lg-5 mx-auto` + `max-width: 90%` para ≥768px; ≤767px mantém 100% + padding `.75rem` (D2/C-1) |
| Alerta informativo, painel de contadores (`#offlinePainel`), card de sincronização | herdam `main` | Já no container | Sem mudança estrutural; herdam a nova largura |
| Card "Lista/pesquisa de itens" | `#buscaItem`, `#btnLerQR`, `#avisoPacote`, `table-responsive` > `table` (5 colunas), `#semPacoteDica` | Pesquisa e tabela no mesmo card; `d-flex gap-2 mb-3` | Mesma largura integral do card para pesquisa+QR e tabela; cabeçalhos alinhados (D3); botão mantém `btn-outline-primary` (C-2) |
| Modal `#modalColetaOffline` | form de coleta (4 resultados, local, observação) | Intocado | Sem mudança funcional; herda a largura do container |

### 2. CSS embutido do template (bloco `<style>` local)

| Bloco | Alteração |
|---|---|
| `.offbar`, `.offbar-brand`, `.offbar-info`, `.offbar-line1` | Reorganização para marca empilhada + quebra mobile (D1/D4) |
| Media queries (≥992px, ≥768px, ≤767.98px, ≤575.98px) | Regra de largura do `main` alinhada ao sistema (D2); demais regras preservadas |
| `body { overflow-x: hidden; }` | **Preservado** (proteção contra transbordo) |

### 3. `app/web/static/css/style.css` — **só se reuso exigir**

| Regra | Condição |
|---|---|
| `.navbar-brand` (L197-223) | **Intocado** (padrão de referência) |
| Demais regras | Nenhuma alteração prevista; preferência por CSS local do template (mudança no style.css exige bump adicional de querystring) |

### 4. `app/web/static/js/sw.js`

| Regra | Alteração |
|---|---|
| `CACHE_VERSION` | `inventario-offline-v24` → `inventario-offline-v25` (D5) |
| `PRECACHE_URLS` (allowlist) | **Intocada** (mesmos estáticos) |
| Handlers install/activate/fetch | **Intocados** |

### 5. `app/web/static/js/inventario_offline.js` e JS inline do template

**Intocados.** O JS consome por `id`/`name` (contrato DOM em `contracts/ui-shell-offline-contract.md` — ver contracts/) e classes funcionais (`badge-soft-*`, `tag-badge`, `result-option`): preservá-los é o requisito de não quebrar a coleta.

**Nota**: mudança em `style.css` (se ocorrer) implica bump da querystring `?v=` na referência do template — o arquivo está na allowlist do SW.
