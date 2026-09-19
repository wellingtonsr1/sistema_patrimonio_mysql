---
description: "Task list for feature 024 — read-only audit of backup config precedence"
---

# Tasks: Auditoria da Precedência da Configuração de Backup Automático

**Input**: Design documents from `/specs/024-auditoria-config-backup/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/audit-report-contract.md, quickstart.md

**Tests**: NENHUM teste automatizado é criado ou executado — a feature é exclusivamente diagnóstica (spec FR-001/NFR-001). A "validação" desta feature é o checklist do `quickstart.md` (research R10), executado na fase de Polish.

**Organization**: Tasks agrupadas por user story (US1–US5 da spec). **Regra transversal**: toda tarefa escreve EXCLUSIVAMENTE em `specs/024-auditoria-config-backup/relatorio.md` (ou lê código); é PROIBIDO alterar qualquer arquivo de produção (código, template, docs, testes, `.env`, banco) — contract §3.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files/sections, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- Feature exclusivamente documental: artefatos em `specs/024-auditoria-config-backup/`; código do projeto (`app/`, `tests/`, `docs/`, `README.md`, `run.py`) é SOMENTE LIDO.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Estabelecer condições de auditoria (baseline limpo e mapa de leitura)

- [x] T001 Registrar baseline zero-diff: executar `git status --porcelain` e anotar o resultado na seção de metodologia do relatório (`specs/024-auditoria-config-backup/relatorio.md`) — condição inicial deve estar limpa fora de `specs/024-…` e `.specify/feature.json` (pré-condição do SC-001)
- [x] T002 [P] Validar o mapa de leitura do plan.md: confirmar existência e extensão dos arquivos-alvo (`app/config.py`, `app/models/backup_config.py`, `app/services/backup_config_service.py`, `app/services/backup_scheduler.py`, `app/services/backup_service.py`, `app/web/admin_routes.py`, `app/web/templates/admin/backups.html`, `app/main.py`, `run.py`, `tests/test_backup_*.py`, `README.md`, `docs/ARQUITETURA_E_MANUTENCAO.md`, `docs/GUIA_DE_MANUTENCAO.md`) e registrar qualquer arquivo novo/inesperado a incluir na varredura

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Artefato de entrega pronto para receber os achados

**⚠️ CRITICAL**: Nenhuma user story começa antes deste phase — todas as tarefas subsequentes consolidam achados neste arquivo

- [x] T003 Criar o esqueleto do relatório `specs/024-auditoria-config-backup/relatorio.md` conforme o contrato (`contracts/audit-report-contract.md` §1.1): as 12 seções numeradas vazias (com placeholders "[a preencher]"), mais as subseções obrigatórias: tabela das 8 env vars (§1.2), 7 respostas-chave (§1.3), 14 critérios de conclusão como checklist (§1.4), rótulos de achados (§1.5); incluir a seção de metodologia com a rubrica de classificação A–H e as regras operacionais do research R2 (incluindo a regra de exclusão de falsos positivos — R7)

**Checkpoint**: Relatório esqueletado — user stories podem iniciar (cada uma preenche suas seções)

---

## Phase 3: User Story 1 — Mapear e classificar todas as ocorrências das constantes (Priority: P1) 🎯 MVP

**Goal**: Inventário 100% das ocorrências das 8 constantes + termos relacionados, cada uma classificada A–H com evidência — respondendo se alguma constante é usada como configuração efetiva

**Independent Test**: contagem de matches das buscas × entradas do inventário do relatório = exaustão; cada entrada com `arquivo:linha`, trecho, classificação e justificativa

### Implementation for User Story 1

- [x] T004 [US1] Executar a varredura exaustiva (buscas obrigatórias do briefing §6): 8 constantes (`BACKUP_AUTO_(ENABLED|SCHEDULE|TIME|WEEKDAY)`, `BACKUP_RETENTION_(DAILY_DAYS|WEEKLY_WEEKS|MONTHLY_MONTHS|KEEP_PRE_RESTORE)`) e termos (`get_effective_config`, `backup_config`, `BackupConfig`, `scheduler`, `schedule`, `retention`, `cleanup`, `pre_restore`/`pre-restauração`) em todo o projeto (`app/`, `tests/`, `README.md`, `docs/`, `run.py`, specs como contexto histórico) e volcar TODOS os matches brutos no inventário do relatório
- [x] T005 [US1] Classificar cada ocorrência inventariada na rubrica A–H (research R2) e preencher a tabela de inventário do relatório: `arquivo:linha | trecho | classificação | papel funcional | justificativa | config-efetiva?`; listar explicitamente os falsos positivos excluídos com justificativa (`ACTION_BACKUP_AUTO_SUCCESS`/`ACTION_BACKUP_AUTO_FAILED` em `app/services/audit_service.py` L69–70/L90–91 — rótulos de auditoria; variáveis locais de `backup_scheduler.py` L625–627 — consumo da efetiva) — pesquisa R7; registrar a contagem final de matches × entradas
- [x] T006 [US1] Preencher a seção 3 do relatório ("Análise do config.py", contrato §1.1): para CADA uma das 8 constantes — `Nome / Uso encontrado / Arquivo / Função / Classificação (A–H) / Fallback? / Configuração efetiva? / Conclusão` — cobrindo os papéis verificados: definição (`app/config.py` L67–87), fallback por campo (`app/services/backup_config_service.py` L122/132/142/170–182 via `_first_defined(row.x, config.BACKUP_X)`), bootstrap de boot (`app/services/backup_scheduler.py` L31–39 + L117–124), teste (`tests/test_backup_*.py` monkeypatch), doc (`README.md`, `docs/`); veredicto por constante se é ou não usada como configuração efetiva em runtime

**Checkpoint**: US1 completa — pergunta central da auditoria respondida com inventário classificado (MVP)

---

## Phase 4: User Story 2 — Auditar o scheduler e a retenção em runtime (Priority: P1)

**Goal**: Fluxos de decisão runtime documentados com evidência linha a linha (scheduler: ativação/frequência/horário/dia; retenção: 4 valores)

**Independent Test**: cada decisão runtime tem fluxo rastreável `arquivo:linha` nomeando a fonte (constante direta = violação; `get_effective_config()` = conforme)

### Implementation for User Story 2

- [x] T007 [P] [US2] Rastrear e documentar os fluxos do scheduler na seção 4 do relatório (reconfirmando linha a linha em `app/services/backup_scheduler.py` — NÃO herdar as linhas do plan): ativação (loop principal ~L796–800: `refresh_effective_config()` por tick → `_eff().auto_enabled`), frequência (`_effective_schedule()` sobre `eff.schedule`), horário (`_effective_time()` sobre `eff.time`), dia da semana (`eff.weekday` 0–6, semântica 0=domingo…6=sábado), catch-up (~L802+: avaliado 1×/start lendo a efetiva) e o fallback de boot (L116–124: condição exata — "Falha ao ler configuração efetiva — mantendo snapshot anterior" L107–109 — quando `get_effective_config` levanta); registrar SE alguma decisão lê constante diretamente (violação) ou via efetiva
- [x] T008 [P] [US2] Rastrear e documentar os fluxos da retenção na seção 5 do relatório: `_apply_retention` (`app/services/backup_scheduler.py` ~L625–627: `eff.retention_daily_days/weekly_weeks/monthly_months`), `keep_pre_restore` (onde é consumido — trigger da retenção e restauração), janelas diária/semanal/mensal (âncoras da política GFS) — confirmando que NENHUM dos 4 valores lê `config.BACKUP_RETENTION_*` diretamente na decisão; evidência por valor

**Checkpoint**: US2 completa — consumidores runtime mapeados (US1+US2 = núcleo do diagnóstico)

---

## Phase 5: User Story 3 — Auditar fluxo da tela, cache e aplicação sem reinício (Priority: P1)

**Goal**: Fluxo real tela → persistência → leitura → scheduler documentado; cache/snapshot quantificado; instalação nova e reinício caracterizados

**Independent Test**: cada etapa do fluxo é citável (`arquivo:linha`); janela máxima de desatualização registrada; comportamento de instalação nova confirmado no código

### Implementation for User Story 3

- [x] T009 [P] [US3] Rastrear e documentar o fluxo da tela na seção 6 do relatório: `GET /admin/backups` (`config_form = get_effective_config(db, create=False)` em `app/web/admin_routes.py` ~L840), modal `#modalBackupConfig` (`app/web/templates/admin/backups.html` — apresentação), `POST /admin/backups/configuracoes` (~L888–963: validação → `save_backup_config` commit único → auditoria `BACKUP_CONFIGURACAO_ALTERADA` before/after → redirect 303 `?success=|error=`), persistência (model `BackupConfig` singleton id=1 — campos/tipos/defaults de `app/models/backup_config.py`), e como o valor chega ao scheduler (snapshot por tick); desenhar na seção 2 do relatório o diagrama do fluxo REAL com `arquivo:linha` em cada seta
- [x] T010 [P] [US3] Analisar cache/snapshot e preencher a seção 9 do relatório: `_current_effective` (module-level, `backup_scheduler.py` ~L90) — quando criado (lazy `_eff()` L128–133), quando renovado (start L790 + por tick L799), janela máxima de desatualização (confirmar o valor do `wait()`/ciclo do loop no código — esperado 30 s), modo de falha (mantém snapshot anterior L107–109), ausência de cache em `backup_config_service` (cada `get_effective_config` consulta o banco — confirmar), cenário do briefing §16 (02:00→03:00: aplicável sem reinício? em quanto tempo?); documentar também `create=True/False` (leitura com/sem efeito colateral — 022)
- [x] T011 [P] [US3] Caracterizar instalação nova, reinício e defaults no relatório (alimenta seções 2/8/9): linha `backup_config` inexistente → criação lazy `BackupConfig(id=1, auto_enabled=False)` (`app/services/backup_config_service.py` L72–76), campos `None` = "não definido" → resolução por campo persistido → env → default 020 (`_DEFAULT_*` L25–32 — duplicação intencional, research R6), env inválida → tratada como ausente com log (nunca levanta), default real `BACKUP_AUTO_ENABLED="false"` → instalação nova nasce DESATIVADA (`app/config.py` L67; teste anti-regressão `tests/test_backup_config.py` L151–153); comportamento pós-reinício (config persistida volta a valer; snapshot reconstruído do banco no 1º tick)

**Checkpoint**: US3 completa — fluxo ponta a ponta, cache e estados iniciais documentados

---

## Phase 6: User Story 4 — Verificar documentação e variáveis de ambiente (Priority: P2)

**Goal**: Precedência documentada × real comparada; tabela das 8 env vars completa; testes existentes inventariados — sem alterar nada

**Independent Test**: cada afirmação documental tem veredito (fiel/divergente/não confirmável) com evidência; tabela de 8 linhas completa; cobertura de testes mapeada por tema

### Implementation for User Story 4

- [x] T012 [P] [US4] Comparar precedência DOCUMENTADA × REAL e preencher a seção 7 do relatório: conferir afirmação por afirmação em `README.md` (~L972–995: tabela das variáveis, comportamento do scheduler thread/30 s, regra da retenção e pre-restore), `docs/ARQUITETURA_E_MANUTENCAO.md` (~L264: estrutura da tabela `backup_config`; ~L1215: fluxo de configuração/precedência/aplicação sem reinício), `docs/GUIA_DE_MANUTENCAO.md` (~L113: env como fallback da primeira inicialização) — veredito por afirmação (fiel/divergente/não confirmável) com evidência do código; DIVERGÊNCIAS apenas registradas (nada corrigido nesta feature — Constitution XI)
- [x] T013 [P] [US4] Preencher a tabela das 8 variáveis de ambiente (contrato §1.2) no relatório: `Variável | Necessária? | Função atual | Fonte efetiva | Observação` — com base nas referências reais do inventário (T005/T006), distinguindo "não usada diretamente" de "desnecessária" (briefing §25) e considerando bootstrap/fallback/instalação nova/compatibilidade/testes; veredicto por constante: `POTENCIALMENTE REMOVÍVEL` ou `DEVE SER MANTIDA COMO FALLBACK` (alimenta a resposta-chave 7) — NADA é removido
- [x] T014 [P] [US4] Inventariar os testes existentes e preencher a seção 10 do relatório (leitura dos arquivos — NÃO executar a suíte): `tests/test_backup_config.py` (precedência por campo, env vence default, persistido vence env, inválidos → default, `create=False`, anti-regressão do default via subprocesso), `tests/test_backup_automatico.py` (agendamento/scheduler), `tests/test_backup_retencao.py` (GFS/keep_pre_restore), `tests/test_backup_monitoramento.py` (monitoramento); mapear cobertura por tema do briefing §26: configuração persistida, fallback para ambiente, defaults, precedência, alteração pela tela, scheduler, retenção, configuração inválida, instalação sem `backup_config` — apontando lacunas, se houver

**Checkpoint**: US4 completa — documentação e env vars avaliadas contra o real

---

## Phase 7: User Story 5 — Relatório final de diagnóstico (Priority: P2)

**Goal**: Relatório consolidado: resumo executivo, dupla fonte de verdade, achados classificados, recomendações sem implementação, 7 respostas e 14 critérios com evidência

**Independent Test**: ler o relatório e verificar cada afirmação contra `arquivo:linha`; 7 respostas e 14 critérios completos

### Implementation for User Story 5

- [x] T015 [US5] Consolidar o relatório (depends T006–T014): preencher seção 1 (resumo executivo com veredito global), seção 8 (dupla fonte de verdade: Existe/Não existe + justificativa incluindo cenários-limite — fallback de boot quando o banco falha, env válida vencendo default mas nunca o persistido), seção 11 (todos os achados rotulados OK/ATENÇÃO/INCONSISTÊNCIA/RISCO/BLOQUEADOR com justificativa — esperado preliminar: fluxo principal OK; registrar ATENÇÃO/RISCO se identificados, ex.: janela de fallback de boot), seção 12 (recomendações SOMENTE descritivas para tarefa futura — nada implementado), responder as 7 perguntas-chave (contrato §1.3, veredito SIM/NÃO/PARCIAL + evidência) e marcar os 14 critérios de conclusão (§1.4) com `arquivo:linha`
- [x] T016 [US5] Revisão de qualidade das evidências (depends T015): verificar que TODA afirmação do relatório tem `arquivo:linha` + trecho citado (NFR-002/FR-019); afirmações não verificáveis marcadas como tais (nunca como fato); NENHUMA credencial/segredo citado (valores de env descritos por função/default, não conteúdo real de `.env` — Constitution VI); linguagem técnica objetiva em português

**Checkpoint**: US5 completa — relatório de diagnóstico entregue e consistente

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Validação final da entrega (equivalente aos "testes" desta feature)

- [x] T017 [P] Executar a validação do `specs/024-auditoria-config-backup/quickstart.md` passo a passo (zero diff, exaustão da varredura, respostas/critérios, spot-checks independentes no código, qualidade das evidências) e registrar o resultado
- [x] T018 [P] Verificação final zero-diff: `git status --porcelain` contém APENAS caminhos sob `specs/024-auditoria-config-backup/` (e `.specify/feature.json`) — qualquer alteração de produção é revertida antes de declarar conclusão (SC-001)
- [x] T019 [P] Conferência de completude do relatório contra o contrato (`contracts/audit-report-contract.md` §1.1–§1.5): 12 seções presentes, tabela das 8 env vars completa, 7 respostas-chave com veredito, 14 critérios marcados com evidência, todos os achados rotulados, falsos positivos excluídos listados

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências — inicia imediatamente
- **Foundational (Phase 2)**: depende do Setup — BLOQUEIA todas as user stories (o esqueleto do relatório é o artefato compartilhado)
- **US1 (Phase 3)**: depende da Foundational — produz o inventário que alimenta US2/US3/US4
- **US2/US3/US4 (Phases 4–6)**: dependem de US1 (T005/T006); são mutuamente independentes — podem executar em paralelo (seções diferentes do relatório)
- **US5 (Phase 7)**: depende de US2+US3+US4 completas
- **Polish (Phase 8)**: depende de US5

### User Story Dependencies

- **US1 (P1)**: nenhuma dependência além da Foundational — é o MVP
- **US2 (P1)**: precisa de T005/T006 (inventário + papéis); T007 e T008 paralelizáveis entre si
- **US3 (P1)**: precisa de T005/T006; T009/T010/T011 paralelizáveis entre si
- **US4 (P2)**: precisa de T005/T006; T012/T013/T014 paralelizáveis entre si
- **US5 (P2)**: consolida TODAS as anteriores — executar por último

### Parallel Opportunities

- T001/T002 (Setup) em paralelo
- T007+T008 (US2) em paralelo — seções 4 e 5 do relatório
- T009+T010+T011 (US3) em paralelo — seções 6, 9 e material para 2/8
- T012+T013+T014 (US4) em paralelo — seções 7, tabela de env vars e 10
- T017+T018+T019 (Polish) em paralelo
- Cross-story: US2, US3 e US4 inteiras podem rodar em paralelo após US1

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (baseline + mapa de leitura)
2. Complete Phase 2: Foundational (esqueleto do relatório)
3. Complete Phase 3: US1 (inventário + classificação + análise por constante)
4. **STOP and VALIDATE**: o inventário classificado já responde a pergunta central ("alguma constante é usada como configuração efetiva?")

### Incremental Delivery

1. MVP (US1) → resposta central documentada
2. +US2 → consumidores runtime (scheduler/retenção) evidenciados
3. +US3 → fluxo da tela, cache e estados iniciais evidenciados
4. +US4 → documentação e env vars avaliadas
5. +US5 → relatório consolidado (entrega final)
6. Polish → validação quickstart + zero diff + completude do contrato

### Notes

- Toda tarefa é SOMENTE LEITURA de produção; escrita apenas em `specs/024-auditoria-config-backup/relatorio.md`
- A auditoria NÃO herda conclusões do plan/research: cada linha citada é reconfirmada na execução (contract §3)
- Buscas de referência (ajustar padrões conforme necessário): `rg -n "BACKUP_AUTO_(ENABLED|SCHEDULE|TIME|WEEKDAY)|BACKUP_RETENTION_(DAILY_DAYS|WEEKLY_WEEKS|MONTHLY_MONTHS|KEEP_PRE_RESTORE)"` e `rg -n "get_effective_config|backup_config|BackupConfig"`
- Nenhuma execução de aplicação, suíte pytest, migration ou acesso de escrita a banco em NENHUMA tarefa
- Nenhuma correção é implementada: problemas encontrados viram recomendação (seção 12) para eventual spec futura
