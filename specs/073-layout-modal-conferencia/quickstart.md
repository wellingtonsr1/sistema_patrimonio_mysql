# Quickstart: Validação da Correção de Layout do Modal de Conferência (073)

**Feature**: `073-layout-modal-conferencia`  
**Objetivo**: Roteiro executável de validação ponta a ponta das correções de espaçamento, dimensionamento e estabilidade do modal de conferência patrimonial.

---

## 1. Pré-requisitos e Inicialização

Certifique-se de que o ambiente de desenvolvimento está pronto e inicie a aplicação:

```bash
# Ativar o ambiente virtual e iniciar a aplicação
.venv/bin/python run.py
```
Acesse a aplicação no navegador em `http://localhost:8000`. Faça login com o usuário administrador ou um operador com permissão `inventario.conferir`.

---

## 2. Cenários de Teste Manual

### Cenário 1: Verificação Visual e Espaçamento Interno em Desktop
1. Navegue até a tela de Inventários (`/inventarios`).
2. Clique em um inventário com status **Em Andamento** ou crie um novo inventário para testes.
3. Na tabela de **Bens esperados**, localize qualquer item pendente e clique no botão de conferência (ícone `bi-check2-square`).
4. **Verificações visuais**:
   - [ ] O modal abre centralizado na tela.
   - [ ] O campo "Local onde foi encontrado (para local diferente)" (`<select>`) possui recuo lateral de no mínimo `16px` em relação às bordas da janela modal (não encosta na borda).
   - [ ] O campo de texto "Observação" (`<textarea>`) respeita o mesmo recuo lateral, alinhando-se perfeitamente com o campo acima.
   - [ ] Há apenas um rótulo "Resultado da conferência *" (sem repetição).
   - [ ] Os botões "Cancelar" e "Registrar resultado" estão perfeitamente visíveis no rodapé, alinhados à direita e dentro da moldura do modal.

---

### Cenário 2: Estabilidade e Interação com o Dropdown de Localização
1. Com o modal de conferência aberto, clique na opção de rádio **"🟡 Encontrado em local diferente"**.
2. Clique sobre o campo `<select>` "Local onde foi encontrado".
3. **Verificações de interação**:
   - [ ] O menu suspenso de locais abre e **permanece aberto** (não fecha sozinho).
   - [ ] Role a lista de locais e selecione um local diferente.
   - [ ] O local selecionado é exibido no campo e o foco permanece estável.
   - [ ] O modal não fecha e o foco não é forçado de volta para o botão fechar ("X").

---

### Cenário 3: Altura Reduzida da Janela e Rolagem Controlada
1. Redimensione a janela do seu navegador ou ative o modo responsivo do DevTools (F12) configurando a altura para **500px** ou **600px**.
2. Abra o modal de conferência.
3. **Verificações de responsividade**:
   - [ ] O título do modal e o botão fechar ("X") permanecem fixos no topo.
   - [ ] Os botões "Cancelar" e "Registrar resultado" permanecem fixos e visíveis na base do modal, sem serem cortados pela margem da tela.
   - [ ] O corpo do modal apresenta barra de rolagem vertical suave para acessar as opções de rádio, o dropdown e a observação.
   - [ ] Não ocorre nenhuma barra de rolagem horizontal.

---

### Cenário 4: Registro da Conferência e Cancelamento
1. Preencha uma observação: `Conferência de teste - layout validado`.
2. Clique no botão **"Registrar resultado"**.
3. **Verificação**:
   - [ ] O modal fecha suavemente.
   - [ ] A página recarrega com o status do bem atualizado.
   - [ ] A linha na tabela exibe a observação gravada.
4. Abra o modal de outro item e clique em **"Cancelar"** (ou pressione a tecla `Esc`).
5. **Verificação**:
   - [ ] O modal é fechado sem submissão e o backdrop escuro desaparece completamente.

---

## 3. Testes Automatizados de Regressão

Execute a suíte automatizada focada nos testes de acessibilidade e inventário:

```bash
# 1. Teste de Acessibilidade Estática (Spec 069: fieldset, labels, IDs únicos)
.venv/bin/pytest tests/test_acessibilidade_estatica_069.py

# 2. Testes de Regra de Negócio de Inventário
.venv/bin/pytest tests/test_inventario.py tests/test_inventario_reconferencia_ui.py
```

### Critério de Sucesso dos Testes Automatizados:
- `tests/test_acessibilidade_estatica_069.py`: 17 passed (ou 16 passed, 1 skipped).
- `tests/test_inventario.py`: 32 passed.
- `tests/test_inventario_reconferencia_ui.py`: 6 passed.
- **Total**: 100% de sucesso sem falhas de regressão.
