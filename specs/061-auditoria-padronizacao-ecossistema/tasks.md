---
description: "Task list para a Feature 061 — auditoria e padronização do ecossistema SisPatrimônio Pro"
---

# Tasks: 061 — auditoria e padronização do ecossistema

**Input**: Design documents de `/specs/061-auditoria-padronizacao-ecossistema/` (spec.md, plan.md, research.md, data-model.md, contracts/ecossistema-contratos.md, quickstart.md)

**Prerequisites**: plan.md ✅ · spec.md ✅ · research.md ✅ · data-model.md ✅ · contracts/ ✅ · quickstart.md ✅

**Testes**: incluídos onde a spec exige (FR-003 baseline, FR-027 plano de testes, Constitution VIII — suíte verde por lote).

**Organização**: por user story. A US1 (Diagnóstico, somente leitura) é o **gate** — nenhuma alteração funcional antes do checkpoint T014 (regra fundamental da spec + Constitution I).

## Formato: `[ID] [P?] [Story] Descrição`

- **[P]**: paralelizável (arquivos diferentes, sem dependência de tarefa incompleta)
- **[Story]**: user story de origem (US1…US6 da spec)
- Caminhos exatos em cada tarefa; resultados de diagnóstico vão sempre para `specs/061-auditoria-padronizacao-ecossistema/diagnostico.md`

---

## Phase 1: Setup (infraestrutura compartilhada)

**Purpose**: preparar o ambiente de diagnóstico sem alterar nada funcional.

- [x] T001 Criar o esqueleto do relatório em specs/061-auditoria-padronizacao-ecossistema/diagnostico.md com as seções do Entregável A (arquitetura, fluxo deploy, fluxo instalação, fluxo banco, fluxo HTTPS, divergências classificadas, problemas, causas prováveis/confirmadas) e status `Draft`
- [x] T002 [P] Registrar no diagnostico.md §Metodologia o estado do workspace: `git status --short`, branch atual (`061-auditoria-padronizacao-ecossistema`), `git remote -v`, última versão do commit (`git log --oneline -5`)

**Checkpoint**: esqueleto pronto; nenhum arquivo funcional tocado.

---

## Phase 2: Foundational (pré-requisitos bloqueantes)

**Purpose**: baseline e insumos que TODAS as user stories consomem. Nenhuma story começa antes deste fase concluir.

- [x] T003 Executar a suíte completa de testes (`.venv/bin/python -m pytest -q` no Linux; `test.bat -q` no Windows) e registrar o **baseline** (nº passed/failed/skipped) no diagnostico.md §Baseline de testes (FR-003, SC-001)
- [x] T004 [P] Clonar o repositório PRO em modo leitura (`git clone git@github.com:wellingtonsr1/SisPatrimonioPro.git` em diretório temporário fora do projeto), registrar HEAD e árvore raiz no diagnostico.md §Snapshot PRO (research F1)
- [x] T005 [P] Extrair as whitelists de `deploy.sh` (bloco `find … ! -name`) e `deploy.bat` (equivalentes) comparando filtro a filtro, e registrar a tabela de equivalência `.sh`×`.bat` no diagnostico.md §Deploy (research F1)

**Checkpoint**: baseline de testes registrado; PRO acessível em leitura; whitelists mapeadas. Stories podem começar.

---

## Phase 3: User Story 1 — Diagnóstico completo e baseline, sem alterar nada (Priority: P1) 🎯 MVP

**Goal**: relatório de diagnóstico completo (Entregável A) com causas prováveis/confirmadas — em especial a causa raiz do HTTPS perdido na instalação Windows — sem modificar nenhum arquivo funcional.

**Independent Test**: validar que (a) `diagnostico.md` cobre todas as seções com evidências (arquivo:linha ou comando reprodutível), (b) `git status` permanece limpo, (c) baseline de testes anotado, (d) matriz MariaDB×MySQL (Entregável B) preenchida com células verificadas.

### Implementação para US1

- [x] T006 [US1] Inventariar a dev: `git ls-files` (residuais commitados? `app/config.py~`, `_teste_smtp_direto.py`, `uninstall.sh-old`, `..env.un~`), diretórios `mnt/` e `TASKS/`, e registrar classificação preliminar (intencional/obsoleta/erro/risco) no diagnostico.md §Arquitetura/Divergências
- [x] T007 [US1] Rastrear o baseline HTTPS funcional da dev com evidência arquivo:linha: `run.py` (passagem de `ssl_certfile/ssl_keyfile`) → `app/config.py` (`APP_SSL_CERTFILE`/`APP_SSL_KEYFILE`/`APP_PORT`/`AUTH_COOKIE_SECURE`, `_normaliza_caminho_cert`) → `scripts/gera_cert_dev.py` (CA + SAN IP/localhost/sispatrimoniopro.local) → `data/ssl/` (fora do Git) → documentar o fluxo completo no diagnostico.md §HTTPS (FR-021)
- [x] T008 [US1] Comparar o snapshot PRO (T004) com a whitelist (T005): arquivos necessários ausentes, residuais indevidos presentes, diferenças `deploy.sh`×`deploy.bat` — classificar cada diferença (intencional/necessária/obsoleta/erro/risco) no diagnostico.md §Divergências dev×PRO (Entregável D parcial, FR-016)
- [x] T009 [US1] Mapear o instalador Windows **já localizado** — terceiro repositório `SisPatrimonioPro-install` (`~/IA/SisPatrimonioPro-install`, remoto `git@github.com:wellingtonsr1/SisPatrimonioPro-install.git`), arquivo `install no windows/nativa/install.ps1` (982 linhas; serviço via Tarefa Agendada, firewall previsto, **sem config SSL/cert** — ver research F5) — passo a passo (Python, venv, MySQL, banco/usuário, `.env`, serviço, firewall, certificados, HTTPS) com arquivo:linha no diagnostico.md §Instalação Windows, incluindo variantes docker/ e uninstall.ps1 e os docs `README.md`/`TROUBLESHOOTING.md` (FR-018)
- [x] T010 [US1] Identificar a **causa raiz** da perda do HTTPS na instalação Windows: comparar o que o instalador produz (envs TLS? certificado gerado? caminhos? serviço? firewall?) contra o baseline mapeado em T007, separando causas prováveis de confirmadas com evidência, no diagnostico.md §Causas (FR-018; depende de T007 e T009)
- [x] T011 [US1] Auditar a camada de banco (`app/config.py` `DATABASE_URL`, engine/pool/charset, `init_db`/`_ensure_schema_migrations`, services de backup com `mysqldump`, SQL de instalação/inicialização) e preencher a matriz MariaDB×MySQL (Entregável B) no diagnostico.md §Banco — célula sem verificação explícita fica marcada "não verificado" (FR-006, FR-007)
- [x] T012 [US1] Inventariar referências a XAMPP fora do versionado da dev: clone do PRO (T004), repositório `SisPatrimonioPro-install` (grep já indica 0 — registrar), arquivos ignorados/locais da máquina Windows, `.env` local (atenção a `MYSQLDUMP_PATH`/caminhos `C:\\xampp`), e como o serviço de banco é iniciado/parado na máquina real — classificar cada ocorrência (necessária/histórica/instalador/scripts/testes/docs) no diagnostico.md §XAMPP (FR-012; research F3/F5 confirmam 0 nos repos versionados)
- [x] T013 [US1] Consolidar o diagnostico.md: causas prováveis × confirmadas, problemas, lista preliminar de arquivos candidatos a Alterar/Criar/Remover/Não alterar (rascunho do Entregável D) — completo e revisável (FR-001)
- [x] T014 [US1] **Checkpoint/gate**: apresentar o diagnóstico ao responsável, registrar a aprovação (status `Draft` → `Approved` no diagnostico.md) e confirmar `git status` limpo — libera US2/US3 (FR-001; D-001 da spec)

**Checkpoint**: diagnóstico aprovado pelo responsável; baseline registrado; nada alterado. **MVP atingido.**

---

## Phase 4: User Story 2 — HTTPS sobrevive à instalação no Windows (e no Linux) (Priority: P1)

**Goal**: a configuração HTTPS funcional da dev (baseline 056, porta 8000, sem redirect) é reproduzida pelos instaladores — Windows primeiro (causa raiz de T010), Linux também (contrato C2) — sobrevivendo a reboot, reinício de serviço, atualização e reinstalação.

**Independent Test**: instalar em VM Windows limpa com MySQL nativo → `https://host:8000/health` 200 sem passo manual; repetir após reboot/reinício/atualização/reinstalação (SC-003, SC-004).

### Implementação para US2

- [x] T015 [US2] Produzir a lista de arquivos do lote HTTPS (Alterar/Criar/Remover/Não alterar com justificativa) em specs/061-auditoria-padronizacao-ecossistema/lista-arquivos.md §HTTPS, a partir das causas confirmadas em T010, e obter aprovação (FR-004, D-005)
- [x] T016 [US2] Corrigir o instalador Windows (arquivo localizado em T009) para produzir o contrato C2: gerar/apontar certificado reutilizando o mecanismo da 056 (`scripts/gera_cert_dev.py` + `APP_SSL_CERTFILE`/`APP_SSL_KEYFILE`), gravar `APP_PORT=8000` e `AUTH_COOKIE_SECURE=true` quando TLS ativo, e criar regra de firewall nomeada idempotente (ex.: "SisPatrimonioPro HTTPS 8000") — sem segunda implementação de HTTPS (FR-018, FR-020, FR-022, D-003, D-006)
- [x] T017 [US2] Adicionar etapa HTTPS equivalente ao `install.sh` (mesmo contrato C2) preservando a idempotência e o padrão de log sem segredos do instalador 027 (FR-017, FR-022)
- [x] T018 [US2] Garantir que certificados/chaves privadas nunca entram no Git nem no snapshot PRO: verificar `.gitignore` (cobertura de `data/ssl/` e equivalentes Windows) e as whitelists de `deploy.sh`/`deploy.bat` (FR-025)
- [ ] T019 [US2] Validar HTTPS na instalação Windows (VM limpa + MySQL nativo): `https://host:8000/health` 200 com cadeia validada no cliente com a CA instalada; HTTPS permanece após reboot do servidor, reinício do serviço, atualização e reinstalação; `http://host:8000` falha handshake (sem redirect — D-002); registrar resultados no diagnostico.md §Validação (SC-003, SC-004, FR-022)
- [x] T020 [US2] Executar a suíte completa e comparar com o baseline de T003 (zero regressão silenciosa) (SC-001)

**Checkpoint**: HTTPS funcional nas instalações Linux e Windows, reproduzindo o baseline da dev; suíte verde.

---

## Phase 5: User Story 3 — Windows com MySQL Server nativo, sem XAMPP (Priority: P1)

**Goal**: arquitetura `Windows → MySQL Server nativo → SisPatrimônio Pro` funcionando sem nenhuma dependência de XAMPP; referências restantes apenas históricas/documentadas.

**Independent Test**: VM Windows sem XAMPP + MySQL nativo → instalação ponta a ponta (banco + sistema + HTTPS) sem que qualquer etapa exija XAMPP (SC-005).

### Implementação para US3

- [x] T021 [US3] Produzir a lista de arquivos do lote XAMPP/MySQL em specs/061-auditoria-padronizacao-ecossistema/lista-arquivos.md §XAMPP (a partir do inventário T012) e obter aprovação (FR-004, D-005)
- [x] T022 [US3] Substituir, no instalador Windows (arquivo de T009), cada dependência XAMPP confirmada em T012 pelo caminho MySQL nativo: detectar MySQL instalado (versão/serviço), iniciar serviço parado, validar conexão, criar banco/usuário somente se faltarem, testar credenciais/schema/aplicação (FR-013) — **feito no lote M-1..M-5** (lista-arquivos.md §MySQL): guard XAMPP em `Detect-Host` (serviço apontando para `C:\xampp` nunca é reutilizado), `Ensure-Packages` instala MySQL Server nativo via winget `Oracle.MySQL` (fallback: orientar configuração pelo MySQL Installer e reexecutar — idempotente), `Get-DbServerKind` detecta o servidor real (`SELECT VERSION()`) e valida a faixa (MySQL ≥ 8.0, MariaDB ≥ 10.5, `die` com mensagem clara em versão incompatível), `Build-DatabaseUrl` grava o scheme do servidor (`mysql+pymysql`/`mariadb+pymysql`); `migrations/0002` recebeu caminho MySQL via `information_schema` (M-1) e `requirements.txt` ganhou `cryptography` (M-5, emenda aprovada na lista) — suíte 923/1 idêntica
- [x] T023 [US3] Atualizar/remover referências XAMPP classificadas como dependência real (docs e scripts apontados em T012) — **nenhuma remoção às cegas**; referências históricas mantidas com marcação explícita (FR-012) — **feito**: diagnóstico confirmou ZERO dependência funcional de XAMPP em código/scripts (só históricas); `install.ps1` agora recusa serviço XAMPP com aviso explícito (FR-013); README do repo de instalação recebeu a seção "XAMPP não é suportado como banco do sistema" com nota de que referências históricas permanecem como registro (M-4)
- [x] T024 [US3] Documentar a faixa de versões de MySQL suportada (resultado do diagnóstico T011/T022) e garantir mensagem clara do instalador para versão incompatível/serviço quebrado (FR-013) — **feito**: README ganhou a tabela de faixas (MySQL 8.0+ / MariaDB 10.5+ com justificativa por SGBD) e o instalador valida a versão REAL do servidor em `Get-DbServerKind`, abortando com mensagem de ação (`Atualize o servidor de banco e reexecute`) para versão incompatível e com instrução de configuração quando o serviço do MySQL não sobe após o winget
- [ ] T025 [US3] Validar instalação Windows sem XAMPP ponta a ponta (banco+sistema+HTTPS) e executar a suíte comparando ao baseline (SC-005, SC-001)

**Checkpoint**: Windows funciona apenas com MySQL nativo; XAMPP sem papel funcional (SC-005).

---

## Phase 6: User Story 4 — Deploy reproduzível e PRO consistente (Priority: P2)

**Goal**: `deploy.sh` e `deploy.bat` publicam snapshots equivalentes para a mesma dev, contendo tudo que a produção precisa e nada indevido (contrato C1).

**Independent Test**: mesma dev commitada → snapshots via `.sh` e `.bat` equivalentes (mesmos arquivos, line endings tratados); divergências residuais 100% classificadas (SC-007, SC-002).

### Implementação para US4

- [ ] T026 [US4] Produzir a lista de arquivos do lote deploy em specs/061-auditoria-padronizacao-ecossistema/lista-arquivos.md §Deploy (a partir de T008) e obter aprovação (FR-004, D-005)
- [ ] T027 [P] [US4] Corrigir as whitelists de `deploy.sh` e `deploy.bat` conforme classificação de T008: incluir o que a produção precisa (ex.: avaliar `scripts/gera_cert_dev.py` se o contrato C2 exigir no PRO), excluir residuais (ex.: `app/config.py~` se commitado), garantir equivalência `.sh`×`.bat` e tratamento de line endings (FR-015)
- [ ] T028 [P] [US4] Criar teste de contrato do snapshot em `tests/test_deploy_snapshot.py` (padrão da casa): whitelist `.sh` ≡ `.bat`; conteúdo proibido ausente (venv, `data/ssl/`, `.env`, `specs/`, `tests/`, residuais `*~`/`*-old`); arquivos essenciais presentes (`app/`, `run.py`, `requirements.txt`, `README.md`) (contrato C1, FR-015; Constitution VIII)
- [ ] T029 [US4] Validar publicação dupla: mesma dev publicada por `deploy.sh` (Linux) e `deploy.bat` (Windows) → snapshots equivalentes; e `deploy.sh rollback <hash-dev>` restaura o PRO corretamente (SC-007; depende de T027)
- [ ] T030 [US4] Executar a suíte completa e comparar ao baseline (SC-001)

**Checkpoint**: deploy reproduzível nos dois SOs; PRO consistente com a dev (SC-002, SC-007).

---

## Phase 7: User Story 5 — Paridade MariaDB × MySQL sem editar código (Priority: P2)

**Goal**: mesma base de código executa em Linux+MariaDB e Windows+MySQL apenas por configuração; `DATABASE_URL` montada programaticamente com percent-encoding; matriz (Entregável B) sem célula inventada.

**Independent Test**: apontar a aplicação para MariaDB e MySQL apenas via `.env` e validar comportamento equivalente (schema idempotente, operações, backup/restore) (SC-006).

### Implementação para US5

- [ ] T031 [US5] Produzir a lista de arquivos do lote banco/DATABASE_URL em specs/061-auditoria-padronizacao-ecossistema/lista-arquivos.md §Banco (a partir da matriz T011) e obter aprovação (FR-004, D-005)
- [ ] T032 [P] [US5] Padronizar a montagem da `DATABASE_URL` nos pontos apontados pelo diagnóstico (scripts/instaladores/aplicação): montagem programática única com percent-encoding de senha com caracteres especiais, sem duplicação (FR-009, FR-010)
- [ ] T033 [P] [US5] Corrigir apenas as incompatibilidades MariaDB×MySQL **comprovadas** na matriz (T011): nenhum código assumindo comportamento exclusivo de um banco sem tratamento compatível ou limitação aprovada (FR-008)
- [ ] T034 [US5] Testes: unitário do percent-encoding da URL (padrão pytest da casa) + validação de conexão/operações com MariaDB (Linux) e MySQL (Windows) apenas via configuração (SC-006, FR-027)
- [ ] T035 [US5] Executar a suíte completa e comparar ao baseline (SC-001)

**Checkpoint**: paridade provada nos dois bancos; matriz final sem células não verificadas não-explicitadas.

---

## Phase 8: User Story 6 — Instaladores idempotentes, seguros e documentação fiel (Priority: P3)

**Goal**: reinstalação/atualização sem perda indevida de dados; zero segredo em logs/argv/Git; documentação atualizada e sem instruções XAMPP operacionais (contrato C4).

**Independent Test**: reexecutar cada instalador sobre instalação existente → dados/`.env` preservados; varredura de segredos limpa; procedimentos da docs batem com o comportamento real (SC-008, SC-009, SC-010).

### Implementação para US6

- [ ] T036 [US6] Registrar atestado de idempotência dos instaladores corrigidos (T016/T017/T022): reexecução reutiliza banco/usuário/`.env`/cert válido; nenhuma recriação sem `--recreate-db` com dupla confirmação (Linux) ou equivalente aprovado (Windows) (FR-011, FR-017, SC-008)
- [ ] T037 [P] [US6] Executar a varredura de segurança final em deploy/instaladores/docs: senhas/tokens/chaves privadas em Git, logs, argv, mensagens de erro, histórico, saída do PowerShell, temporários — registrar resultado no diagnostico.md §Segurança (FR-026, SC-009, contrato C4)
- [ ] T038 [US6] Atualizar a documentação necessária: `README.md` (instalação/atualização Linux e Windows), `docs/HTTPS_LOCAL.md` (instalação nativa + regeneração de cert), `docs/ARQUITETURA_E_MANUTENCAO.md` (arquitetura, MariaDB/MySQL, requisitos por SO, deploy, troubleshooting) — removendo instruções XAMPP operacionais e mantendo fidelidade ao comportamento real (FR-029, SC-010, Constitution XI)
- [ ] T039 [US6] Executar a suíte completa final e comparar ao baseline (SC-001)

**Checkpoint**: idempotência provada, segurança varrida, documentação fiel.

---

## Phase 9: Polish & Cross-Cutting (Fases 4–5 do plano)

**Purpose**: validação integrada ponta a ponta e fechamento da feature.

- [ ] T040 Executar a matriz de cenários completa do quickstart.md (dev/prod × Linux-MariaDB/Windows-MySQL; instalação limpa, atualização, reinstalação, banco existente/inexistente; HTTPS pós-reboot/reinício) e registrar cada resultado no diagnostico.md §Validação (FR-027, FR-028)
- [ ] T041 Executar a validação de deploy ponta a ponta (Fase 5 do plano): `deploy.sh` + `deploy.bat` sobre a mesma dev → snapshots equivalentes (SC-007) → instalação a partir do PRO com `/health` via HTTPS (FR-028)
- [ ] T042 [P] Atualizar specs/061-auditoria-padronizacao-ecossistema/spec.md (status → `Implemented` com data e resumo de validação) e conferir checklists/requirements.md
- [ ] T043 Fechamento: conferir que nenhum arquivo fora das listas de specs/061-auditoria-padronizacao-ecossistema/lista-arquivos.md foi alterado (D-005), `git status` limpo, e todos os SC-001…SC-010 demonstrados ou registrados como limitação documentada

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Fase 1)**: imediato, sem dependências.
- **Foundational (Fase 2)**: depende do Setup; **BLOQUEIA todas as stories** (baseline de testes + PRO em leitura + whitelists mapeadas).
- **US1 (Fase 3)**: depende da Fase 2; termina no **gate T014** (aprovação do responsável) que libera as demais.
- **US2 (Fase 4)** e **US3 (Fase 5)**: dependem de T014; podem rodar em paralelo (arquivos diferentes — instalador Windows/`install.sh` × docs/scripts). US3 usa o inventário de T012.
- **US4 (Fase 6)** e **US5 (Fase 7)**: dependem de T014; paralelizáveis entre si (deploy scripts × config de banco). US4/T027 depende de T008; US5 depende de T011.
- **US6 (Fase 8)**: depende de US2+US3 (idempotência dos instaladores corrigidos) e se beneficia de US4/US5; documentação (T038) deve refletir o estado final.
- **Polish (Fase 9)**: depende de todas as stories desejadas estarem completas.

### User Story Dependencies

- **US1 (P1)**: sem dependências entre stories; é o gate.
- **US2 (P1)**: depende de T007+T009+T010 (baseline e causa raiz) — dentro de US1.
- **US3 (P1)**: depende de T012 (inventário XAMPP) — dentro de US1; independente de US2 (mas valida junto o cenário Windows).
- **US4 (P2)**: independente de US2/US3 no código; o contrato C1 referencia o C2 (whitelist × cert no PRO), então idealmente após US2.
- **US5 (P2)**: independente; usa a matriz de T011.
- **US6 (P3)**: consolida tudo; última antes do Polish.

### Parallel Opportunities

- Fase 2: T004 ∥ T005 (e T003 em seguida, pois o baseline deve refletir o workspace estável).
- US1: T006 ∥ T007 ∥ T011 ∥ T012 (leituras independentes); T008 após T004+T005; T009→T010 sequência.
- US2: T016 (instalador Windows) ∥ T017 (install.sh) — arquivos diferentes.
- US4: T027 ∥ T028.
- US5: T032 ∥ T033.
- US6: T037 ∥ T038 (varredura × docs).

---

## Implementation Strategy

### MVP First (US1 — diagnóstico)

1. Fase 1 (Setup) → Fase 2 (Foundational) → Fase 3 (US1 completa)
2. **STOP no gate T014**: responsável revisa o diagnóstico e aprova (ou realinha o escopo da Fase 2/3 da spec — as listas de arquivos).
3. Só então seguir para as correções.

### Incremental Delivery

1. US1 → checkpoint (nada mudou, tudo documentado)
2. US2 (HTTPS instalação) → validar independente (VM Windows)
3. US3 (MySQL nativo sem XAMPP) → validar independente
4. US4 + US5 (deploy e paridade de banco) → validar
5. US6 (idempotência/segurança/docs) → validar
6. Polish → validação integrada (Fases 4–5 do plano) → SC-001…SC-010 demonstrados

### Regras permanentes durante a implementação

- Nenhum arquivo funcional alterado antes de T014; depois, **somente** arquivos nas listas aprovadas de `lista-arquivos.md` (D-005).
- Suíte verde ao fim de cada lote (T020/T025/T030/T035/T039) — comparação explícita com o baseline de T003.
- Sem XAMPP, sem segunda implementação de HTTPS, sem segredo em log/argv, sem operação destrutiva em banco (contratos C2–C4).

---

## Notes

- [P] = arquivos diferentes, sem dependência pendente.
- [Story] rastreia a user story de origem (US1…US6 da spec).
- Resultados de diagnóstico SEMPRE em `specs/061-auditoria-padronizacao-ecossistema/diagnostico.md`; listas de arquivos em `lista-arquivos.md`.
- Commits por lote lógico (após cada checkpoint), nunca antes do gate T014.
- Cenários que exigem máquina Windows/VM real: registrar como limitação se indisponíveis — a feature não pode ser declarada concluída sem eles (spec §Assumptions).
