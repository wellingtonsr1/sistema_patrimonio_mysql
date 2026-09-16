# Research: Correção das Regras de Movimentação Patrimonial

**Feature**: 005-correcao-regras-movimentacao | **Date**: 2026-09-15
**Base**: Análise do código-fonte existente (`app/services/movement_service.py`, `app/web/routes.py`, `app/api/movements_api.py`, `app/models/movement.py`, `app/models/enums.py`, `tests/test_movements.py`). Cada decisão abaixo foi confirmada diretamente na arquitetura em camadas do projeto.

---

## R1 — Como resolver e comparar a combinação Origem x Destino (Local e Responsável)

**Decision**:
A validação de alteração patrimonial efetiva deve ser executada de forma atômica no início de `MovementService.create_movement` (linhas 25–60 de `app/services/movement_service.py`).
Para isso, os valores efetivos de destino são unificados antes de qualquer aplicação de regra:
- `origin_location_id = asset.location_id`
- `origin_custodian_id = asset.custodian_id`
- `effective_dest_location_id = data.destination_location_id if (data.destination_location_id and data.destination_location_id > 0) else origin_location_id`
- `effective_dest_custodian_id`:
  - Se `m_type == MovementType.RETURN_STOCK`: `None` (Estoque).
  - Se `m_type == MovementType.WRITE_OFF`: `None` (Baixa desvincula custódia).
  - Se `m_type == MovementType.ALLOCATION`: `data.destination_custodian_id` (obrigatório).
  - Se `m_type == MovementType.TRANSFER`: `data.destination_custodian_id` se fornecido, senão mantém `origin_custodian_id`.
  - Outros tipos (ex: manutenção): mantêm as regras específicas existentes.

Com os quatro valores resolvidos, calculam-se os booleanos de alteração:
- `is_location_same = (effective_dest_location_id == origin_location_id)`
- `is_custodian_same = (effective_dest_custodian_id == origin_custodian_id)`

Caso `is_location_same` e `is_custodian_same` sejam ambos verdadeiros:
- Em `ALLOCATION` ou `TRANSFER`: bloquear imediatamente lançando `ValueError("Nenhuma alteração efetiva detectada. O local e o colaborador de destino são idênticos à situação atual do bem.")`.
- Em `RETURN_STOCK`: caso o bem já esteja no estoque (`origin_custodian_id is None`) e o local não tenha mudado (`is_location_same`), bloquear com `ValueError("O equipamento já se encontra no estoque neste local.")`.

**Rationale**:
- Na implementação atual (`movement_service.py:136`), quando `destination_location_id` é `None` (como ocorre quando o usuário seleciona "-- Manter Local Atual --" no formulário web), o sistema atribui silenciosamente o local anterior sem validar se houve mudança efetiva.
- A comparação dos IDs efetivos elimina a ambiguidade de valores `None` ou `0` vindos de formulários ou payloads parciais.
- Centralizar essa resolução no service respeita o Princípio II (Camadas) e Princípio III (Regras de Negócio nos Services).

**Alternativas consideradas**:
- *Validar no frontend com JavaScript*: Rejeitada como controle principal, pois violaria o Princípio VI (validação de segurança e integridade sempre no backend) e não protegeria chamadas via API REST (`/api/v1/movements`) ou CLI (`app/cli.py`). Validação no backend é obrigatória.
- *Validar no schema Pydantic (`MovementCreate`)*: Rejeitada, pois o schema Pydantic não tem acesso ao estado atual do bem no banco de dados (`asset.location_id` e `asset.custodian_id`) sem acoplamento indevido com a sessão de banco.

---

## R2 — Diferenciação rigorosa entre Alocação / Cautela e Transferência de Setor / Filial

**Decision**:
Aplicar estritamente a matriz de regras para diferenciar a finalidade de cada tipo:

1. **Local igual E Responsável diferente (`is_location_same and not is_custodian_same`)**:
   - Tipo correto: `MovementType.ALLOCATION` (`ALOCACAO_CAUTELA`).
   - Se o operador solicitar `MovementType.TRANSFER` (`TRANSFERENCIA_LOCAL`):
     Rejeitar lançando `ValueError("Para transferência de setor/filial é obrigatório selecionar um local de destino diferente do atual. Para alterar apenas o colaborador responsável, utilize Alocação / Cautela.")`.
   - Se solicitar `MovementType.ALLOCATION`: Permitir. Exige `destination_custodian_id`. Atualiza o responsável, mantém o local, gera termo de responsabilidade (`TR-...`) e define status `IN_USE`.

2. **Local diferente E Responsável igual (`not is_location_same and is_custodian_same`)**:
   - Tipo correto: `MovementType.TRANSFER` (`TRANSFERENCIA_LOCAL`).
   - Se o operador solicitar `MovementType.ALLOCATION`:
     Rejeitar lançando `ValueError("O colaborador informado já é o responsável atual pelo equipamento. Para transferir o equipamento de local mantendo o mesmo responsável, utilize Transferência de Setor / Filial.")` ou, se o bem estava no estoque, `ValueError("Para alocação/cautela é obrigatório selecionar um colaborador de destino.")`.
   - Se solicitar `MovementType.TRANSFER`: Permitir. Exige `destination_location_id`. Atualiza o local, preserva o custodiante (`origin_custodian_id`), e grava corretamente no registro de movimentação `destination_custodian_id = origin_custodian_id` (corrigindo o bug atual que salvava `None`).

3. **Local diferente E Responsável diferente (`not is_location_same and not is_custodian_same`)**:
   - A operação representa entrega do bem a um novo colaborador em outra localidade.
   - Tipo correto: `MovementType.ALLOCATION` (`ALOCACAO_CAUTELA`).
   - Se o operador solicitar `MovementType.TRANSFER` informando um novo colaborador diferente:
     Rejeitar lançando `ValueError("A entrega do equipamento a um novo colaborador deve ser registrada como Alocação / Cautela para emissão do Termo de Responsabilidade.")`.
   - Se solicitar `MovementType.ALLOCATION`: Permitir. Atualiza atomicamente `asset.location_id = effective_dest_location_id` e `asset.custodian_id = effective_dest_custodian_id`, gerando o termo de responsabilidade (`TR-...`).

**Rationale**:
- Alocação e Transferência possuem significados jurídicos e patrimoniais distintos: Alocação gera Termo de Responsabilidade/Cautela assinado pelo colaborador (guarda pessoal), enquanto Transferência move a carga patrimonial da dependência física/contábil (sala/setor/filial).
- Na implementação atual, era permitido fazer Transferência sem mudar de local, ou mudar de responsável sem gerar termo. A diferenciação rígida garante conformidade com as regras do sistema.

**Alternativas consideradas**:
- *Permitir Transferência trocar colaborador sem emitir termo*: Rejeitada. Criaria bens em posse de colaboradores sem o devido termo de responsabilidade assinado.
- *Permitir Alocação sem colaborador*: Rejeitada. Conceitualmente uma alocação a colaborador exige a identificação do colaborador que assume a custódia.

---

## R3 — Tratamento do ciclo de vida com Estoque e Devolução

**Decision**:
Regras específicas para itens em estoque:
1. **Saída de Estoque para Colaborador**:
   - Ocorre quando `origin_custodian_id is None` e `effective_dest_custodian_id is not None`.
   - Deve ser registrado obrigatoriamente como `MovementType.ALLOCATION`.
   - O status do ativo transita de `AVAILABLE` para `IN_USE`.
   - Gera Termo de Responsabilidade (`TR-...`).
2. **Estoque para Nenhum (sem responsável)**:
   - Se o local de destino for diferente (`not is_location_same`): Trata-se de uma `Transferência de Setor / Filial` entre estoques/almoxarifados. Deve ser aprovado como `TRANSFER`, mantendo `custodian_id = None` e status `AVAILABLE`.
   - Se o local for idêntico (`is_location_same`): Bloquear (nenhuma alteração efetiva).
   - Tentativa de registrar como `ALLOCATION`: Bloquear (Alocação exige colaborador).
   - Tentativa de registrar como `RETURN_STOCK`: Bloquear se o bem já estiver disponível no estoque.
3. **Devolução ao Estoque (`RETURN_STOCK`)**:
   - Exige que o bem esteja atribuído a um colaborador (`origin_custodian_id is not None`) OU venha de manutenção.
   - Se o bem já estiver sem colaborador e no mesmo local: `ValueError("O equipamento já se encontra no estoque neste local.")`.
   - Na devolução, `asset.custodian_id` é anulado (`None`), status passa para `AVAILABLE`, e `destination_custodian_name` é padronizado como "Almoxarifado / Estoque". Gera termo de devolução.

**Rationale**:
- Elimina inconsistências onde bens eram devolvidos ao estoque consecutivas vezes ou bens sem colaborador geravam termos vazios.

**Alternativas consideradas**:
- *Permitir Devolução ao Estoque alterar apenas localidade*: Se o objetivo for apenas mudar o local de um bem que já está no estoque, o tipo adequado do patrimônio é Transferência de Setor / Filial, não Devolução.

---

## R4 — Tratamento na Interface Web e na API REST

**Decision**:
1. **API REST (`app/api/movements_api.py`)**:
   - Captura `ValueError` lançado por `MovementService.create_movement` e retorna `HTTP 400 Bad Request` com a mensagem exata do erro no campo `detail`.
2. **Rota Web (`app/web/routes.py`)**:
   - Captura `ValueError` e redireciona para a tela de movimentação com o parâmetro `error`:
     `RedirectResponse(url=f"/movements/new?asset_id={asset_id}&error={quote(str(err))}", status_code=status.HTTP_303_SEE_OTHER)`.
   - Na tela `app/web/templates/movements/new.html`, o alerta já existente exibe a mensagem retornada no topo do formulário.
3. **Formulário Web (`app/web/templates/movements/new.html`)**:
   - Manter as 4 opções de tipo de movimentação existentes (`ALOCACAO_CAUTELA`, `TRANSFERENCIA_LOCAL`, `DEVOLUCAO_ESTOQUE`, `BAIXA_DESCARTE`).
   - Melhorar os textos de auxílio (tooltips/legendas) nas opções para deixar clara a finalidade de cada uma:
     - Alocação: Entrega ou troca de colaborador responsável (gera Termo de Cautela).
     - Transferência: Mudança de setor, filial ou sala (mantém o responsável ou bem em estoque).
     - Devolução: Retorno de bem em uso para o estoque.
     - Baixa: Retirada definitiva por descarte ou perda.

**Rationale**:
- Consistência total entre canais de entrada (Web, API e CLI) sem duplicação de regras (Princípio III da Constituição).

---

## R5 — Preservação do Inventário Patrimonial e Trilha Histórica (Princípios IV e V)

**Decision**:
- Nenhuma alteração DDL ou migração no banco de dados.
- Nenhuma alteração em registros históricos já salvos na tabela `movements`.
- O módulo de Inventário (`app/services/inventario_service.py`) não é modificado e continua operando estritamente como conferência física independente (Princípio V).
- Quando uma divergência de inventário (ex.: bem conferido em `LOCAL_DIFERENTE`) for regularizada pelo operador via tela de movimentações, a operação obedecerá à nova matriz de movimentação (`Transferência de Setor / Filial` para o local correto), mantendo total coerência do ecossistema.

**Rationale**:
- Conformidade estrita com os Princípios I, IV, V e VII da Constituição do SisPatrimônio Pro.
