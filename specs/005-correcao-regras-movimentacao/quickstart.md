# Quickstart: Correção das Regras de Movimentação Patrimonial

**Feature**: 005-correcao-regras-movimentacao | **Date**: 2026-09-15
Protocolo de validação executável, ponta a ponta, das novas regras e bloqueios da matriz de movimentação patrimonial.

---

## Pré-requisitos

- Ambiente de desenvolvimento ativo com Python 3.10+ e dependências instaladas (`pip install -r requirements.txt`).
- Banco de dados de testes configurado (SQLite em memória durante pytest, ou MariaDB em desenvolvimento).

---

## 1. Suíte Automatizada (Validação Primária)

Execute a suíte existente para certificar que não há regressões, seguida pelos testes específicos da matriz de movimentação:

```bash
# Valida se toda a suíte de testes permanece verde (Princípio VIII)
pytest tests/test_movements.py -v

# Execução da suíte completa de testes do sistema
pytest -v
```

### Casos de Teste Essenciais a serem Validados:
1. **Bloqueio por dados idênticos (US1)**: Tentativa de mover bem mantendo o mesmo local e o mesmo responsável deve levantar `ValueError` com mensagem amigável e não gravar registro.
2. **Alocação no mesmo local (US2)**: Alocar bem para novo colaborador mantendo o setor/departamento atual deve ter sucesso, atualizar custodiante e emitir Termo de Responsabilidade.
3. **Bloqueio de transferência sem mudança de local (US2)**: Tentar registrar Transferência de Setor mantendo o local atual deve ser bloqueado com mensagem orientando o uso de Alocação / Cautela.
4. **Transferência mantendo responsável (US3)**: Transferir bem para novo setor/filial mantendo o mesmo colaborador deve atualizar o local, preservar o responsável e gravar histórico com o custodiante correto.
5. **Transferência de item em estoque (US3)**: Transferir bem sem custodiante entre locais deve atualizar o local e manter status Disponível.
6. **Alocação com mudança de local e responsável (US4)**: Mover bem para outro local sob novo custodiante como Alocação deve atualizar local e responsável atomicamente e emitir termo.
7. **Bloqueio de transferência com troca de responsável (US4)**: Tentar registrar Transferência com novo colaborador diferente deve ser rejeitado orientando Alocação / Cautela.
8. **Devolução redundante de estoque (US5)**: Tentar devolver bem que já está sem colaborador no mesmo local deve ser bloqueado.

---

## 2. Validação Manual via API REST (`POST /api/v1/movements`)

### 2.1 Teste de Bloqueio por Dados Idênticos (Cenário Inválido)
```bash
curl -X POST http://localhost:8000/api/v1/movements \
  -H "Content-Type: application/json" \
  -H "Cookie: session_token=<SEU_TOKEN_ADMIN>" \
  -d '{
    "asset_id": 1,
    "movement_type": "TRANSFERENCIA_LOCAL",
    "destination_location_id": 1,
    "reason": "Tentativa de mover para o mesmo local",
    "operator_name": "Auditor"
  }'
```
**Resultado Esperado**: `HTTP 400 Bad Request`
```json
{
  "detail": "Para transferência de setor/filial é obrigatório selecionar um local de destino diferente do atual. Para alterar apenas o colaborador responsável, utilize Alocação / Cautela."
}
```

### 2.2 Teste de Alocação no Mesmo Local (Cenário Válido)
```bash
curl -X POST http://localhost:8000/api/v1/movements \
  -H "Content-Type: application/json" \
  -H "Cookie: session_token=<SEU_TOKEN_ADMIN>" \
  -d '{
    "asset_id": 1,
    "movement_type": "ALOCACAO_CAUTELA",
    "destination_custodian_id": 2,
    "reason": "Atribuição a novo colaborador do departamento",
    "operator_name": "Gestor TI"
  }'
```
**Resultado Esperado**: `HTTP 201 Created`, com `term_code` gerado (`TR-2026-XXXXX`), status `EM_USO` e novo responsável atribuído.

---

## 3. Validação Manual via Interface Web (`/movements/new`)

1. Acesse `http://localhost:8000/movements/new?asset_id=1`.
2. Observe o local e responsável atuais exibidos no cabeçalho do bem.
3. Selecione a opção **"Alocação a Colaborador"** e deixe o mesmo colaborador atual selecionado.
4. Clique em **"Registrar Movimentação"**.
5. **Verificação**: A página deve recarregar exibindo o alerta de erro em banner vermelho informando:
   `Nenhuma alteração efetiva detectada. O local e o colaborador de destino são idênticos aos atuais.`
6. O histórico do equipamento (`/assets/{id}`) não deve conter nenhum novo registro.
