# UI Contract — Trilha de Fluxo & Movimentações (Feature 063)

**Alcance**: o card `flow-card` de cada item de **movimentação** na seção "Trilha de Fluxo & Movimentações" de `app/web/templates/assets/detail.html` (atualmente L257–268). Itens de **auditoria** da timeline, a seção "Custódia & Localização Atual" (L109–114), o card "Ficha Técnica", badges de tipo/termo, motivo e observações: **fora do contrato** (intocados). Os demais pontos que exibem snapshots (`movements/list.html`, `dashboard.html`, `reports/movements_report.html`, termo) também ficam fora (research R6).

## 1. Estado protegido (não muda)

- Rótulos `Origem` (`flow-label-origin`) e `Destino` (`flow-label-dest`); seta central; grid Bootstrap (`col-12 col-md-5` / `col-md-2`).
- Linha do colaborador (`flow-sub`): `{{ item.data.origin_custodian_name or 'Nenhum' }}` / `{{ item.data.destination_custodian_name or 'Almoxarifado / Estoque' }}`.
- Badges de tipo/termo, data, motivo e observações do item.
- A seção "Custódia & Localização Atual" inteira (referência visual — AC01).
- Dropdowns da Feature 062 (`movements/new.html`, `assets/form.html`) — byte-a-byte (AC05).
- Nada é gravado, regravado ou reformatado no banco (AC06/AC07).

## 2. Novo estado (muda apenas o corpo de cada ponto Origem/Destino)

Macro local no template (definida no topo de `assets/detail.html`, após o `extends` — research R4):

```jinja
{% macro _local_curto(name, department) -%}
{%- if department and name.endswith(' - ' + department) -%}
{{- name.rsplit(' - ' + department, 1)[0] -}}
{%- else -%}
{{- name -}}
{%- endif -%}
{%- endmacro %}
```

Regra por ponto, quando a **relação existe** (`item.data.origin_location` / `destination_location`):

```jinja
<div class="flow-value ...">{{ loc.department }}</div>
{% set curto = _local_curto(loc.name, loc.department) %}
{% set partes = [] %}
{% if curto and curto != loc.department %}{% set _ = partes.append(curto) %}{% endif %}
{% if loc.branch and loc.branch not in partes and loc.branch != loc.department %}{% set _ = partes.append(loc.branch) %}{% endif %}
<div class="flow-sub-local">{{ partes | join(' • ') }}</div>
```

- **Linha principal**: `location.department` — ex.: `Divisão de Previdência`.
- **Linha de contexto**: componentes deduplicados unidos por ` • ` — ex.: `Sede • IPMJP - Sede`; se sobrar só `branch`, mostra só ele (ex.: `Clube`); se não sobrar nenhum, a linha é omitida.
- **Deduplicação** (edge cases 3/4 da spec): componente igual ao `department` ou repetido é omitido — `Shopping 4400 - Shopping 4400` e `Sede • Sede` jamais aparecem.

Quando a **relação não existe** (FR-010 — research R3):

```jinja
<div class="flow-value ...">{{ item.data.destination_location_name or 'Estoque Geral' }}</div>
```

Snapshot cru como texto único, sem linha de contexto e sem decomposição — ex.: `Fornecedor / Entrada Inicial` (origem da ENTRADA_AQUISICAO), local excluído do cadastro.

## 3. Exemplos antes/depois (dados reais)

| Antes (atual) | Depois (063) |
|---|---|
| `IPMJP - Sede - Divisão de Previdência (Sede - Divisão de Previdência)` + `Jackceline Dias (PROV-000074)` | `Divisão de Previdência` / `Sede • IPMJP - Sede` + `Jackceline Dias (PROV-000074)` |
| `IPMJP - Sede - Setor de Recadastramento (Sede - Setor de Recadastramento)` | `Setor de Recadastramento` / `Sede • IPMJP - Sede` |
| `Clube da Pessoa Idosa (Clube - Clube da Pessoa Idosa)` [name == department] | `Clube da Pessoa Idosa` / `Clube` (sem duplicação) |
| `Fornecedor / Entrada Inicial` (origem de entrada) | `Fornecedor / Entrada Inicial` (texto único, sem contexto — inalterado) |
| `Estoque Geral` (snapshot vazio) | `Estoque Geral` (fallback preservado) |

## 4. Contrato de não-mutação (com o backend)

- Nenhum caminho de escrita é alterado: `MovementService.create_movement`, `asset_service.py`, `import_service.py` intocados — o snapshot gravado permanece `"{branch} - {department} ({name})"` (FR-003), travado por `test_import_asset_movements.py` L134/L216 e pelo teste de não-mutação novo (US2).
- Registros existentes não são regravados (FR-004); a busca 049 (`ilike` nos snapshots) continua casando termos antigos.
- A leitura da página continua pela mesma rota `GET /assets/{id}` (`patrimonio.visualizar`), com a mesma `timeline` do service — nenhuma consulta nova (FR-002).
- Repovoamento/parâmetros do detalhe (`?created=true`, `?moved=true`) inalterados.

## 5. Fora do contrato

- Colunas Origem/Destino de `movements/list.html`, `dashboard.html`, `reports/movements_report.html`; local do termo (`get_term_details`); selects da Feature 062; itens de auditoria da timeline; seção "Custódia & Localização Atual"; higiene de dados (typos) — feature própria.
