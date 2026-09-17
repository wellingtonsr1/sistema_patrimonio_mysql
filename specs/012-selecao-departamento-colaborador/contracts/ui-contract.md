# Contract — UI (Web) da feature 012

**Feature**: 012-selecao-departamento-colaborador | **Data**: 2026-09-17 (**REVISADO**)

Superfície alterada: **apenas** `app/web/templates/custodians/form.html` (compartilhado por cadastro e edição — flag `is_edit`) e os 4 handlers correspondentes em `app/web/routes.py`. Padrões visuais Bootstrap 5 existentes (Constitution X).

---

## 1. Campo "Departamento / Setor *" (cadastro)

### 1.1 Renderização
- **Label**: mantém `Departamento / Setor <span class="text-danger">*</span>`.
- **Controle**: **campo de seleção (dropdown `<select class="form-select">` nativo)** dos valores oficiais (derivados de `locations.department` — contract service §1.1), server-rendered. **Nenhuma lista fixa no HTML** (FR-001). **Sem lógica de pesquisa** — sem datalist, sem digitação/filtro (decisão de UX 2026-09-17; R5 revista).
  - Marcação: `<select name="department" class="form-select" required>` com `<option value="{valor}">` por oficial.
  - Atributo `required` presente (primeira linha de defesa — a garantia é o backend, FR-003).
- **Option vazia** ("— Selecione —") como estado inicial no cadastro.
- **Placeholder/digitação**: não se aplicam a um dropdown — o controle não aceita texto livre (FR-002 estruturalmente garantido).
- **Pré-seleção na edição**: o valor vigente do colaborador (`selected`); se não constar da lista (grafia herdada), é acrescentado como opção extra pré-selecionada (FR-014/I2-b).

### 1.2 Regras de interação
- Digitação não existe no controle; **não é possível submeter valor fora da lista** com sucesso (o backend rejeita — FR-002/AC-02; o dropdown só oferece valores oficiais, e o vigente fora da lista permanece pré-selecionado até que outro valor seja escolhido).
- Submissões com caixa/trim diferentes de um oficial são **aceitas e canonizadas** (ex.: "SUPORTE" grava "Setor de Suporte" — contract service §1.2 regra 3); não há erro por variação de caixa.
- Nenhum botão/link "criar novo departamento" no formulário (fora do escopo — spec Seção 8).

## 2. Campo "Departamento / Setor" (edição)

- Mesmo controle da Seção 1 (mesma fonte — FR-006/AC-06).
- **Pré-seleção**: o valor vigente do colaborador como valor inicial (`value="{{ custodian.department }}"`).
  - Se o valor vigente **consta** na lista oficial → pré-selecionado como hoje.
  - Se o valor vigente **não consta** (grafia herdada sem local correspondente — possível por RV-5/Q2), o texto atual aparece preenchido; a submissão **idêntica ao valor vigente** é aceita sem re-normalização (FR-014 — remediação `/speckit-analyze` I2, opção b); a validação oficial aplica-se apenas a valor submetido **diferente** do vigente.

## 3. Estados de erro (mesma mecânica atual)

| Estado | Apresentação |
|---|---|
| Submissão sem seleção | Redirect `303 → /custodians/new?error=...` (ou `.../{id}/edit?error=...`), alerta `alert-danger` padrão do template — "Departamento/Setor é obrigatório" |
| Valor fora da lista oficial | Mesmo caminho — "Departamento/Setor inválido — selecione um registro da lista oficial" |
| Variação de caixa/trim de um oficial | **Não é erro** — canonizado e gravado (§1.2) |

Nenhum novo tipo de alerta/estilo — reuso integral do bloco `{% if error %}` existente.

## 4. Handlers web (`app/web/routes.py`)

- `form_new_custodian` / `form_edit_custodian` (GET): injetam `departments = DepartmentService.list_official(db)` no contexto do template (consulta `DISTINCT` já praticada em 3 pontos do arquivo — precedentes linhas 342/406/1806).
- `create_custodian_form` / `update_custodian_form` (POST):
  - Novo parâmetro oculto do formulário: `department_source: Optional[str] = Form(None)`.
  - **Quando `department_source == "official"`** (formulário da nova UI): `department = DepartmentService.ensure_official(db, department)` antes de montar `CustodianCreate`/`CustodianUpdate` — `ValueError` vira redirect `?error=` (padrão atual).
  - **Exceção na edição (remediação I2, opção b)**: em `update_custodian_form`, quando o valor submetido (após trim) for **idêntico ao valor vigente** do colaborador, `ensure_official` é pulado — a submissão do vigente (mesmo fora da lista) é aceita sem re-normalização (FR-014); a validação aplica-se apenas a valor **diferente**.
  - **Sem o marcador** (caminho legado: testes existentes, integrações): comportamento atual integral — nenhum convite a `ensure_official` (R6 revista).
  - Marcação do formulário: `<input type="hidden" name="department_source" value="official">` (o dropdown sempre envia o marcador).
- Auditoria e redirects: inalterados.

## 5. Demais telas — intocadas

`custodians/list.html`, `custodians/detail.html`, `assets/*`, `movements/*`, `reports/*` continuam lendo `custodian.department` (texto) — nenhum template fora de `custodians/form.html` é alterado.

## 6. Non-goals visuais

- Sem biblioteca JS externa (Select2/TomSelect vetadas — research R5).
- Sem tela/CRUD de gerenciamento de departamentos (novos valores oficiais surgem do fluxo de **locais**, já existente — research R8 revista).
- Sem alteração no menu, permissões visíveis (`can()`) ou navegação.
