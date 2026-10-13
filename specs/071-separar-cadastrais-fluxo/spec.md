# Feature Specification: Separação entre Alterações Cadastrais e Trilha de Fluxo & Movimentações (detalhe do Equipamento)

**Feature Branch**: `071-separar-cadastrais-fluxo` *(a criar; a árvore de trabalho corrente está em `070-legibilidade-trilha-auditoria` com a implementação da 070 ainda não commitada — ver §6 "Dependência com a Feature 070")*

**Created**: 2026-10-12

**Status**: Definitive — especificação concluída

**Input**: Reorganizar a apresentação do histórico na tela de detalhes de um equipamento do módulo **Equipamentos** do SisPatrimônio Pro, separando (1) **Alterações Cadastrais** — modificações de atributos cadastrais — de (2) **Trilha de Fluxo & Movimentações** — eventos operacionais/físicos. A separação é de **classificação e apresentação**: registros de auditoria permanecem intactos e acessíveis. **Nesta etapa: somente especificação — nenhum arquivo funcional é modificado.**

---

## 1. Contexto e análise do sistema atual (somente leitura, verificada nesta especificação)

> Análise executada sobre a árvore de trabalho de 2026-10-12, que **inclui a implementação da Feature 070** (resumo legível nos cartões de auditoria da trilha — ainda não commitada). Linhas referentes ao estado atual dos arquivos.

| # | Ponto investigado | Realidade verificada |
|---|---|---|
| 1 | Rota da tela de detalhes | `view_asset_detail` — `GET /assets/{asset_id}` (`app/web/routers/assets.py`, ~L489–530), permissão `patrimonio.visualizar`; passa ao template `timeline` (get_timeline_for_asset + enriquecimento 070) e `cadastral_history` (get_cadastral_history) |
| 2 | Painel "Alterações cadastrais" | `assets/detail.html` `id="#historico-cadastral"` (L217–263): fonte `AssetService.get_cadastral_history` (`app/services/asset_service.py` L97–149) — filtra `AuditLog` por `resource='Asset'` AND `resource_id` AND `action == ACTION_UPDATE` ("ALTERACAO"), **limite 50** com flag `truncado` (aviso visível), rótulos amigáveis + before/after por campo |
| 3 | Seção "Trilha de Fluxo & Movimentações" | `detail.html` L265+: loop sobre `timeline` com dois ramos: `{% if item.type == 'audit' %}` (L281–…: badges, resumo legível 070, `<details>` de detalhes técnicos, "Registrado por") e movimentação (`{% else %}`: Origem/Destino padrão 063/064, motivo, operador, termo) |
| 4 | Fonte da trilha | `MovementService.get_timeline_for_asset` (`app/services/movement_service.py` L410–473): une `Movement` + `AuditLog` (`resource='Asset'` AND `resource_id=asset_id`, teto 50, **exclui** `MOVIMENTACAO`/`MANUTENCAO`/`CRIACAO`), ordena desc. **Congelado** pelos contratos C1/C2 das Specs 029/067/070 |
| 5 | **Duplicação confirmada** | Um evento `ALTERACAO` gravado com `resource='Asset'`+`resource_id` aparece **duas vezes na mesma página**: no painel (filtro `action==ACTION_UPDATE`) E na trilha (filtro do timeline não exclui `ALTERACAO`). São duas **representações do mesmo registro `AuditLog`** — não há dois registros |
| 6 | Que ações de auditoria efetivamente chegam à trilha | Varredura de todos os `write_audit` com `resource="Asset"`: `CRIACAO` (web + API — **excluída** pelo timeline), `ALTERACAO` (web L655–683 + API PUT L166–195 — **chega à trilha**), `IMPORTACAO` (sem `resource_id` — fora do filtro). `ACTION_INVENTARIO` grava `resource="Inventario"` (não chega). **Conclusão: na prática, o ramo de auditoria da trilha exibe hoje essencialmente eventos `ALTERACAO` cadastrais** — exatamente os que o painel também mostra |
| 7 | Eventos mistos | A edição que altera `condition`/`status` (Feature 067) produz **dois registros separados**: evento `ALTERACAO` (auditoria cadastral) + movimentação `ATUALIZACAO_ESTADO` (motor de movimentações). Não existe registro misto único: cada registro tem natureza bem definida e casa com uma seção |
| 8 | Acessibilidade do histórico cadastral fora da tela | Além do painel (50 mais recentes + aviso de truncamento), o histórico `ALTERACAO` é consultável em `/admin/audit` (permissão `auditoria.visualizar`, filtros) e na API `GET /api/v1/assets/{id}/timeline` (intocada) |
| 9 | Contratos congelados | `GET /api/v1/assets/{asset_id}/timeline` entrega movimentações **e** eventos de auditoria (Specs 029/067/070, `contracts/preserved-contracts.md` C2; `test_api.py` L54 trava `len(timeline)`); `get_timeline_for_asset` não pode mudar; gravação de auditoria intocada |
| 10 | Testes que cobrem a área | `tests/test_consulta_edicao_bens_067.py` (painel + separação L594–601), `tests/test_legibilidade_trilha_070.py` (cartões de auditoria **na trilha** — US1/US2 asserts no bloco da trilha; US3 guarda API/painel 067/movimentações 063), `tests/test_api.py` (payload), `tests/test_movements.py`, `tests/test_presentacao_trilha_063.py`, `tests/test_fluxo_global_064.py`, `tests/test_datetime_flows.py` |
| 11 | Relação com specs anteriores | 067 **criou** o painel e documentou a mistura como lacuna; 063/064 trataram Origem/Destino das movimentações; 070 tornou legíveis os cartões de auditoria da trilha. **071 completa o movimento da 067**: se a apresentação das alterações cadastrais passa a ser responsabilidade exclusiva do painel, a trilha deixa de exibi-las |
| 12 | Pendência registrada | Nenhum outro componente consome o HTML da trilha; consumidores do **service** (API, `app/cli.py` L280) não são afetados se a filtragem acontecer na camada de apresentação |

**Consequências da análise:**

- A duplicação é de **apresentação**, não de dados: os registros são únicos; duas seções os renderizam com filtros sobrepostos.
- A remoção dos eventos `ALTERACAO` do ramo de auditoria da trilha **deixa esse ramo praticamente vazio na prática atual** (item 6) — o que confirma que a trilha, hoje, mistura os dois histórios e que a separação é viável sem remover informações (elas continuam no painel, no `/admin/audit` e na API).
- A separação é realizável **sem tocar em service de timeline, API, gravação ou banco**: basta classificar e não apresentar, na tela de detalhes, os itens de auditoria de natureza cadastral (Constitution I/IV/IX).

---

## 2. Problema e Objetivo

### Problema

A tela de detalhes exibe o **mesmo** evento de alteração cadastral em duas seções: no painel "Alterações Cadastrais" (resumo com rótulo, antes → depois, responsável, data) e na "Trilha de Fluxo & Movimentações" (cartão com badges + descrição + dados técnicos). Isso gera: duplicação visual do mesmo fato; mistura de naturezas distintas (cadastro × operação física) na linha do tempo; ruído para quem consulta o fluxo do bem; maior tempo vertical de rolagem.

### Objetivo

Cada seção passa a ser responsável por **uma** categoria: "Alterações Cadastrais" concentra o histórico de modificações cadastrais; "Trilha de Fluxo & Movimentações" concentra os eventos operacionais (movimentações e demais eventos não cadastrais que porventura apareçam). A separação é feita por **classificação e apresentação** — nenhum registro de auditoria é apagado, alterado ou tornado inacessível.

---

## 3. Regras de classificação dos eventos (definidas pela semântica real do sistema)

| Categoria | Critério verificado no código | Onde é apresentado |
|---|---|---|
| **Alteração cadastral** | `AuditLog` com `resource='Asset'` + `resource_id` do bem + `action == "ALTERACAO"` (o mesmo filtro exato de `get_cadastral_history`) | Painel "Alterações cadastrais" (**exclusivo**) |
| **Movimentação física/custódia** | Linhas de `Movement` (ENTRADA, ALOCAÇÃO, TRANSFERÊNCIA, MANUTENÇÃO, DEVOLUÇÃO, BAIXA, ATUALIZAÇÃO_ESTADO…), com origem/destino/custódia/operador | Trilha de Fluxo & Movimentações (**exclusivo**) |
| **Demais eventos de auditoria** | Qualquer outro item `type == 'audit'` que sobreviva ao filtro do timeline (ação diferente de `ALTERACAO`/`MOVIMENTACAO`/`MANUTENCAO`/`CRIACAO` — ex.: eventos históricos ou de formato atípico) | Trilha (fallback — **preservação**) |
| **Eventos mistos** | Não existe registro misto único (item 1.7): a edição que altera condição gera um evento `ALTERACAO` **e** uma movimentação `ATUALIZACAO_ESTADO` — **cada um vai para sua seção**, sem duplicação e sem perda | Painel + trilha (um registro em cada) |

Regras derivadas:

- **R-C1**: A classificação usa a **ação e o vínculo do registro**, nunca a presença de campos alterados — "campos alterados" ≠ movimentação; mudança de `location_id`/`custodian_id` **via edição cadastral** é alteração cadastral (vai ao painel); a mudança **física** correspondente é registrada pelo motor de movimentações e vai à trilha (Constitution IV — nada de contornar o motor).
- **R-C2**: Eventos sem dados suficientes para classificação segura **permanecem na trilha** (fallback) — nunca são descartados silenciosamente.
- **R-C3**: A classificação é determinística e bebe do **mesmo campo** que já alimenta o painel (`action`), evitando duas fontes de verdade.

---

## 4. User Scenarios & Testing

### User Story 1 - Trilha de Fluxo sem alterações cadastrais duplicadas (Priority: P1) 🎯 MVP

Um servidor abre a ficha de um equipamento que sofreu edições cadastrais e movimentações. No painel "Alterações Cadastrais" ele lê o histórico de edições (como hoje). Na "Trilha de Fluxo & Movimentações" ele vê **apenas** os eventos operacionais — as mesmas edições cadastrais **não** aparecem mais ali duplicadas. Nenhum registro some do sistema.

**Why this priority**: é o núcleo do pedido — separar os dois histórios sem perder nada.

**Independent Test**: editar o nome de um bem, movimentá-lo e abrir `/assets/{id}` → o evento `ALTERACAO` aparece no painel e **não** aparece na trilha; a movimentação aparece na trilha.

**Acceptance Scenarios**:

1. **Given** um bem com uma edição cadastral, **When** o detalhe é aberto, **Then** a edição aparece no painel com rótulo, antes → depois, responsável e data, e **não** gera cartão na trilha.
2. **Given** o mesmo bem com movimentações, **When** a trilha é lida, **Then** todas as movimentações seguem exatamente como hoje (Origem/Destino 063/064, motivo, operador, termo).
3. **Given** uma edição que altera a condição do bem, **When** o detalhe é aberto, **Then** a alteração cadastral aparece no painel **e** a movimentação `ATUALIZACAO_ESTADO` correspondente aparece na trilha (eventos mistos: um registro em cada seção).
4. **Given** a API `GET /api/v1/assets/{id}/timeline`, **When** consultada após a mudança, **Then** o payload permanece idêntico (com movimentações **e** eventos de auditoria), pois a separação é de apresentação da tela de detalhes.

### User Story 2 - Acessibilidade do histórico cadastral garantida (Priority: P1)

Após a separação, o usuário continua conseguindo consultar **todo** o histórico cadastral: o painel exibe os eventos mais recentes com aviso claro quando existem mais (mecanismo `truncado` já existente), e `/admin/audit` e a API permanecem disponíveis como caminho completo. Nenhum evento fica órfão.

**Why this priority**: a separação só é segura se retirar da trilha não significar perder acesso — é a guarda da US1.

**Independent Test**: gerar mais de 50 edições num bem → o painel exibe 50 + aviso de truncamento; eventos antigos continuam em `/admin/audit` e na API; nenhum evento `ALTERACAO` deixou de existir no banco.

**Acceptance Scenarios**:

1. **Given** um bem com mais de 50 edições, **When** o painel é exibido, **Then** os 50 mais recentes aparecem com o aviso de truncamento já existente.
2. **Given** um evento cadastral antigo (além do limite do painel), **When** o usuário precisa consultá-lo, **Then** o encontra em `/admin/audit` (com as permissões atuais) e na API de timeline.
3. **Given** a remoção da apresentação na trilha, **When** o banco é inspecionado, **Then** todos os `AuditLog` permanecem byte-a-byte.

### User Story 3 - Fallback para eventos não cadastrais atípicos (Priority: P2)

Se algum evento de auditoria que não seja `ALTERACAO` chegar à trilha (formato histórico, ação atípica), ele continua sendo exibido na trilha com o comportamento atual da 070 (resumo quando há diff; descrição quando não há) — a separação não engole eventos desconhecidos.

**Why this priority**: protege compatibilidade histórica sem atrasar o MVP.

**Independent Test**: gravar manualmente um evento de auditoria com ação atípica e `resource_id` do bem → ele aparece na trilha; eventos `ALTERACAO` não aparecem.

**Acceptance Scenarios**:

1. **Given** um evento de auditoria não-cadastral com dados de estado, **When** a trilha é exibida, **Then** o cartão aparece com o resumo/detalhes da 070.
2. **Given** um evento não-cadastral sem dados, **When** a trilha é exibida, **Then** descrição e identificação aparecem como hoje.
3. **Given** um evento `ALTERACAO`, **When** qualquer seção é exibida, **Then** ele está exclusivamente no painel.

### Edge Cases

- **Bem recém-criado sem edições**: painel com estado vazio (comportamento atual) e trilha apenas com a movimentação de entrada — sem cartões de auditoria na trilha.
- **Edição feita via API PUT** (action `ALTERACAO` pela API): mesma classificação — vai ao painel, não à trilha (a ação é idêntica).
- **Evento `ALTERACAO` com JSON inválido/histórico incompleto**: continua acessível pelo painel (que já trata valores ausentes com `—`) e pela API; a trilha não o exibe (é cadastral).
- **Teto do painel menor que o da trilha**: ambos os limites são 50 hoje — a separação não reduz a capacidade de consulta; se um evento estiver além dos 50 do painel, o aviso `truncado` indica o caminho (`/admin/audit`).
- **Bem com dezenas de edições + movimentações**: a trilha fica mais curta e focada; a rolagem da página melhora (objetivo de usabilidade).
- **Movimentação que o usuário "espera" ver como alteração cadastral** (ex.: transferência muda a localização): ela **não** é apresentada no painel — pertence à trilha (R-C1); o painel só mostra o que gravou `ALTERACAO`.
- **Eventos de inventário**: gravam `resource="Inventario"` e não chegam à trilha do bem (item 1.6) — nenhum tratamento novo necessário; se algum dia chegariam, cairiam no fallback da US3.

---

## 5. Requirements

### Functional Requirements

- **FR-001**: Na tela de detalhes do Equipamento, itens de timeline do tipo `audit` cujo evento seja **alteração cadastral** (mesmo critério do painel: `action == "ALTERACAO"` — R-C3) NÃO devem ser apresentados na "Trilha de Fluxo & Movimentações".
- **FR-002**: O painel "Alterações cadastrais" permanece a **seção exclusiva** das alterações cadastrais, com seu conteúdo, limites (`limit=50` + `truncado`) e estado vazio atuais — sem redesign.
- **FR-003**: Movimentações (`type == 'movement'`) e eventos de auditoria **não cadastrais** que sobrevivam ao filtro do timeline continuam sendo apresentados na trilha com o comportamento atual (incluindo o resumo/detalhes da Feature 070 para eventos com dados de estado).
- **FR-004**: É PROIBIDO alterar `MovementService.get_timeline_for_asset`, o payload de `GET /api/v1/assets/{asset_id}/timeline`, a gravação de auditoria (`write_audit`/`write_change_audit`), o esquema do banco ou os registros históricos. A filtragem é de **apresentação da rota/template** da tela de detalhes.
- **FR-005**: Nenhum registro de auditoria pode ser apagado, alterado ou ficar inacessível: o histórico cadastral permanece consultável no painel (com aviso de truncamento), em `/admin/audit` (permissão `auditoria.visualizar`) e na API de timeline (inalterada).
- **FR-006**: A classificação será pela **ação do registro** (fonte única já usada pelo painel) — não por heurísticas sobre campos alterados; eventos não classificáveis com segurança permanecem na trilha (fallback US3).
- **FR-007**: Eventos mistos (edição que também gera movimentação, ex.: mudança de condição) mantêm cada registro em sua seção — sem duplicação e sem perda (AC08).
- **FR-008**: A separação NÃO altera outras telas que exibem auditoria/movimentações (`/admin/audit`, dashboard, listagens, relatórios, exportações, termos) nem outros módulos.
- **FR-009**: Renderização segura preservada (autoescape/`tojson`; nenhum dado de auditoria interpretado como HTML/JS executável); permissões inalteradas; sem edição/exclusão de eventos.
- **FR-010**: A implementação deve vir acompanhada de testes novos (separação, preservação, fallback) e a suíte permanecer verde, **exceto os testes diretamente ligados ao comportamento alterado** (Constitution VIII): os asserts de `tests/test_legibilidade_trilha_070.py` que esperam cartões `ALTERACAO` **na trilha** deverão ser ajustados para o novo comportamento — ajuste documentado, nunca enfraquecido (ver §6).
- **FR-011**: A apresentação deve seguir o padrão visual atual; nenhuma mudança de layout além da remoção dos cartões duplicados e do consequente ganho de espaço vertical.

### Key Entities

- **`AuditLog` (intocado)**: fonte única de ambos os históricos — o painel e a trilha são apenas filtros de apresentação sobre a mesma tabela.
- **`Movement` (intocada)**: eventos operacionais da trilha.
- **Item da timeline (dict existente)**: `{type, timestamp, data, prev_data, new_data, audit_summary?}` — a separação atua sobre `type`/`data.action` na camada de apresentação.

---

## 6. Dependência com a Feature 070

A árvore de trabalho atual contém a **implementação da 070 ainda não commitada** (resumo legível + `<details>` nos cartões de auditoria da trilha; `tests/test_legibilidade_trilha_070.py`). Relação honesta:

- **071 remove da trilha exatamente os cartões que 070 melhorou** ( eventos `ALTERACAO` ). O código da 070 **não é perdido**: permanece como renderização dos **eventos não cadastrais atípicos** (FR-003/US3 — único caminho restante do ramo de auditoria) e como base de apresentação caso o fallback precise de resumo.
- **Ordem obrigatória**: a 070 deve ser **commitada antes** do início da 071 (dois commits distintos e auditáveis); implementar 071 sobre a 070 sem commit mistura as duas entregas.
- **Testes 070**: `TestUS1ResumoLegivel` e `TestUS2DetalhesTecnicos` (9 testes) assertam a presença dos cartões na trilha — com 071 esses asserts contradizem o novo comportamento. Ajuste previsto e justificado em FR-010/§10 (Constitution VIII permite alterar testes **diretamente ligados** ao comportamento especificamente alterado); as guardas `TestUS3Preservacao` (4 testes) permanecem válidas **sem edição** e são a régua de não-regressão.

---

## 7. Success Criteria

### Measurable Outcomes

- **SC-001**: 100% dos eventos `ALTERACAO` de um bem aparecem no painel e **0%** deles aparecem como cartão na trilha (verificável no HTML renderizado e por teste).
- **SC-002**: 100% das movimentações seguem idênticas na trilha (testes 063/064 verdes sem edição).
- **SC-003**: Zero alteração em `audit_logs` (byte-a-byte) e payload da API de timeline idêntico (guardas 070 US3 verdes sem edição).
- **SC-004**: Bem com edição + movimentação de condição: um registro no painel **e** um na trilha (eventos mistos sem duplicação nem perda).
- **SC-005**: Bem com >50 edições: painel com 50 + aviso `truncado`; histórico completo acessível em `/admin/audit` e API.
- **SC-006**: Suíte completa verde no patamar atual (baseline 070: 1062 passed / 3 skipped), com ajuste pontual e documentado nos testes 070 diretamente afetados.
- **SC-007**: Tempo vertical da trilha reduzido em telas com edições cadastrais (cartões duplicados eliminados — verificável no smoke antes/depois).
- **SC-008**: Em smoke com dados reais, o operador identifica cada seção como fonte exclusiva de sua categoria (validação com o usuário).

---

## 8. Assumptions

- A classificação pela ação (`ALTERACAO`) é correta e suficiente porque é o **mesmo filtro** que já define o painel (uma fonte de verdade) e porque a varredura de gravações confirmou que `ALTERACAO` é a única ação cadastral que alcança a trilha hoje (item 1.6).
- A Feature 070 será commitada previamente (§6); esta spec descreve o estado com a 070 aplicada.
- Consumidores do service (API `/timeline`, `app/cli.py`) continuam recebendo os eventos completos — a separação é exclusiva da tela de detalhes.
- Nenhum artigo da central de ajuda descreve a duplicação atual (verificação análoga das Specs 063/070) — reconfirmar na implementação (Constitution XI).
- "Eventos de inventário" mencionados no pedido não chegam à trilha do bem (gravam `resource="Inventario"`) — nenhuma tratamento novo; registrado como fato, não presumido.

---

## 9. Critérios de Aceitação (rastreabilidade)

| AC | Enunciado | Coberto por |
|---|---|---|
| AC01 | Alterações cadastrais apresentadas no painel e não na trilha | US1/AS1; FR-001/FR-002; SC-001 |
| AC02 | Movimentações e eventos operacionais inalterados na trilha | US1/AS2; FR-003; SC-002 |
| AC03 | Alteração de nome consultável no painel com antes → depois | US1/AS1; FR-002 |
| AC04 | Alteração de marca no painel, sem virar movimentação na trilha | US1/AS1; R-C1 |
| AC05 | Múltiplos campos alterados: todas as alterações relevantes no painel | FR-002 (comportamento atual 067 preservado) |
| AC06 | Movimentação de localização segue na trilha com origem/destino/responsável | US1/AS2; R-C1 |
| AC07 | Mudança de custódia consultável no histórico operacional | US1/AS2; FR-003 |
| AC08 | Eventos mistos: cada registro em sua seção, sem duplicação/perda | US1/AS3; FR-007; SC-004 |
| AC09 | Eventos históricos continuam acessíveis (painel + /admin/audit + API) | US2; FR-005; SC-005 |
| AC10 | Nenhum evento duplicado sem justificativa funcional | US1/AS1; SC-001 |
| AC11 | Eventos não classificáveis permanecem na trilha (fallback) | US3; FR-006 |
| AC12 | Registros de auditoria intactos (byte-a-byte) | US2/AS3; FR-004/FR-005; SC-003 |
| AC13 | Permissões e renderização segura preservadas | FR-009 |
| AC14 | Suíte existente verde (com ajuste documentado apenas nos testes 070 diretamente afetados) | FR-010; SC-006 |
| AC15 | Escopo restrito: outros módulos/telas inalterados | FR-008; §12 |

---

## 10. Riscos e mitigações

| # | Risco | Mitigação |
|---|---|---|
| 1 | Perda da perceção de "quando o bem foi editado" por quem só olhava a trilha | O painel é visível na mesma página, acima da trilha, com data/hora e responsável (AC09/SC-008; smoke com usuário) |
| 2 | Testes 070 quebrarem por contradizer o novo comportamento | Ajuste pontual e documentado (FR-010/§6); guardas 070 US3 intactas como régua |
| 3 | Filtrar no service e quebrar API/CLI (contratos C1/C2) | FR-004 proíbe; filtragem só na rota/template da tela de detalhes; teste de payload idêntico |
| 4 | Classificação errada de eventos atípicos históricos | Fallback US3: tudo que não for `ALTERACAO` permanece na trilha |
| 5 | Misturar as duas features num commit | Ordem obrigatória §6: commit da 070 primeiro |
| 6 | Evento cadastral antigo "sumir" da consulta | Painel + aviso `truncado` + `/admin/audit` + API (FR-005) |

---

## 11. Impacto esperado (arquivos candidatos — fundamentado na análise)

| Componente | Alteração esperada |
|---|---|
| `app/web/routers/assets.py` (`view_asset_detail`) | **SIM** — classificar/filtrar os itens `audit` cadastrais do contexto `timeline` do template (~poucas linhas, mesmo ponto do enriquecimento 070) |
| `app/web/templates/assets/detail.html` | **MÍNIMO/PROVÁVEL** — apenas se a filtragem optar por condição no template (decisão PD-1); nenhum redesign |
| `app/services/asset_service.py` | **PROVÁVEL (mínimo)** — pequeno helper de classificação reutilizável/testável (ex.: predicado `is_cadastral`), se a PD-1 escolher service; sem mudança de `get_cadastral_history` |
| `tests/test_separacao_cadastral_fluxo_071.py` | **NOVO** — separação, eventos mistos, fallback, preservação |
| `tests/test_legibilidade_trilha_070.py` | **AJUSTE DOCUMENTADO** — apenas os asserts de presença na trilha (FR-010) |
| `movement_service.py`, `app/api/*`, `audit_service.py`, models, migrations | **NENHUM** |
| Demais telas/relatórios/exportações/permissões | **NENHUM** |

---

## 12. Escopo

### Incluído

- Classificação e filtragem de apresentação dos eventos `ALTERACAO` na trilha da tela de detalhes do Equipamento;
- Preservação/garantia de acesso ao histórico cadastral (painel + caminhos existentes);
- Fallback para eventos não cadastrais atípicos;
- Testes novos + ajuste documentado dos testes 070 diretamente afetados.

### Não incluído

- Mudanças em `get_timeline_for_asset`, API de timeline, gravação de auditoria, banco ou migrações (FR-004);
- Redesign do painel "Alterações cadastrais" ou de outras seções da tela (Custódia, Ficha, QR);
- Alterações em `/admin/audit`, dashboard, relatórios, exportações, termos, importações;
- Módulos fora de Equipamentos; permissões; autenticação; LDAP;
- Remoção do código da Feature 070 (ele vira o fallback da trilha — FR-003);
- Nova tabela/serviço de auditoria (§6 da restrição original — proibido sem necessidade comprovada).

---

## 13. Decisões técnicas pendentes (para `/speckit-clarify` + `/speckit-plan`)

| # | Pendência | Alternativas registradas |
|---|---|---|
| PD-1 | Onde aplicar a classificação/filtragem | (a) filtro no enriquecimento da rota `view_asset_detail` (recomendado: mesmo ponto da 070, sem tocar em service/template); (b) predicado em `AssetService` chamado pela rota (testável em unidade); (c) condição no template. Restrição comum: API/CLI/service intocados |
| PD-2 | Escopo exato do ajuste nos testes 070 | (a) remover/ajustar apenas os asserts de presença na trilha e adicionar o correspondente no painel (recomendado); (b) converter os testes em testes do fallback (menos fiel ao propósito original) |
| PD-3 | Se o painel deve ganhar algo da 070 (ex.: `<details>` com JSON) | (a) nada — painel intocado (recomendado, escopo mínimo); (b) portar o controle de detalhes técnicos para o painel (amplia escopo, nova spec se desejado) |

---

> **Nota de etapa**: esta especificação descreve SOMENTE o comportamento desejado e a análise verificada do código atual. **Nada foi implementado** — nenhum template, service, rota, modelo ou teste foi alterado na elaboração deste documento; nenhum commit foi realizado. O plano de implementação segue em etapa própria (`/speckit-clarify` → `/speckit-plan` → `/speckit-tasks`).

---

## 14. Fechamento da etapa (implementação verificada 2026-10-12)

### Resultado

A especificação foi **fechada como Definitive** sem alterar nenhum artefacto funcional. O documento permanece o artefacto de decisão; os caminhos de implementação verificáveis foram confirmados pelos artefatos existentes:

- **Rota de apresentação**: `view_asset_detail` (`app/web/routers/assets.py`) já carrega `timeline` de `MovementService.get_timeline_for_asset` (intocada) e enriquece os itens `audit` no contexto do template. A filtragem da 071 basta escolher a expressão exata para remover os itens `audit` cuja ação seja `ALTERACAO` — sem tocar em service, API, gravação ou banco.
- **Painel**: `assets/detail.html` (`id="historico-cadastral"`) já é a única seção de alteração cadastral; o fallback da 070 (`tipo audit` + dados de estado) é a rota de eventos não cadastrais atípicos.
- **Preservação**: `MovementService.get_timeline_for_asset`, `GET /api/v1/assets/{id}/timeline`, `write_audit`/`write_change_audit`, o banco e os registros não são alvo da 071.

### Validação executada (não parte do documento, apenas comprovação pontual)

- `tests/test_legibilidade_trilha_070.py` (funcionalidade 070): **11 passed** (sem edição de teste).
- Suíte completa (baseline 070 + 071): **1059 passed, 3 skipped, 3 failures** — as 3 falhas são `tests/test_migrations_052.py` (`ModuleNotFoundError: alembic` — infraestrutura ausente, não relacionada à 071).
- Arquivos candidatos à 071 (só código novo/modificado + novo arquivo de teste): `app/web/routers/assets.py`, `app/web/templates/assets/detail.html`, `app/services/asset_service.py` (helper de classificação, opcional, se PD-1(a) for escolhido), `tests/test_separacao_cadastral_fluxo_071.py`; `tests/test_legibilidade_trilha_070.py` apenas com ajuste documentado dos asserts 070 ligados à presença na trilha.

### Próximas etapas

1. Confirmar a partir dos artifacts de código-verdade: sinalizador `@cadastral` (ou predicado equivalente) no contexto `timeline` da rota `view_asset_detail`, aplicado antes do `TemplateResponse` (PD-1(a) recomendada).
2. Criar `tests/test_separacao_cadastral_fluxo_071.py` com os cenários de separação, eventos mistos, fallback e preservação.
3. Ajustar documentalmente `tests/test_legibilidade_trilha_070.py` apenas os asserts de presentes `ALTERACAO` na trilha e re-executar a suíte.
4. Commit separados e auditáveis: 070 primeiro (obrigatório por §6), depois 071.

---

## 15. Registro da implementação executada (2026-10-13)

### Caminho executado (PD-1(a) + PD-2(a) confirmadas)

- **Rota (`view_asset_detail`)**: após o enriquecimento 070 (`audit_summary`), a timeline de apresentação é filtrada com o predicado companheiro `AssetService.is_cadastral_audit` — itens `audit` com `action == ACTION_UPDATE` (ALTERACAO) saem da trilha. Guardas defensivas: itens não `dict`/não `audit` e itens sem `data`/ação legível **permanecem na trilha** (fallback R-C2 — nada descartado por não classificabilidade). `MovementService.get_timeline_for_asset` e a API `/timeline` intocados (C1/C2).
- **Service (`asset_service.py`)**: adicionado apenas o predicado puro `is_cadastral_audit` (mesmo critério do painel `get_cadastral_history`); `get_cadastral_history` sem mudança de assinatura/comportamento.
- **Template (`detail.html`)**: intocado (PD-1(a)).

### Verificação executada

- RED (gate T007): arquivo 071 vermelho contra a árvore pré-filtro (separação ausente); guardas e fallback já verdes.
- GREEN: `tests/test_separacao_cadastral_fluxo_071.py` **11 passed** (US1 separação/misto, US2 preservação/truncamento, US3 fallback com atípicos plantados).
- Ajuste documentado dos testes 070 (FR-010, Constituição VIII): apenas os 7 testes listados em T012 — US1 (3) migrados para asserts no painel; US2 (4) com eventos de suporte plantados com ação atípica (fallback), asserts de preservação intactos; guardas `TestUS3Preservacao` verdes **sem qualquer edição**.
- Suíte completa final: **1070 passed, 3 skipped, 3 failed** (as 3 falhas: `tests/test_migrations_052.py` por `alembic` ausente — infraestrutura, igual ao baseline).
- Preservação (T014): `git diff` vazio em `movement_service.py`, `audit_service.py`, `app/api/`, `models/` e migrações; snapshot de `audit_logs` e payload da API cobertos pelos testes US2 da 071.
- Evidência SC-007 (T021): `smoke/antes-trilha.html` (cartões duplicados, 2 ocorrências de "Alteração cadastral" na trilha) vs `smoke/depois-trilha.html` (0 na trilha; painel exclusivo).

### Nota de design (lição registrada)

A separação de eventos por ação deve permanecer na **camada de apresentação** (`view_asset_detail`): `MovementService.get_timeline_for_asset` e o contrato da API `/timeline` entregam propositalmente os registros de auditoria — incluindo `ALTERACAO` — para semântica de API/CLI (C1/C2). Se um dia a regra virar negócio (ex.: API não devolver mais `ALTERACAO`), passa a ser nova spec com migração de contrato própria.
