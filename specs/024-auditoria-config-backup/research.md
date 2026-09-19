# Research: Auditoria da Precedência da Configuração de Backup Automático

**Feature**: 024 — `specs/024-auditoria-config-backup/` | **Data**: 2026-09-19
**Natureza**: feature exclusivamente diagnóstica (somente leitura). As "decisões" abaixo são decisões de **como auditar e entregar**, não de código.

---

## R1 — Abordagem: análise estática com evidência citável (nada é executado)

**Decision**: A auditoria é feita 100% por leitura de código (`code_search` + leitura direcionada de janelas de linhas). Nenhuma aplicação é executada, nenhuma suíte de teste é rodada, nenhum banco é acessado para escrita, nenhuma migration é executada. Toda afirmação do relatório cita arquivo/linha (ou teste).

**Rationale**: a spec (FR-001, NFR-001/002) exige zero diff e evidência citável; análise estática é suficiente porque a pergunta da auditoria é sobre **quem lê o quê** — propriedade determinável por inspeção de código e fluxo de import/call. O comportamento de precedência já está coberto por testes automatizados existentes (inventariados como evidência), o que dispensa experimentação empírica.

**Alternatives considered**: execução controlada de testes pontuais para "provar" comportamentos — rejeitada: desnecessária (testes já existem e são evidência), viola o espírito somente-leitura e adiciona custo sem ganho diagnóstico.

## R2 — Metodologia de classificação A–H das ocorrências

**Decision**: cada ocorrência das 8 constantes é classificada em exatamente uma categoria (A definição, B fallback, C bootstrap, D configuração efetiva, E apresentação, F validação, G teste, H outro), com regras operacionais:

- **A** = a linha define a constante (`BACKUP_X = os.getenv(...)`) — `app/config.py` L67–87.
- **B** = a linha lê a constante **como valor alternativo** quando o persistido está indefinido — `backup_config_service.py` L122/132/142/170–182 (`_first_defined(row.x, config.BACKUP_X)`).
- **C** = a linha usa a constante para construir **estado inicial/snapshot de boot** — `backup_scheduler.py` L117–124 (fallback na montagem do `EffectiveBackupConfig` quando a leitura ao banco falha) + L31–39 (imports exclusivamente a serviço desses usos).
- **D** = a linha usa a constante para **decidir comportamento em runtime**. Varredura exaustiva prévia (2026-09-19) **não encontrou nenhuma ocorrência D** — decisão a reconfirmar na execução, com relatório vazio se confirmado.
- **E** = uso apenas para exibir valor na interface — nenhum template consome as constantes diretamente (o modal `#modalBackupConfig` consome `get_effective_config`).
- **F** = uso apenas para validar — nenhum uso isolado de validação direta encontrado (validações consomem a efetiva).
- **G** = ocorrência em `tests/` (`monkeypatch.setattr(config, "BACKUP_...")` — fixação hermética de fallback).
- **H** = outro, com explicação (ex.: menções textuais em docs/specs — registradas como documentação, não como uso de código).

**Rationale**: o briefing §7 define as categorias; as regras operacionais eliminam ambiguidade nas fronteiras (ex.: L117–124 é **C bootstrap**, não B, porque constrói snapshot de boot e não valor por campo; é também **fallback** no sentido funcional — o relatório registra ambos os rótulos quando aplicável).

**Alternatives considered**: classificar L117–124 como D — rejeitada: não é leitura por campo com prioridade persistido→env; é caminho de exceção (banco indisponível) com validação de faixa própria; a evidência dos logs ("Falha ao ler configuração efetiva — mantendo snapshot anterior") permite citar a condição exata.

## R3 — Fluxos de decisão já rastreados (mapa preliminar a reconfirmar linha a linha na execução)

**Decision**: o relatório documenta os fluxos reais encontrados:

- **Ativação**: scheduler loop (L796–800) → `refresh_effective_config()` por tick (L790/L799) → `get_effective_config(db)` → `row.auto_enabled` (persistido) → env → default `False`. Não há leitura direta de `config.BACKUP_AUTO_ENABLED` na decisão (apenas no fallback de boot, R2/C).
- **Frequência**: `_effective_schedule()` sobre `eff.schedule` (efetiva validada) — não `BACKUP_AUTO_SCHEDULE` direto.
- **Horário**: `_effective_time()` sobre `eff.time` — não `BACKUP_AUTO_TIME` direto.
- **Dia da semana**: `eff.weekday` validado 0–6 — semântica 0=domingo…6=sábado (model L26, config L76).
- **Retenção**: `_apply_retention` (L625–627) lê `eff.retention_*` (efetiva); `keep_pre_restore` idem — não há leitura direta de `config.BACKUP_RETENTION_*` na política.
- **Tela**: `GET /admin/backups` → `config_form = get_effective_config(db, create=False)` (L840); `POST /admin/backups/configuracoes` → validação `save_backup_config` (commit único) → auditoria `BACKUP_CONFIGURACAO_ALTERADA` before/after (L925–963) → redirect 303 `/admin/backups?success=|error=`.

**Rationale**: spec FR-004/005/006; mapa preliminar já verificado nesta fase de plan e a ser reconfirmado com evidência linha a linha na implementação (a auditoria não pode herdar conclusões do plan sem checagem própria).

## R4 — Cache/snapshot e aplicação sem reinício (janela máxima de desatualização)

**Decision**: registrar no relatório o mecanismo exato: `_current_effective` (module-level, `backup_scheduler.py` L90) é **renovado a cada tick** (L799) e no start (L790). Janela máxima de desatualização = um ciclo do loop (30 s — a confirmar no trecho do `Event().wait` durante a execução). Alteração pela tela é aplicada **sem reinício**, no próximo tick. Falha de leitura mantém o snapshot anterior (crash-safe, L107/109); primeiro uso fora do servidor/testes → fallback de boot (L116–124). Não existe cache no `backup_config_service` (cada `get_effective_config` consulta o banco) — a confirmar na execução.

**Rationale**: spec FR-009/FR-010 e briefing §16 (cenário 02:00→03:00). O ponto exato do relatório é quantificar a janela e as condições de exceção.

## R5 — Instalação nova e default de `BACKUP_AUTO_ENABLED`

**Decision**: o relatório responde: linha `backup_config` inexistente + `create=True` → criação lazy `BackupConfig(id=1, auto_enabled=False)` (service L72–76) → campos `None` = "não definido" → resolução por campo cai em env → default da 020. Default real do código: `os.getenv("BACKUP_AUTO_ENABLED", "false")` → **`False`** (config L67) — instalação nova nasce **desativada** (conservador), protegido por teste anti-regressão via subprocesso (`tests/test_backup_config.py` L151–153).

**Rationale**: briefing §20/§21; resposta baseada exclusivamente no código (nada presumido).

## R6 — Fonte dos defaults: duplicação intencional service × config

**Decision**: registrar como achado de projeto (não problema): `backup_config_service.py` L25–32 duplica os valores default da 020 em `_DEFAULT_*` em vez de importar as constantes de `config.py`. Motivação arquitetural (docstring L25): os defaults são a **fonte final da precedência**, independentes das variáveis de ambiente — se importasse `config.BACKUP_AUTO_TIME`, uma env inválida ("99:99") venceria o default, quebrando a precedência documentada. O trecho envolvido tem testes (config inválida → default, `test_backup_config.py` L131–135, L246–255).

**Rationale**: distinguir duplicação intencional (default ≠ env) de dupla fonte de verdade (env vencendo default) — exatamente o tipo de nuance que a classificação A–H precisa capturar.

## R7 — Desambiguação de nomes semelhantes (falsos positivos da varredura)

**Decision**: varredura por prefixo (`BACKUP_AUTO_`, `BACKUP_RETENTION_`) captura também nomes **não-config** que devem ser excluídos da classificação com justificativa: `ACTION_BACKUP_AUTO_SUCCESS`/`ACTION_BACKUP_AUTO_FAILED` (`audit_service.py` L69–70, 90–91) são **rótulos de eventos de auditoria**, não constantes de configuração; variáveis locais de scheduler (`daily_days = _effective_int(eff.retention_daily_days, ...)` L625–627) são consumo da efetiva, não das constantes. O relatório lista esses casos como "excluídos da classificação" para provar que a varredura foi exaustiva.

**Rationale**: rigor do briefing §6/§7 (todas as ocorrências com justificativa); evita inflar a categoria D com falsos positivos.

## R8 — Comparação documentado × real

**Decision**: fontes documentais a conferir (sem alterá-las nesta feature): `README.md` L972–995 (tabela das 8 variáveis + descrição do scheduler e da retenção), `docs/ARQUITETURA_E_MANUTENCAO.md` L264 e L1215, `docs/GUIA_DE_MANUTENCAO.md` L113. Veredito por afirmação: fiel / divergente / não confirmável, com evidência do código. Specs 020–022 são contexto histórico (não conferidas como doc viva).

**Rationale**: spec US4/FR-014; Constitution Princípio XI — divergências são registradas para tarefa futura, não corrigidas aqui.

## R9 — Formato e local do relatório final

**Decision**: relatório em `specs/024-auditoria-config-backup/relatorio.md` (decidido; Assumption 4 da spec resolvida), com as 12 seções do briefing §30, tabela das 8 env vars (§18), as 7 respostas-chave com veredito SIM/NÃO/PARCIAL (§28), os 14 critérios de conclusão marcados com evidência (§31) e os achados classificados OK/ATENÇÃO/INCONSISTÊNCIA/RISCO/BLOQUEADOR (§29). Evidências em formato `arquivo:linha` + trecho citado.

**Rationale**: artefato persistente versionável (a conversa não é entregável); spec FR-016/FR-019.

## R10 — Validação da entrega (equivalente a "testes" desta feature)

**Decision**: como não há código novo, a validação é um checklist de conformidade documental: (1) zero diff fora de `specs/` (`git status --porcelain` limpo de tudo exceto `specs/024-…` e `.specify/feature.json`); (2) 100% das ocorrências classificadas (contagem de matches × entradas do relatório); (3) 7 respostas com veredito + evidência; (4) 14 critérios marcados; (5) cada achado com rótulo e recomendação sem implementação; (6) nenhuma credencial/segredo citado. Detalhado em `quickstart.md`.

**Rationale**: spec FR-016–FR-019, SC-001–SC-007; Constitution Princípio XII (validação é parte da definição de pronto).
