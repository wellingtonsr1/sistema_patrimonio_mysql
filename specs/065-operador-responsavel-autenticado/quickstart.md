# Guia de Validação Rápida (Quickstart): Feature 065

**Feature**: Operador Responsável Vinculado ao Usuário Autenticado  
**Branch**: `065-operador-responsavel-autenticado`  
**Date**: 2026-10-09  

---

## Cenários Práticos de Validação

Este guia descreve como validar o funcionamento da funcionalidade ponta a ponta após a implementação.

---

### Cenário 1: Validação Visual no Formulário Web

1. **Pré-requisito**: Iniciar o servidor (`python run.py`).
2. **Passos**:
   - Efetuar login com um usuário que possui nome completo definido (ex: `carlos.silva` / "Carlos Silva").
   - Navegar até a tela de nova movimentação: `/movements/new`.
3. **Resultado Esperado**:
   - O campo **"Operador Responsável"** exibe automaticamente `"Carlos Silva"`.
   - O campo está em estado de somente leitura (`readonly`), impedindo edições diretas pelo usuário.
   - Ao lado do rótulo, é exibida a indicação auxiliar `(Preenchido automaticamente)`.

---

### Cenário 2: Validação Anti-Spoofing (Gravação no Servidor)

1. **Passos**:
   - Submeter o formulário de movimentação via ferramenta de desenvolvimento (dev tools) ou script HTTP, enviando no corpo da requisição POST `operator_name="Operador Falso"`.
2. **Resultado Esperado**:
   - O servidor intercepta a requisição, ignora a string `"Operador Falso"` e grava a movimentação com a identidade real do usuário da sessão (`"Carlos Silva"`).
   - O histórico de movimentações (`/movements`) e o log de auditoria exibem `"Carlos Silva"`.

---

### Cenário 3: Execução da Suíte de Testes Automatizados

1. **Comando**:
   ```powershell
   .venv\Scripts\pytest.exe tests/test_movements.py -k "operator"
   ```
2. **Resultado Esperado**:
   - Todos os testes referentes a operador e movimentações passam com sucesso (`PASSED`).
