# Feature Specification: Correção das Regras de Movimentação Patrimonial

**Feature Branch**: `005-correcao-regras-movimentacao`
**Created**: 2026-09-15
**Status**: Draft

**Input**:
"SPEC — CORREÇÃO DAS REGRAS DE MOVIMENTAÇÃO PATRIMONIAL.

Corrigir a lógica dos tipos de movimentação existentes no SisPatrimônio Pro para que cada movimentação represente corretamente a alteração patrimonial realizada.

A correção deve:

* impedir movimentações sem alteração efetiva;
* diferenciar corretamente Alocação/Cautela de Transferência de Setor/Filial;
* permitir mudança de responsável sem exigir mudança de local;
* permitir mudança de local sem exigir mudança de responsável;
* tratar corretamente operações em que local e responsável mudam simultaneamente;
* preservar o histórico existente;
* preservar as movimentações válidas;
* manter o funcionamento atual do Inventário;
* fazer somente as alterações necessárias.

Não criar um novo tipo de movimentação.

Não refatorar o sistema de forma ampla.

A matriz de movimentação deve ser determinística e baseada na comparação entre o estado atual do bem e os dados de destino informados pelo operador."

---

## User Scenarios & Testing

### User Story 1 - Bloqueio de movimentações sem alteração efetiva

**Priority**: P1

Um operador do patrimônio tenta registrar uma movimentação de um bem patrimonial, mas os dados de destino informados são rigorosamente iguais à situação atual do equipamento: mesmo local e mesmo responsável.

O sistema deve detectar que não existe alteração patrimonial efetiva, bloquear o registro, exibir uma mensagem clara e não gravar nenhuma nova movimentação, termo ou alteração no Asset.

#### Independent Test

Selecionar um bem e informar exatamente o mesmo local e o mesmo responsável já cadastrados.

Verificar:

* operação rejeitada;
* mensagem de validação apresentada;
* nenhum novo Movement criado;
* nenhum novo termo criado;
* nenhum campo patrimonial alterado;
* histórico anterior preservado integralmente.

#### Acceptance Scenarios

1. **Given** um bem localizado no "RH" sob responsabilidade do colaborador "João", **When** o operador tenta movimentar o bem para "RH" com "João" como responsável, **Then** o sistema bloqueia a operação informando que não houve alteração efetiva.

2. **Given** um bem no "Estoque de TI" sem responsável, **When** o operador informa o mesmo local e nenhum responsável, **Then** o sistema bloqueia a operação.

3. **Given** uma operação bloqueada por origem e destino idênticos, **When** o operador consulta o histórico, **Then** nenhum novo Movement ou termo é encontrado.

---

# Matriz Normativa de Movimentação

A aplicação da matriz deve ser determinística.

A comparação deve considerar:

* `location_id` atual;
* `location_id` de destino;
* `custodian_id` atual;
* `custodian_id` de destino.

### Definições

* **Local igual**: `location_id` de origem e destino são iguais.
* **Local diferente**: `location_id` de origem e destino são diferentes.
* **Responsável igual**: `custodian_id` de origem e destino são iguais.
* **Responsável diferente**: `custodian_id` de origem e destino são diferentes.
* Dois valores `NULL` de responsável são considerados **iguais**.
* Um responsável `NULL` e um responsável identificado são considerados **diferentes**.

### Matriz

| Local     | Responsável | Resultado                                                                                                                           |
| --------- | ----------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| Igual     | Igual       | **Bloquear** — nenhuma alteração efetiva                                                                                            |
| Igual     | Diferente   | **Alocação / Cautela**                                                                                                              |
| Diferente | Igual       | **Transferência de Setor / Filial**                                                                                                 |
| Diferente | Diferente   | **Alocação / Cautela**, quando houver responsável de destino válido e a operação representar entrega/atribuição ao novo colaborador |

### Regras determinísticas complementares

1. **Local igual + responsável igual**

   * Sempre bloquear.
   * Não criar Movement.
   * Não criar termo.
   * Não alterar Asset.

2. **Local igual + responsável diferente**

   * Classificar como **Alocação / Cautela**.
   * Permitir mudança somente do responsável.
   * Manter o local atual.
   * Exigir responsável de destino válido.

3. **Local diferente + responsável igual**

   * Classificar como **Transferência de Setor / Filial**.
   * Atualizar o local.
   * Preservar o responsável.
   * Não exigir novo responsável.

4. **Local diferente + responsável diferente**

   * Classificar como **Alocação / Cautela** quando houver responsável de destino válido e a operação representar entrega/atribuição ao novo colaborador.
   * Atualizar local e responsável de forma atômica.
   * Gerar o Termo de Responsabilidade/Cautela.

5. **Estoque → colaborador**

   * É uma **Alocação / Cautela**.
   * Exige responsável de destino.
   * O bem passa para `Em Uso`.
   * Deve gerar o Termo de Responsabilidade/Cautela.

6. **Estoque → outro local de estoque, permanecendo sem responsável**

   * É uma **Transferência de Setor / Filial**.
   * O responsável continua `NULL`.
   * O bem permanece disponível/em estoque conforme as regras atuais.

7. **Alocação / Cautela sem responsável de destino**

   * Deve ser bloqueada.
   * Não pode gerar termo sem custodiante.

8. **Transferência de Setor / Filial com local de destino igual ao local atual**

   * Deve ser bloqueada.
   * Transferência exige alteração efetiva de local.

9. **Devolução ao Estoque**

   * Possui fluxo próprio.
   * Não deve ser classificada pela matriz acima.

10. **Baixa / Descarte Definitivo**

    * Possui fluxo próprio.
    * Não deve ser classificada pela matriz acima.

11. **Manutenção**

    * Possui fluxo próprio.
    * Não deve ser classificada pela matriz acima.

---

# User Story 2 - Alocação ou mudança de responsável no mesmo local

**Priority**: P1

Um colaborador passa a utilizar um bem que permanece fisicamente no mesmo local.

Exemplo:

* bem no RH + João;
* destino: RH + Maria.

A operação deve ser registrada como **Alocação / Cautela**.

Também deve ser possível:

* bem no RH sem responsável;
* destino: RH + João.

Nesse caso, o bem passa a ter João como responsável e status `Em Uso`.

#### Acceptance Scenarios

1. **Given** um bem no departamento "TI" atribuído a "Carlos", **When** o operador registra Alocação para "Mariana" mantendo "TI", **Then** o responsável passa a ser Mariana, o local permanece TI e um Termo de Cautela é gerado.

2. **Given** um bem no Financeiro sem responsável, **When** o operador registra Alocação para "Roberto" mantendo Financeiro, **Then** o responsável passa a ser Roberto e o status passa para `Em Uso`.

3. **Given** um bem no RH sob responsabilidade de João, **When** o operador tenta registrar Transferência mantendo RH e alterando somente o responsável para Maria, **Then** a operação é rejeitada e o sistema informa que a alteração deve ser realizada como Alocação / Cautela.

---

# User Story 3 - Transferência de local mantendo o responsável

**Priority**: P2

Um bem muda de setor, filial, sala ou outro local patrimonial, mas permanece sob responsabilidade do mesmo colaborador.

Também é possível transferir um bem entre locais de estoque mantendo-o sem responsável.

#### Acceptance Scenarios

1. **Given** um notebook em "Filial SP - TI" sob responsabilidade de João, **When** o operador registra Transferência para "Matriz RJ - TI" mantendo João, **Then** o local é atualizado e João permanece responsável.

2. **Given** um equipamento no "Almoxarifado Central" sem responsável, **When** o operador registra Transferência para "Depósito Secundário", **Then** o local é atualizado, o responsável permanece `NULL` e o bem continua disponível.

3. **Given** um bem no RH, **When** o operador tenta registrar Transferência para RH, **Then** a operação é bloqueada porque não existe alteração efetiva de local.

---

# User Story 4 - Alocação com mudança simultânea de local e responsável

**Priority**: P2

Um bem é entregue a um novo colaborador que está em outro setor ou filial.

Exemplo:

* origem: Estoque Geral + sem responsável;
* destino: Filial Curitiba - Vendas + Marcos.

A operação é **Alocação / Cautela**.

#### Acceptance Scenarios

1. **Given** um equipamento no Estoque Geral sem responsável, **When** o operador registra Alocação para Marcos na Filial Curitiba - Vendas, **Then** o local passa a ser Filial Curitiba - Vendas, Marcos passa a ser responsável, o status passa para `Em Uso` e um Termo de Cautela é gerado.

2. **Given** um bem na Matriz - TI sob responsabilidade de João, **When** o operador registra Alocação para Fernanda na Filial Santos - Operações, **Then** o local e o responsável são atualizados atomicamente e a movimentação é registrada como Alocação / Cautela.

3. **Given** uma operação com local diferente e responsável diferente, **When** não existe responsável de destino válido, **Then** a operação não pode ser concluída como Alocação / Cautela.

---

# User Story 5 - Validação de operações com Estoque

**Priority**: P3

O sistema deve preservar a consistência do ciclo de estoque.

### Acceptance Scenarios

1. **Given** um bem em uso por Lucas, **When** o operador registra Devolução ao Estoque, **Then** o vínculo com Lucas é removido, o status passa para `Disponível`, a devolução é registrada e o termo correspondente é emitido conforme as regras existentes.

2. **Given** um bem já disponível no estoque e sem responsável, **When** o operador tenta registrar nova Devolução ao Estoque sem alteração de local, **Then** o sistema rejeita a operação informando que o bem já se encontra no estoque.

3. **Given** um bem no estoque, **When** o operador tenta concluir uma Alocação / Cautela sem selecionar responsável, **Then** a operação é bloqueada.

4. **Given** um bem no estoque sem responsável, **When** o operador o transfere para outro local de estoque, **Then** a operação é registrada como Transferência de Setor / Filial e o bem continua sem responsável.

---

# Edge Cases

### Bem baixado ou descartado

Bens com status `Baixado`/`Descartado` permanecem bloqueados para novas movimentações, conforme as regras existentes.

### Inventário Patrimonial

Quando o inventário encontrar um bem em local diferente (`LOCAL_DIFERENTE`):

* o inventário registra somente a divergência;
* não altera automaticamente o Asset;
* não cria automaticamente uma Transferência;
* não altera responsável;
* não cria Termo.

A regularização posterior deve ser feita pelo fluxo normal de movimentação.

Uma divergência de inventário deve permanecer independente da posterior regularização patrimonial.

### Manutenção

Os fluxos de envio para assistência técnica e retorno de manutenção permanecem inalterados, incluindo o status `EM_MANUTENCAO`.

A matriz de Alocação/Transferência não deve interferir nesses fluxos.

### Baixa / Descarte Definitivo

Continua sendo operação terminal conforme as regras existentes:

* desvincula o responsável quando aplicável;
* define status `Baixado`;
* exige justificativa;
* exige condição de descarte;
* não é classificada pela matriz de Alocação/Transferência.

### Preservação do histórico

Nenhuma movimentação ou auditoria já existente deve:

* ser alterada;
* ser recalculada;
* ser reclassificada;
* ser excluída.

As novas validações aplicam-se somente a novas operações.

### Manter Local Atual

Quando a interface oferecer a opção **"Manter Local Atual"**, o sistema deve interpretar essa opção como:

```text
local_destino = local_atual
```

A matriz deve então ser aplicada normalmente.

Não deve existir comportamento implícito ou diferente entre:

* selecionar explicitamente o mesmo local;
* selecionar "Manter Local Atual".

---

# Requirements

## Functional Requirements

### FR-001 — Comparação prévia

O sistema DEVE comparar, antes da confirmação da movimentação:

* local atual;
* local destino;
* responsável atual;
* responsável destino.

Essa comparação deve ocorrer antes da criação do Movement ou alteração persistente do Asset.

### FR-002 — Bloqueio de operação idêntica

O sistema DEVE bloquear qualquer nova operação sujeita à matriz quando:

```text
local atual == local destino
E
responsável atual == responsável destino
```

A operação não deve gerar Movement, termo ou alteração no Asset.

### FR-003 — Alocação no mesmo local

O sistema DEVE processar como `ALOCACAO_CAUTELA` a operação:

```text
local igual
responsável diferente
```

O responsável de destino é obrigatório.

### FR-004 — Transferência com responsável preservado

O sistema DEVE processar como `TRANSFERENCIA_LOCAL` a operação:

```text
local diferente
responsável igual
```

O responsável atual deve ser preservado.

### FR-005 — Transferência exige alteração de local

O sistema DEVE rejeitar uma `TRANSFERENCIA_LOCAL` quando:

```text
local destino == local atual
```

A mensagem deve informar que uma transferência exige alteração efetiva de localidade.

### FR-006 — Local e responsável diferentes

Quando:

```text
local diferente
responsável diferente
```

e houver responsável de destino válido, o sistema DEVE processar a operação como `ALOCACAO_CAUTELA` quando a operação representar entrega/atribuição do bem ao novo colaborador.

A atualização de local e responsável deve ser atômica.

### FR-007 — Estoque para colaborador

O sistema DEVE processar:

```text
Estoque + sem responsável
        ↓
Novo local + colaborador
```

como `ALOCACAO_CAUTELA`.

O bem deve passar para `Em Uso` conforme as regras existentes e deve ser gerado o Termo de Responsabilidade/Cautela.

### FR-008 — Alocação exige responsável

O sistema DEVE impedir `ALOCACAO_CAUTELA` quando não existir responsável de destino válido.

### FR-009 — Devolução redundante

O sistema DEVE impedir `DEVOLUCAO_ESTOQUE` quando o bem já estiver disponível, sem responsável e no estoque, sem alteração efetiva de local.

### FR-010 — Tipos existentes

O sistema DEVE preservar os tipos de movimentação existentes, incluindo:

* `ALOCACAO_CAUTELA`;
* `TRANSFERENCIA_LOCAL`;
* `DEVOLUCAO_ESTOQUE`;
* `BAIXA_DESCARTE`;
* demais tipos já existentes no domínio.

NÃO DEVE ser criado novo tipo de movimentação para atender esta feature.

### FR-011 — Histórico

O sistema DEVE preservar integralmente todos os registros históricos existentes.

Nenhuma movimentação anterior deve ser reclassificada ou modificada.

### FR-012 — Inventário

O sistema DEVE manter o funcionamento atual do módulo de Inventário.

O inventário deve continuar sendo instrumento de conferência e divergência, sem alteração automática do cadastro patrimonial.

### FR-013 — Camada de serviço

As regras da matriz DEVEM estar concentradas na camada de serviço, especialmente no `MovementService`, ou na camada de domínio/serviço atualmente responsável pela validação das movimentações.

Web e API devem utilizar a mesma regra de negócio.

### FR-014 — Responsável `NULL`

Para aplicação da matriz:

```text
NULL + NULL = responsável igual
NULL + responsável válido = responsável diferente
responsável válido + NULL = responsável diferente
```

### FR-015 — Atomicidade

Nas operações que alterarem simultaneamente local e responsável, a atualização do Asset e o registro da movimentação devem ocorrer de forma transacional, evitando estado parcial.

### FR-016 — Não duplicação de regras

A validação da matriz não deve ser implementada de maneira divergente em múltiplos pontos da aplicação.

A interface pode realizar validações de usabilidade, mas a regra definitiva deve permanecer na camada de serviço.

---

# Key Entities

### Bem Patrimonial — Asset

Equipamento cadastrado no patrimônio.

Atributos relevantes:

* status;
* condição;
* `location_id`;
* `custodian_id`.

### Movimentação — Movement

Registro histórico e comprobatório de evento patrimonial.

Atributos relevantes:

* `movement_type`;
* local de origem;
* local de destino;
* responsável de origem;
* responsável de destino;
* justificativa/motivo;
* operador;
* código do termo, quando aplicável.

### Localidade — Location

Estrutura física da organização composta conforme o modelo atual por filial, departamento, sala ou área.

### Colaborador / Custodiante — Custodian

Pessoa a quem a guarda do bem é atribuída.

---

# Success Criteria

### SC-001

100% das novas tentativas de registrar operação sujeita à matriz com local e responsável idênticos devem ser bloqueadas.

### SC-002

Operações com:

```text
local diferente
responsável igual
```

devem ser processadas como Transferência de Setor / Filial.

### SC-003

Operações com:

```text
local igual
responsável diferente
```

devem ser processadas como Alocação / Cautela.

### SC-004

Operações com:

```text
local diferente
responsável diferente
```

e responsável de destino válido, quando representarem entrega/atribuição ao novo colaborador, devem ser processadas como Alocação / Cautela.

### SC-005

Nenhum histórico anterior deve ser alterado, reclassificado ou excluído.

### SC-006

O módulo de Inventário deve permanecer funcional e sem alteração automática do cadastro patrimonial.

### SC-007

A suíte de testes existente deve permanecer verde.

Devem ser acrescentados testes cobrindo, no mínimo:

* local igual + responsável igual;
* local igual + responsável diferente;
* local diferente + responsável igual;
* local diferente + responsável diferente;
* `NULL + NULL`;
* `NULL + responsável`;
* responsável + `NULL`;
* estoque → colaborador;
* estoque → outro estoque;
* alocação sem responsável;
* transferência sem mudança de local;
* devolução redundante;
* bens baixados;
* manutenção;
* inventário com divergência de local.

---

# Assumptions

1. Não serão criados novos tipos de movimentação.

2. Os tipos existentes são suficientes para representar os cenários previstos.

3. Não haverá refatoração ampla.

4. As alterações devem ser cirúrgicas e limitadas às regras necessárias.

5. A matriz deve ser aplicada principalmente aos fluxos de `ALOCACAO_CAUTELA` e `TRANSFERENCIA_LOCAL`.

6. `DEVOLUCAO_ESTOQUE`, `BAIXA_DESCARTE` e manutenção possuem regras próprias e não devem ser artificialmente enquadradas na matriz.

7. Dois responsáveis `NULL` são considerados iguais.

8. Quando o usuário selecionar "Manter Local Atual", o destino será considerado igual ao local atual.

9. A ausência de responsável no estoque representa estado válido de custódia e não deve ser tratada como erro por si só.

10. O Inventário não deve corrigir automaticamente divergências patrimoniais.

11. Os perfis RBAC existentes continuam controlando o acesso às movimentações.

12. Não devem ser alteradas permissões ou regras de segurança como parte desta feature.

13. O histórico existente é considerado imutável.

14. A implementação deve preservar o comportamento válido já existente fora das regras especificamente corrigidas nesta feature.

---

# Scope Constraints

Esta feature NÃO deve:

* criar novos tipos de movimentação;
* alterar o modelo de dados sem necessidade comprovada;
* migrar ou reclassificar movimentações históricas;
* alterar o funcionamento do Inventário;
* alterar regras de manutenção;
* alterar regras de baixa/descarte que já funcionam;
* alterar o RBAC;
* realizar refatoração arquitetural ampla;
* duplicar a lógica da matriz entre Web/API;
* modificar funcionalidades não relacionadas à correção das regras de movimentação.

A implementação deve modificar somente os arquivos necessários para corrigir a regra de negócio, interface/API diretamente relacionada e testes correspondentes.
