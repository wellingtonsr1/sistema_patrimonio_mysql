# Research: Inventário — Remover colaborador responsável do snapshot (feature 034)

**Data**: 2026-09-24 · **Spec**: [spec.md](spec.md) · **Plan**: [plan.md](plan.md)

Resolve os pontos de implementação restantes após o clarify (H-1/H-2/H-3). Todas as
decisões respeitam a Constitution (mudança mínima, sem migração destrutiva).

## D1 — Como a geração deixa de gravar o campo (sem migração)

**Decisão**: remover a atribuição `expected_custodian_name=...` em
`InventarioService._scope_query`-loop de criação de itens (e no caminho equivalente de
adição de itens). A coluna permanece no model (H-1) e fica `NULL` nos registros novos.

**Rationale**: parar de alimentar é a forma mínima e reversível; `nullable=True` já
permite registros sem o valor. Nenhuma migration, nenhum dado tocado.

**Alternatives considered**: remover a coluna do model — rejeitado (H-1: histórico;
e remover coluna do model sem remover do banco quebra o SQLAlchemy em legados).

## D2 — Como a ata decide entre "com coluna" (legado) e "sem coluna" (novo)

**Decisão**: **critério por presença de dado no inventário** — a coluna
"Responsável Esperado" aparece na ata **se e somente se** algum item do inventário tem
`expected_custodian_name` preenchido. Inventário novo (nunca grava) → coluna ausente
nas 3 exportações; inventário legado → coluna presente com o histórico (H-2). O valor
"Estoque / Livre" (para item sem custodiante em legado) permanece como hoje.

**Rationale**: um único critério simples e determinístico, sem novo flag no
inventário, sem depender de data de criação comparada com a data da feature (frágil),
e honesto: a ata exibe exatamente o que o snapshot daquele inventário registrou.

**Alternatives considered**:
- *Flag booleano no inventário* (`snapshot_sem_custodia`): exige migração aditiva e
  sincronização de estado — desnecessário quando a presença do dado já informa o caso.
- *Comparar `created_at` com a data de deploy*: frágil (ambientes fora de sync),
  rejeitado.

## D3 — Superfícies de tela: remover ou esconder

**Decisão**: **remover as referências do snapshot/conferência** nos 2 templates
(`detail.html`: linha do colaborador no card do item e no rodapé de local; 
`conferir.html`: "Colaborador esperado:"). Inventários legados não exibirão mais o
valor nas telas (a tela mostra a conferência, não a ata — e o critério de conferência
nunca foi o colaborador). O histórico continua íntegro no banco e na ata legado (H-2).

**Rationale**: o objetivo do input é que o colaborador **não seja utilizado como
critério de conferência**; exibi-lo na tela de conferência reafirma exatamente o que
se quer eliminar. A ata legado (H-2) preserva o histórico para comprovação — superfícies
corretas para cada propósito.

**Alternatives considered**: manter exibição condicional `if` em telas para legados —
rejeitado: manteria a responsabilidade como informação de conferência na interface,
contrariando o objetivo do input (a remoção na tela é uniforme; nada se perde, pois a
ata legado e o banco preservam o histórico).

## D4 — Pacote offline (033): remoção imediata e global

**Decisão**: remover as chaves `expected_custodian_id`/`expected_custodian_name` do
payload do pacote em `InventarioOfflineService.generate_package` para todo inventário
(H-3). Ajustar o contrato/data-model da 033 (`expected_custodian_id/name` fora da lista
de campos do FR-003 daquela feature) e o teste que asserta o campo. O client
(`inventario_offline.js`) não usa o campo para nada funcional (verificado).

**Rationale**: payload técnico transitório (H-3); nenhum comportamento do client depende
dele; remoção global evita dois formatos de pacote convivendo (simplicidade de contrato).

**Alternatives considered**: campo condicional por inventário legado — rejeitado: dois
formatos de pacote para nenhum ganho funcional (o client não usa o dado).

## D5 — Testes: novos + ajustes (Princípio VIII)

**Decisão**: em `tests/test_inventario.py`:
1. **Novos** (7 do input): snapshot de novo inventário sem colaborador (nenhum item com
   o campo); responsável diferente não gera divergência (conferência ENCONTRADO com
   custodiante do bem alterado entre criação e conferência); bem sem responsável
   participa normalmente; divergência de local continua; imutabilidade (alterar
   custodiante/local depois não muda snapshot); inventário não altera cadastro
   (reafirmado); ata: inventário novo SEM a coluna e inventário legado COM a coluna
   (D2), nos 3 formatos (CSV texto, Excel workbook, PDF buffer).
2. **Ajustes**: testes existentes que assertam `expected_custodian_name` na criação
   passam a assertar a ausência do valor em inventários novos (comportamento alterado
   pela spec — exceção prevista no Princípio VIII).
3. **033**: ajustar o teste do pacote que lista o campo entre os campos do FR-003.

**Rationale**: TDD (Constitution VIII); a ata é o ponto mais sensível — coberta nos
três formatos com o critério D2.

**Alternatives considered**: suite nova separada — rejeitado: o comportamento é do
Inventário e os testes já vivem em `test_inventario.py` (padrão do repositório).
