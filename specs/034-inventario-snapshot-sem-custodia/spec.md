# Feature Specification: Inventário — Remover o colaborador responsável do snapshot de bens esperados

**Feature Branch**: `034-inventario-snapshot-sem-custodia`

**Created**: 2026-09-24

**Status**: Draft

**Input**: Alterar o módulo de Inventário para que o colaborador responsável não faça parte do snapshot dos bens esperados nem da conformidade da conferência. O Inventário deve focar na conferência física (existência, tombamento, localização esperada/encontrada e divergências). Correção da responsabilidade do bem continua nos fluxos próprios (movimentação/alocação/cautela ou edição cadastral). Alteração cirúrgica: sem mexer nas regras de movimentação/alocação, sem migração destrutiva, sem apagar dados históricos.

## Estado atual analisado (fatos do repositório — leitura prévia, Seção "Restrições de implementação" do input)

| Fato verificado | Relevância |
|---|---|
| O snapshot grava o **nome textual** do colaborador esperado (`expected_custodian_name`, texto, opcional) no item do inventário, capturado do cadastro do bem na geração da lista | É o dado a ser eliminado de novos snapshots |
| **Não existe** identificador/ID do colaborador no snapshot — apenas o nome textual | Reduz o escopo: nada de FK a tratar |
| A conferência **já não compara** colaborador: as divergências existentes são apenas LOCAL_DIFERENTE, NAO_ENCONTRADO e SEM_IDENTIFICACAO | A mudança remove o dado do snapshot e das superfícies de exibição; a lógica de conformidade já é por local/presença |
| O colaborador esperado aparece como informação auxiliar em: tela do inventário (cards dos itens), tela de conferência ("Colaborador esperado:"), e ata de inventário nas três exportações (coluna "Responsável Esperado") | Superfícies a revisar nesta feature |
| O pacote offline (feature 033) inclui `expected_custodian_name` no payload do pacote | Ajuste cruzado pontual nesta feature |
| O cadastro de colaboradores (Custodian) e sua relação com o bem são usados por outros módulos (equipamentos, movimentações, relatórios de colaboradores, alocação/cautela) | FORA de escopo — nada do cadastro muda |
| Constitution V (snapshot imutável), VII (migração apenas aditiva idempotente), I (nenhuma alteração não relacionada) | Restringem a implementação |

## Clarifications

### Session 2026-09-24

- Q: O que fazer com os dados de colaborador esperado já gravados nos inventários que existem hoje? → A: **Preservar tudo** — a coluna e os dados já gravados permanecem no banco; apenas NOVOS inventários deixam de gravar o campo (sem migração destrutiva — Princípio VII; histórico íntegro) (decisão H-1).
- Q: Na ata de um inventário ANTIGO à mudança (com histórico gravado), como tratar a coluna "Responsável Esperado" ao regenerar a ata? → A: **Preservar quando houver histórico** — a ata de inventário legado continua exibindo o responsável esperado gravado (valor comprobatório); a ata de inventário novo não tem a coluna (decisão H-2).
- Q: No pacote offline da feature 033, o campo do colaborador esperado deve sumir imediatamente de todos os pacotes ou só dos inventários novos? → A: **Remover sempre** — o campo some do pacote para TODO inventário (legado ou novo): o pacote é payload técnico transitório, não documento comprobatório, e exibir responsabilidade como dado de conferência é exatamente o que esta spec elimina (decisão H-3).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Snapshot de novos inventários sem colaborador responsável (Priority: P1)

Um usuário autorizado cria um inventário. A lista de bens esperados é gerada como fotografia do patrimônio contendo a identificação do bem (tombamento) e a localização cadastrada no momento — **sem** qualquer informação de colaborador responsável. A criação funciona normalmente mesmo que os bens do escopo não tenham colaborador cadastrado.

**Why this priority**: é o núcleo da mudança — sem isso o Inventário continua tratando responsabilidade, que é papel dos fluxos de movimentação/alocação.

**Independent Test**: criar um inventário e inspecionar a lista de bens esperados: constam tombamento e local esperado; não consta colaborador. Não requer conferir nem encerrar.

**Acceptance Scenarios**:

1. **Given** bens com e sem colaborador cadastrado no escopo, **When** o inventário é criado, **Then** o snapshot de cada item contém tombamento e local esperado e não contém colaborador responsável.
2. **Given** um bem cujo cadastro tem colaborador, **When** o inventário é criado, **Then** a criação não exige nem valida colaborador (bem sem colaborador entra normalmente).
3. **Given** o inventário criado, **When** o cadastro do bem é alterado depois (local ou responsável), **Then** o snapshot permanece imutável (Princípio V — comportamento existente reafirmado).

---

### User Story 2 - Conferência e ata sem "responsável esperado" (Priority: P1)

Durante a conferência, o usuário registra a situação encontrada (local, observação, divergências). A tela de conferência não apresenta "colaborador esperado" como dado de conferência, e a conformidade é determinada exclusivamente por presença e localização. A ata exportada dos inventários criados após a mudança não contém a coluna "Responsável Esperado".

**Why this priority**: é o resultado visível da mudança — o coletador deixa de receber a responsabilidade como critério, e os documentos comprobatórios refletem o novo escopo do Inventário.

**Independent Test**: abrir a conferência de um item de inventário novo (sem dado de colaborador no snapshot) e exportar a ata: nenhuma referência a "responsável/colaborador esperado". Um bem encontrado com responsável diferente no cadastro resulta CONFORME quando o local bate.

**Acceptance Scenarios**:

1. **Given** inventário novo com bem localizado no local esperado, **When** o cadastro do bem tem colaborador diferente do original (ou nenhum), **Then** a conferência resulta ENCONTRADO (conforme) — nenhuma divergência de responsável existe.
2. **Given** inventário novo, **When** a conferência de um item é aberta, **Then** não há rótulo "Colaborador esperado" na tela.
3. **Given** inventário novo encerrado, **When** a ata é exportada (CSV, Excel, PDF), **Then** não consta a coluna "Responsável Esperado".
4. **Given** bem encontrado em local diferente do esperado, **When** registrado, **Then** a divergência de localização continua sendo gerada e o cadastro não é alterado (comportamento existente reafirmado).

---

### User Story 3 - Inventários históricos permanecem acessíveis e íntegros (Priority: P2)

Inventários criados **antes** da mudança mantêm seus dados gravados: continuidade de consulta, conferência dos itens pendentes, encerramento, ata e auditoria — sem perda ou reescrita de histórico.

**Why this priority**: protege dados reais já produzidos; depende da mudança de geração (US1), mas é um requisito de compatibilidade com risco próprio.

**Independent Test**: abrir um inventário anterior à mudança, consultar itens (inclusive com histórico de colaborador esperado gravado), exportar a ata e verificar integridade. Nenhuma edição de dados é necessária.

**Acceptance Scenarios**:

1. **Given** inventário anterior à mudança com colaborador esperado gravado nos itens, **When** consultado, **Then** o histórico permanece acessível e íntegro (nenhum dado é apagado ou reescrito).
2. **Given** inventário anterior à mudança em andamento, **When** itens pendentes são conferidos e o inventário encerrado, **Then** o fluxo funciona normalmente e a ata preserva o histórico existente.
3. **Given** qualquer inventário anterior, **When** a estrutura do banco é verificada após a mudança, **Then** nenhuma migração destrutiva ocorreu (colunas/dados históricos preservados).

---

### Edge Cases

- **Bem sem colaborador cadastrado** no momento da criação: entra no snapshot normalmente (hoje o campo é opcional — a mudança não pode introduzir exigência de colaborador).
- **Inventário em andamento criado antes da mudança**: itens com colaborador esperado já gravado permanecem como estão (dados históricos); a conferência segue sem comparar responsável.
- **Re-conferência de item**: comportamento existente (confirmação antes de substituir) inalterado.
- **Bem não previsto encontrado em campo**: ocorrência registrada como hoje; colaborador não participa.
- **Pacote offline preparado para inventário criado antes da mudança**: o pacote novo NÃO inclui o campo (decisão H-3 — remoção imediata e global no payload; o histórico no banco permanece, decisão H-1).
- **Colaborador alterado no cadastro entre a criação e a conferência**: não afeta o snapshot (imutabilidade) nem gera divergência.

## Requirements *(mandatory)*

### Functional Requirements

**Snapshot (geração)**

- **FR-001**: A geração da lista de bens esperados de NOVOS inventários MUST NOT armazenar colaborador responsável no snapshot do item.
- **FR-002**: O snapshot de novos inventários MUST conter, no mínimo: identificação/tombamento do bem e localização cadastrada no momento da criação (e demais dados estritamente necessários à identificação, como descrição/serial já existentes).
- **FR-003**: A criação do inventário MUST NOT depender da existência de colaborador responsável nos bens do escopo.

**Conferência e conformidade**

- **FR-004**: A conferência MUST NOT exibir "colaborador esperado" como dado de conferência.
- **FR-005**: A determinação de conformidade/divergência MUST basear-se exclusivamente na presença do bem e na comparação localização encontrada × localização esperada (e na situação "sem identificação") — o colaborador responsável MUST NOT gerar divergência de inventário. *(Fato do repositório: a lógica atual já não compara responsável; este FR formaliza e trava a regra.)*
- **FR-006**: A correção da responsabilidade de um bem MUST continuar ocorrendo exclusivamente pelos fluxos próprios existentes (movimentação/alocação/cautela ou edição cadastral) — o Inventário não cria, altera ou sugere movimentações automaticamente.

**Documentos e superfícies**

- **FR-007**: A ata de inventário (CSV, Excel e PDF) de inventários criados após a mudança MUST NOT conter a coluna "Responsável Esperado".
- **FR-008**: Inventários criados ANTES da mudança MUST preservar seus dados históricos (incluído o colaborador esperado já gravado), acessíveis em consulta e ata; nenhum dado histórico MUST ser apagado ou reescrito.
- **FR-009**: Nenhuma migração destrutiva MAY ser executada; alterações de estrutura, se necessárias, são aditivas e idempotentes, preservando a compatibilidade histórica.
- **FR-010**: O pacote offline (feature 033) MUST NOT incluir colaborador esperado em NENHUM pacote gerado após a mudança (inventários legados e novos — decisão H-3); a documentação/contrato/data-model dessa feature é ajustado no mesmo escopo.
- **FR-011**: As telas do módulo de Inventário MUST ser revisadas para não apresentar colaborador responsável como parte do snapshot/conferência de novos inventários; telas de outros módulos (equipamentos, colaboradores, movimentações) MUST NOT ser alteradas.
- **FR-012**: Nenhuma regra de movimentação, alocação/cautela, edição cadastral, permissão, autenticação ou auditoria MAY ser alterada fora deste escopo (Princípio I); a suíte de testes existente permanece verde.

### Key Entities *(include if feature involves data)*

- **Item de inventário (snapshot)**: fotografia do bem esperado — identificação (tombamento) + localização esperada no momento da criação; imutável após a criação (Princípio V); **para inventários criados após esta feature, sem informação de colaborador responsável**. Itens de inventários anteriores podem carregar o histórico já gravado.
- **Colaborador (cadastro patrimonial)**: permanece integralmente como está — relação com o bem, telas e fluxos de responsabilidade/alocação inalterados; deixa apenas de alimentar o snapshot do Inventário.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos inventários criados após a mudança geram snapshot sem colaborador responsável (verificável por inspeção da lista de bens esperados e do armazenamento).
- **SC-002**: Em conferência de inventário novo, um bem localizado no local esperado resulta CONFORME mesmo com colaborador diferente (ou ausente) no cadastro — zero divergências de responsável em 100% dos casos.
- **SC-003**: 100% das atas exportadas de inventários novos (CSV, Excel, PDF) sem a coluna "Responsável Esperado".
- **SC-004**: 100% dos inventários anteriores à mudança permanecem consultáveis, com histórico íntegro (itens, conferências, divergências e ata).
- **SC-005**: A suíte de testes existente permanece 100% verde, com novos testes cobrindo: snapshot sem colaborador; responsável diferente sem divergência; bem sem responsável; divergência de local; imutabilidade do snapshot; inventário não altera cadastro; inventários existentes consultáveis.

## Assumptions

- **Conformidade atual**: já verificado no repositório que a conferência não compara colaborador (divergências são apenas de local/ausência) — a mudança é remover o dado do snapshot e das superfícies de exibição/documento, não alterar a lógica de comparação.
- **Dados históricos**: decisão H-1 (2026-09-24) — preservar integralmente: a coluna do snapshot e os dados já gravados de inventários anteriores permanecem no banco (sem migração destrutiva — Princípio VII); novos registros não a alimentam. Ata de inventário legado (definição no planning) lê o histórico gravado como está.
- **Ata de inventários legados**: decisão H-2 (2026-09-24) — a regeneração de ata de inventário legado preserva a coluna com o histórico gravado (valor comprobatório — a ata é prova do que era esperado na época); a ata de inventário novo não contém a coluna. Atas já emitidas não são reeditadas.
- **Feature 033 (offline)**: decisão H-3 — remoção do campo do pacote é imediata e global (legado e novo), por ser payload técnico transitório; o ajuste do contrato/data-model/testes dessa feature é feito dentro desta spec (alteração cruzada mínima), sem reabrir seu escopo.
- **Escopo**: somente o módulo de Inventário e suas superfícies diretas; módulos de patrimônio, colaboradores e movimentações permanecem intocados.

## Fora de escopo

- Qualquer alteração em movimentações, alocação/cautela ou seus fluxos e relatórios.
- Alteração no cadastro de colaboradores ou nas telas de outros módulos que exibem custódia atual do bem.
- Migração destrutiva ou remoção de colunas/dados históricos de inventários anteriores.
- Novos critérios de conformidade ou divergência no Inventário.
- Alteração de permissões, autenticação, auditoria ou backup.
