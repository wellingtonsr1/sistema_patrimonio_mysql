# Quickstart: 052-migracoes-alembic

Como validar a adoção do Alembic em 5 minutos (após o implement).

## 1. Estado do repositório de migrações

```bash
.venv/bin/alembic history
# 0002_migracoes_legadas_idempotentes
# 0001_baseline
```

## 2. Suíte (SQLite — sem DDL de migração)

```bash
DATABASE_URL_TEST="sqlite:///:memory:" .venv/bin/python -m pytest -q
```

Tudo verde exceto os 2 failures pré-existentes de `test_backup_externo.py`.

## 3. Teste condicional de migrações

- Em SQLite: valida estrutura das revisões (encadeamento, upgrade/downgrade definidos).
- Com MariaDB em `DATABASE_URL_TEST`: executa `upgrade head` em banco vazio, idempotência na 2ª passada e `downgrade -1 → upgrade +1`.

## 4. Banco legado (prova SC-001)

Em uma cópia do banco de produção/validação:

```bash
# antes: dump de referência
mysqldump --no-data ... > antes.sql
# boot da aplicação (init_db roda create_all + stamp + upgrade)
# depois: dump de comparação
mysqldump --no-data ... > depois.sql
diff antes.sql depois.sql   # única diferença: tabela alembic_version
```

## 5. Ciclo restore (FR-008)

Backup → restore pelo fluxo 017 → boot → aplicação sobe e schema converge (banco restaurado pré-Alembic recebe stamp + revisão idempotente; pós-Alembic antigo recebe upgrade head).
