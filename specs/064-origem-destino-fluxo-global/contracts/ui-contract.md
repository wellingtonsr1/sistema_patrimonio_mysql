# UI Contract — Feature 064: Fluxo Global de Movimentações (Origem/Destino)

**Data**: 2026-10-07 · **Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)

Contrato de apresentação das células Origem/Destino da tabela do Fluxo Global (`/movements`). Define o **estado protegido** (o que não muda), o **novo estado** (o que muda) e a **regra de composição** que a implementação e os testes devem seguir.

## §1 Estado protegido (byte-a-byte)

| Elemento | Local atual | Protegido por |
|---|---|---|
| Rótulos de coluna, cabeçalho, botões (Pesquisar/Exportar CSV/Nova Movimentação), filtros | `list.html` L20–60, L60–115 | testes de rota existentes + revisão de diff |
| `<style>` escopado da Feature 039 (`.mov-lista-table`, larguras de coluna em px, `.mov-fluxo`, `.mov-sec`, media query) | `list.html` L9–30 | AC10; nenhum seletor/largura alterado |
| Estrutura das `<td>`: classes `small mov-fluxo` (Origem) e `small` (Destino), ícones `bi-geo-alt*`/`bi-person*`, classes de cor | `list.html` L127–137 | contratos §2 |
| Colaborador: `{{ m.origin_custodian_name or '-' }}` / `{{ m.destination_custodian_name or '-' }}` | `list.html` L129–130, L134–135 | AC05 |
| Snapshot no banco, busca 049, CSV, termo, dashboard, relatório, dropdown 062, trilha 063 | backend + demais templates | US2 (guarda) + suítes 062/063 |

## §2 Novo estado — célula Origem (`td.small.mov-fluxo`, L128–130)

Quando `m.origin_location` **existe**:

```html
<div><i class="bi bi-geo-alt text-muted me-1"></i>{{ m.origin_location.department }}</div>
<div class="text-muted mov-sec">{{ contexto }}</div>
<div class="text-muted mov-sec"><i class="bi bi-person me-1"></i>{{ m.origin_custodian_name or '-' }}</div>
```

Quando `m.origin_location` **não existe** (FK nula): exatamente como hoje —
`{{ m.origin_location_name or '-' }}` (snapshot cru byte-a-byte: `Fornecedor / Entrada Inicial`, `Não definido`, formatos antigos).

## §3 Novo estado — célula Destino (`td.small`, L131–135)

Quando `m.destination_location` **existe**:

```html
<div class="fw-semibold" style="color:var(--c-primary-text);"><i class="bi bi-geo-alt-fill me-1"></i>{{ m.destination_location.department }}</div>
<div class="mov-sec" style="color:var(--c-primary-text);">{{ contexto }}</div>
<div class="mov-sec" style="color:var(--c-primary-text);"><i class="bi bi-person-fill me-1"></i>{{ m.destination_custodian_name or '-' }}</div>
```

Quando não existe: snapshot cru como hoje (`{{ m.destination_location_name or '-' }}`).

## §4 Regra de composição do contexto (idêntica à 063)

Macro no topo do arquivo (após o `extends`, antes dos blocos):

```jinja
{% macro _local_curto(name, department) -%}
{%- if department and name.endswith(' - ' + department) -%}
{{- name.rsplit(' - ' + department, 1)[0] -}}
{%- else -%}
{{- name -}}
{%- endif -%}
{% endmacro %}
```

Composição por célula ( Origem e Destino, com `loc` = relação):

```jinja
{% set curto = _local_curto(loc.name, loc.department) %}
{% set partes = [] %}
{% if curto and curto != loc.department %}{% set _ = partes.append(curto) %}{% endif %}
{% if loc.branch and loc.branch not in partes and loc.branch != loc.department %}{% set _ = partes.append(loc.branch) %}{% endif %}
{{ partes | join(' • ') }}
```

Regras: (1) linha principal = `loc.department` (cadastro atual — Clarifications 2026-10-07); (2) contexto na linha seguinte, classe `mov-sec`, join por ` • `; (3) deduplicação: nenhum valor aparece 2× no mesmo contexto (proibido `Clube • Clube` e `Clube da Pessoa Idosa - Clube da Pessoa Idosa`); (4) campos vazios não geram separador órfão; (5) se `partes` ficar vazia, a linha de contexto não renderiza (sem linha em branco).

## §5 Mockup antes/depois

| Antes (snapshot cru) | Depois (contrato §2–§4) |
|---|---|
| `IPMJP - Sede - Assessoria de Gabinete (Sede - Assessoria de Gabinete)` | **Assessoria de Gabinete** / `Sede • IPMJP - Sede` |
| `Clube - Clube da Pessoa Idosa (Clube da Pessoa Idosa)` | **Clube da Pessoa Idosa** / `Clube` |
| `Sede - Sala de Reunião (Sede - Sala de Reunião)` | **Sala de Reunião** / `Sede • IPMJP - Sede` |
| `Não definido` + `Nenhum / Estoque` | `Não definido` + `Nenhum / Estoque` (byte-a-byte) |
| `Fornecedor / Entrada Inicial` | `Fornecedor / Entrada Inicial` (byte-a-byte) |

## §6 Violações de contrato (qualquer uma falha os testes)

1. Qualquer alteração fora das 2 `<td>` + macro (inclui `<style>`, larguras, cabeçalhos).
2. Exibição de texto que não venha de `loc.department`/`_local_curto(loc.name)`/`loc.branch`/snapshots (ex.: `Custodian.department`).
3. Qualquer snapshot reformatado, regravado ou interpretado (ex.: parsear `Não definido`).
4. Consulta nova ou alteração em `movement_service.py`/`report_service.py`/routers.
5. Contexto duplicado (`X • X`) ou separador órfão (` • ` no fim/início).
