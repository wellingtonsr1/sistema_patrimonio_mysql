# Quickstart: Validação da Correção do Deadlock da Restauração (feature 019)

Protocolo de validação de ponta a ponta. Executar após o `/speckit-implement`.

## 1. Pré-requisitos

- Ambiente do projeto ativo (Python 3.10+; dependências instaladas).
- **Baseline da suíte**: registrar o resultado de `python -m pytest tests/ -q --tb=no` ANTES de editar (patamar esperado: as falhas pré-existentes conhecidas; desvio ⇒ PARAR e investigar).
- MariaDB/XAMPP ativo no Windows; `MYSQLDUMP_PATH` configurada (018) — a restauração deriva o cliente `mysql` do mesmo bin.
- Usuário com permissão `backup.restaurar`.
- **Um backup válido recente** listado na tela Administração → Backups.

## 2. Suíte automatizada

```bash
python -m pytest tests/test_backup_restore.py -q
python -m pytest tests/test_backup_manual.py -q   # 018 intocada
python -m pytest tests/ -q --tb=no                # patamar = baseline
```

Cobertura nova esperada (testes 019):

- worker roda ciclo com sessões próprias (nenhuma sessão de request no ciclo destrutivo);
- drenagem: pool ocioso descartado; quiescência aguardada; falha de quiescência aborta com falha honesta;
- deadline: subprocesso fake que bloqueia no write → `terminate()` + `BACKUP_RESTORE_FALHA` em ≤ timeout configurado (valor baixo em teste);
- liberação: manutenção e slot de concorrência (`_RESTORE_IN_PROGRESS`) limpos em sucesso, falha e exceção (finally);
- guarda externa: geração de backup SEM `_allow_during_restore` continua bloqueada durante a restauração (FR-015);
- manutenção: middleware responde 503 sem tocar banco (rota com dependência de banco derrubada no teste); whitelist mínima; RBAC intacto;
- crash-safety: exceção na thread → manutenção encerrada, estado liberado, falha auditada;
- paridade 018: backup manual segue idêntico;
- credenciais: nenhum log contém a senha (stderr sanitizado).

## 3. Teste real no Windows (obrigatório — FR-001 §29 da 017 aplica-se)

> ⚠️ Restauração é **destrutiva**: executar em janela de manutenção, com backup fresco.

1. **Gerar backup** pela tela (018) → anotar o arquivo.
2. **Criar um registro rastreável** (ex.: um local "TESTE-PRE-RESTORE").
3. **Gerar novo backup** (conterá o registro).
4. **Apagar o registro** e confirmar que ele sumiu da tela.
5. **Restaurar** o backup do passo 3 pela tela:
   - **Esperado**: POST responde 303 imediatamente (redirect para a listagem); página de manutenção aparece nas demais rotas; indicador de fase na tela de Backups (polling); ao concluir: sucesso auditado, manutenção encerrada, registro "TESTE-PRE-RESTORE" **de volta**.
   - **Falha do bug (estado atual, pré-019)**: travamento com `DROP TABLE` esperando metadata lock (não deve mais ocorrer).
6. **Auditoria**: eventos `BACKUP_RESTORE_INICIADO`, `BACKUP_RESTORE_SUCCESS` (ou `_FALHA`) com horários coerentes; nenhuma senha em log.
7. **Diagnóstico de timeout (opcional)**: com `BACKUP_IMPORT_TIMEOUT=5` no `.env` e o cliente `mysql` renomeado temporariamente → restauração falha **em segundos** com mensagem técnica (etapa/tempo), manutenção liberada, backup de segurança disponível. Desfazer após o teste.
8. **Crash-safety (opcional)**: derrubar o servidor durante o import → subir de novo: manutenção NÃO persiste (flag em memória), estado de concorrência limpo.

## 4. Não-regressão no Linux (prova por design + suíte)

- Drenagem do pool, thread, deadline e middleware são multiplataforma (sem shell, sem caminho específico).
- Sem `BACKUP_IMPORT_TIMEOUT` no `.env` do Linux → default 900 s; resolução do cliente segue 018 (PATH).
- Quando houver acesso ao servidor Linux: repetir §3 passos 1/5/6.

## 5. Resultado

Registrar em `specs/019-import-deadlock/tasks.md` → **Validation Results** (suíte, teste real Windows, Linux quando disponível).
