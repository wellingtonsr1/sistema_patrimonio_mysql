# Quickstart: Restauração Segura de Backup (feature 017)

## 1. Suíte automatizada

```bash
python3 -m pytest tests/test_backup_restore.py -q   # novos (A–K)
python3 -m pytest -q                                # regressão completa
```

Baseline esperado antes da implementação: **397 passed + 1 falha pré-existente** (`tests/test_rbac.py::test_lockout_after_failed_attempts`, fora do escopo — Princípio I).

Na suíte, o executor de import é sempre **fake** (SQLite não roda cliente MariaDB — research R2); a validação real do import é o §3.

## 2. Testes obrigatórios (briefing §36 → contract §9)

| Teste | Cenário | Esperado |
|---|---|---|
| A | Autorizado + backup válido + confirmação + backup de segurança + restore + validação | SUCESSO; eventos completos; backup de segurança listado |
| B | Não autorizado | 403 nas 2 rotas; nenhum evento de restore; banco inalterado |
| C | Cancelar confirmação | Nenhum evento de execução; nenhum backup de segurança |
| D | Backup corrompido | Restauração não iniciada; banco preservado; evento de falha |
| E | Backup inexistente | Restauração não iniciada |
| F | Path traversal `../`, `../../` | Bloqueado (reuso de `get_backup_path`) |
| G | Falha ao criar backup de segurança | Restore NÃO inicia; banco preservado; falha registrada |
| H | Falha durante o import | Falha registrada; NENHUM falso sucesso; backup de segurança preservado |
| I | Validação pós-restore | `SELECT 1` + tabelas essenciais + contagens → OK |
| J | Restore concorrente | Somente 1 executa; outro rejeitado com mensagem |
| K | Regressão completa | Suíte inteira verde (exceto RBAC lockout pré-existente) |

## 3. Validação manual no MariaDB real (dump nativo — como na 015/016)

> Executar com o banco real acessível (`DATABASE_URL` do `.env`). Gera artefatos que devem ser removidos ao final.

1. Logar como usuário do perfil Administrador → **Administração → Backups**.
2. Gerar um backup (botão existente) → confirmar `.sql.gz` na listagem com Integridade OK.
3. Criar um dado marcador (ex.: cadastro de teste) que **não** existirá no backup a restaurar.
4. Gerar um segundo backup (este é o backup a ser restaurado — anterior ao marcador).
5. Na linha do backup anterior (passo 2), clicar **Restaurar** → conferir a tela de informações (arquivo, data/hora UTC, tamanho, integridade, advertências, nota de sessões) e **Cancelar** → nenhum evento de execução deve surgir na trilha.
6. Repetir o clique em **Restaurar** → **Continuar** → confirmar **SIM, RESTAURAR BACKUP**.
7. Conferir: mensagem de sucesso citando **os dois arquivos** (restaurado + segurança); na listagem, o backup de segurança (mais recente) está presente com Integridade OK; o marcador do passo 3 **não existe mais** (dados voltaram ao estado do backup).
8. Conferir auditoria (**Administração → Auditoria**): eventos `Restauração Iniciada`, `Backup Pré-Restore Criado`, `Restauração Concluída` — sem credenciais; e que a geração do backup de segurança também registrou `Backup Gerado` (trilha apensável).
9. Conferir integridade externa: extrair o `.sql.gz` baixado → conteúdo é SQL válido; `sha256sum` bate com a listagem.
10. Logar novamente (sessão renovada) e usar o sistema normalmente (AC-16).
11. Remover os artefatos de validação (backups de teste) — sem usar o sistema para exclusão (não há exclusão por design).

## 4. Definition of Done

- [ ] `python3 -m pytest -q` verde (exceto RBAC lockout pré-existente).
- [ ] Testes A–K implementados e passando.
- [ ] Validação §3 concluída no MariaDB real.
- [ ] README + central de ajuda atualizados (restore, backup de segurança, comportamento de sessões).
- [ ] `git diff` restrito a: `backup_service.py`, `audit_service.py` (+8 linhas), `permission_service.py` (+1 permissão), `admin_routes.py` (+2 rotas), `admin/backups.html` (ação + telas), `tests/test_backup_restore.py` (novo), `README.md`, `help_service.py` — **rotas/fluxos da Feature 1, models e demais módulos intocados**.

## 5. Relatório Final Obrigatório (§39 do briefing — entregue ao fim da implementação)

Deve informar exatamente: arquivos alterados e por quê; como o backup é selecionado/validado; como funciona a confirmação; como o backup de segurança é criado/validado; qual mecanismo executa o restore; como o resultado é validado; tratamento de falhas; proteção de concorrência; RBAC; eventos de auditoria; testes executados e resultado; limitações; se houve alteração de estrutura existente.

E declarar explicitamente:

```text
BACKUP MANUAL: REUTILIZADO DA FEATURE 1
RESTORE: IMPLEMENTADO
BACKUP DE SEGURANÇA PRÉ-RESTORE: IMPLEMENTADO
VALIDAÇÃO PÓS-RESTORE: IMPLEMENTADA
AUDITORIA: UTILIZADO O MECANISMO EXISTENTE
AGENDAMENTO: NÃO IMPLEMENTADO
RETENÇÃO AUTOMÁTICA: NÃO IMPLEMENTADA
```
