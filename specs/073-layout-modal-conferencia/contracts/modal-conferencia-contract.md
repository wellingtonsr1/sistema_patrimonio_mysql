# Contract — Modal de Registro de Conferência Patrimonial (073)

> Contrato de **apresentação estrutural e integridade semântica do DOM**. Define as regras de marcação, classes utilitárias, contenção de foco e responsividade do modal de conferência em `app/web/templates/inventarios/detail.html`.

---

## 1. Escopo e Localização

- **Template Alvo**: `app/web/templates/inventarios/detail.html`
- **Componente**: Modal de registro de conferência (`#modalConferir{{ item.id }}`)
- **Loop de Renderização**: `{% for item in expected_itens %}`
- **Condição de Exibição**: `{% if inv.status.value != 'ENCERRADO' and can_conferir %}`

---

## 2. Regras Estruturais de Apresentação

### RE-01 — Estrutura Hierárquica Estrita
O modal DEVE respeitar estritamente a hierarquia de contêineres do Bootstrap 5.3:
```html
<div class="modal fade" id="modalConferir{{ item.id }}" tabindex="-1" aria-hidden="true" aria-labelledby="modalLabel{{ item.id }}">
    <div class="modal-dialog modal-dialog-centered modal-dialog-scrollable">
        <div class="modal-content">
            <form method="post" action="/inventarios/{{ inv.id }}/conferir/{{ item.id }}"
                  {% if item.status.value != 'PENDENTE' %}onsubmit="return confirm('Este item já foi conferido. Registrar um novo resultado vai substituir o anterior. Continuar?')"{% endif %}>
                <div class="modal-header">
                    <h5 class="modal-title" id="modalLabel{{ item.id }}"><span class="tag-badge me-2">{{ item.asset.tag }}</span> {{ item.asset.name }}</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Fechar"></button>
                </div>
                <div class="modal-body">
                    <!-- Todo o conteúdo do formulário aqui dentro -->
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-ghost" data-bs-dismiss="modal">Cancelar</button>
                    <button type="submit" class="btn btn-primary">Registrar resultado</button>
                </div>
            </form>
        </div>
    </div>
</div>
```

### RE-02 — Rolagem Controlada via `.modal-dialog-scrollable`
- A classe `.modal-dialog-scrollable` DEVE estar presente no elemento `.modal-dialog`.
- O cabeçalho (`.modal-header`) e o rodapé (`.modal-footer`) DEVEM permanecer fixos e sempre visíveis.
- O corpo (`.modal-body`) DEVE gerenciar o overflow vertical (`overflow-y: auto; max-height: calc(100vh - ...)` gerenciado nativamente pelo Bootstrap).

### RE-03 — Padding Lateral Canônico
- O dropdown `<select>` e a área de texto `<textarea>` DEVEM residir no interior de `.modal-body`.
- A distância lateral mínima entre as bordas dos controles e a borda da janela modal DEVE ser exatamente a do padding do Bootstrap (`var(--bs-modal-padding) = 1rem` / 16px).

### RE-04 — Estabilidade de Foco do Dropdown
- O elemento `<select>` DEVE responder a eventos de clique com a abertura estável de sua lista nativa de opções.
- A interação não pode provocar emissão de evento de fechamento involuntário pelo `FocusTrap`.

---

## 3. Contrato de Campos do Formulário

| Campo / Elemento | Tag / Tipo | Atributos Obrigatórios | Associação de Rótulo |
|---|---|---|---|
| Rádio Encontrado | `input[type="radio"]` | `name="result"`, `value="ENCONTRADO"`, `required` | Rótulo implícito (`label.result-option`) dentro de `<fieldset>` |
| Rádio Local Diferente | `input[type="radio"]` | `name="result"`, `value="LOCAL_DIFERENTE"` | Rótulo implícito dentro de `<fieldset>` |
| Rádio Não Encontrado | `input[type="radio"]` | `name="result"`, `value="NAO_ENCONTRADO"` | Rótulo implícito dentro de `<fieldset>` |
| Rádio Sem Identificação | `input[type="radio"]` | `name="result"`, `value="SEM_IDENTIFICACAO"` | Rótulo implícito dentro de `<fieldset>` |
| Local onde foi encontrado | `select` | `name="found_location_id"`, `id="modalloc-{{ item.id }}"`, `class="form-select form-select-sm"` | `label[for="modalloc-{{ item.id }}"]` |
| Observação | `textarea` | `name="observation"`, `id="modalobs-{{ item.id }}"`, `class="form-control form-control-sm"`, `rows="2"` | `label[for="modalobs-{{ item.id }}"]` |
| Botão Cancelar | `button[type="button"]` | `class="btn btn-ghost"`, `data-bs-dismiss="modal"` | Texto visível "Cancelar" |
| Botão Registrar | `button[type="submit"]` | `class="btn btn-primary"` | Texto visível "Registrar resultado" |

---

## 4. Matriz de Verificação de Integridade

| Critério | Método de Verificação | Resultado Esperado |
|---|---|---|
| Balanço de tags `<div>` | Parser estático em `test_acessibilidade_estatica_069.py` e auditoria de AST | Balanço de tags neutro (0 divs órfãs) |
| Espaçamento dos inputs | Inspeção CSS no browser | `padding-left` e `padding-right` de `.modal-body` aplicados aos wrappers |
| Confinamento do rodapé | Inspeção de nó ancestral | `.modal-footer` é filho de `form` e de `.modal-content` |
| Unicidade de IDs | `test_acessibilidade_estatica_069.py::test_ids_unicos` | 0 IDs duplicados |
| Preservação de Rádio em Fieldset | `test_acessibilidade_estatica_069.py::test_resultado_da_conferencia_tem_fieldset` | Rádios contidos em `fieldset` com `legend` |
| Submissão HTTP | `POST /inventarios/{id}/conferir/{item_id}` | Código 303 (Redirect) e gravação do resultado |
