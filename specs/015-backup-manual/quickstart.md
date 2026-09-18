# Quickstart: Backup Manual do SisPatrimônio Pro

**Feature**: 015-backup-manual

## Pré-requisitos

```bash
python3 -m pytest -q   # baseline: verde exceto a falha pré-existente RBAC (lockout)
```

## 1. Suíte automatizada

```bash
python3 -m pytest tests/test_backup_manual.py -q   # feature (geração/lista/download/RBAC/auditoria)
python3 -m pytest -q                               # regressão completa
```

**Esperado**: feature verde; suíte completa verde exceto `test_rbac.py::test_lockout_after_failed_attempts` (baseline pré-existente — não é regressão desta feature).

## 2. Cenários automatizados (service + web)

| # | Cenário | Resultado esperado |
|---|---|---|
| 1 | Geração (executor fake) | arquivo em `data/backups/`, nome `backup_*.sql`, tamanho > 0; auditoria `BACKUP_CRIADO/SUCCESS` |
| 2 | Falha de geração (fake lança erro) | exceção controlada; auditoria `BACKUP_CRIADO/FAILURE`; nenhum artefato listado |
| 3 | Listagem | ordenada desc por data/hora; artefato alheio ignorado |
| 4 | Download | bytes servidos == bytes gravados; attachment header; evento `BACKUP_DOWNLOAD` |
| 5 | Download inexistente/fora do padrão | 404, sem tocar disco, sem evento |
| 6 | RBAC | sem permissão → 403 nas 3 rotas; admin → 200 |
| 7 | Menu | item visível com a permissão; ausente sem ela |

## 3. Validação manual (ambiente de produção/homologação com MariaDB)

1. Login com usuário administrador (ou perfil com `backup.gerenciar`).
2. Menu **Administração → Backups**: tela lista backups (vazio no primeiro acesso).
3. Clicar **Gerar backup agora** → confirmação com nome do arquivo; listagem atualizada no topo com data/hora e tamanho.
4. Conferir o arquivo em `data/backups/backup_*.sql` no servidor (dump SQL legível no cabeçalho).
5. Baixar o backup pelo link da listagem; conferir integridade (tamanho igual; cabeçalho SQL válido).
6. **Não-regressão**: navegar pelas telas existentes (patrimônio, movimentações, administração) — nenhuma alteração de comportamento.
7. (Opcional, operacional) Validar o dump: `mysql -u <user> -p <db> < data/backups/backup_*.sql` em banco de **homologação** — restauração está fora do escopo do sistema (política operacional).

## 4. Definition of Done

- [ ] `python3 -m pytest -q` verde (exceto baseline RBAC).
- [ ] Cenários 1–7 passando.
- [ ] Validação manual §3.2–3.6 concluída em ambiente com MariaDB.
- [ ] README (seção 💾) e central de ajuda documentando: o que contém, como gerar/listar/baixar, onde ficam os arquivos, limitações (manual, sem agendamento; restauração por política operacional).
- [ ] `git diff` restrito a: novo `backup_service.py`, `admin_routes.py` (+3 rotas), `admin/backups.html` (novo), `base.html` (+1 item de menu), `permission_service.py` (+1 permissão), `audit_service.py` (+2 constantes), `config.py` (+1 constante), testes novos.
