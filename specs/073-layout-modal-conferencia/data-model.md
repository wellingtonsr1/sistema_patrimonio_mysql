# Data Model — 073-layout-modal-conferencia

> **Nenhuma entidade ou tabela nova.** Esta feature não cria tabelas, colunas, índices, enums, migrações ou esquemas Pydantic. O "modelo" desta especificação formaliza a **hierarquia da árvore DOM do modal de conferência**, os **invariantes de layout e acessibilidade** e as **regras estruturais de contenção** nos templates afetados.

---

## 1. Entidades de Dados Envolvidas (Todas Intocadas)

| Entidade (Tabela) | Uso no Modal | Alteração Estrutural |
|---|---|---|
| `inventarios` | Fornece `inv.id`, `inv.code`, `inv.status` | **Nenhuma** |
| `inventario_itens` | Fornece `item.id`, `item.asset`, `item.status`, `item.expected_location_name`, etc. | **Nenhuma** |
| `locations` | Fornece `all_locations` para o dropdown `<select name="found_location_id">` | **Nenhuma** |
| `audit_logs` | Trilha de auditoria gerada pela rota de conferência existente | **Nenhuma** |

**Zero DDL, zero migração e zero alteração de schemas.** O escopo de modificação de código limita-se exclusivamente a:
- [`app/web/templates/inventarios/detail.html`](file:///home/wellington/IA/sistema_patrimonio_mysql/app/web/templates/inventarios/detail.html) (linhas 407–476).

---

## 2. Modelo da Árvore DOM: Antes e Depois

### 2.1 Árvore DOM Anterior (Defeituosa)
```text
div.modal#modalConferir{id} [tabindex="-1"]
└── div.modal-dialog
    └── div.modal-content
        └── form [action="/inventarios/{id}/conferir/{item.id}"]
            ├── div.modal-header
            └── div.modal-body
                ├── alert-warning (se re-conferência)
                ├── div.text-muted (local esperado)
                ├── label (Resultado da conferência)
                ├── label (Resultado da conferência - DUPLICADO)
                └── fieldset.d-grid
                    ├── legend.visually-hidden
                    └── label.result-option * 4
                <!-- FECHAMENTO PREMATURO DE .modal-body PELO </div> DA LINHA 451 -->
            <!-- ELEMENTOS FORA DE .modal-body (PERDA DE PADDING, WIDTH 100% DAS BORDAS) -->
            ├── div.mb-2
            │   ├── label[for="modalloc-{id}"]
            │   └── select#modalloc-{id}.form-select
            ├── div
            │   ├── label[for="modalobs-{id}"]
            │   └── textarea#modalobs-{id}.form-control
            <!-- FECHAMENTO PREMATURO DE .modal-content PELO </div> DA LINHA 466 -->
        <!-- .modal-footer EJETADO PARA FORA DE .modal-content -->
        ├── div.modal-footer
        │   ├── button[data-bs-dismiss="modal"] (Cancelar)
        │   └── button[type="submit"] (Registrar resultado)
        <!-- </div> EXCEDENTE DA LINHA 474 FECHANDO CONTAINER ANCESTRAL -->
```

### 2.2 Árvore DOM Alvo (Íntegra e Conforme)
```text
div.modal.fade#modalConferir{id} [tabindex="-1", aria-hidden="true", aria-labelledby="modalLabel{id}"]
└── div.modal-dialog.modal-dialog-centered.modal-dialog-scrollable
    └── div.modal-content
        └── form [method="post", action="/inventarios/{id}/conferir/{item.id}"]
            ├── div.modal-header
            │   ├── h5.modal-title#modalLabel{id}
            │   └── button.btn-close [data-bs-dismiss="modal", aria-label="Fechar"]
            ├── div.modal-body
            │   ├── div.alert.alert-warning (se re-conferência)
            │   ├── div.text-muted.small.mb-3 (local cadastrado)
            │   ├── label.form-label.fw-semibold (Resultado da conferência *)
            │   ├── fieldset.d-grid.gap-2.mb-3 [style="border:0;padding:0;margin:0;"]
            │   │   ├── legend.visually-hidden (Resultado da conferência)
            │   │   ├── label.d-block.border.rounded.p-2.result-option (🟢 Encontrado)
            │   │   ├── label.d-block.border.rounded.p-2.result-option (🟡 Encontrado em local diferente)
            │   │   ├── label.d-block.border.rounded.p-2.result-option (🔴 Não encontrado)
            │   │   └── label.d-block.border.rounded.p-2.result-option (⚠️ Sem identificação)
            │   ├── div.mb-2
            │   │   ├── label.form-label.fw-semibold.small [for="modalloc-{id}"]
            │   │   └── select.form-select.form-select-sm#modalloc-{id} [name="found_location_id"]
            │   └── div
            │       ├── label.form-label.fw-semibold.small [for="modalobs-{id}"]
            │       └── textarea.form-control.form-control-sm#modalobs-{id} [name="observation", rows="2"]
            └── div.modal-footer
                ├── button.btn.btn-ghost [type="button", data-bs-dismiss="modal"] (Cancelar)
                └── button.btn.btn-primary [type="submit"] (Registrar resultado)
```

---

## 3. Invariantes de Design e Comportamento

- **I1 — Confinamento Estrito no `.modal-body`**: Todos os campos (`select`, `textarea`, rádios, alertas e rótulos) residem exclusivamente dentro de `<div class="modal-body">`, herdando o padding horizontal (`var(--bs-modal-padding) = 1rem / 16px`).
- **I2 — Confinamento do Rodapé no `<form>` e `.modal-content`**: O container `<div class="modal-footer">` reside no interior de `<form>` e `<div class="modal-content">`, garantindo envio do formulário no clique de "Registrar resultado".
- **I3 — Balanço Neutro de Tags HTML**: O bloco do modal no loop `{% for item in expected_itens %}` abre exatamente 4 tags `<div>` principais (`.modal`, `.modal-dialog`, `.modal-content`, `.modal-body` / `.modal-footer`) e fecha exatamente as mesmas tags, sem tags excedentes no final do loop.
- **I4 — Preservação dos Atributos de Acessibilidade da Spec 069**:
  - `fieldset` com `legend.visually-hidden` para o grupo de rádios;
  - `label[for="modalloc-{{ item.id }}"]` vinculado ao `select#modalloc-{{ item.id }}`;
  - `label[for="modalobs-{{ item.id }}"]` vinculado ao `textarea#modalobs-{{ item.id }}`;
  - Unicidade absoluta de IDs em toda a página gerada.
- **I5 — Rolagem Vertical Interna com Cabeçalho e Rodapé Fixos**: O uso da classe `.modal-dialog-scrollable` confina a rolagem vertical ao elemento `.modal-body`, garantindo que em viewports com altura reduzida (<= 600px), o título e os botões permaneçam permanentemente acessíveis.
- **I6 — Estabilidade de Foco do Dropdown**: Com a árvore DOM íntegra, o `FocusTrap` do Bootstrap 5 reconhece o `<select>` como filho válido de `trapElement`, eliminando qualquer evento de blur indesejado ao interagir com o menu nativo.
- **I7 — Imutabilidade de Backend**: Nenhuma rota (`GET` ou `POST`), método HTTP, validação ou retorno de controller é alterado.
