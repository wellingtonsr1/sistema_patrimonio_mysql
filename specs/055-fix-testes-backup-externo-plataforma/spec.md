# Feature Specification: Correção cross-platform dos testes do destino externo (055)

**Feature Branch**: `055-fix-testes-backup-externo-plataforma`

**Created**: 2026-09-29

**Status**: Implemented (2026-09-29 — validacao.md V1–V6 PASS; suíte 889/0)

**Input**: Corrigir os 2 failures pré-existentes de `tests/test_backup_externo.py` (feature 045) — `test_destino_sem_permissao` e `test_zero_segredos_em_logs` — que falham desde a 045 por premissa POSIX na simulação de "sem permissão de escrita": os testes usam `os.chmod(dir, r-x)` no DIRETÓRIO de destino, o que não impede criar arquivos dentro dele no Windows (atributo READONLY de diretório é ignorado pela API de criação de arquivos). Prova empírica (2026-09-29): `chmod r-x` + `open(d/"x.txt","w")` no Windows → arquivo criado com sucesso. Resultado: a cópia externa tem SUCCESS e o teste espera FAILURE. Nenhum bug de produção — o mecanismo da 045 está correto (mapeia `PermissionError` → `REASON_SEM_PERMISSAO`).

---

## 1. Contexto (fonte: código real, 2026-09-29)

- Cenários F/G da 045 (quickstart): destino externo sem permissão de escrita → cópia externa deve FAIL com motivo "sem permissão de escrita", preservando o backup local.
- `app/services/external_backup_service.py` (etapa 6 da cópia): abre o temporário no destino; `PermissionError` → `REASON_SEM_PERMISSAO` — **correto e intocado**.
- Testes: `os.chmod(dest, stat.S_IRUSR | stat.S_IXUSR)` — POSIX-only. No Windows, `shutil.disk_usage`/`open` no diretório "r-x" funcionam normalmente → SUCCESS inesperado.
- Estes 2 failures viraram o "baseline aceito" de todas as features 045–054 (régua "apenas os 2 failures pré-existentes"), bloqueando a régua ideal de **0 failed**.

## 2. Requisitos

### Functional Requirements

- **FR-001**: A simulação de "sem permissão de escrita" nos testes MUST ser cross-platform: POSIX mantém `chmod r-x` (comportamento original); Windows usa ACL real via `icacls /deny *S-1-1-0:(WD)` (SID bem-conhecido Everyone — sem dependência de locale), fazendo a criação de arquivo levantar a MESMA `PermissionError` mapeada pelo service.
- **FR-002**: Nenhum código de produção (`app/`) MAY ser alterado — a correção é exclusivamente na infraestrutura de teste.
- **FR-003**: As assertions dos testes corrigidos NÃO PODEM ser alteradas (o contrato da 045 permanece: status/reason/registro/auditoria/backup local íntegro).
- **FR-004**: O helper de simulação MUST liberar as permissões em `finally` (restauração para o cleanup do `tmp_path`), nos dois sistemas.
- **FR-005**: A suíte completa MUST terminar com **0 failed** (régua nova: 889+ passed, zero failures permitidos).

### Não-requisitos

- Não alterar o mecanismo de cópia/validação/registro da 045.
- Não criar testes novos além do necessário (os cenários F/G já existem e passam a ser executáveis de verdade no Windows).

## 3. Critérios de sucesso

| # | Critério |
|---|---|
| SC-001 | `pytest tests/test_backup_externo.py` → 20 passed (0 failed) no Windows |
| SC-002 | Suíte completa → **0 failed** (889+ passed) — fim do baseline de 2 failures aceitos |
| SC-003 | `git diff` confinado a `tests/test_backup_externo.py` + artefatos spec-kit |
| SC-004 | Assertions dos cenários F/G idênticas (diff mostra apenas a mecânica de bloqueio) |

## 4. Assumptions

- Ambiente POSIX continua exercendo o caminho original (`chmod r-x`), preservado no helper.
- `icacls` está presente em todo Windows suportado (Vista+); a liberação usa `/remove:d` tolerante a falha (`check=False`).
- A partir da 055, a régua de regressão das próximas features passa a ser "0 failed" (as 2 falhas conhecidas deixam de existir).
