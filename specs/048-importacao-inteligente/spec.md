# Feature Specification: Importação Inteligente (Evolução dos Importadores CSV)

**Feature Branch**: `048-importacao-inteligente`

**Created**: 2026-09-26

**Status**: Draft

**Input**: Evoluir o mecanismo de importação de dados existente (CSV) para uma **Importação Inteligente** — análise automática do arquivo, identificação/mapeamento de colunas com confirmação do usuário, validação por registro, pré-visualização classificada (válidos/avisos/duplicados/erros), identificação de duplicidades e relacionamentos ausentes, respeito integral aos campos opcionais/obrigatórios existentes, cancelamento antes da gravação, gravação segura pelo mecanismo transacional vigente e relatório detalhado. Regra máxima: **ANALISAR → REUTILIZAR → ESTENDER → TESTAR** (nunca RECRIAR → SUBSTITUIR → REESTRUTURAR).

> **Fatos verificados no código (2026-09-26)**: o sistema JÁ POSSUI três importadores CSV com ciclo completo parse → preview → confirmação → execução → auditoria — **Equipamentos** (`import_service.py`: `parse_csv`, `preview_import`, `execute_import` com fluxo patrimonial via `MovementService` — feature 029), **Colaboradores** (`custodian_import_service.py`: matrícula opcional com provisória PROV-%06d da feature 014) e **Locais** (`location_import_service.py`: criação, duplicata por nome). Já existem: detecção de delimitador (`,`/`;`), normalização de colunas por aliases, validação por linha, preview com duplicatas, commit por linha, auditoria e permissões. Esta spec **extende** esse mecanismo — não cria importador paralelo.

---

## Clarifications

### Session 2026-09-26

- Q: Quando o responsável citado no CSV de equipamentos não existir no cadastro de colaboradores, o que o sistema deve fazer com aquela linha? → A: Resolução interativa na pré-visualização — para cada linha com responsável não encontrado, o usuário escolhe: atribuir a um colaborador existente (busca no cadastro), importar o equipamento sem custódia (com AVISO) ou pular a linha; nenhuma atribuição automática e nenhuma escolha silenciosa (decisão 2026-09-26).
- Q: Na confirmação final, o que deve acontecer com as linhas classificadas como duplicadas (tombamento já existente no banco)? → A: Manter o comportamento atual — a escolha existente 'pular duplicados' (skip_duplicates) é preservada e apenas explicitada na nova interface: marcada, duplicados são pulados; desmarcada, a reimportação atualiza o equipamento (comportamento da 029); nenhuma decisão linha a linha (decisão 2026-09-26).
- Q: Como o passo de mapeamento de colunas deve aparecer para o usuário na tela de importação? → A: Passo intermediário dedicado — após enviar o arquivo, uma etapa própria de mapeamento (tabela coluna → campo do sistema, com alterar/ignorar) antecede a pré-visualização; só avança após confirmado (decisão 2026-09-26).

## 1. Objetivo

Melhorar o processo atual de importação para que o administrador consiga, **antes de gravar qualquer dado**:

- ver o arquivo analisado automaticamente (formato, cabeçalho, colunas, registros);
- reconhecer e revisar o mapeamento de colunas (confirmar, alterar, ignorar);
- ver cada registro classificado individualmente (VÁLIDO / AVISO / DUPLICADO / ERRO / NÃO ENCONTRADO / IGNORADO);
- identificar duplicidades e relacionamentos ausentes **antes** da gravação;
- cancelar sem nenhum efeito no banco;
- confirmar a importação com gravação segura pelo mecanismo existente;
- receber um relatório detalhado por registro.

A análise/pré-visualização é operação **somente de leitura**: nada no banco é alterado até a confirmação explícita.

## 2. Fatos verificados no código (fonte das reutilizações — 2026-09-26)

| # | Fato | Consequência |
|---|---|---|
| F1 | **Importadores existentes**: rotas `/assets/import` (+`/confirm`), `/custodians/import` (+`/confirm`), `/locations/import` (+`/confirm`) em `app/web/routes.py`, com permissões `patrimonio.criar` (equipamentos) e guardas próprias de colaboradores/locais | Fluxo de duas fases (processar → confirmar) JÁ existe; a Importação Inteligente o aprimora, sem novas URLs paralelas |
| F2 | **Parser compartilhável**: `_detect_delimiter` (`,`/`;`), `parse_csv` com `COLUMN_ALIASES` (~50 aliases de tombamento/equipamento/categoria/etc.), normalização com remoção de acentos, `_validate_row` por linha (tombamento/equipamento/categoria obrigatórios) | A identificação automática de colunas **evolui os aliases existentes** (sem inventar mapeamentos perigosos); o parser não é duplicado |
| F3 | **Campos obrigatórios reais**: Equipamentos: tombamento, equipamento, categoria (local/responsável Opcionais — ausência tratada); Colaboradores: nome, email, cargo, setor (matrícula Opcional → provisória PROV-%06d, feature 014); Locais: nome, filial, departamento | As regras de obrigatoriedade são as existentes — não se universaliza obrigatório/opcional (§8/§9 do pedido) |
| F4 | **Fluxo patrimonial já preservado (029)**: entrada via `MovementService.create_movement` (`ENTRADA_AQUISICAO` + snapshots reais), custódia do CSV aplicada exclusivamente pelo motor de movimentações (`resolve_movement_type`), operador = usuário autenticado, unidade transacional **por linha** (erro de linha não deixa estado parcial nem impede as demais) | Nenhum segundo mecanismo de movimentação; a Importação Inteligente reapresenta e refina a classificação, não reescreve a execução |
| F5 | **Duplicidades existentes**: tombamento duplicado (skip ou update com reimportação — comportamento atual com `skip_duplicates`), serial_number duplicado, matrícula por `_find_by_registration_code`, email por `_find_by_email`, local por nome (`_find_existing_location`) | Classificação DUPLICADO deriva dessas verificações existentes; sem transformar o importador em "upsert global" |
| F6 | **Relacionamentos existentes**: custodiante resolvido por nome/matrícula (`_resolver_custodiante`); local por `LocationService.get_by_name`; local/custodiante ausentes no CSV = ausência legítima (nunca "Estoque Central"/fallback fabricado) | NÃO ENCONTRADO é classificação explícita; sem atribuição automática de outro colaborador/local |
| F7 | **Transacionalidade atual**: commit por linha com rollback da linha em erro (documentado e seguro — 029); preview nunca grava | Mantida; o pedido proíbe gravação parcial inesperada — o comportamento documentado da 029 é preservado e explicitado na confirmação |
| F8 | **Auditoria atual**: `write_audit` no confirm de cada importador (padrão `IMPORT_*`) | Reutilizada; sem segundo sistema de auditoria |
| F9 | **CSV suportado hoje**: UTF-8 (leitura `utf-8-sig` — BOM tratado), delimitador detectado, aspas/campo com vírgula pelo `csv.DictReader`, fixtures `tests/*.csv` com `;` (colaboradores) e `,` (equipamentos/locais) | O parser existente continua; alterações somente para detecção de arquivo vazio/sem registros/sem cabeçalho |
| F10 | **Testes existentes**: `test_import_asset_location.py`, `test_import_asset_movements.py`, `test_custodian_import.py`, `test_custodian_import_optional_matricula.py` (incluem equipamento sem local/sem responsável e matrícula mista) | Regras atuais já testadas devem permanecer verdes; novos testes cobrem a camada inteligente |

## 3. Escopo

### Incluído

- **Camada de análise pré-gravação** (só leitura) sobre os parsers existentes: detecção de arquivo vazio/sem registros/sem cabeçalho/corrompido; leitura do cabeçalho; identificação automática de colunas evoluindo os `COLUMN_ALIASES` existentes; mapeamento revisável pelo usuário (confirmar/alterar/ignorar); colunas desconhecidas marcadas como "não utilizada" (nunca descartadas em silêncio, nunca criadas no banco).
- **Classificação por registro**: VÁLIDO, VÁLIDO COM AVISO, DUPLICADO, ERRO, NÃO ENCONTRADO, IGNORADO — derivada das validações/verificações existentes (obrigatoriedade real de cada entidade, duplicidade de tombamento/matrícula/email/nome/serial, relacionamento de responsável e local), incluindo duplicidade **dentro do próprio arquivo**.
- **Pré-visualização detalhada** com resumo (total/válidos/avisos/duplicados/erros/ignorados) e tabela por linha (linha, identificadores, situação, problema), com filtros por classificação reutilizando componentes/tabelas existentes.
- **Confirmação explícita** com resumo antes da gravação; registros com ERRO não são gravados; tratamento de avisos conforme o comportamento atual (`skip_duplicates`); cancelamento sem nenhum efeito.
- **Gravação** pelos `execute_import`/`execute_custodian_import`/`execute_locations_import` existentes (mecanismo transacional vigente — commit por linha documentado da 029, rollback da linha em erro), com relatório final detalhado e reprocessamento (corrigir o CSV e reanalisar; a análise relê o estado atual do banco — nada duplicado).
- **Tratamento de ausências conforme regra real**: responsável/local ausentes permanecem ausentes quando o fluxo permite; colaborador/local inexistentes são classificados NÃO ENCONTRADO conforme o importador atual (equipamentos: linha rejeitada com mensagem clara — comportamento atual; locais: criação é regra existente do importador de locais); nenhum fallback fabricado ("Estoque Central", "Sem responsável", local padrão, usuário padrão).
- **Preservação de dados**: normalização (caixa/acentos/espaços) usada apenas para comparação; valores originais são os armazenados; matrícula ausente não é inventada (a provisória PROV-%06d só quando a regra existente da 014 se aplica ao fluxo — importadores de colaboradores).
- **Segurança de upload**: extensão/tamanho/conteúdo validados, mecanismos de upload existentes, sem execução de conteúdo, sem path traversal, sem armazenamento permanente desnecessário.
- **Compatibilidade**: rotas, permissões, templates e comportamentos dos importadores atuais preservados; a evolução acontece dentro do mesmo fluxo de telas.
- Documentação/ajuda atualizadas na mesma tarefa (Princípio XI).

### Não incluído (fora de escopo)

- Novo sistema de importação paralelo, "importador universal"/framework genérico, novo parser, nova tela de identidade própria, processamento assíncrono/filas/jobs (arquivos atuais são pequenos/médios), novos campos no banco por colunas desconhecidas, upsert global, criação automática de colaboradores por nome, fallbacks fabricados, segundo sistema de auditoria/permissões, alteração em movimentações/inventário/manutenção/relatórios/backup/AD/RBAC além do previsto.

## 4. User Scenarios & Testing *(mandatory)*

### User Story 1 — Análise e mapeamento de colunas antes da gravação (Priority: P1) 🎯

O administrador seleciona o tipo de importação, envia o CSV e o sistema analisa o arquivo sem gravar nada: formato detectado, cabeçalho lido, cada coluna identificada automaticamente (evoluindo os aliases existentes — ex.: `tombamento`, `TOMBAMENTO`, `nº tombamento`, `patrimonio` → Tombamento) e apresentada com o mapeamento sugerido. Colunas ambíguas são claramente marcadas como sugestão a confirmar; colunas desconhecidas aparecem como "não utilizada". O usuário ajusta o mapeamento em um **passo intermediário dedicado** (tela própria entre o upload e a pré-visualização — decisão 2026-09-26), confirmando/alterando/ignorando colunas, e só então segue para a análise dos registros.

**Why this priority**: é o núcleo da "inteligência" — evitar gravação com colunas erradas é o maior ganho de segurança.

**Independent Test**: com CSVs de cabeçalhos variados (canônico, com variações/acentos, com colunas desconhecidas), o sistema apresenta o mapeamento correto/ambíguo/não utilizado — sem tocar o banco.

**Acceptance Scenarios**:

1. **Given** CSV com cabeçalho `tombamento,descricao,local,responsavel,matricula`, **When** o arquivo é analisado, **Then** as colunas são mapeadas para Tombamento/Descrição/Local/Responsável/Matrícula conforme os aliases existentes, com o banco inalterado.
2. **Given** CSV com coluna `cor` sem campo correspondente, **When** analisado, **Then** `cor` aparece como "Coluna não utilizada" — nada é descartado em silêncio nem criado no banco.
3. **Given** coluna ambígua (`responsavel` × `nome` × `colaborador`), **When** analisada, **Then** o sistema apresenta o mapeamento como sugestão explícita exigindo confirmação, sem escolher silenciosamente.
4. **Given** arquivo vazio, sem registros, sem cabeçalho ou corrompido, **When** enviado, **Then** recebe erro compreensível (sem traceback) e nada é gravado.

---

### User Story 2 — Classificação por registro e pré-visualização sem gravação (Priority: P1)

Com o mapeamento confirmado, cada registro é avaliado **individualmente** pelas regras reais da entidade: obrigatórios presentes, opcionais tolerados, duplicidades (banco e dentro do arquivo), relacionamentos (responsável/local) verificados pelos mecanismos atuais. A pré-visualização mostra resumo e tabela por linha com situação e problema, com filtros (Todos/Válidos/Avisos/Erros/Duplicados/Ignorados). Nenhum dado é alterado na pré-visualização; o usuário pode cancelar.

**Why this priority**: um erro isolado não pode rejeitar o arquivo inteiro nem gravar dados errados — é a promessa central de segurança.

**Independent Test**: com CSVs mistos (válidos, incompletos, duplicados, responsável/local inexistente, sem local e sem responsável), cada registro recebe a classificação correta e o banco permanece inalterado.

**Acceptance Scenarios**:

1. **Given** arquivo com registros completos e incompletos (com/sem responsável, com/sem local), **When** analisado, **Then** cada registro é classificado individualmente conforme as regras existentes — o arquivo não é rejeitado em bloco.
2. **Given** registro somente com tombamento e descrição (local/responsável vazios), **When** as regras do fluxo permitirem, **Then** é VÁLIDO e será gravado com Local/Responsável ausentes (exibidos como "não informado" — rótulo de exibição na tela/relatório, não valor armazenado no banco) — sem inventar "Estoque Central" ou "Sem responsável".
3. **Given** tombamento já existente no banco, **When** analisado, **Then** o registro é DUPLICADO com a linha identificada, antes da gravação.
4. **Given** tombamento repetido dentro do próprio arquivo, **When** analisado, **Then** a duplicidade interna é identificada antes da gravação.
5. **Given** responsável/matrícula não encontrados no cadastro, **When** analisado, **Then** o registro é classificado NÃO ENCONTRADO com a mensagem clara ("Responsável não encontrado: João Silva / Matrícula: MAT-999") e, na pré-visualização, o usuário resolve linha a linha: atribuir a um colaborador existente (busca), importar sem custódia (com AVISO) ou pular a linha — nenhuma atribuição automática e nenhuma escolha silenciosa (decisão 2026-09-26).
6. **Given** qualquer análise, **When** o usuário cancela, **Then** o banco permanece exatamente como antes.

---

### User Story 3 — Confirmação, gravação segura e relatório (Priority: P1)

Após revisar, o administrador vê o resumo de confirmação (total/válidos/avisos/duplicados/erros) e confirma. A gravação usa os `execute_*` existentes (mecanismo transacional vigente — commit por linha documentado da 029 com rollback da linha em erro; registros com ERRO nunca gravados; avisos conforme o comportamento atual). Ao final, relatório detalhado por registro (importados/avisos/duplicados/erros/ignorados) e possibilidade de corrigir o CSV e reanalisar sem duplicar o já importado.

**Why this priority**: fecha o ciclo com segurança e rastreabilidade — a gravação reutiliza a arquitetura existente em vez de reinventá-la.

**Independent Test**: com o mesmo CSV misto, a confirmação grava somente os classificados permitidos, registra auditoria pelo padrão atual, produz relatório por linha e uma reanálise do mesmo arquivo identifica os já importados como duplicados.

**Acceptance Scenarios**:

1. **Given** pré-visualização com 1.210 válidos, 18 avisos, 10 duplicados e 5 erros, **When** o usuário confirma, **Then** somente válidos (e avisos conforme o comportamento atual) são gravados; erros nunca; duplicados conforme a escolha existente explicitada na confirmação (`skip_duplicates` marcado → pulados; desmarcado → reimportação atualiza, comportamento da 029 — decisão 2026-09-26).
2. **Given** erro durante a gravação, **When** ocorre, **Then** o comportamento é o documentado da 029 (linha com erro sofre rollback e não impede as demais; mensagem clara ao operador; resultado registrado) — sem estado parcial oculto.
3. **Given** importação concluída, **When** o relatório é exibido, **Then** mostra totais e o detalhe por linha (ex.: "Linha 18 — ERRO — Tombamento 000126 — já cadastrado").
4. **Given** o mesmo arquivo reenviado após a importação, **When** reanalisado, **Then** os registros já importados aparecem como DUPLICADO (estado atual do banco relido) — nada é duplicado.
5. **Given** qualquer confirmação, **When** concluída, **Then** a auditoria registra usuário/tipo/arquivo/quantidades/resultado pelo mecanismo existente, sem segredos.

### Edge Cases

- **CSV com BOM, ponto e vírgula, campos com vírgula/aspas, acentuação**: tratados pelo parser existente (`utf-8-sig`, detecção de delimitador, `csv.DictReader`) — casos de teste dedicados.
- **Encoding inválido**: erro compreensível sem traceback.
- **Colunas vazias e linhas em branco**: ignoradas com classificação IGNORADO na análise (sem erro).
- **Nome de local com diferenças de caixa/espaços/acentos**: comparação normalizada, valor original preservado ao gravar (regra atual de duplicata por nome).
- **Matrícula mista (com/sem)**: regra da 014 respeitada (provisória PROV-%06d apenas no fluxo de colaboradores, onde já existe); nenhum invento para equipamentos.
- **Local inexistente no CSV de equipamentos**: regra atual (linha rejeitada com mensagem clara) preservada; no importador de locais, criação é a regra existente.
- **CSV grande**: manter o fluxo atual (sem jobs/filas) — arquivos do órgão são pequenos/médios; limites atuais de upload preservados.
- **Segredo/credencial**: nunca registrado em auditoria/logs.

## 5. Requirements *(mandatory)*

### Functional Requirements

**Análise e mapeamento (US1)**

- **FR-001**: O sistema MUST analisar o arquivo (formato, cabeçalho, colunas, registros) **sem alterar o banco de dados** — a análise e a pré-visualização são operações somente de leitura.
- **FR-002**: A identificação automática de colunas MUST evoluir os aliases existentes de cada importador (`COLUMN_ALIASES` de equipamentos/colaboradores/locais), reconhecendo variações de caixa, acentos e abreviações já suportadas — sem inventar mapeamentos perigosos.
- **FR-003**: Mapeamento ambíguo MUST ser apresentado como **sugestão a confirmar** pelo usuário — nunca escolhido silenciosamente.
- **FR-004**: O usuário MUST poder revisar o mapeamento: confirmar, alterar a associação e ignorar/marcar coluna como não utilizada.
- **FR-005**: Colunas sem campo correspondente MUST ser exibidas como "não utilizada" — sem descartar em silêncio, sem gravar em banco sem campo correspondente e sem criar colunas/campos automaticamente.
- **FR-006**: Arquivos inválidos (vazio, sem registros, sem cabeçalho quando necessário, corrompido, encoding inválido, formato não suportado) MUST ser detectados previamente com mensagem compreensível — sem traceback.

**Classificação e preview (US2)**

- **FR-007**: Cada registro MUST ser classificado individualmente: VÁLIDO, VÁLIDO COM AVISO, DUPLICADO, ERRO, NÃO ENCONTRADO, IGNORADO — conforme as regras reais de cada entidade (F3), nunca por rejeição em bloco do arquivo.
- **FR-008**: Campos opcionais de cada entidade MUST ser tratados como opcionais (registrados como "não informado" quando ausentes e o fluxo permitir) — sem transformar todos os campos em obrigatórios ou opcionais, sem inventar valores substitutos ("Estoque Central", "Sem responsável", local/usuário padrão) que não existam como regra explícita.
- **FR-009**: Duplicidades MUST ser identificadas antes da gravação: tombamento/matrícula/email/serial/nome já existentes no banco (mecanismos atuais) e duplicidade dentro do próprio arquivo — com a linha indicada.
- **FR-010**: Relacionamentos (responsável/matrícula, local) MUST ser verificados pelos mecanismos atuais: colaborador inexistente → NÃO ENCONTRADO sem atribuição automática nem escolha por aproximação sem confirmação, com **resolução interativa na pré-visualização** (atribuir a colaborador existente via busca / importar sem custódia com AVISO / pular a linha — decisão 2026-09-26); local inexistente → regra atual de cada importador preservada (equipamentos: rejeição com mensagem; locais: criação).
- **FR-011**: A pré-visualização MUST apresentar resumo (total/válidos/avisos/duplicados/erros/ignorados) e tabela por linha (linha, identificadores, situação, problema), com filtros por classificação reutilizando componentes existentes.
- **FR-012**: A atualização de registro existente MUST permanecer exatamente como hoje (reimportação de equipamentos com `skip_duplicates`; locais e colaboradores operação de criação) — sem transformar a importação em "upsert global". Na nova interface, a escolha existente de pular/atualizar duplicados é **explicitada na confirmação** (decisão 2026-09-26): marcada → duplicados pulados; desmarcada → reimportação atualiza; sem decisão linha a linha.

**Confirmação, gravação e relatório (US3)**

- **FR-013**: Antes de gravar, o sistema MUST apresentar resumo de confirmação (quantidades por classificação) com opções de cancelar/voltar/confirmar; cancelar não produz efeito algum.
- **FR-014**: Registros classificados com ERRO MUST NOT ser gravados; avisos e duplicados seguem o comportamento atual (escolha `skip_duplicates` explicitada na confirmação e regras vigentes); nenhum modo "forçar importação" inventado.
- **FR-015**: A gravação MUST reutilizar `execute_import`/`execute_custodian_import`/`execute_locations_import` com a estratégia transacional vigente (commit por linha documentado da 029; rollback da linha em erro; erro informado claramente; resultado registrado) — sem gravações parciais ocultas, sem commits duplicados, sem estados intermediários inconsistentes.
- **FR-016**: O fluxo patrimonial MUST ser preservado: entrada e custódia exclusivamente via `MovementService.create_movement` (029) — nenhum segundo mecanismo de movimentação, nenhum preenchimento de campos que ignore o histórico.
- **FR-017**: O relatório final MUST apresentar totais e o detalhe por linha (linha, situação, identificadores, motivo); se existir mecanismo de exportação de erros, reutilizado.
- **FR-018**: Reprocessamento: reenviar o CSV corrigido reexecuta a análise contra o estado atual do banco — registros já importados aparecem como DUPLICADO (nada duplicado).
- **FR-019**: Normalização (caixa/acentos/espaços) MAY ser usada apenas para comparação; os valores originais MUST ser preservados ao gravar (nomes, descrições, acentos).
- **FR-020**: O formato CSV atual MUST ser preservado (delimitador detectado, `utf-8-sig`/BOM, aspas, campos com vírgula, quebras de linha) — o parser existente não é alterado sem necessidade; arquivos grandes seguem o fluxo atual (sem jobs/filas).

**Segurança, auditoria e compatibilidade**

- **FR-021**: Uploads MUST validar extensão, tamanho e conteúdo, reutilizando os mecanismos existentes; sem execução de conteúdo, sem path traversal, sem armazenamento permanente desnecessário.
- **FR-022**: Auditoria MUST usar o módulo existente (`write_audit`, padrão atual de cada importador) com usuário, tipo, arquivo, quantidades analisada/importada/rejeitada/ignorada, resultado e data/hora — nunca senhas/tokens/credenciais; nenhum segundo sistema de auditoria.
- **FR-023**: Permissões existentes de cada importador MUST ser reutilizadas (`patrimonio.criar` e guardas vigentes de colaboradores/locais); nova permissão só com justificativa, padrão RBAC, sem concessão automática e com testes.
- **FR-024**: Rotas, URLs e fluxos dos importadores atuais MUST continuar funcionando (compatibilidade — §36 do pedido); a evolução ocorre dentro do mesmo fluxo de telas, seguindo o padrão visual existente (nenhum CSS global novo, nenhuma nova identidade visual).
- **FR-025**: Nenhuma alteração MAY quebrar funcionalidades existentes fora do previsto: movimentações, inventário, manutenção, relatórios, backup, AD, RBAC, GLPI, 1Doc, e-mail permanecem intocados; sistema continua iniciando normalmente (verificado pela suíte).

### Key Entities *(include if feature involves data)*

- **Análise de arquivo (em memória)**: resultado somente leitura do parse existente — nome/arquivo, delimitador detectado, cabeçalho, colunas com mapeamento sugerido/confirmado/ignorado, total de registros. Nenhuma persistência própria.
- **Classificação de registro (em memória)**: situação por linha (VÁLIDO/AVISO/DUPLICADO/ERRO/NÃO ENCONTRADO/IGNORADO) + motivo legível, derivada das validações e verificações existentes.
- **Resultado de importação**: contadores e detalhe por linha produzidos pelos `execute_*` existentes (estruturas já retornadas hoje, refinadas na apresentação) + evento de auditoria existente.

## 6. Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das análises/pré-visualizações sem nenhuma escrita no banco (verificado por teste que conta escritas entre upload e confirmação).
- **SC-002**: 100% dos arquivos dos cenários de teste têm cada registro classificado individualmente (zero rejeição em bloco de arquivo com registros mistos).
- **SC-003**: 0 gravações com mapeamento ambíguo não confirmado; 0 colunas descartadas silenciosamente; 0 colunas/campos criados automaticamente no banco.
- **SC-004**: 0 valores fabricados ("Estoque Central", "Sem responsável", local/usuário padrão) onde não exista regra explícita — verificado por teste.
- **SC-005**: 100% das duplicidades (banco e interno ao arquivo) identificadas antes da gravação nos cenários de teste.
- **SC-006**: 0 registros com ERRO gravados na confirmação; 0 duplicações no reprocessamento do mesmo arquivo.
- **SC-007**: 0 alterações fora do previsto: suíte existente 100% verde (baseline atual: **775 passed**), rotas/URLs dos importadores preservadas.
- **SC-008**: 0 segredos em auditoria/logs; 100% das importações confirmadas registradas na auditoria existente.
- **SC-009**: Relatório final com 100% das linhas problemáticas identificadas por número de linha e motivo legível.

## 7. Pendências de decisão (estilo P-7 — detalhes de plan)

- **P-1**: forma de transporte do estado entre análise → mapeamento → preview → confirmação (o mecanismo atual serializa o CSV no formulário de confirmação — avaliar reuso vs. extensão mínima).
- **P-2**: rótulos finais das classificações na interface (VÁLIDO/AVISO/etc.) e cores dos badges existentes.
- ~~P-3~~ **RESOLVIDA no clarify (2026-09-26)**: passo intermediário dedicado de mapeamento, entre upload e pré-visualização.

## 8. Arquivos/módulos potencialmente afetados (preliminar — confirmar no plan)

- `app/services/import_service.py`, `custodian_import_service.py`, `location_import_service.py` — **extensões** (análise de cabeçalho/colunas, classificação por registro, duplicidade interna ao arquivo) sobre `parse_*`/`preview_*` existentes; `execute_*` intocados salvo ajuste mínimo de relatório.
- `app/web/routes.py` — evolução das rotas existentes de import (mesmas URLs; fases de análise/mapeamento no fluxo atual).
- `app/web/templates/assets/import.html` (e equivalentes de colaboradores/locais) — evolução das telas existentes.
- `tests/` — novos testes da camada inteligente + regressão dos existentes (`test_import_*`, `test_custodian_import*`).
- `docs/` + ajuda — atualização na mesma tarefa.
- **Intocáveis**: `movement_service` (motor), modelos, `permission_service` (a menos que justificado), auditoria, backup, AD, e-mail, 1Doc, GLPI, inventário, outras telas.

## 9. Assumptions

- Os três importadores existentes (Equipamentos, Colaboradores, Locais) são o universo desta feature; eventual quarto importador seria analisado no plan (varredura confirmará).
- O mecanismo de duas fases já existente (upload/preview → confirm) permanece a base do fluxo; a "inteligência" entra como análise/mapeamento/classificação antes da confirmação.
- Arquivos do órgão são pequenos/médios (centenas a poucos milhares de linhas) — nenhum processamento assíncrono.
- Aderência integral à Constitution v1.0.0 (I menor alteração possível; II/III camadas/services; IV fluxo patrimonial intocável; VI/RBAC; VII banco aditivo — aqui nada; VIII testes; IX auditoria; X UI; XI docs; XII validação).
