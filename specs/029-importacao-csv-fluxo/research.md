# Phase 0 Research: Registrar no Fluxo as movimentações da importação CSV de equipamentos

**Feature**: 029-importacao-csv-fluxo | **Date**: 2026-09-21

Pesquisa executada por leitura do código real nesta sessão (evidências com arquivo/linha).
Nenhum [NEEDS CLARIFICATION] permanece.

## 1. Fatos verificados no código (D1–D10)

| # | Fato (prova) | Evidência |
|---|---|---|
| **D1** | **O importador contorna o motor de movimentações**: `execute_import` cria o `Asset` com `location_id=location_id` direto no construtor e, em seguida, monta uma `Movement` manualmente via `db.add`, com `movement_type=MovementType.ACQUISITION`, `origin_location_name="Importação CSV"`, `origin_custodian_name="Sistema"`, `term_code=f"TR-CSV-{datetime.now().year}-{asset.id:04d}"`, `reason=f"Cadastro em massa via importação CSV (Linha {i})"` e `operator_name=operator_name` (default `"Importação CSV"`). | `app/services/import_service.py` — bloco "Criar novo asset" + "Registrar movimentação de entrada" |
| **D2** | **A coluna de custodiante/colaborador não é processada**: `COLUMN_ALIASES` de `import_service.py` não tem nenhuma entrada para custodiante/colaborador/responsável; `execute_import` nunca consulta `Custodian`; o CSV real de carga `docs/doc_proviśorios/docs_para_testes/doc-final/equipamentos.csv` traz a coluna `Custodiante` (nome do colaborador) — hoje silenciosamente ignorada. O importador nunca define `asset.custodian_id`. | `COLUMN_ALIASES` (alias de "localizacao" existe; de custodiante não) + ausência de `custodian` no `execute_import` |
| **D3** | **Reimportação não movimenta**: no ramo `existing and not skip_duplicates` (atualização), o importador altera apenas campos cadastrais (name, category, brand, model, serial, invoice, supplier, value, date, condition, notes) e NUNCA localização/custódia — nem estado, nem histórico. Linha repetida com `skip_duplicates=True` é apenas contada como `skipped`. | `import_service.py` — bloco "Atualizar existente" |
| **D4** | **`MovementService.create_movement` faz commit atômico por movimentação** (`db.commit()` no fim) e valida a matriz (VAL-002..VAL-008). `operator_name` vem de `MovementCreate.operator_name` (default `"Operador do Sistema"`; nas movimentações manuais web o formulário envia o nome do operador). | `app/services/movement_service.py` L18–245 + `app/web/routes.py` `create_movement_form` |
| **D5** | **A matriz implementada** (para ALOCACAO/TRANSFERENCIA): nenhuma alteração efetiva → erro VAL-002; alocação exige custodiante (VAL-003); mudança só de local com mesmo responsável → proibida como ALOCAÇÃO, é `TRANSFERENCIA_LOCAL` (VAL-004/VAL-006); entrega a novo colaborador → deve ser `ALOCACAO_CAUTELA` (VAL-007, com termo `TR-{ano}-{seq:05d}` gerado automaticamente quando `generate_term` ou tipo ALLOCATION/RETURN_STOCK); devolução redundante ao estoque → erro VAL-008. A decisão de tipo a partir de (local atual, custodiante atual, local destino, custodiante destino) está implícita nessas validações. | `movement_service.py` L91–141 |
| **D6** | **O Fluxo lê de fonte única real**: `MovementService.get_timeline_for_asset` combina `Movement` + `AuditLog` (descartando ações `CRIACAO`/`MOVIMENTACAO`/`MANUTENCAO` para não duplicar o que já é movimentação) e alimenta a tela de detalhe do bem (`web/routes.py` L689) e `/api/v1/assets/{id}/timeline`. Para aparecer no Fluxo, o registro precisa existir na tabela `movements` — a auditoria da importação não aparece como movimentação. | `movement_service.py` `get_timeline_for_asset` + `web/routes.py` L689 + `test_api.py` L50–54 |
| **D7** | **Auditoria da importação existe e é independente, fora do service**: as rotas `/assets/import/confirm` (web) e `/api/v1/assets/import/csv` (API) chamam `write_audit(ACTION_IMPORT, module="Patrimônio", resource="Asset", user=request.state.user, ...)` **após** `execute_import`. O `write_audit` faz `db.commit()` — portanto não pode ser movido para dentro de `execute_import` sem alterar a transação do lote (decisão R9). | `web/routes.py` L560–586 + `api/assets_api.py` L211–227 + `audit_service.py` L186 |
| **D8** | **Padrão do cadastro manual para a entrada do bem** (`AssetService.create`): `Asset` criado com `status = IN_USE if initial_custodian_id else AVAILABLE`, movimentação inicial `ACQUISITION` com snapshots reais (`origin_location_name="Fornecedor / Entrada Inicial"`, `origin_custodian_name="Almoxarifado Geral"`, `destination_*` preenchidos quando há local/custodiante inicial, `term_code=f"TR-INIC-{ano}-{asset.id:04d}"`, `operator_name=data.initial_operator or "Sistema"`). **Importante**: o cadastro manual também não usa `create_movement` para a entrada (bem ainda não existe no momento da movimentação) — a entrada é `Movement` construída no service de cadastro com snapshots reais. | `app/services/asset_service.py` L126–198 |
| **D9** | **Modelo User** possui `full_name` (String 150, opcional) e `username` (String 100). As telas/sessões usam o usuário em `request.state.user`. A spec exige "nome de exibição do usuário autenticado" como operador da movimentação. | `app/models/user.py` |
| **D10** | **Testes existentes de importação que dependem do comportamento atual**: `tests/test_import_asset_location.py` (13 testes). Comportamento atual verificado no código: coluna de localização **reconhecida** com valor inexistente **já** gera erro de linha e pula a criação do bem (bloco de resolução de local com `errors.append` + `continue`), e o teste `test_import_localizacao_valida_nao_importa_com_local_inexistente` cobre isso e está verde no baseline; o teste `test_import_localizacao_inexistente` importa sem local apenas porque usa a coluna `loc`, que **não é alias reconhecido** pelo parser (o próprio arquivo documenta esse fato em `test_import_com_alias_loc`). Ou seja: **o comportamento atual já é o exigido pela FR-013** — nenhum ajuste de teste existente é necessário. Os 13 testes (local válida, vazia, aliases, múltiplas linhas, sem coluna) são preservados sem alteração. | `tests/test_import_asset_location.py` (lido integralmente nesta sessão) + bloco de resolução de local em `execute_import` |

## 2. Decisões de estratégia (justificadas, com alternativas rejeitadas)

### R1 — Entrada do bem importado segue o padrão do cadastro manual (D8)

**Decisão**: ao criar equipamento novo via CSV, a movimentação de entrada `ACQUISITION` passa a ser construída com **snapshots reais**: origem `"Fornecedor / Entrada Inicial"` / `"Almoxarifado Geral"`, destino = local resolvido do CSV (ou "Estoque Central" quando ausente), `new_status = AVAILABLE` (a entrada não aloca), `reason` com motivo patrimonial claro (mencionando importação CSV), `operator_name` = nome de exibição do usuário autenticado, termo `TR-INIC-{ano}-{id}` (padrão do cadastro manual; a entrada não é cautela — não gera `TR-` sequencial de termo de responsabilidade). A exigência de spec FR-008 (sem snapshots fabricados que caracterizem falsa custódia/operador) fica plenamente atendida.

**Alternativas rejeitadas**:
- *Roteirizar a criação pela `AssetService.create`* — duplicaria validações/tags e alteraria contratos (`AssetCreate`) sem necessidade; o importador tem fluxo próprio de duplicatas/serial.
- *Chamar `create_movement` para a entrada* — impossível: o bem ainda não existe quando a entrada é registrada (mesma razão pela qual o cadastro manual não faz isso — D8); exigiria alterar a ordem de criação/commit, alteração maior e sem ganho patrimonial.
- *Manter "Importação CSV"/"Sistema" como origem* — é a fabricação que a spec proíbe (FR-008): registra falsa custódia/operador e corrompe a leitura do Fluxo.

### R2 — A coluna de custodiante entra pelos aliases e resolve pelo cadastro; nome não encontrado = erro de linha

**Decisão**: `COLUMN_ALIASES` recebe entradas canônicas `custodiante`/`colaborador` (com variações usuais: `custodian`, `responsavel`, `responsável`), normalizadas pelo mecanismo existente (`_normalize_column_name`, que já trata acentos/caixa). No `execute_import`, a linha com custodiante informado resolve pelo cadastro por **nome exato** (`Custodian.name`, primeiro match por `ilike` exato; por fim busca por matrícula como fallback documentado — CSVs de carga costumam usar nome, mas matrícula é o identificador oficial). Nome não encontrado → **erro na linha** ("colaborador 'X' não encontrado no cadastro de colaboradores"), bem não cadastrado, espelhando o tratamento já existente para local inexistente. Valor vazio/branco (ex.: `" "` no CSV real) = ausência de custodiante.

**Por quê**: FR-001/FR-012 proíbem inventar colaborador; o erro de linha é o mesmo padrão do local (comportamento do importador, preservado para local) e mantém a simetria local/custodiante que o planejamento de tarefas vai implementar.

O erro/pulo de linha já implementado para local inexistente já atende à FR-013 — a implementação apenas o preserva e o espelha para o custodiante (T014).

**Alternativas rejeitadas**:
- *Criar colaborador implicitamente* — proibido (FR-001/FR-012).
- *Ignorar silenciosamente (como hoje)* — é exatamente o bug da spec: o estado iria para um caminho e o histórico para outro.
- *Alocar "primeiro nome parecido"* — inventaria dados (falsa alocação, risco de homônimos sem controle).

**Critério determinístico para nomes duplicados no cadastro** (remediação C1 do analyze): a resolução por nome usa `filter(Custodian.name.ilike(nome_exato))` **com `order_by(Custodian.id)`** (primeira ocorrência determinística entre bancos) e é documentada na docstring; se o CSV informar matrícula válida, a resolução por `registration_code` tem precedência (identificador oficial, sempre único).

### R3 — Custódia do CSV aplicada exclusivamente via `MovementService.create_movement`; commit por linha

**Decisão**: no `execute_import`, após criar/atualizar o `Asset` (com `db.flush()` para materializar o `id`), a custódia é aplicada **somente** quando há mudança efetiva (ver R4): monta-se `MovementCreate(asset_id, movement_type=<decisão R5>, destination_location_id, destination_custodian_id, reason=..., operator_name=<usuário autenticado>, generate_term=True)` e chama-se `MovementService.create_movement(db, data)`, que atualiza o estado do bem, grava a movimentação e faz `commit`. Para garantir a unidade da linha (spec FR-019/K), o importador passa a **commitar por linha** (`db.commit()` após cada linha processada com sucesso; em erro da linha: `db.rollback()` e report no resultado — as demais linhas seguem o comportamento atual do lote). O fluxo de erro de linha existente (`errors.append(...)`) é preservado.

**Por quê**: FR-002/FR-003 (mesma operação de domínio; tipos existentes); D4 mostra que `create_movement` já é atômico por movimentação — o commit por linha fecha a unidade transacional da linha dentro do padrão do importador (que hoje commita o lote inteiro no fim); o rollback por linha evita estado parcial do bem (equipamento alocado sem movimentação), que é o requisito K da spec.

**Alternativas rejeitadas**:
- *Aplicar custódia direto no `Asset` e gravar `Movement` manualmente (como hoje)* — é o bug: contorna o motor (Constitution IV) e duplica regras.
- *Commit único do lote + rollback total em qualquer erro* — mudaria radicalmente o comportamento atual do lote (linhas boas perderiam a importação por causa de uma linha ruim) e quebraria o contrato do resultado (`imported/skipped/errors`) da UI.
- *Transaction begin/commit aninhado com SAVEPOINT* — complexidade sem precedentes no projeto e ganho nulo sobre commit por linha (que já isola a linha).

### R4 — Regra de mudança efetiva: decidir pela diferença de local e custodiante (reimportação)

**Decisão**: a comparação é sempre **estado atual do bem (após o flush de atualização cadastral) × destino informado no CSV**:
- custodiante do CSV ausente **na reimportação** = manter custódia atual (não desalocar) — carga de dados cadastrais não tem semântica de devolução; devolução continua sendo operação manual (`DEVOLUCAO_ESTOQUE`);
- local do CSV ausente na reimportação = manter local atual (comportamento atual);
- `resolve_movement_type` devolve `None` quando local e custodiante são iguais aos atuais → **nenhuma movimentação** (FR-015).

**Por quê**: FR-014/FR-015 distinguem os três caminhos (criar/atualizar/reimportar); a semântica "ausente = manter" é o comportamento atual do importador para local e evita devoluções falsas em cargas parciais; a devolução real continua manual, única operação com essa semântica no sistema.

**Alternativa rejeitada**: ausente = desalocar (devolução) — fabricaria movimentação de devolução a partir de CSV, invertendo a regra da spec FR-009/FR-010 (não inventar movimentações).

### R5 — `MovementService.resolve_movement_type`: a matriz como fonte única, sem tocar o motor

**Decisão**: novo método **estático e puro** em `MovementService`: `resolve_movement_type(current_location_id, current_custodian_id, dest_location_id, dest_custodian_id) -> Optional[MovementType]`, com a tabela de decisão:

| local atual × destino | custodiante atual × destino | resultado |
|---|---|---|
| igual | igual | `None` (nenhuma movimentação — VAL-002) |
| igual | diferente | `ALOCACAO_CAUTELA` (VAL-003/004) |
| diferente | igual | `TRANSFERENCIA_LOCAL` (VAL-004/006) |
| diferente | diferente (destino com custodiante) | `ALOCACAO_CAUTELA` (VAL-007 — entrega com termo) |
| estoque (sem custodiante) → custodiante | qualquer local | `ALOCACAO_CAUTELA` (alocação existente) |
| custodiante → estoque (destino sem custodiante) | — | **não aplicável via CSV** (devolução é operação manual — R4) |

Sem efeitos colaterais, sem DB, sem mutação — `create_movement` **continua intocado** e permanece o executor com todas as validações (o importador depende das validações do motor, não as reimplementa). O método é reutilizável por futuras telas (ex.: pré-visualização de importação) sem duplicação.

**Por quê**: atende FR-004 (matriz centralizada em `MovementService`) sem alterar o comportamento do motor (Princípio I); extrai em forma legível a decisão que hoje está implícita nas validações VAL-002..VAL-007 (D5) — exatamente a mesma lógica, agora consultável.

**Alternativas rejeitadas**:
- *Importador decide o tipo com ifs próprios* — duplicaria a matriz (proibido FR-004/Constitution III).
- *Chamar `create_movement` com tipo "chute" e deixar o erro VAL-002 travar* — transformaria reimportação idêntica em erro falso para o operador (viola FR-015/cenário E: "não deve aparecer como erro falso").

### R6 — Novo equipamento com custodiante + localização: entrada (ACQUISITION sem custódia) + alocação (ALOCACAO_CAUTELA)

**Decisão**: para equipamento novo importado com custodiante e/ou localização: (1) cria o bem **disponível** (`AVAILABLE`, sem custodiante) com a movimentação de entrada real (R1) apontando o local do CSV como destino da entrada; (2) se o CSV informar custodiante, chama `create_movement` com `ALOCACAO_CAUTELA` para o custodiante + local → status `IN_USE`, termo sequencial padrão `TR-{ano}-{seq:05d}`, operador = usuário autenticado. Para bem novo sem custodiante, apenas (1) — com local ou sem local conforme o CSV (sem movimentação extra). Isso produz, no Fluxo, a sequência patrimonialmente correta: **entrada no acervo → entrega/cautela ao responsável**, exatamente como um cadastro manual com alocação inicial seguida de movimentação.

**Por quê**: FR-006/SC-003 (histórico reconstrói a atribuição); FR-007 (termo padrão); a `ALOCACAO_CAUTELA` é o tipo já existente para entrega a colaborador (FR-003/FR-011) e reutiliza as validações VAL-003 (exige custodiante) do motor; evita sobrecarregar a entrada com custódia (que hoje é fabricada e falsa — D1).

**Alternativas rejeitadas**:
- *Entrada já alocada (status IN_USE direto, como o cadastro manual com custodiante inicial)* — exigiria que a entrada fabricasse a custódia (exatamente o problema atual) ou duplicasse no importador a lógica de snapshots de custódia do cadastro manual; a entrada+alocação separadas usam o motor para a custódia e mantêm a matriz como fonte única (FR-004).
- *Uma única movimentação "de importação"* — exigiria tipo novo (proibido) ou falsa ALOCAÇÃO para bem sem custodiante (proibido FR-009).

### R7 — Reimportação com mudança: atualização cadastral + movimentação da diferença

**Decisão**: no ramo de atualização (D3), após atualizar os campos cadastrais existentes, o importador compara local/custodiante atuais × destino do CSV via `resolve_movement_type` (R4): se devolver tipo, chama `create_movement` (commit da unidade); se devolver `None`, nenhuma movimentação (reimportação idêntica — FR-015). Histórico anterior é preservado por construção (`create_movement` só adiciona; nada é apagado — FR-017).

**Por quê**: FR-016/SC-003; reutiliza o mesmo caminho da criação (uma única implementação de custódia no importador, sem duplicação).

**Alternativa rejeitada**: continuar sem movimentar na atualização (comportamento atual) — é metade do bug da spec (mudança real sem histórico).

### R8 — Operador da movimentação = usuário autenticado (nome de exibição)

**Decisão**: `execute_import` recebe `operator_name: Optional[str] = None`. As rotas web e API passam o usuário autenticado já disponível em `request.state.user` (D7): `full_name` quando existir, senão `username` (D9). Fallback de compatibilidade (nenhuma rota usa, apenas chamadas diretas/testes sem operador): `"Importação CSV"` — que deixa de ser o valor default do parâmetro atual. `MovementCreate.operator_name` recebe esse valor; o Fluxo exibe o operador real (FR-005/SC-001). Nenhuma rota usa usuário fictício nem o colaborador do CSV como autor.

**Por quê**: FR-005; o padrão `full_name or username` é o dado de exibição já disponível nas rotas; o importador não conhece request (camadas — Constitution II).

**Alternativas rejeitadas**:
- *"Sistema"* — proibido pela spec (FR-005) quando há usuário autenticado.
- *Passar o objeto `User` até o service* — acoplaria o service ao modelo de autenticação sem ganho (o campo da movimentação é o nome de exibição).
- *Importador lendo request/contexto global* — viola camadas.

### R9 — Auditoria `ACTION_IMPORT` permanece nas rotas, fora da transação do lote

**Decisão**: nada muda nos eventos: as rotas continuam chamando `write_audit(ACTION_IMPORT, ...)` **após** `execute_import` (D7). O `execute_import` NÃO passa a chamar `write_audit` (o `write_audit` comita a sessão — mover para dentro quebraria a unidade por linha e duplicaria o evento por rota). A auditoria da importação e a movimentação patrimonial continuam conceitos distintos (FR-018): uma importação com alocação gera auditoria de importação + movimentação patrimonial; uma linha sem custódia gera apenas a auditoria da operação.

**Por quê**: FR-018/FR-021 (auditoria preservada, sem duplicação); D7 (transação).

**Alternativa rejeitada**: mover a auditoria para dentro do importador — mudaria transacionalidade e duplicaria o evento entre web/API.

### R10 — Testes: estratégia

**Decisão**: novo arquivo `tests/test_import_asset_movements.py` cobrindo os cenários A–L da spec, nos padrões existentes: fixture `db_session` (SQLite em memória), criação de locais/colaboradores de apoio como em `test_import_asset_location.py` (D10), chamada de `execute_import` com `operator_name` explícito, verificação de `Movement` via query e do Fluxo via `MovementService.get_timeline_for_asset`. Para o cenário J (usuário autenticado), teste de integração com `TestClient` seguindo o padrão de autenticação da suíte (`test_api.py`); para K (falha transacional), monkeypatch de `MovementService.create_movement` para levantar `ValueError` e verificação de que o bem não fica alocado sem movimentação. **Nenhum teste existente é modificado**: `tests/test_import_asset_location.py` permanece integral (13 testes — o comportamento de erro para local inexistente já é o exigido pela FR-013, ver D10); os novos cenários (colaborador inexistente, erros de linha) entram apenas no arquivo novo.

**Por quê**: Princípio VIII; a spec exige os cenários A–L; nada é modificado em testes existentes.

**Alternativa rejeitada**: espalhar os testes pelos arquivos existentes — o arquivo dedicado documenta a feature e evita conflito com testes pré-existentes.
