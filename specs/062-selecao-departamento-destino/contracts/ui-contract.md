# UI Contract — Selects de Localização (Feature 062)

**Alcance**: os 2 selects em escopo. Os outros 4 pontos que iteram sobre `locations` ficam FORA (research R3): `assets/list.html` L76, `assets/labels.html` L69, `inventarios/new.html` L40 (filtros com `loc.name` puro) e `locations/list.html` L64 (tabela).

## 1. Select de destino da movimentação — `app/web/templates/movements/new.html` (L102–106)

### Estado protegido (não muda)

- `<select name="destination_location_id" class="form-select">` — atributos idênticos.
- Primeira opção: `<option value="">-- Manter Local Atual --</option>` — fora de qualquer `optgroup`, primeira do select.
- `value` de cada opção: `{{ loc.id }}`.
- Sem atributo `selected` no loop (não existe hoje; research R7).
- Rótulo do campo (`Novo Local / Departamento`) e demais elementos do form: intocados.

### Novo estado (muda apenas o corpo do loop)

```html
<select name="destination_location_id" class="form-select">
    <option value="">-- Manter Local Atual --</option>
    {% for branch, locs in locations | groupby('branch') %}
    <optgroup label="{{ branch }}">
        {% for loc in locs %}
        <option value="{{ loc.id }}">{{ loc.department }} ({{ branch }})</option>
        {% endfor %}
    </optgroup>
    {% endfor %}
</select>
```

Renderização esperada (dados de produção, 36 locais):

```
-- Manter Local Atual --
[ Clube ]
  Clube da Pessoa Idosa (Clube)
[ IPMJP - Sede ]
  Acessoria de Controle Interno (IPMJP - Sede)
  Acessoria de Gabinete (IPMJP - Sede)
  ... (ordem da fonte: departamento → nome)
[ IPMJP – Sede ]          ← grupo próprio (travessão, 1 registro — higiene é feature própria)
  Data Center (IPMJP – Sede)
[ Shoping ]
  Shoping 4400 (Shoping)
```

## 2. Select de Localização do Equipamento — `app/web/templates/assets/form.html` (L109–111)

### Estado protegido (não muda)

- `<select name="location_id" class="form-select">` — atributos idênticos.
- Primeira opção: `<option value="">-- Estoque Central / Almoxarifado --</option>` — fora de qualquer `optgroup`, primeira do select.
- `value="{{ loc.id }}"` e ausência de `selected` (form de criação não pré-seleciona local).

### Novo estado

Mesmo padrão do §1: loop `groupby('branch')` → `<optgroup label="{{ branch }}">` → `<option value="{{ loc.id }}">{{ loc.department }} ({{ branch }})</option>`.

## 3. Exemplos antes/depois (movimentação)

| Antes (atual) | Depois (062) |
|---|---|
| `Sede - Divisão de Previdência (IPMJP - Sede - Divisão de Previdência)` | `Divisão de Previdência (IPMJP - Sede)` no grupo `IPMJP - Sede` |
| `Clube da Pessoa Idosa (Clube - Clube da Pessoa Idosa)` | `Clube da Pessoa Idosa (Clube)` no grupo `Clube` |

## 4. Ordem e determinismo

- Grupos: ordenação case-insensitive por unidade (`groupby` Jinja2 ordena pela chave — research R1): `Clube`, `IPMJP - Sede`, `IPMJP – Sede`, `Shoping`.
- Opções dentro do grupo: ordem estável da fonte (departamento → nome).
- Nenhum critério novo de ordenação é introduzido no backend.

## 5. Contrato de não-mutação (com o backend)

- O formulário envia exatamente como hoje: `destination_location_id` (int) na movimentação, `location_id` (int) no equipamento.
- O snapshot gravado pela movimentação permanece `"{branch} - {department} ({name})"` — travado pelos testes existentes (`test_import_asset_movements.py` L134/L216) e reforçado pelo teste de não-mutação novo (US3 da spec).
- O repovoamento em erro do form de movimentação (redirect `?error=`) permanece: bem e tipo repovoados; local de destino não é pré-selecionado (comportamento atual, sem mudança).

## 6. Fora do contrato

- Selects de filtro (R3), tabela de locais, select de colaborador (`c.name (matrícula - department)` — L97/L121), rótulos de todas as outras telas, histórico/termo/relatórios (snapshots), dashboard.
