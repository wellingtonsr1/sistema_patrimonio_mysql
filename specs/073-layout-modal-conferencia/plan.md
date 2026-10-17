# Implementation Plan: Correção de Layout, Espaçamento e Dimensionamento do Modal de Conferência Patrimonial

**Branch**: `073-layout-modal-conferencia` | **Date**: 2026-10-17 | **Spec**: [specs/073-layout-modal-conferencia/spec.md](spec.md)

**Input**: Feature specification from `specs/073-layout-modal-conferencia/spec.md`

---

## Summary

O modal de conferência patrimonial (`#modalConferir{{ item.id }}` em `app/web/templates/inventarios/detail.html`) apresentava campos encostados nas bordas laterais sem padding, rodapé de botões ejetado para fora da moldura do modal, instabilidade no dropdown de locais (fechamento instantâneo via FocusTrap do Bootstrap devido à árvore DOM desbalanceada) e falta de rolagem vertical controlada em viewports compactos.

A solução técnica consiste em restaurar cirurgicamente a hierarquia canônica do Bootstrap 5.3 (`.modal > .modal-dialog.modal-dialog-scrollable > .modal-content > form > (.modal-header + .modal-body + .modal-footer)`), eliminando uma tag residual `</div>` deixada pela Spec 069 que fechava prematuramente o `.modal-body`, removendo um rótulo duplicado e adicionando `.modal-dialog-scrollable` para manter cabeçalho e botões fixos com rolagem interna suave no corpo do formulário.

---

## Technical Context

**Language/Version**: Python 3.10+ (Jinja2 Templates, HTML5)  
**Primary Dependencies**: Bootstrap 5.3.3 (CSS e JS bundle local), Bootstrap Icons 1.11.3  
**Storage**: N/A (zero alteração de banco de dados ou schemas)  
**Testing**: `pytest` com TestClient FastAPI e parser estático de HTML (stdlib `html.parser`)  
**Target Platform**: Navegadores Web modernos (Chrome, Firefox, Edge, Safari) em desktop e dispositivos móveis  
**Project Type**: Web Application (Jinja2 + Bootstrap frontend com FastAPI backend)  
**Performance Goals**: Renderização instantânea do modal sem flicker ou reflow indesejado  
**Constraints**: Zero dependências externas adicionais; zero alterações em rotas, backend ou banco de dados; preservação estrita das regras de acessibilidade da Spec 069  
**Scale/Scope**: Limitado cirurgicamente ao modal `#modalConferir{{ item.id }}` no template `app/web/templates/inventarios/detail.html`

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio Constitucional | Avaliação de Conformidade | Status |
|---|---|---|
| **I. Preservação do Sistema Existente** | Modificação incremental restrita ao template do modal. Nenhum outro módulo ou tela é tocado. | **PASSED** |
| **II. Arquitetura em Camadas** | Nenhuma regra de negócio colocada em template. Apenas estrutura semântica de apresentação HTML. | **PASSED** |
| **III. Regras de Negócio nos Services** | As submissões continuam consumindo a rota e o `InventarioService` existente. | **PASSED** |
| **IV. Integridade Patrimonial** | O modal de conferência mantém seu propósito estrito de aferição física sem alteração cadastral do patrimônio. | **PASSED** |
| **V. Integridade do Inventário** | As quatro opções de conferência e seus payloads permanecem idênticos. | **PASSED** |
| **VI. Segurança por Padrão** | A condição `can_conferir` e a autenticação do formulário são estritamente preservadas. | **PASSED** |

---

## Project Structure

### Documentation (this feature)

```text
specs/073-layout-modal-conferencia/
├── spec.md              # Especificação de requisitos funcionais e visuais
├── plan.md              # Este plano de implementação técnica
├── research.md          # Diagnóstico da causa raiz e decisões de arquitetura
├── data-model.md        # Modelo da árvore DOM e invariantes
├── quickstart.md        # Roteiro de validação manual e automatizada
├── checklists/
│   └── requirements.md  # Checklist de qualidade da especificação
└── contracts/
    └── modal-conferencia-contract.md # Contrato estrutural e de apresentação
```

### Source Code (affected files)

```text
app/web/templates/inventarios/
└── detail.html          # Template com o modal de conferência (linhas 407–476)
```

---

## Execution Workflow

### Fase 1: Preparação e Guarda de Regressão
- Confirmar baseline de testes verdes para acessibilidade e inventário:
  - `tests/test_acessibilidade_estatica_069.py`
  - `tests/test_inventario.py`
  - `tests/test_inventario_reconferencia_ui.py`

### Fase 2: Correção Cirúrgica no Template (`detail.html`)
1. Remover o `<label>` duplicado na linha 432:
   ```html
   <!-- Manter apenas uma ocorrência do rótulo -->
   <label class="form-label fw-semibold">Resultado da conferência <span class="text-danger">*</span></label>
   ```
2. Remover a tag residual `</div>` na linha 451 (que precedia `</fieldset>`).
3. Adicionar a classe `.modal-dialog-scrollable` ao contêiner `.modal-dialog`.
4. Assegurar que os blocos `<div class="mb-2">` (select de localização) e `<div>` (textarea de observação) fiquem devidamente situados antes do fechamento de `<div class="modal-body">`.
5. Assegurar que `<div class="modal-footer">` fique encapsulado no interior de `<form>` e `<div class="modal-content">`.
6. Eliminar a tag `</div>` órfã ao final do loop do modal (linha 474).

### Fase 3: Verificação e Testes
1. Execução da suíte de testes estáticos `test_acessibilidade_estatica_069.py` para garantir conformidade de fieldset, labels e unicidade de IDs.
2. Execução da suíte de inventário para garantir envio e gravação sem regressão.
3. Validação manual com o roteiro de `quickstart.md` (desktop, tela reduzida, dropdown estável).
