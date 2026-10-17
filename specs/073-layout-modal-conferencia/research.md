# Research: Correção de Layout, Espaçamento e Dimensionamento do Modal de Conferência Patrimonial

**Feature**: `073-layout-modal-conferencia`  
**Status**: Concluído (Fase 0)  
**Spec de Referência**: `specs/073-layout-modal-conferencia/spec.md`

---

## 1. Pesquisa e Diagnóstico Técnico

### 1.1 Investigação da Causa Raiz
Para atender às diretrizes pré-implementação exigidas pela especificação:
1. **Template identificado**: [`app/web/templates/inventarios/detail.html`](file:///home/wellington/IA/sistema_patrimonio_mysql/app/web/templates/inventarios/detail.html#L407-L476).
2. **Origem da falha estrutural**:
   - No `commit 18c7c5608dfe4d129507fab465fbf0c18cbe94f0` (implementação da Spec 069), o container `<div class="d-grid gap-2 mb-3">` contendo as 4 opções de rádio foi substituído por `<fieldset class="d-grid gap-2 mb-3" style="border:0;padding:0;margin:0;">` para agrupamento semântico acessível.
   - Contudo, a tag de fechamento correspondente `</div>` original foi mantida inadvertidamente na linha 451, imediatamente antes de `</fieldset>`.
   - Um segundo rótulo duplicado `<label class="form-label fw-semibold">Resultado da conferência <span class="text-danger">*</span></label>` foi também introduzido na linha 432.
3. **Análise de parsing HTML5**:
   - De acordo com o algoritmo de construção de árvore da especificação HTML5 (implementado por Chromium, Gecko e WebKit), uma tag finalizadora `</div>` encontrada dentro de um `<fieldset>` força o fechamento do elemento `fieldset` e de todos os elementos abertos até o ancestral `div` mais próximo.
   - O ancestral `div` mais próximo era justamente `<div class="modal-body">`.
   - Com isso, `<div class="modal-body">` era fechado prematuramente na linha 451.
4. **Consequências no Layout e CSS**:
   - Os elementos seguintes:
     - `<div class="mb-2">` contendo o rótulo e o dropdown `<select name="found_location_id">`;
     - `<div>` contendo o rótulo e a área de texto `<textarea name="observation">`;
     ficaram posicionados como filhos diretos de `<form>` ou `.modal-content`.
   - No Bootstrap 5.3, a regra CSS de padding lateral reside em `.modal-body`:
     ```css
     .modal-body {
       position: relative;
       flex: 1 1 auto;
       padding: var(--bs-modal-padding); /* 1rem ou 1.5rem */
     }
     ```
   - Estando fora de `.modal-body`, os wrappers dos campos não recebiam padding. Como `.form-select` e `.form-control` possuem `width: 100%`, os elementos esticavam por toda a largura do contêiner modal de borda a borda.
5. **Consequências no Rodapé e no DOM**:
   - Na linha 466, a tag `</div>` que originalmente fecharia `modal-body` passou a fechar `<div class="modal-content">`.
   - O rodapé `<div class="modal-footer">` foi ejetado para fora de `.modal-content`, ficando direto sob `.modal-dialog`.
   - Ao final do bloco do modal (linhas 471-474), existiam três tags de fechamento `</div>`, gerando uma tag `</div>` órfã para cada item iterado em `expected_itens`.
   - Em uma listagem com 20 itens, 20 tags `</div>` excedentes eram emitidas, fechando prematuramente `<main id="conteudo-principal">`, `<body>` e `<html>`.
6. **Mecanismo da Falha "Abre e Fecha" do Dropdown**:
   - O componente modal do Bootstrap 5 implementa uma trava de foco (`FocusTrap`, classe `sn` no bundle JS) quando o modal está aberto (`tabindex="-1"` e listener `focusin.bs.focustrap`).
   - Quando o DOM está quebrado e o `<select>` reside fora do contêiner formal esperado ou com a árvore do documento corrompida, ao clicar no `<select>` para expandir o menu pop-up nativo, o evento de foco emitido não é corretamente reconhecido como pertencente a `trapElement`.
   - A função `_handleFocusin(t)` detecta que o foco "escapou" e aciona imediatamente `i[0].focus()`, transferindo o foco de volta para o primeiro elemento focável do modal (`.btn-close`).
   - A perda de foco (`blur`) no `<select>` provoca o fechamento imediato do dropdown suspenso, gerando o efeito relatado pelo usuário de "abre e fecha".

---

## 2. Decisões Técnicas e Racional

### Decisão 1: Restauração da Hierarquia Canônica do Bootstrap 5.3
- **Escolha**:
  ```html
  <div class="modal fade" id="modalConferir{{ item.id }}" tabindex="-1" aria-hidden="true" aria-labelledby="modalLabel{{ item.id }}">
      <div class="modal-dialog modal-dialog-centered modal-dialog-scrollable">
          <div class="modal-content">
              <form method="post" action="/inventarios/{{ inv.id }}/conferir/{{ item.id }}" ...>
                  <div class="modal-header">
                      <h5 class="modal-title" id="modalLabel{{ item.id }}">...</h5>
                      <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Fechar"></button>
                  </div>
                  <div class="modal-body">
                      <!-- 1. Alerta de re-conferência se aplicável -->
                      <!-- 2. Local cadastrado -->
                      <!-- 3. Rótulo e Fieldset de resultado (4 radios) -->
                      <!-- 4. Dropdown de Local onde foi encontrado -->
                      <!-- 5. Campo de Observação -->
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
- **Racional**: Esta é a estrutura recomendada oficialmente pelo Bootstrap 5 e consistente com os demais modais do sistema (`modalEncerrar` em `detail.html`, `modalBackupConfig` em `backups.html` e `modalColetaOffline` em `offline.html`).
- **Alternativas descartadas**:
  - *Adicionar padding inline/customizado via CSS no wrapper*: Rejeitado porque não resolveria a corrupção do DOM nem a ejeção do rodapé nem o problema do FocusTrap.

---

### Decisão 2: Uso da Classe `.modal-dialog-scrollable`
- **Escolha**: Incluir `modal-dialog-scrollable` no contêiner `.modal-dialog`.
- **Racional**:
  - A classe nativa do Bootstrap 5 adiciona `overflow-y: auto` exclusivamente no `.modal-body`, fixando o cabeçalho (`.modal-header`) no topo e o rodapé (`.modal-footer`) na base da janela modal.
  - Elimina o risco de os botões "Cancelar" e "Registrar resultado" ficarem cortados quando a janela do navegador estiver com altura reduzida (ex: 600px em notebooks ou com ferramentas de desenvolvedor abertas).
- **Alternativas descartadas**:
  - *Alturas fixas em pixels via CSS*: Rejeitado por inflexibilidade em telas de resoluções diferentes.
  - *Regras customizadas de media query*: Rejeitado para evitar redundância com utilitários já presentes no Bootstrap 5.3.

---

### Decisão 3: Preservação Estrita das Regras da Spec 069 (Acessibilidade)
- **Escolha**:
  - Manter o grupo de rádios dentro de `<fieldset class="d-grid gap-2 mb-3" style="border:0;padding:0;margin:0;">` com `<legend class="visually-hidden">Resultado da conferência</legend>`.
  - Manter o rótulo com `for="modalloc-{{ item.id }}"` apontando para o `<select id="modalloc-{{ item.id }}">`.
  - Manter o rótulo com `for="modalobs-{{ item.id }}"` apontando para o `<textarea id="modalobs-{{ item.id }}">`.
  - Manter um único `<label class="form-label fw-semibold">Resultado da conferência <span class="text-danger">*</span></label>`, eliminando a linha duplicada.
- **Racional**: Mantém 100% de aprovação na suíte de testes automatizados `tests/test_acessibilidade_estatica_069.py`.

---

### Decisão 4: Zero Dependências Externas Novas
- **Escolha**: O elemento `<select>` continuará sendo o componente nativo HTML estilizado pela classe `.form-select form-select-sm` do Bootstrap.
- **Racional**: Com a árvore DOM íntegra e encapsulada dentro de `.modal-body`, o componente nativo é extremamente estável, rápido e totalmente compatível com navegadores desktop e móveis, sem risco de conflito de z-index ou dependências de scripts pesados (Select2, Choices, etc.).
