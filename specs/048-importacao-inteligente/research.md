# Research: 048 — Importação Inteligente

**Data**: 2026-09-26 · **Feature**: `048-importacao-inteligente` · **Spec**: [spec.md](spec.md)

Todas as decisões partem de fatos verificados no código (2026-09-26). Formato: Decisão → Racional → Alternativas.

---

## R1 — Análise de colunas sobre os aliases existentes (`analyze_columns`)

**Decisão**: função `analyze_columns(content, kind)` na camada compartilhada (`import_intelligence.py`) que lê apenas o cabeçalho (mesma `_detect_delimiter` + `csv` já vigentes) e sugere o campo canônico de cada coluna usando **os `COLUMN_ALIASES` do `kind` selecionado** — o "em união" refere-se à camada compartilhada consumir as 3 tabelas dos services sem duplicar código; a análise de UM arquivo usa apenas a tabela do importador escolhido (esclarecimento A1). Cada coluna recebe uma sugestão com confiança: `auto` (alias direto, inclui variações de caixa/acentos já cobertas pela normalização existente), `ambigua` (colisão: a reversão alias→campo devolve 2+ campos canônicos **do mesmo kind** — o exemplo cross-entity "responsavel" NÃO é ambiguidade, pois o kind já foi escolhido pelo usuário na tela) ou `desconhecida`. A coluna `nº tombamento`/`patrimonio` já é coberta pelos aliases atuais — nada é inventado.

**Racional**: os aliases já são a inteligência de mapeamento do sistema (~50 entradas só em equipamentos); evolui-los na apresentação atende §5 do pedido sem criar segundo mecanismo. A confiança `ambigua` materializa o "não escolher silenciosamente" (FR-003).

**Alternativas**: (a) biblioteca externa de fuzzy matching — rejeitada: dependência nova proibida em espírito pelo pedido (§42) e desnecessária dado o alias map existente; (b) renomear/refatorar `COLUMN_ALIASES` dos services — rejeitada: quebraria compatibilidade (Princípio I); a camada compartilhada apenas os **consome**.

---

## R2 — Camada compartilhada `import_intelligence.py` (sem framework universal)

**Decisão**: novo módulo com exatamente três responsabilidades transversais aos três importadores: (1) `analyze_columns`, (2) `classify_rows` (casca que chama as validações/verificações existentes de cada service), (3) detecção de duplicidade interna ao arquivo (chave natural: tombamento para equipamentos, matrícula/email para colaboradores, nome para locais). Regras específicas de entidade (obrigatoriedade, normalização de categoria, movimento) **permanecem** nos services de cada importador.

**Racional**: §35 do pedido proíbe framework genérico, mas também proíbe triplicar parser/validação/preview (§1). A fronteira é clara: o que os três compartilham (análise/classificação/preview) vai para a camada; o que é específico fica em cada service. Três consumers, zero abstração especulativa.

**Alternativas**: (a) triplicar a lógica nos 3 services — rejeitada: duplicação direta proibida; (b) transformar os services em plugins de um motor genérico — rejeitada: §35 e Princípio I (reestruturação).

---

## R3 — Classificação por registro como casca sobre o que existe

**Decisão**: `classify_rows(rows, db, kind, mapping, overrides)` classifica cada linha em VALIDO/AVISO/DUPLICADO/ERRO/NAO_ENCONTRADO/IGNORADO reutilizando, na ordem: (1) `_validate_row` do service (obrigatórios reais — F3); (2) duplicidade interna ao arquivo (R2); (3) verificações de duplicata do banco já existentes (tag, serial, matrícula, email, nome do local); (4) resolução de relacionamentos existente (`_resolver_custodiante` por matrícula→nome, `LocationService.get_by_name`). Campos opcionais ausentes geram AVISO informacional ("Responsável não informado"), **sem** bloquear quando a regra atual os permite (F3: equipamentos; a nota do pedido §9/§10).

**Racional**: o importador atual mistura "rejeição na leitura" (linhas com erro nem entram no preview — `parse_csv` descarta) e verificação na execução. A camada inteligente **reapresenta** essas mesmas regras por linha ANTES da execução, sem alterá-las — o `execute_*` continua sendo a última instância (defesa em profundidade).

**Alternativas**: (a) reescrever as validações na camada nova — rejeitada: duplicação de regra e risco de divergência; (b) classificar só na execução — rejeitada: é exatamente o que o pedido quer mover para antes da gravação.

---

## R4 — Resolução interativa de NÃO ENCONTRADO (clarify 2026-09-26)

**Decisão**: linhas com responsável inexistente recebem na preview três ações por linha: `skip` (linha pulará), `sem_custodia` (grava sem custodiante — regra de opcionalidade de equipamentos permite) e `assign:<custodian_id>` (busca reutilizando a pesquisa existente de colaboradores; preview mostra os candidatos quando a busca por nome é ambígua). Os overrides viajam na confirmação como JSON no formulário oculto (mesmo transporte do `csv_rows`) e a camada aplica **antes** do `execute_import`: linhas resolvidas com colaborador entram com `custodiante` preenchido; `sem_custodia` entram com custodiante vazio; `skip` são removidas do lote. **Nenhuma mudança em `execute_import`** — o service executa como se o CSV tivesse chegado daquele jeito.

**Racional**: materializa a decisão do clarify mantendo o `execute_import` como única instância de gravação (Princípio III/IV — nenhuma regra nova de custódia; o motor de movimentações continua resolvendo `resolve_movement_type`).

**Alternativas**: (a) atribuição automática por proximidade de nome — proibida (§12/F6); (b) criar colaborador na hora — proibida (F6/NUNCA do `_resolver_custodiante`); (c) resolver na execução — rejeitada: perderia a revisão prévia que é o propósito da feature.

---

## R5 — Fases nas mesmas URLs (`step` server-rendered)

**Decisão**: o par upload→preview atual ganha a fase de mapeamento **sem URL nova**: `POST /assets/import` (com `file`) renderiza o passo de mapeamento (`step=map`) com o arquivo serializado em campo oculto (mesmo padrão `csv_rows|tojson` já vigente nos confirm); `POST /assets/import` com `step=analyze` (mapeamento + arquivo oculto) renderiza a preview classificada com filtros; `POST /assets/import/confirm` (existente) recebe as linhas resolvidas + `skip_duplicates` explicitado. O mesmo nos três importadores (custodians/locations). Server-rendered, sem JS novo além do existente.

**Racional**: §36 do pedido (não quebrar URLs) + P-3 do clarify (passo dedicado) + padrão do projeto (server-rendered, textarea oculto já vigente em 3 templates).

**Alternativas**: (a) URLs novas (`/assets/import/map`) — rejeitada: à primeira vista viola §36 e cria superfície de permissão nova; (b) wizard client-side em JS — rejeitada: quebra o padrão server-rendered do projeto (Princípio X).

---

## R6 — Arquivos inválidos: guardas na análise

**Decisão**: a camada valida na análise (e a rota apresenta mensagem amigável, sem traceback): arquivo vazio/só BOM; sem registros (só cabeçalho); sem cabeçalho utilizável (todas as colunas vazias/duplicadas); `UnicodeDecodeError` (encoding inválido) capturado; tamanho > limite já vigente (10 MB no template). CSV corrompido (aspas não fechadas) → `csv.Error` capturado com linha aproximada.

**Racional**: §27 do pedido; o parser atual já cobre delimitador/BOM/aspas (F9) — só faltam as guardas de estado vazio/corrompido, que hoje produziriam tela estranha ou exceção.

**Alternativas**: biblioteca de detecção de encoding (`chardet`) — rejeitada: dependência nova sem necessidade; `utf-8-sig` + fallback com mensagem é suficiente para o cenário do órgão.

---

## R7 — Normalização para comparação, original para gravação

**Decisão**: toda comparação (duplicidade interna, duplicata de banco, relacionamento) usa os normalizadores já existentes (`_fold` com remoção de acentos, `_normalize_registration_code` trim+upper, `ilike` no SQL). O valor gravado continua sendo o do CSV após o `strip()` já vigente nos services — acentos e caixa originais preservados (§25 do pedido).

**Racional**: é exatamente o comportamento atual dos três services (ex.: `CustodianService` normaliza matrícula mas grava o nome como veio); a feature não altera isso, apenas o explicita nos testes (Teste L — encoding/acentuação).

**Alternativas**: normalizar ao gravar — rejeitada: destruiria informação original (§25) e mudaria comportamento existente.

---

## R8 — Relatório final: enumeração de linhas nos resultados (aditivo)

**Decisão**: os três `execute_*` passam a incluir no dict de retorno a lista de linhas processadas (`row_results`: linha, status, identificadores, motivo) — mudança **aditiva** no retorno (assassinatura inalterada), que hoje devolve apenas contadores e mensagens agregadas. O template de resultado apresenta o relatório por linha do pedido (§32). O evento de auditoria existente do confirm ganha as quantidades por classificação na description (ainda sem segredos).

**Racional**: §32 do pedido exige relatório por linha; hoje os services só agregam. A extensão é mínima e retrocompatível (quem consome `imported/skipped/errors` continua funcionando — os testes da 029/014 provam).

**Alternativas**: relatório construído só pela diferença preview×resultado — rejeitada: frágil (estado do banco pode mudar entre preview e confirm por outro usuário).

---

## R9 — Compatibilidade total (regressão como contrato)

**Decisão**: com o mapeamento aceito como sugerido, o resultado final é idêntico ao fluxo atual: mesmos aliases, mesmas validações, mesma execução, mesma auditoria. Os testes existentes (`test_import_asset_*`, `test_custodian_import*`) devem passar **sem alteração** (a rota continua aceitando o fluxo antigo de duas fases; a nova fase de mapeamento é pass-through quando o usuário não altera nada). Qualquer divergência detectada nos testes de regressão é bug da feature, não dos testes.

**Racional**: §41/§36 do pedido e Princípio I — a evolução não pode quebrar os importadores existentes.

**Alternativas**: migrar os testes antigos para o novo fluxo — rejeitada: enfraqueceria a garantia de compatibilidade (Constitution VIII proíbe enfraquecer testes).

---

## Pendências da spec

- **P-1** → R5: transporte via campos ocultos (padrão vigente), análise reexecutada server-side a cada fase.
- **P-2** → R3/contrato: rótulos e badges definidos (badges existentes do sistema).
- **P-3** → R5: passo intermediário dedicado (clarify), server-rendered, mesma URL.
