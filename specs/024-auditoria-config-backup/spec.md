# Feature Specification: Auditoria da Precedência da Configuração de Backup Automático

**Feature Branch**: `feature-auditoria-config-backup`

**Created**: 2026-09-19

**Status**: Draft

**Input**: Verificar se a configuração de Backup Automático e Retenção administrada pela tela possui uma única fonte de verdade em runtime e se as constantes existentes em `app/config.py` estão sendo utilizadas somente como bootstrap/fallback. Análise exclusivamente de leitura — diagnóstico técnico, sem nenhuma alteração.

## Regra fundamental da feature

Esta feature é **exclusivamente diagnóstica (somente leitura)**. É PROIBIDO: editar qualquer arquivo de código, template, CSS, JS, banco, configuração, `.env`, `.gitignore`, scheduler, services, models ou migrations; criar tabelas; executar migrations; corrigir automaticamente qualquer problema encontrado. O resultado é um **diagnóstico técnico preciso** — problemas encontrados são apenas registrados, com a correção necessária descrita para uma tarefa futura (Constitution, Princípio I).

## Realidade verificada (componentes existentes a auditar)

*Analisado antes de escrever esta spec — a auditoria DEVE confirmar o comportamento real, não presumir que os papéis abaixo correspondem ao que o código faz.*

1. **Constantes (briefing)**: `app/config.py` linhas 63–87 define as 8 constantes `BACKUP_AUTO_ENABLED`, `BACKUP_AUTO_SCHEDULE`, `BACKUP_AUTO_TIME`, `BACKUP_AUTO_WEEKDAY`, `BACKUP_RETENTION_DAILY_DAYS`, `BACKUP_RETENTION_WEEKLY_WEEKS`, `BACKUP_RETENTION_MONTHLY_MONTHS`, `BACKUP_RETENTION_KEEP_PRE_RESTORE` (cada uma via `os.getenv` com default), precedidas de comentário que afirma: "a leitura viva é feita por backup_config_service.get_effective_config()".
2. **Model**: `app/models/backup_config.py` — classe `BackupConfig` (tabela `backup_config`), singleton `id=1`, campos operacionais `None` = "não definido" → resolução efetiva; exportado em `app/models/__init__.py`.
3. **Service de configuração**: `app/services/backup_config_service.py` — `get_backup_config(db, create=True)` (criação lazy da linha singleton), `get_effective_config(db, create=True)` (resolução por campo: persistido → env → default), `EffectiveBackupConfig` (dataclass de saída) e salvamento (`save_backup_config`). **Não existe** `app/schemas/*backup*` — não há schema Pydantic para backup.
4. **Scheduler**: `app/services/backup_scheduler.py` importa as 8 constantes de `config`; usa-as **apenas no bloco de fallback** de `refresh_effective_config()` (linhas ~117–124) quando a leitura via `get_effective_config` falha; mantém snapshot module-level `_current_effective`; as decisões runtime usam `eff.retention_*`/`_eff()` (ex.: linhas 625–627). **A auditoria deve confirmar** esse fluxo e verificar se algum outro ponto do módulo (ou de outro módulo) consome constantes diretamente.
5. **Rota/tela**: `app/web/admin_routes.py` — `GET /admin/backups/configuracoes` e `POST /admin/backups/configuracoes` (validação backend → `save_backup_config` → auditoria `BACKUP_CONFIGURACAO_ALTERADA` before/after → redirect 303); `GET /admin/backups` injeta `config_form = get_effective_config(db, create=False)` no modal `#modalBackupConfig` (`templates/admin/backups.html`).
6. **Inicialização**: `app/main.py` (lifespan) inicia/para o scheduler (`start_scheduler`/`stop_scheduler`).
7. **Testes existentes**: `tests/test_backup_config.py` (precedência, fallback env→default, valores inválidos, `create=False`, anti-regressão do default `BACKUP_AUTO_ENABLED=false` via subprocesso), `tests/test_backup_automatico.py`, `tests/test_backup_retencao.py`, `tests/test_backup_monitoramento.py` — vários usam `monkeypatch.setattr(config, "BACKUP_...")` (classificação: teste).
8. **Documentação**: `README.md` (tabela das 8 variáveis com defaults), `docs/ARQUITETURA_E_MANUTENCAO.md` e `docs/GUIA_DE_MANUTENCAO.md` descrevem a precedência "persistido → env → default" e a aplicação sem reinício. As specs 020/021/022 descrevem a arquitetura na época — **código atual é a fonte da auditoria**.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Mapear e classificar todas as ocorrências das constantes (Priority: P1)

Um mantenedor solicita a auditoria. O primeiro passo é varrer o projeto inteiro em busca de todas as ocorrências das 8 constantes (`BACKUP_AUTO_*` e `BACKUP_RETENTION_*`) e dos termos `get_effective_config`, `backup_config`, `BackupConfig`, `scheduler`, `schedule`, `retention`, `cleanup`, `pre_restore` (e variações). Cada ocorrência é registrada com arquivo/linha e classificada: **A** definição, **B** fallback, **C** bootstrap, **D** configuração efetiva, **E** apresentação, **F** validação, **G** teste, **H** outro (explicar). O objetivo: determinar se alguma ocorrência usa as constantes como **configuração efetiva em runtime**.

**Why this priority**: sem o mapa completo, não é possível garantir que nenhuma constante seja usada diretamente para decidir comportamento — é a pergunta central da auditoria.

**Independent Test**: para cada constante, a lista de ocorrências cobre 100% dos matches de busca do projeto, cada uma com arquivo/linha e classificação justificada.

**Acceptance Scenarios**:

1. **Given** o projeto atual, **When** as 8 constantes são buscadas, **Then** todas as ocorrências (código, testes, docs, specs) estão listadas com arquivo/linha.
2. **Given** cada ocorrência, **When** classificada, **Then** a classificação (A–H) é justificável pelo trecho de código citado — nenhuma ocorrência fica sem classificação.
3. **Given** a classificação final, **When** analisada, **Then** é possível responder objetivamente se as constantes funcionam apenas como bootstrap/fallback ou se algum componente as usa como configuração efetiva.

---

### User Story 2 - Auditar o scheduler e a retenção em runtime (Priority: P1)

O segundo passo rastreia os pontos onde o comportamento é decidido. **Scheduler**: como o sistema decide se o backup automático está ativado, a frequência (`daily`/`weekly`), o horário e o dia da semana (0–6) — verificando se cada decisão lê `config.BACKUP_*` diretamente ou via `get_effective_config()` (ou equivalente). **Retenção**: como os serviços determinam janelas diária/semanal/mensal e `keep_pre_restore` — lendo `config.py` diretamente ou a configuração efetiva. Cada fluxo é documentado exatamente como encontrado (não como documentado).

**Why this priority**: scheduler e retenção são os consumidores efetivos da configuração — qualquer leitura direta de constante aqui é a violação que a auditoria procura.

**Independent Test**: cada decisão runtime (ativado? frequência? horário? dia? janelas de retenção? pre-restore?) tem um fluxo rastreável arquivo/linha que nomeia a fonte usada.

**Acceptance Scenarios**:

1. **Given** o scheduler, **When** o fluxo "está ativado?" é rastreado, **Then** a fonte real é identificada (`config.BACKUP_AUTO_ENABLED` direto = violação registrada; `get_effective_config()` = conforme documentado).
2. **Given** a retenção, **When** cada um dos 4 valores é rastreado, **Then** a fonte efetiva de cada um é identificada com evidência.
3. **Given** o dia da semana em `weekly`, **When** verificado, **Then** fica registrado de onde vem o valor 0–6 (config direta ou efetiva) e a semântica (0=domingo…6=sábado) confirmada no código.

---

### User Story 3 - Auditar o fluxo da tela, o cache e a aplicação sem reinício (Priority: P1)

O terceiro passo segue a configuração do administrador: tela → `POST /admin/backups/configuracoes` → validação → persistência (tabela/modelo) → leitura posterior (`get_effective_config`) → scheduler e retenção. São verificados: o modelo/tabela real (singleton? campos? valores default? como é localizado/criado/atualizado), a função `get_effective_config()` em detalhe (ordem de precedência, validação, valores inválidos → default, parâmetro de leitura sem criação), e a existência de **cache/snapshot/variável global** que possa manter valor antigo após alteração na tela (cenário do briefing: administrador altera 02:00 → 03:00 e o scheduler continua usando 02:00). Também é avaliada, por análise estática, a aplicação da configuração sem reinício e o comportamento após reinício, e o cenário de instalação nova sem linha persistida (env/default como fallback).

**Why this priority**: é onde uma "dupla fonte de verdade" ou um cache obsoleto se esconderia — mesmo com o scheduler lendo a função central, um snapshot não renovado anularia a configuração da tela na prática.

**Independent Test**: o fluxo completo é representado como diagrama do que o código realmente faz (não o documentado), com cada seta citável (arquivo/linha).

**Acceptance Scenarios**:

1. **Given** uma alteração salva pela tela, **When** o fluxo até o scheduler é rastreado, **Then** cada etapa (rota → service → persistência → leitura → scheduler) é evidenciada no código.
2. **Given** qualquer cache/snapshot/variável global da configuração, **When** analisado, **Then** fica registrado quando é criado, quando é renovado e se uma alteração na tela o invalida — incluindo a janela máxima de desatualização.
3. **Given** instalação nova sem linha `backup_config`, **When** o comportamento é analisado, **Then** o fallback real (env → default) e o estado inicial do backup automático (habilitado/desabilitado) são confirmados no código.

---

### User Story 4 - Verificar documentação e variáveis de ambiente (Priority: P2)

O quarto passo compara a precedência **documentada** com a **real encontrada** (destacando divergências) e avalia, com base nas referências reais, o papel atual de cada variável de ambiente (`BACKUP_AUTO_*`/`BACKUP_RETENTION_*`) numa tabela: necessária? função atual? fonte efetiva? observação? Nenhuma variável é declarada desnecessária apenas por existir configuração na tela — a conclusão considera bootstrap, fallback, instalação nova, compatibilidade e testes. Documentações citadas (README, `docs/`) são conferidas contra o comportamento real.

**Why this priority**: garante que o diagnóstico final sirva para decisão (o que manter/remover/mudar numa tarefa futura) e que a documentação reflita o comportamento real.

**Independent Test**: a tabela das 8 variáveis está preenchida com referências ao código; cada afirmação documental tem veredito (fiel/divergente) com evidência.

**Acceptance Scenarios**:

1. **Given** a precedência documentada (persistido → env → default), **When** comparada com o código, **Then** a ordem real é apresentada ao lado da documentada, com divergências destacadas.
2. **Given** cada variável de ambiente, **When** avaliada, **Then** a conclusão distingue "não usada diretamente" de "desnecessária" (briefing §25).
3. **Given** a documentação atual, **When** conferida, **Then** afirmações não correspondentes ao código ficam registradas como divergência (sem corrigir nada nesta feature).

---

### User Story 5 - Relatório final de diagnóstico (Priority: P2)

O resultado é consolidado num relatório com: (1) resumo executivo; (2) fonte efetiva real (diagrama do fluxo encontrado); (3) análise por constante (nome, usos, arquivos, funções, classificação, fallback?, efetiva?, conclusão); (4) análise do scheduler; (5) análise da retenção; (6) análise da tela; (7) precedência documentada vs real; (8) dupla fonte de verdade (existe/não existe, justificada); (9) cache e atualização (imediatamente ou só após reinício?); (10) testes existentes e cobertura; (11) problemas classificados (OK / ATENÇÃO / INCONSISTÊNCIA / RISCO / BLOQUEADOR); (12) recomendação de correção futura **sem implementar**. As 7 perguntas-chave são respondidas SIM/NÃO/PARCIAL e os 14 critérios de conclusão marcados com evidência.

**Why this priority**: é a entrega da feature — o diagnóstico técnico preciso e acionável.

**Independent Test**: ler o relatório e verificar que cada afirmação cita arquivo/linha (ou teste) e que as 7 perguntas e 14 critérios estão respondidos.

**Acceptance Scenarios**:

1. **Given** o relatório final, **When** as 7 perguntas-chave são lidas, **Then** cada uma tem veredito SIM/NÃO/PARCIAL com explicação e evidência.
2. **Given** qualquer problema registrado, **When** classificado, **Then** recebe um dos rótulos (OK/ATENÇÃO/INCONSISTÊNCIA/RISCO/BLOQUEADOR) com justificativa.
3. **Given** um problema com correção futura proposta, **When** a feature termina, **Then** nada foi implementado/corrigido — apenas descrito.

---

### Edge Cases

- **Falha na leitura da configuração efetiva** (ex.: banco indisponível no 1º tick): o código prevê manter snapshot anterior ou cair em env/default — a auditoria registra esse comportamento de fallback como parte do fluxo real, sem considerá-lo automaticamente uma violação.
- **Janela entre alteração na tela e próxima avaliação do scheduler**: se existir snapshot renovado por tick, há janela máxima conhecida de desatualização — registrar o valor encontrado (não medir empiricamente; análise estática).
- **Ocorrências em testes** (`monkeypatch.setattr(config, "BACKUP_...")`): classificadas como **G — Teste**; não contam como uso runtime, mas são listadas (revelam a API interna exercitada).
- **Ocorrências em docs/specs antigas** (020/021/022): refletem a arquitetura da época; o código atual prevalece — divergências são registradas, não "corrigidas" nas specs antigas.
- **Constante sem uso runtime direto ≠ removível**: conclusões sobre remoção consideram bootstrap, fallback, instalação nova, compatibilidade e testes (briefing §25); nenhuma constante é removida nesta feature.
- **Valores inválidos** (env ou banco): verificar e registrar para onde caem (default? validação em segunda camada?) sem alterar nada.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A análise é exclusivamente de leitura: nenhum arquivo de código, template, CSS, JS, banco, configuração, `.env` ou teste é criado, alterado ou removido; nenhuma migration é executada; nenhuma correção é aplicada automaticamente.
- **FR-002**: O sistema deve varrer o projeto inteiro pelas 8 constantes (`BACKUP_AUTO_ENABLED`, `BACKUP_AUTO_SCHEDULE`, `BACKUP_AUTO_TIME`, `BACKUP_AUTO_WEEKDAY`, `BACKUP_RETENTION_DAILY_DAYS`, `BACKUP_RETENTION_WEEKLY_WEEKS`, `BACKUP_RETENTION_MONTHLY_MONTHS`, `BACKUP_RETENTION_KEEP_PRE_RESTORE`) e pelos termos `get_effective_config`, `backup_config`, `BackupConfig` e termos relacionados (scheduler, schedule, retention, cleanup, pre_restore e variações), listando todas as ocorrências com arquivo/linha.
- **FR-003**: Cada ocorrência deve ser classificada em exatamente uma categoria: A definição, B fallback, C bootstrap, D configuração efetiva, E apresentação, F validação, G teste, H outro (com explicação).
- **FR-004**: O fluxo real de decisão do scheduler deve ser documentado para: ativação, frequência (`daily`/`weekly`), horário e dia da semana — nomeando a fonte de cada valor (constante direta ou configuração efetiva), com evidência arquivo/linha.
- **FR-005**: O fluxo real da retenção deve ser documentado para os 4 valores (janela diária, semanal, mensal, `keep_pre_restore`) — fonte efetiva de cada um, com evidência.
- **FR-006**: O fluxo real da tela deve ser documentado: rota(s) envolvida(s), onde os valores são recebidos/validados/persistidos, em qual tabela/modelo, como são lidos posteriormente e como chegam ao scheduler e à retenção — como diagrama do que o código faz, não do que a documentação afirma.
- **FR-007**: A estrutura real da tabela/modelo de configuração deve ser registrada: nome, campos, tipos, defaults, unicidade (singleton vs múltiplos registros), mecanismos de localização/criação/atualização.
- **FR-008**: A função central de resolução da configuração efetiva deve ser analisada em detalhe: consulta ao persistido, consulta a env, defaults, ordem de precedência, validação, comportamento com valores inválidos, leitura sem efeito colateral (parâmetro de criação) e se é relida a cada execução.
- **FR-009**: A existência de cache/snapshot/variável global/singleton em memória da configuração deve ser investigada; se existir, registrar quando é criado, como é renovado/invalidado e se uma alteração pela tela o atualiza (cenário: altera 02:00 → 03:00 e o scheduler continua em 02:00).
- **FR-010**: O comportamento com e sem reinício deve ser avaliado por análise estática: alteração pela tela aplicada sem reinício? configuração sobrevive corretamente ao reinício da aplicação?
- **FR-011**: Cada uma das 8 variáveis de ambiente deve ser avaliada na tabela final: necessária? função atual? fonte efetiva? observação — com conclusão baseada nas referências reais, distinguindo "não usada diretamente" de "desnecessária".
- **FR-012**: Situações de dupla fonte de verdade devem ser identificadas: qualquer cenário em que `config.py` e a configuração persistida possam determinar comportamentos diferentes (ex.: tela desativada + env ativa + scheduler lendo a env).
- **FR-013**: O comportamento em instalação nova (sem registro persistido) deve ser determinado: o que a configuração efetiva resolve, se env/default atuam como fallback e se o backup automático inicia habilitado ou desabilitado (default atual).
- **FR-014**: A precedência documentada deve ser comparada com a precedência real encontrada; divergências destacadas claramente (ordem documentada vs ordem real).
- **FR-015**: Os testes existentes relacionados (backup, config, scheduler, retenção, monitoramento) devem ser inventariados e mapeados quanto à cobertura: configuração persistida, fallback para ambiente, defaults, precedência, alteração pela tela, scheduler, retenção, configuração inválida, instalação sem registro — sem alterar nenhum teste.
- **FR-016**: O relatório final deve conter as 12 seções do formato (resumo executivo; fonte efetiva real; análise por constante; scheduler; retenção; tela; precedência documentada vs real; dupla fonte de verdade; cache e atualização; testes existentes; problemas encontrados; recomendação) e responder com evidência as 7 perguntas-chave (SIM/NÃO/PARCIAL onde aplicável).
- **FR-017**: Cada problema encontrado deve ser classificado: OK / ATENÇÃO / INCONSISTÊNCIA / RISCO / BLOQUEADOR.
- **FR-018**: Quando houver problema, a recomendação deve descrever SOMENTE o que deveria ser corrigido em tarefa futura — nenhuma correção é implementada nesta feature.
- **FR-019**: O diagnóstico é válido somente com evidência citável do código (arquivo/linha ou teste); afirmações não verificáveis são marcadas como tais, não apresentadas como fato.

### Non-Functional Requirements

- **NFR-001** (Escopo zero-diff): `git diff` ao final da auditoria não contém nenhuma alteração em código, testes, docs de produção, templates ou configuração — os únicos artefatos são os desta feature (`specs/…`).
- **NFR-002** (Evidência): todo veredito citável por arquivo/linha; nenhuma conclusão baseada apenas em documentação ou specs anteriores.
- **NFR-003** (Neutralidade): nenhuma recomendação de remoção sem considerar bootstrap/fallback/instalação nova/compatibilidade/testes; nenhum código, banco ou config alterado para "testar" hipóteses.
- **NFR-004** (Preservação): sistema existente integralmente preservado (Constitution, Princípio I); a auditoria não executa a aplicação nem migrações contra banco real.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Nenhum arquivo fora de `specs/` é modificado pela feature (diff limpo).
- **SC-002**: 100% das ocorrências das 8 constantes estão listadas e classificadas (A–H) com arquivo/linha.
- **SC-003**: O mapa de dependências real (não o documentado) é produzido: constantes → service de configuração → leitura efetiva → scheduler/retention, com o fluxo real substituindo o esperado.
- **SC-004**: As 7 perguntas-chave respondidas com veredito e evidência: (1) a configuração da tela é a fonte efetiva? (2) `config.py` é apenas fallback? (3) existe dupla fonte de verdade? (4) o scheduler usa a configuração da tela? (5) a retenção usa a configuração da tela? (6) a função central realmente centraliza a configuração? (7) alguma constante pode ser removida (potencialmente removível vs deve ser mantida como fallback, com justificativa)?
- **SC-005**: A tabela das 8 variáveis de ambiente está completa (necessária? função atual? fonte efetiva? observação?).
- **SC-006**: Os 14 critérios de conclusão estão marcados com evidência: onde a tela persiste; onde a efetiva é lida; a função central existe e funciona como documentado; scheduler usa a efetiva; retenção usa a efetiva; função real das constantes; env como fallback ou efetiva; dupla fonte de verdade; cache; aplicação sem reinício; instalação nova sem registro; coerência dos defaults; testes de precedência; risco de a tela ser ignorada.
- **SC-007**: Todo achado está classificado (OK/ATENÇÃO/INCONSISTÊNCIA/RISCO/BLOQUEADOR) e, para os não-OK, existe recomendação de correção futura descrita sem implementação.

## Assumptions

1. O código atual é a única fonte de verdade da auditoria; `README.md`, `docs/` e specs 020–022 são referências a conferir, não a seguir.
2. A auditoria é análise estática: nenhuma aplicação é executada, nenhum banco é acessado para escrita, nenhuma migration é executada, nenhum teste é alterado; a suíte não precisa ser executada para esta feature.
3. Janelas de desatualização de cache/snapshot são determinadas pela leitura do código (ex.: periodicidade de renovação), sem medição empírica.
4. O local do relatório final (arquivo dentro de `specs/024-auditoria-config-backup/` ou resposta na conversa) é decidido na fase de tasks da feature — não é código de produção.
5. Esta feature não cria a eventual spec de correção: se a auditoria encontrar INCONSISTÊNCIA/RISCO/BLOQUEADOR, uma segunda spec exclusivamente corretiva pode ser criada depois, a critério do requisitante.
