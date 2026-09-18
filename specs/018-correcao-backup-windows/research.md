# Phase 0 Research: Correção do Backup Manual no Windows

**Feature**: 018-correcao-backup-windows | **Date**: 2026-09-18

## Diagnóstico conclusivo (FR-001/FR-002) — executado nesta máquina (Windows, ambiente real do usuário)

> O briefing proíbe presumir a causa. As provas abaixo foram **executadas** no ambiente onde o
> sistema roda, não inferidas. Cada prova cita o método que a sustenta.

| # | Prova | Método | Resultado |
|---|---|---|---|
| **D1** | A chamada atual do service falha exatamente como em produção | Reprodução fiel do `env` do `_run_mysqldump` (`env = {"MYSQL_PWD": ..., "PATH": "/usr/local/bin:/usr/bin:/bin"}` + `subprocess.run(["mysqldump", ...])`) nesta máquina Windows | `FileNotFoundError: [WinError 2] O sistema não pode encontrar o arquivo especificado` — a exceção que cai no ramo `(OSError, subprocess.SubprocessError)` do `generate_backup`, gerando a mensagem genérica do log real |
| **D2** | `mysqldump` não está no PATH do Windows desta máquina | `python -c "import shutil; print(shutil.which('mysqldump'))"` (e `mariadb-dump`, `mysql`) | Todos → `None` |
| **D3** | O binário existe apenas na instalação XAMPP, fora do PATH | Listagem de `C:\xampp\mysql\bin\` | `mysqldump.exe`, `mysql.exe`, `mariadb-dump`**não** está lá (XAMPP traz `mysqldump.exe` da linha MySQL/MariaDB) — presente em `C:\xampp\mysql\bin\mysqldump.exe` |
| **D4** | O ambiente substituído é a causa — não o binário em si | Mesma chamada com `env` herdado do `os.environ` + PATH do sistema | Continua `FileNotFoundError` **porque o executável não está em lugar nenhum do PATH (D2)** — ou seja, há **duas causas encadeadas**: (a) o código destrói o PATH herdado; (b) mesmo o PATH do Windows não contém o utilitário. Corrigir só (a) não resolve nesta máquina; corrigir só (b) deixa o código frágil em qualquer ambiente |
| **D5** | O log atual é a consequência exata do silêncio do dump | `data/logs/app.error.log` (2 ocorrências hoje 07:59/08:02) + código: `_run_mysqldump` não registra stderr/exceção; `_run_mysql_import` registra (padrão oposto dentro do mesmo arquivo) | Mensagem exata `Falha na geração do backup manual (erro de disco/subprocesso).` — sem causa |
| **D6** | Não existe configuração de executável no projeto | `app/config.py` (só `BACKUP_DIR`, `DATABASE_URL`), `.env` (92 bytes, sem variável de dump), `.env.example` inexistente | Nenhum mecanismo atual para apontar o executável |
| **D7** | As rotas/telas/auditoria não têm papel na falha | `app/web/admin_routes.py` L797–830 (`backup.gerenciar`, chama `BackupService.generate_backup`) | Falha 100% no service; camada web só propaga `BackupError` |
| **D8** | A suíte existente corrobora o diagnóstico | `python -m pytest tests/ -q` (2026-09-18): 3 falhas em tests/test_backup_restore.py (test_ciclo_completo_service_sucesso, test_web_post_executa_ciclo_completo, test_falha_no_import_sem_falso_sucesso) | O ciclo de restauração 017 gera o backup de segurança pelo dump REAL (`restore_backup` não recebe `security_backup_executor` nesses testes) — falha nesta máquina Windows com o MESMO erro de resolução do executável (D1/D4). Corroboração independente: o bug atinge qualquer caminho que chame `_run_mysqldump`. Esses 3 testes permanecem dependentes de ambiente (fora do escopo alterá-los — Princípio I) |

**Resposta às 6 perguntas do FR-001** (espelhadas no plan.md):

1. **Causa**: encadeada — ambiente do subprocesso com PATH fixo Unix (código) + utilitário ausente do PATH do Windows (ambiente). D1/D4.
2. **Por que funciona no Linux**: o PATH fixo Unix (`/usr/bin` etc.) contém o `mysqldump` do servidor Linux.
3. **Por que falha no Windows**: diretórios Unix inexistentes; `C:\xampp\mysql\bin` fora do PATH do usuário; sem variável de configuração para o executável.
4. **Trecho causador**: `env = {"MYSQL_PWD": password, "PATH": "/usr/local/bin:/usr/bin:/bin"}` e a chamada `["mysqldump", ...]` em `_run_mysqldump` (mesmo padrão em `_run_mysql_import` com `["mysql", ...]`).
5. **Menor alteração**: (A) ambiente herdado (`os.environ.copy()`) + `MYSQL_PWD`; (B) resolução do executável: `MYSQLDUMP_PATH` (config, opcional) → fallback `shutil.which` → erro diagnóstico; (C) log técnico no dump; (D) `BackupError` distinto para "não encontrado" vs. "retornou erro". Mesma alteração aplicada ao import (`MYSQLDUMP_PATH` cobre ambos: clientes do mesmo diretório bin; se só o dump for apontado, o import cai no fallback PATH — ver R3).
6. **Continua no Linux?** Sim: fallback `shutil.which` encontra o binário como hoje; ambiente herdado é superset do PATH fixo atual (o PATH fixo atual não adiciona nada que o PATH do sistema do servidor Linux não tenha — ver R2).

## Decisões de design

### R1 — Ambiente do subprocesso: herdar `os.environ` + `MYSQL_PWD`

- **Decisão**: `env = os.environ.copy(); env["MYSQL_PWD"] = password`.
- **Rationale**: preserva o mecanismo de segurança (senha EXCLUSIVAMENTE no ambiente — FR-005/Princípio VI) e faz o Windows/Linux resolverem o executável pelo PATH real do processo. É o mínimo que elimina a causa (a).
- **Alternativas rejeitadas**:
  - *Manter PATH fixo Unix + concatenar `C:\xampp\...`*: hardcode de caminho específico (proibido, briefing §7); quebraria em outro Windows.
  - *`shell=True`*: briefing §5 proíbe sem necessidade; superfície de injeção maior.
  - *Passar senha via `--password=` no argv*: visível no processo (`ps`/Gerenciador de Tarefas) — viola FR-005.

### R2 — Ambiente herdado não enfraquece o Linux

- **Decisão**: nenhuma diferenciação por SO (FR-009).
- **Rationale**: no servidor Linux, `subprocess` com ambiente herdado resolve `mysqldump` pelo PATH do sistema, que já contém `/usr/bin`. O PATH fixo atual é um **subconjunto** do herdado; o único efeito colateral teórico seria um binário *diferente* aparecendo antes no PATH herdado — cenário coberto pela `MYSQLDUMP_PATH` (fixa o executável explícito) e pela validação pós-dump já existente (gzip legível, FR-011). Comportamento Linux = superset funcional do atual, provado pela suíte (Teste F do briefing).

### R3 — Resolução do executável: `MYSQLDUMP_PATH` (opcional) → fallback PATH → erro diagnóstico

- **Decisão**: nova variável opcional `MYSQLDUMP_PATH` em `app/config.py` (default `None`), documentada no `.env.example` criado **apenas com exemplo de caminho** (sem segredo). No service: se configurada, usa o valor como executável (Path absoluto; falha clara se inexistente); senão, `shutil.which("mysqldump")` → se ausente, `BackupError` com mensagem distinta ("utilitário de dump não encontrado no servidor...").
- **Rationale**: briefing §7 proíbe caminho fixo hardcoded e auto-descoberta complexa (ex.: varredura de `C:\xampp`); a variável é a "configuração mínima indispensável" do FR-007 e resolve a causa (b) nesta máquina (um apontamento no `.env`).
- **Alternativas rejeitadas**:
  - *Auto-descoberta de XAMPP no código*: briefing §7 proíbe; frágil (instalações em `C:\xampp`, `D:\xampp`, MariaDB standalone...).
  - *Usar `mariadb-dump` preferencialmente*: D3 mostra que este XAMPP só tem `mysqldump.exe`; trocar a ferramenta sem necessidade viola o briefing §6.
  - *Config por SO (ex.: `MYSQLDUMP_PATH_WINDOWS`)*: desnecessário — a variável é do servidor, não do SO; uma só basta (briefing §26).

### R4 — `MYSQLDUMP_PATH` cobre dump e import (um único ponto)

- **Decisão**: o mesmo valor resolve `mysqldump` (dump) e, por derivação do diretório, `mysql` (import da 017) — `Path(mysqldump_path).with_name("mysql" + sufixo)`; se a derivação não existir, fallback `shutil.which("mysql")`.
- **Rationale**: ambos os clientes vivem no mesmo `bin` do SGBD (D3); evita segunda variável e mantém a restauração 017 consistente no Windows. A suíte continua com executores FAKE (padrão 015–017) — nenhuma chamada real nos testes.
- **Alternativa rejeitada**: variável separada `MYSQL_PATH` — configuração duplicada sem ganho (briefing §19).

### R5 — Log técnico no dump (paridade com o import) + sanitização

- **Decisão**: `_run_mysqldump` passa a registrar, em falha: etapa ("dump"), tipo/mensagem da exceção, código de retorno (quando `CalledProcessError`) e stderr **sanitizado** com `_sanitize_stderr` existente (replace da senha + truncamento 500 chars). Nenhum handler novo; mesmo `logger = logging.getLogger(__name__)` (briefing §22).
- **Rationale**: FR-003/US2; `_sanitize_stderr` já existe e é testada no caminho de import — reuso direto (Princípio I/III).
- **Alternativa rejeitada**: propagar stderr ao usuário/auditoria — pode conter host/segredos; permanece só no log técnico (padrão do import).

### R6 — Mensagens amigáveis distintas; nada mais muda na superfície

- **Decisão**: novos textos `BackupError`: (a) "O utilitário de dump não foi encontrado no servidor. Verifique a configuração MYSQLDUMP_PATH/PATH." (b) mantém "O utilitário de dump retornou erro." e timeout como estão. A auditoria e a tela continuam idênticas (FR-016/FR-018).
- **Rationale**: distingue "executável ausente" (FR-014) sem criar hierarquia de exceções nova; operador entende o remédio (configurar o caminho) sem ver segredo.

## Fatos de código que amarram o plano

| Fato | Evidência |
|---|---|
| Executor é injetável para testes (`dump_executor`) | `generate_backup(..., dump_executor=...)` — testes novos podem fakear sem tocar subprocesso |
| Temporários/validação/integridade/SHA-256/renomear atômico | `generate_backup` passos 1–5 — **não serão tocados** (FR-011/012/013 já implementados e testados) |
| Auditoria success/failure já cobre falha com descrição controlada | bloco `except Exception` de `generate_backup` — **não muda de formato** |
| `_sanitize_stderr(stderr_text, password)` já existe | reuso no dump (R5) |
| Guard de restauração (017) intocado | `restore_in_progress()` check em `generate_backup` |

## Sem [NEEDS CLARIFICATION]

Todas as decisões acima derivam do código existente + diagnóstico executado. A única escolha de operação (valor de `MYSQLDUMP_PATH` no `.env` da máquina) é do operador — documentada no quickstart §3.
