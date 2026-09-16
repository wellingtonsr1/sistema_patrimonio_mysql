Sim. Abaixo está o **`plan.md` completo**, já consolidado com as correções. Você pode **substituir o conteúdo inteiro do `plan.md`** por este.

# Implementation Plan: Correção das Regras de Movimentação Patrimonial

**Branch**: `005-correcao-regras-movimentacao` | **Date**: 2026-09-15 | **Spec**: `specs/005-correcao-regras-movimentacao/spec.md`

**Input**: Feature specification from `specs/005-correcao-regras-movimentacao/spec.md`

---

## Summary

Corrigir a lógica de validação das movimentações patrimoniais no SisPatrimônio Pro para aplicar de forma determinística a matriz de combinação entre local e responsável de origem e destino.

A solução deve:

* impedir o registro de movimentações sem alteração efetiva;
* diferenciar corretamente Alocação a Colaborador / Cautela de Transferência de Setor / Filial;
* permitir mudança de responsável mantendo o local;
* permitir mudança de local mantendo o responsável;
* tratar corretamente operações em que local e responsável mudam simultaneamente;
* tratar corretamente operações envolvendo estoque;
* preservar o histórico existente;
* preservar as movimentações válidas;
* manter o funcionamento atual do Inventário;
* preservar os fluxos específicos de devolução, manutenção e baixa;
* fazer somente as alterações necessárias.

A regra de negócio deve permanecer centralizada na camada de serviço responsável pela criação das movimentações, evitando duplicação entre Web, API e demais consumidores existentes.

Antes da implementação, deve ser confirmado no código quais fluxos atualmente utilizam o serviço de movimentações e qual é o ponto efetivo responsável pela criação e persistência dos registros `Movement`.

**Não será criado novo tipo de movimentação.**

**Não haverá alteração de schema ou migração de banco.**

**Não haverá refatoração arquitetural ampla.**

---

# Technical Context

**Language/Version**: Python 3.10+

**Primary Dependencies**:

* FastAPI
* SQLAlchemy 2
* Pydantic v2
* Jinja2
* Bootstrap 5
* pytest

Nenhuma dependência nova é prevista.

**Storage**:

* MariaDB/MySQL em produção;
* SQLite em memória para a suíte de testes.

**Schema**:

Nenhuma alteração de schema DDL é prevista.

As estruturas existentes de:

* `assets`;
* `movements`;
* `locations`;
* `custodians`;

devem ser suficientes para atender à feature.

**Testing**:

A suíte existente deve permanecer verde.

Novos testes devem ser adicionados para cobrir integralmente a matriz de movimentação e seus casos de borda.

O arquivo de testes principal previsto é:

```text
tests/test_movements.py
```

A análise deve verificar se existem outros testes de movimentação relevantes antes da implementação, para evitar duplicação ou alteração desnecessária.

**Target Platform**:

* servidor Linux;
* navegador web moderno;
* interface Web server-rendered;
* API REST JSON.

**Project Type**:

Aplicação monolítica em camadas:

```text
Web/API → Services → Models
```

**Performance Goals**:

A validação deve utilizar os dados já necessários para a criação da movimentação, evitando consultas redundantes e processamento adicional significativo.

Não é necessário estabelecer uma complexidade O(1) artificial para a operação completa, pois a criação da movimentação depende dos dados persistidos do Asset e das entidades relacionadas.

**Constraints**:

* não criar novos tipos de `MovementType`;
* não alterar movimentações históricas;
* não reclassificar registros históricos;
* não alterar o funcionamento do módulo de Inventário;
* não realizar refatoração ampla;
* não duplicar regras de negócio entre Web, API e Service;
* não modificar regras específicas de manutenção sem necessidade;
* não modificar regras existentes de baixa/descarte sem necessidade;
* não introduzir alterações de banco de dados.

**Scale/Scope**:

O escopo inicial esperado é pequeno e cirúrgico.

Arquivos previstos:

```text
app/services/movement_service.py
tests/test_movements.py
```

O template Web e as rotas Web/API somente devem ser alterados se a análise do código demonstrar necessidade real.

---

# Constitution Check

**GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.**

| Princípio (Constitution v1.0.0)                 |  Status | Observação                                                                                                                        |
| ----------------------------------------------- | :-----: | --------------------------------------------------------------------------------------------------------------------------------- |
| **I. Preservação / Evolução Incremental**       |  ✅ PASS | Alteração cirúrgica e incremental, sem refatoração ampla ou remoção de funcionalidades.                                           |
| **II. Arquitetura em Camadas**                  | ✅ PASS* | A regra deve permanecer na camada de serviço. A Phase 0 deve confirmar os fluxos reais de criação de movimentações.               |
| **III. Regras de Negócio nos Services**         | ✅ PASS* | A matriz deve ser centralizada no service responsável pela criação da movimentação. O método exato será confirmado na pesquisa.   |
| **IV. Integridade Patrimonial / Movimentações** |  ✅ PASS | Movimentações sem alteração efetiva serão bloqueadas; histórico existente permanece imutável.                                     |
| **V. Integridade do Inventário**                |  ✅ PASS | O módulo de Inventário permanece fora do escopo e continua sem alterar automaticamente o cadastro patrimonial.                    |
| **VI. Segurança por Padrão**                    |  ✅ PASS | Permissões existentes continuam governando o acesso às movimentações. Nenhuma alteração de RBAC prevista.                         |
| **VII. MariaDB / Proteção de Dados**            |  ✅ PASS | Nenhuma alteração DDL, tabela ou coluna prevista.                                                                                 |
| **VIII. Testes como Não-Regressão**             |  ✅ PASS | A suíte existente deve permanecer verde e novos testes cobrirão a matriz.                                                         |
| **IX. Auditoria**                               | ✅ PASS* | Movimentações válidas devem continuar utilizando o mecanismo de auditoria existente. O fluxo atual será confirmado na Phase 0.    |
| **X. Interface Consistente**                    | ✅ PASS* | A interface existente deve ser preservada; alterações somente serão realizadas se necessárias para suportar corretamente a regra. |
| **XI. Documentação Fiel**                       |  ✅ PASS | A documentação da feature deve refletir a matriz normativa e o comportamento efetivamente implementado.                           |
| **XII. Especificação e Validação**              |  ✅ PASS | SPEC → pesquisa → plano → tarefas → implementação → testes e validação.                                                           |

**Resultado preliminar: 12/12 princípios compatíveis com a feature, com os itens marcados `*` sujeitos à confirmação durante a Phase 0.**

---

# Project Structure

## Documentation

```text
specs/005-correcao-regras-movimentacao/

├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── movement-rules-contract.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Documentos

**`spec.md`**

Especificação funcional da feature e matriz normativa de movimentação.

**`plan.md`**

Plano técnico de implementação.

**`research.md`**

Registro das verificações realizadas no código existente antes da implementação.

**`data-model.md`**

Descrição dos estados de origem/destino e entidades envolvidas.

**`quickstart.md`**

Procedimento executável para validação manual e automatizada da feature.

**`contracts/movement-rules-contract.md`**

Contrato da matriz de regras que deverá ser respeitado pelo serviço.

**`checklists/requirements.md`**

Checklist de completude e qualidade da especificação.

**`tasks.md`**

Tarefas concretas de implementação, geradas após o plano e a pesquisa.

---

# Source Code Structure

```text
app/

├── models/
│   └── movement.py
│
├── schemas/
│   └── movement.py
│
├── services/
│   └── movement_service.py
│
├── web/
│   ├── routes.py
│   └── templates/
│       └── movements/
│           └── new.html
│
└── api/
    └── movements_api.py

tests/
└── test_movements.py
```

### Arquivos prioritários

#### `app/services/movement_service.py`

Ponto principal da implementação.

Deve conter, no ponto apropriado da lógica existente, a validação da matriz:

```text
Local igual + Responsável igual
    → BLOQUEAR

Local igual + Responsável diferente
    → ALOCAÇÃO / CAUTELA

Local diferente + Responsável igual
    → TRANSFERÊNCIA DE SETOR / FILIAL

Local diferente + Responsável diferente
    → ALOCAÇÃO / CAUTELA
      quando houver responsável de destino válido
      e a operação representar entrega/atribuição.
```

A implementação deve respeitar a estrutura existente do service e evitar refatorações desnecessárias.

#### `tests/test_movements.py`

Deve receber testes para todas as combinações da matriz e casos especiais.

#### `app/web/templates/movements/new.html`

Não deve ser alterado automaticamente.

Somente deverá ser modificado caso a pesquisa demonstre que:

* a interface não informa adequadamente a regra;
* a seleção atual permite uma operação que deveria ser bloqueada antes do envio;
* é necessária uma orientação de usabilidade para tornar a nova regra compreensível.

A validação definitiva continua sendo responsabilidade do service.

#### `app/web/routes.py`

Não deve ser alterado se o tratamento atual das exceções provenientes do service já funcionar corretamente.

Somente modificar se a análise demonstrar que o erro de validação não chega corretamente à interface.

#### `app/api/movements_api.py`

Não deve ser alterado se já delegar corretamente ao service e converter as exceções existentes para resposta HTTP adequada.

Somente modificar se necessário para preservar o contrato atual da API diante das novas validações.

---

# Phase 0 — Research

Antes da criação das tarefas de implementação, deve ser realizada uma análise somente leitura do código existente.

O objetivo é confirmar o comportamento real antes de alterar qualquer arquivo.

## R1 — Ponto efetivo de criação de Movement

Verificar:

* onde `Movement` é instanciado;
* onde é persistido;
* qual método do `MovementService` realiza a operação;
* se `create_movement` realmente é o ponto central;
* se existem outros métodos que criam movimentações.

Resultado esperado:

```text
movement creation entry points
```

## R2 — Fluxo Web

Verificar:

* rota `/movements/new`;
* POST correspondente;
* dados recebidos;
* tipo de movimentação recebido;
* tratamento de erros;
* chamada ao service;
* comportamento após sucesso;
* comportamento após falha.

## R3 — Fluxo API

Verificar:

* `/api/v1/movements`;
* schema utilizado;
* chamada ao service;
* tratamento de `ValueError` ou exceções específicas;
* resposta HTTP atual.

## R4 — Fluxos CLI ou outros consumidores

Verificar se existe algum comando, script ou outro consumidor capaz de criar movimentações.

Se existir, determinar se utiliza o mesmo service.

Não presumir que CLI utiliza `MovementService` sem confirmação no código.

## R5 — Estado atual do Asset

Verificar como o sistema atualmente:

* lê `location_id`;
* lê `custodian_id`;
* altera `location_id`;
* altera `custodian_id`;
* altera `status`;
* realiza commit.

## R6 — Transação

Verificar se a criação de Movement e atualização do Asset já ocorrem dentro da mesma transação.

Caso já exista mecanismo transacional, preservá-lo.

Não criar nova infraestrutura transacional se a existente já atender ao requisito.

## R7 — Termos

Verificar:

* quando o Termo de Responsabilidade/Cautela é gerado;
* quando o código do termo é criado;
* quais tipos de movimentação geram termo;
* comportamento quando ocorre falha de validação.

Uma operação bloqueada não deve gerar termo.

## R8 — Devolução ao Estoque

Verificar o fluxo atual de `DEVOLUCAO_ESTOQUE`.

Confirmar:

* validações existentes;
* atualização de responsável;
* atualização de status;
* alteração de local;
* geração de termo;
* registro de Movement.

A feature deve corrigir apenas o comportamento redundante identificado, sem refatorar o fluxo.

## R9 — Baixa / Descarte

Verificar o fluxo atual de `BAIXA_DESCARTE`.

Preservar as regras existentes.

Não aplicar automaticamente a matriz de Alocação/Transferência a esse fluxo.

## R10 — Manutenção

Verificar os fluxos de envio e retorno de manutenção.

Confirmar que a nova validação não interfere em:

```text
EM_MANUTENCAO
```

ou nos tipos específicos já existentes.

## R11 — Inventário

Confirmar que:

* inventário registra divergências;
* divergência de local não altera automaticamente `Asset.location_id`;
* inventário não cria automaticamente Transferência;
* a regularização posterior utiliza o fluxo normal de movimentação.

Nenhuma alteração no módulo de Inventário deve ser feita como parte desta feature.

## R12 — Testes existentes

Localizar todos os testes relacionados a:

* Movement;
* Asset;
* custodian;
* location;
* estoque;
* devolução;
* inventário;
* termos.

Evitar criar testes duplicados quando já existir cobertura apropriada.

---

# Phase 1 — Design

Após a pesquisa, devem ser consolidados os seguintes artefatos.

## Data Model

O `data-model.md` deve documentar:

```text
Asset
 ├── location_id
 ├── custodian_id
 └── status

Movement
 ├── movement_type
 ├── origin_location
 ├── destination_location
 ├── origin_custodian
 ├── destination_custodian
 └── term
```

Não devem ser criadas novas entidades ou colunas.

## Movement Matrix

A regra normativa deve ser:

| Local     | Responsável | Resultado                                                                                     |
| --------- | ----------- | --------------------------------------------------------------------------------------------- |
| Igual     | Igual       | Bloquear                                                                                      |
| Igual     | Diferente   | Alocação / Cautela                                                                            |
| Diferente | Igual       | Transferência de Setor / Filial                                                               |
| Diferente | Diferente   | Alocação / Cautela, quando houver responsável destino válido e representar entrega/atribuição |

### Regras para `NULL`

```text
NULL + NULL
→ responsável igual

NULL + responsável
→ responsável diferente

responsável + NULL
→ responsável diferente
```

---

# Movement Type Rules

## ALOCAÇÃO / CAUTELA

Pode representar:

```text
mesmo local + novo responsável
```

ou:

```text
novo local + novo responsável
```

ou:

```text
estoque + novo responsável
```

Sempre exige responsável de destino válido.

Quando aplicável:

* atualiza responsável;
* pode atualizar local;
* altera status para `Em Uso`;
* gera Termo de Responsabilidade/Cautela conforme o fluxo existente.

## TRANSFERÊNCIA DE SETOR / FILIAL

Representa mudança oficial de localização.

Pode representar:

```text
novo local + mesmo responsável
```

ou:

```text
estoque/local A + estoque/local B
sem responsável
```

Não exige novo responsável.

Exige alteração efetiva de local.

## DEVOLUÇÃO AO ESTOQUE

Fluxo específico.

Não deve ser classificada pela matriz geral.

Deve continuar obedecendo às regras atuais, incluindo:

* remoção de responsável;
* status disponível;
* termo de devolução;
* eventual alteração de local.

Uma devolução redundante deve ser bloqueada quando o bem já estiver disponível, sem responsável e no estoque, sem alteração de local.

## BAIXA / DESCARTE

Fluxo terminal existente.

Não deve ser classificado pela matriz.

## MANUTENÇÃO

Fluxo específico existente.

Não deve ser classificado pela matriz.

---

# Validation Order

A implementação deve respeitar uma ordem que evite efeitos parciais.

Ordem conceitual:

```text
1. Carregar Asset atual
        ↓
2. Validar existência e estado permitido
        ↓
3. Resolver destino
        ↓
4. Comparar local origem/destino
        ↓
5. Comparar responsável origem/destino
        ↓
6. Aplicar regras específicas do tipo de movimentação
        ↓
7. Bloquear operações inválidas
        ↓
8. Atualizar Asset
        ↓
9. Criar Movement
        ↓
10. Gerar termo quando aplicável
        ↓
11. Auditoria existente
        ↓
12. Commit
```

A ordem exata deve respeitar o código atual e ser ajustada durante a Phase 0 caso o serviço existente utilize outro fluxo transacional equivalente.

Nenhuma alteração persistente deve ocorrer antes das validações obrigatórias.

---

# Transactional Integrity

Nas operações que alterarem simultaneamente local e responsável:

```text
Asset.location_id
Asset.custodian_id
Movement
Term
Audit
```

devem permanecer consistentes com a transação existente.

Se qualquer etapa obrigatória falhar, a operação não deve deixar estado parcial.

A implementação deve reutilizar o mecanismo transacional já existente.

---

# Error Handling

As mensagens devem ser claras para o operador.

### Sem alteração efetiva

Mensagem conceitual:

```text
Não foi realizada nenhuma alteração. O local e o responsável de destino são iguais aos dados atuais do bem.
```

### Transferência sem mudança de local

Mensagem conceitual:

```text
Transferência de Setor / Filial exige alteração do local do bem.
```

### Alocação sem responsável

Mensagem conceitual:

```text
Alocação / Cautela exige a seleção de um colaborador responsável.
```

### Devolução redundante

Mensagem conceitual:

```text
O bem já está disponível no estoque e não possui responsável.
```

As mensagens finais devem respeitar o padrão já utilizado pela aplicação.

Não é necessário alterar a estrutura de tratamento de erros se o mecanismo existente já suportar essas mensagens.

---

# Test Strategy

Os testes devem verificar comportamento, não implementação interna.

## Matriz mínima

### Caso 1

```text
Local igual
Responsável igual
→ bloqueio
```

### Caso 2

```text
Local igual
Responsável diferente
→ ALOCAÇÃO_CAUTELA
```

### Caso 3

```text
Local diferente
Responsável igual
→ TRANSFERENCIA_LOCAL
```

### Caso 4

```text
Local diferente
Responsável diferente
→ ALOCAÇÃO_CAUTELA
```

quando houver responsável de destino válido e representar entrega/atribuição.

## Casos `NULL`

Testar:

```text
NULL → NULL
NULL → responsável
responsável → NULL
```

## Estoque

Testar:

```text
estoque → colaborador
estoque → outro estoque
estoque → mesmo estoque
```

## Tipos específicos

Testar:

```text
DEVOLUCAO_ESTOQUE
BAIXA_DESCARTE
MANUTENÇÃO
```

para garantir que não sofreram regressão.

## Inventário

Confirmar que a execução da suíte de inventário permanece verde e que nenhuma alteração automática no Asset foi introduzida.

---

# Regression Strategy

Após a implementação:

1. executar testes específicos de movimentação;
2. executar testes relacionados a Asset;
3. executar testes relacionados a termos;
4. executar testes de Inventário;
5. executar a suíte completa;
6. verificar que nenhuma migração foi criada;
7. verificar que nenhum novo `MovementType` foi criado;
8. verificar que nenhum registro histórico foi alterado.

---

# Quickstart Validation

O `quickstart.md` deve conter uma sequência mínima de validação:

```text
1. Preparar banco de testes.
2. Criar/selecionar Asset com local e responsável conhecidos.
3. Testar local igual + responsável igual.
4. Testar local igual + responsável diferente.
5. Testar local diferente + responsável igual.
6. Testar local diferente + responsável diferente.
7. Testar estoque → colaborador.
8. Testar estoque → estoque.
9. Testar Alocação sem responsável.
10. Testar Transferência sem mudança de local.
11. Testar devolução redundante.
12. Testar bem baixado.
13. Testar manutenção.
14. Executar testes de Inventário.
15. Executar suíte completa.
```

---

# API and Web Compatibility

A implementação não deve alterar o contrato externo existente sem necessidade.

A API deve continuar retornando as estruturas atuais.

Caso o service utilize `ValueError` ou outra exceção já tratada pelas rotas, deve-se preservar o mecanismo atual.

Somente alterar as rotas caso a nova validação não seja corretamente propagada pela estrutura existente.

A interface Web deve continuar utilizando o fluxo atual de mensagens/redirects.

---

# Audit Compatibility

Movimentações válidas devem continuar passando pelo mecanismo de auditoria existente.

Operações bloqueadas antes da criação da movimentação:

* não devem criar Movement;
* não devem gerar Termo;
* não devem alterar Asset;
* não devem gerar uma auditoria de alteração patrimonial como se a operação tivesse sido concluída.

Caso o sistema possua auditoria específica de tentativa/erro, ela deve ser preservada conforme o comportamento atual.

---

# Historical Data

Nenhuma operação de migração ou correção histórica faz parte desta feature.

Não executar:

```text
UPDATE movements ...
DELETE movements ...
reclassificação histórica
reprocessamento de movimentos
```

Os registros existentes devem permanecer exatamente como estão.

---

# Scope Guard

A implementação NÃO deve:

* criar novos tipos de movimentação;
* criar novas tabelas;
* criar novas colunas;
* alterar enums existentes sem necessidade;
* migrar dados;
* reclassificar histórico;
* apagar histórico;
* alterar o módulo de Inventário;
* alterar permissões;
* alterar RBAC;
* alterar fluxos de manutenção;
* refatorar todo o `MovementService`;
* duplicar a matriz em Web e API;
* alterar arquivos não relacionados sem justificativa.

Se durante a implementação for identificada necessidade de alteração fora desse escopo, a tarefa deve ser interrompida para análise antes de introduzir a mudança.

---

# Expected Implementation Approach

A implementação deve seguir esta ordem:

```text
Phase 0
  ↓
Pesquisar código atual
  ↓
Confirmar ponto central de criação
  ↓
Confirmar consumidores Web/API/CLI
  ↓
Confirmar transação
  ↓
Confirmar termos/auditoria
  ↓
Confirmar testes existentes
  ↓
Phase 1
  ↓
Consolidar data-model
  ↓
Consolidar contrato da matriz
  ↓
Revisar quickstart
  ↓
Gerar tasks
  ↓
Implementar somente tarefas necessárias
  ↓
Executar testes específicos
  ↓
Executar suíte completa
```

---

# Expected File Changes

O conjunto inicial esperado é:

```text
MODIFICAR
├── app/services/movement_service.py
└── tests/test_movements.py

POSSIVELMENTE MODIFICAR, SOMENTE SE NECESSÁRIO
├── app/web/templates/movements/new.html
├── app/web/routes.py
└── app/api/movements_api.py
```

Nenhum arquivo adicional deve ser alterado sem justificativa baseada na análise do código.

---

# Structure Decision

A estrutura existente em camadas será preservada:

```text
Web/API
   ↓
Movement Service
   ↓
Models / Database
```

A lógica normativa da matriz deve permanecer na camada de serviço.

A Web e a API não devem implementar versões próprias da matriz.

O código existente deve ser preservado sempre que já atender ao comportamento requerido.

---

# Complexity Tracking

Não há violação prevista da arquitetura ou da Constituição.

| Violação         | Por que é necessária | Alternativa mais simples rejeitada porque |
| ---------------- | -------------------- | ----------------------------------------- |
| Nenhuma prevista | N/A                  | N/A                                       |

Caso a Phase 0 revele alguma necessidade que represente aumento significativo de escopo, ela deve ser documentada e avaliada antes da implementação.

---

# Final Gate

Antes de considerar o plano pronto para `/speckit.tasks`, deve estar confirmado:

* [ ] ponto real de criação de Movement;
* [ ] consumidores Web identificados;
* [ ] consumidores API identificados;
* [ ] consumidores CLI/outros identificados;
* [ ] fluxo transacional identificado;
* [ ] geração de termos identificada;
* [ ] auditoria identificada;
* [ ] fluxo de devolução identificado;
* [ ] fluxo de baixa identificado;
* [ ] fluxo de manutenção identificado;
* [ ] fluxo de Inventário confirmado;
* [ ] testes existentes identificados;
* [ ] nenhum novo tipo de movimentação necessário;
* [ ] nenhuma alteração de schema necessária;
* [ ] matriz validada contra o código existente;
* [ ] escopo de arquivos confirmado.



