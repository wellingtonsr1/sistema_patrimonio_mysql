# Quickstart: Validação da Correção do Backup Manual no Windows (feature 018)

Protocolo de validação de ponta a ponta. Executar após o `/speckit-implement`.

## 1. Pré-requisitos

- Ambiente do projeto ativo (Python 3.10+; dependências instaladas).
- Baseline da suíte antes da edição (medida em 2026-09-18): **420 passed / 4 failed** — 1 lockout pré-existente (tests/test_rbac.py::test_lockout_after_failed_attempts) + 3 falhas do ciclo de restauração 017 (tests/test_backup_restore.py::test_ciclo_completo_service_sucesso, ::test_web_post_executa_ciclo_completo, ::test_falha_no_import_sem_falso_sucesso) que dependem do dump real nesta máquina Windows (mesma causa que a 018 corrige — research D8). Patamar pós-018: **mesmas 4** + testes novos verdes
- Aplicação executável localmente (`python run.py`) com banco MariaDB via `DATABASE_URL`.
- Usuário com permissão `backup.gerenciar` (perfil Administrador).
- **Windows**: XAMPP com MariaDB instalado (ex.: `C:\xampp\mysql\bin\mysqldump.exe`).
- **Linux** (quando disponível): servidor atual onde o backup já funcionava.

## 2. Suíte automatizada (executores FAKE — nunca subprocesso real)

```bash
python -m pytest tests/ -q --tb=short
```

Esperado: patamar **312 + novos ≥ 6 passed**, mesma única falha pré-existente (lockout).

## 3. Teste real no Windows (obrigatório — unitários não são prova; briefing §29)

1. **Configurar o executável** (uma linha no `.env` do servidor, caminho SEM aspas; ajustar para a instalação real):
   ```text
   MYSQLDUMP_PATH=C:\xampp\mysql\bin\mysqldump.exe
   ```
   > Alternativa sem variável: incluir `C:\xampp\mysql\bin` no PATH do Windows e reiniciar o processo. A variável é o caminho recomendado (não depende do ambiente do shell que iniciou a aplicação).
2. **Reiniciar a aplicação** (config lida no start).
3. **Gerar backup real**: login → Administração → Backups → "Gerar Backup".
   **Esperado**: mensagem de sucesso; arquivo novo `backup_AAAAMMDD_HHMMSS_micros.sql.gz` na listagem com **Integridade OK** e **SHA-256** exibido.
4. **Provar o arquivo**: baixar o backup e conferir `sha256sum`/`certutil -hashfile <arq> SHA256` contra o valor exibido; (opcional, destrutivo: NÃO restaurar em produção — extrair o `.sql` e conferir cabeçalho/CREATE TABLE).
5. **Auditoria**: Administração → Auditoria → eventos de backup de sucesso presentes, sem credenciais.
6. **Validar o diagnóstico (caminho feliz de falha controlada)**: temporariamente renomear o executável apontado por `MYSQLDUMP_PATH` (ou apontar para caminho inexistente) → reiniciar → gerar backup:
   **Esperado**: mensagem **"utilitário de dump não foi encontrado no servidor..."** (distinta de "retornou erro"); log técnico em `data/logs/app.error.log` com etapa e tipo da exceção; **nenhuma senha** no log; nenhum `.part` listado; auditoria de FALHA registrada. Reverter o rename.
7. **Conferir que a restauração (017) continua saudável**: com `MYSQLDUMP_PATH` configurado, a tela de restauração lista backups normalmente (não executar restauração em produção; a suíte cobre o fluxo com FAKE).

## 4. Teste real no Linux (quando ambiente disponível — não-regressão)

1. Sem `MYSQLDUMP_PATH` configurada: gerar backup pela tela.
   **Esperado**: sucesso idêntico ao atual (fallback PATH encontra o `mysqldump` do servidor); arquivo com Integridade OK; auditoria de sucesso.
2. Conter logs em `data/logs/app.error.log`: nenhuma mensagem nova de falha.
3. Credenciais: `grep -ri "MYSQL_PWD\|senha\|password" data/logs/app.error.log` (na janela do teste) → **zero ocorrências reais** (senhas nunca aparecem).

## 5. Checklist de aceite (espelha spec §31)

- [ ] Causa real identificada e documentada (research D1–D7) — ✔ registrada no plan
- [ ] Executável localizado/executado corretamente no Windows (com `MYSQLDUMP_PATH`) e no Linux (fallback PATH)
- [ ] Caminhos e diretório tratados corretamente (sem alteração — provado intocado)
- [ ] Falhas: executável ausente, subprocesso com erro, timeout → FALHA com diagnóstico
- [ ] Código de retorno ≠ 0 → FALHA (nunca falso sucesso)
- [ ] Arquivo parcial nunca listado/disponibilizado
- [ ] Mensagens distintas ao operador (não encontrado vs. retornou erro)
- [ ] Log técnico permite diagnosticar; **zero credenciais** em logs/auditoria
- [ ] Auditoria e RBAC existentes intactos; download funcionando
- [ ] Linux sem regressão (suíte + teste real quando disponível)
- [ ] Windows funcionando (teste real §3)
- [ ] Nenhuma alteração não relacionada (`git status` confinado: `app/config.py` [só a variável nova], `app/services/backup_service.py`, testes, README, docs, artefatos da 018)
