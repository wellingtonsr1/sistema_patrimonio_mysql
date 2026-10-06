# Manuais — Evolução de Filtros (slice optgroup, fora da 062)

**Candidatura**: `/specs/062-selecao-departamento-destino/smoke/evolucao-filtros/`
**Base**: Feature 062 (`specs/062-selecao-departamento-destino/`), padrão `groupby('branch')` + `Departamento (Unidade)` + `value = loc.id`
**Status**: **PARA CANDIDATURA** — nenhum arquivo de `app/` alterado

---

## O que funciona no padrão da 062 (já provado no `features/062`)

- `<select name="location_id" class="form-select">` mantido;
- opção vazia `value=""` primeira, fora de qualquer `optgroup`;
- `<optgroup label="{{ branch }}">` + `<option value="{{ loc.id }}">{{ loc.department }} ({{ branch }})</option>`;
- zero backend: a lista `LocationService.get_all(db)` é a única fonte (já ordenada `branch, department, name`);
- não-mutação da gravação: `destination_location_id`/`location_id` continua enviando o `id`, o snapshot continua no formato `"{branch} - {department} ({name})"`.

---

## O que esta slice propõe aplicar ao filtro `location_id`

| Template | Linha | Original (`loc.name`) | Meta (optgroup + rótulo) |
|---|---|---|---|
| `assets/list.html` | 76 | `<option value="{{ loc.id }}">{{ loc.name }}</option>` | `{{ loc.department }} ({{ branch }})` |
| `assets/labels.html` | 69 | idem | idem |
| `inventarios/new.html` | 40 | idem | idem |
| `locations/list.html` | 64 | (tabela) | **não se aplica** (ver abaixo) |

- `value = loc.id` (único identificador) permanece;
- a URL e a lógica de filtro são **exatamente iguais** — só muda a exibição;
- os demais filtros (status, category, brand, model, department, maintenance, datas) permanecem inalterados, inclusive `loc.name` em `assets/list.html`;

---

## Descarte e fallback

### `locations/list.html` (L64) — não é select
- É uma **tabela** de locais; optgroups não se aplicam à exibição de lista. A hierarquia já sai como badges por linha (branch/department). Neste slice: **registro + descarte**.

### `inventarios/new.html` — `department` (select) não é candidato
- O select de `department` filtra por **texto livre** (`departments` vinda do router), sem vínculo de unidade. Aplica-se a evolução de departamentos, não à optgroup; **não é alterado**.

### Dados de qualidade (análise de 2026-10-06)
- `Location.department` e `Custodian.department` são **2 colunas de texto livre**, sem FK entre si;
- Drift comprovado em `locations.department`: `Divisão Previdenciária` (8 espaços), `Assessoria Gabinete/Controle` (4 cada), `Setor de Serviços Gerais` (1), typos (`Acessoria`, `Assist}ência`, `Superitendência`), branch `IPMJP – Sede` com travessão;
- Correção de dados **não está no escopo** desta slice; registra-se como risco para a feature 063.

---

## O que foi feito (sem tocar `app/`)

- 4 arquivos HTML estáticos em `specs/062-selecao-departamento-destino/smoke/evolucao-filtros/`:
  - `evolucao-filtros-assets-list.html` — mockup do filtro `location_id` (filtro de equipamentos);
  - `evolucao-filtros-assets-labels.html` — mockup do filtro `location_id` (etiquetas);
  - `evolucao-filtros-inventarios-new.html` — mockup do filtro `location_id` (novo inventário);
  - `evolucao-filtros-locations-list.html` — registro da não aplicabilidade (tabela);
- `handoff-evolucao-filtros.md` — este documento.

---

## Como integrar (se o usuário aprovar a candidatura)

1. Rend revisiones dos 4 templates no `app/web/templates/`;
2. Adicionar testes de renderização (erguindo o padrão da 062, `groupby + optgroup + rótulo + value = loc.id`);
3. Rodar a suíte completa (degrau esperado: +3 testes, 0 falhas, 0 test editados);
4. Gerar smoke visual dos 3 filtros + `locations/list.html` (comentado de tabela);
5. Abrir feature 063 no spec-kit e cruzar com o hiper-candidato a optgroup.

---

## Próximos passos (decisão do usuário)

- **[x] Slice gerado** (4 mockups + manual);
- **[ ] Crítica rápida dos dados** (`locations.department` × `custodians.department`) — recomendada antes de levar à feature 063;
- **[ ] Aprovar merge?** — se sim, aplicar aos 3 selects e gerar testes/smoke;
- **[ ] Greenfield?** — criar `specs/063-selecao-filtrar-por-departamento/`.

