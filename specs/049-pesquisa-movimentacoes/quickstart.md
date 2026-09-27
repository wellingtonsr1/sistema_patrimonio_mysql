# Quickstart: Validação da Pesquisa no Fluxo Global de Movimentações

**Feature**: 049-pesquisa-movimentacoes  
**Branch**: `049-pesquisa-movimentacoes`  
**Date**: 2026-09-27  

Este guia detalha como executar os testes automatizados e validar manualmente o campo de pesquisa na página "Fluxo Global de Movimentações".

---

## 1. Pré-Requisitos

- Ambiente virtual Python 3.10 ativo com dependências instaladas.
- Banco de dados de testes SQLite em memória (padrão de execução da suíte `pytest`).
- Servidor de desenvolvimento rodando (caso queira validar visualmente via navegador).

---

## 2. Execução dos Testes Automatizados (Suíte Pytest)

Para rodar todos os testes de movimentação incluindo os novos cenários da pesquisa (Testes A ao J):

```bash
# Executar a suíte de testes de movimentação
pytest tests/test_movements.py -v

# Executar testes garantindo ausência de regressão geral de permissões
pytest tests/test_rbac.py -v
```

### Resultados Esperados:
- Todos os testes de criação, regras de transição, geração de termos e conferência de inventário devem passar com 100% de sucesso.
- Os novos testes cobrindo pesquisa por tombamento, descrição, colaborador, matrícula, local, tipo, operador, termo, combinações com filtros e estado vazio devem ser aprovados.

---

## 3. Roteiro de Validação Manual na Interface Web

1. **Iniciar a aplicação**:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

2. **Acessar a página**:
   - Faça login com usuário que possua permissão `movimentacao.visualizar` (ex.: `admin`).
   - Acesse o menu lateral: **Movimentações** (`/movements`).

3. **Cenários a Validar na Tela**:
   - **Tombamento**: Digite o número de um tombamento cadastrado (ex.: `PAT-0001`) e clique em **Filtrar**. Verifique se apenas as movimentações daquele equipamento são exibidas.
   - **Equipamento**: Digite parte do nome do bem (ex.: `Dell` ou `Notebook`) e clique em **Filtrar**.
   - **Colaborador / Matrícula**: Digite o nome de um colaborador ou matrícula (ex.: `Silva` ou `MAT-1001`).
   - **Local**: Digite o nome de uma sala ou setor (ex.: `TI` ou `Almoxarifado`).
   - **Tipo Combinado**: Digite um termo de busca e escolha um tipo no dropdown (ex.: "Transferência de Local"). Ambos os filtros devem ser respeitados.
   - **Limpar**: Clique no botão **Limpar** e confirme que a listagem geral retorna e a URL volta para `/movements`.
   - **Termo Inexistente**: Digite `TERMO_INEXISTENTE_XYZ` e clique em **Filtrar**. Verifique se o estado vazio exibe a mensagem amigável: *"Nenhuma movimentação encontrada para a pesquisa informada."* e o botão para limpar a busca.
