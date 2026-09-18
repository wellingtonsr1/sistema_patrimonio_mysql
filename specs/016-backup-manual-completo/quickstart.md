# Quickstart: Backup Manual — Briefing Completo

**Feature**: 016-backup-manual-completo

## Pré-requisitos

```bash
python3 -m pytest -q   # baseline: 385 passed + falha pré-existente RBAC lockout
```

## 1. Suíte automatizada

```bash
python3 -m pytest tests/test_backup_manual.py -q   # feature (A–J + novos)
python3 -m pytest -q                               # regressão completa (Teste J)
```

**Esperado**: feature verde; suíte completa verde exceto `test_rbac.py::test_lockout_after_failed_attempts` (baseline).

## 2. Testes obrigatórios do briefing (§34 — A–J)

| Teste | Cenário | Onde |
|---|---|---|
| A | Autorizado cria backup (arquivo, tamanho, auditoria) | suíte 015 adaptada |
| B | Não autorizado → acesso negado, nenhum backup | suíte 015 |
| C | Download autorizado | suíte 015 adaptada (gzip) |
| D | Download não autorizado | suíte 015 |
| E | Inexistente → 404 seguro | suíte 015 |
| F | Path traversal bloqueado | suíte 015 + `.part` inacessível |
| G | Falha → `BACKUP_FALHA`, sem falso sucesso, sem parcial | novo (literal) |
| H | Múltiplos backups, nenhum sobrescreve, listagem correta | novo (web) |
| I | Integridade: leitura + SHA-256 recomputado == exibido | novo |
| J | Regressão: login, RBAC, módulos existentes | suíte completa |

## 3. Validação manual (MariaDB real — como na 015, agora com gzip/SHA-256)

1. Login admin → **Administração → Backups** → "Gerar backup".
2. Confirmar: arquivo `backup_*.sql.gz` listado no topo com **Integridade OK** e SHA-256 exibido.
3. `file data/backups/backup_*.sql.gz` → gzip; `gunzip -t` → integridade; `gunzip -c | head` → dump SQL MariaDB válido.
4. `sha256sum <arquivo>` → igual ao SHA-256 exibido na tela.
5. Baixar pela interface → bytes idênticos (`sha256sum` no arquivo baixado).
6. Auditoria: eventos `BACKUP_CRIADO` (sucesso) e `BACKUP_DOWNLOAD` na trilha existente.
7. `.part` não existe no diretório após a conclusão.

## 4. Relatório final obrigatório (§39 do briefing — checklist de entrega)

Ao concluir a implementação, o relatório deve conter exatamente:

- [ ] Arquivos alterados e por quê (um a um)
- [ ] Banco identificado; mecanismo de backup utilizado
- [ ] Arquivos/diretórios persistidos identificados; o que entrou no backup; o que foi excluído
- [ ] Local de armazenamento; geração do nome; verificação de integridade; proteção do download; controle RBAC
- [ ] Eventos de auditoria registrados; testes executados e resultados; limitações; dependências externas
- [ ] Declarações explícitas: **RESTORE: NÃO IMPLEMENTADO · AGENDAMENTO: NÃO IMPLEMENTADO · RETENÇÃO AUTOMÁTICA: NÃO IMPLEMENTADA · ALTERAÇÃO DA ARQUITETURA DO BANCO: NÃO REALIZADA**

## Definition of Done

- [ ] `python3 -m pytest -q` verde (exceto baseline RBAC).
- [ ] Testes A–J cobertos e passando.
- [ ] Validação manual §3 concluída no MariaDB.
- [ ] README/ajuda: conteúdo do backup (inclusões/exclusões), `.sql.gz`, SHA-256.
- [ ] `git diff` restrito a: `backup_service.py`, `audit_service.py` (+constante/rótulo), `admin/backups.html` (colunas), `tests/test_backup_manual.py`, `README.md`, `help_service.py`.
