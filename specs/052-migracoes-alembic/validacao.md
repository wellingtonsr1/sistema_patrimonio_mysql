# Registro de Validação — Feature 052 (Migrações de Schema com Alembic)

**Data**: 2026-09-30 · **Feature**: adoção do Alembic com baseline vazio (stamp) — zero DDL no deploy de adoção
**Método**: TDD (10 testes; RED 9 failed + 1 skip comprovado antes da implementação) + validação REAL em MariaDB (XAMPP local) com dumps de schema antes/depois + simulação de restore + régua completa.

## Alteração aplicada

| Arquivo | Mudança |
|---|---|
| `requirements.txt` | `alembic>=1.13` (instalado 1.20.0 no venv) |
| `migrations/` (novo) | `alembic.ini` (URL NÃO vive aqui — env.py lê o app), `env.py` (`DATABASE_URL` do app + override `ALEMBIC_DATABASE_URL` só para tooling/testes + `_register_all_enums()` + `Base.metadata`), `script.py.mako`, `versions/0001_baseline.py` (no-op, Q1) e `versions/0002_migracoes_legadas_idempotentes.py` (absorve os ALTERs antigos; downgrade passivo) |
| `app/database.py` | `_ensure_schema_migrations` **removida**; novo `_ensure_alembic_state()` no fim do `init_db()` (guard SQLite no-op total; sem `alembic_version` → stamp 0001; senão upgrade head; retry único; migrations/ ausente → warning com ação recomendada e boot segue); import de `Path` no TOPO (bug real pego na T009: anotação avalia eager no py<3.14) |
| `deploy.bat` | whitelist dos 2 blocos (publicar + rollback) inclui `migrations/` — sem isso o PRO não bootaria com o código novo |
| `tests/test_migrations_052.py` (novo) | 9 estruturais (sempre rodam, inclusive SQLite) + 1 condicional MariaDB (`MIGRATIONS_TEST_URL`) |
| `docs/ARQUITETURA_E_MANUTENCAO.md` | seção "Migração de esquema" reescrita (workflow completo, regras, integração no boot, dívida Q1); fluxo de init e tabela de tecnologias atualizados |
| `README.md` | `alembic_version` no modelo conceitual + checklist "mudou model? → criou revisão?" (T013) |

## Validação (V1–V6)

| # | Critério | Resultado |
|---|---|---|
| V1 | **SC-001** — adoção no banco REAL de produção: dump `--no-data` antes (613 linhas, sem alembic_version) × depois (621): diff mostra EXATAMENTE `CREATE TABLE alembic_version` + sua coluna `version_num`; **zero** mudança em colunas/índices/tabelas de negócio | ✅ (`evidencias/schema_antes.sql` / `schema_depois.sql`) |
| V2 | **SC-002** — instalação nova em banco vazio dedicado (`..._052test`): boot 1 → `0002`, 27 tabelas, app funcional; boot 2 → no-op (`0002`) | ✅ |
| V3 | **SC-003** — régua completa **912 passed / 1 skipped / 0 failed** (61,7s) — baseline era 903/0; +9 testes novos; skip é o condicional MariaDB por design (Princípio VIII) | ✅ |
| V4 | **SC-004** — teste condicional executado contra MariaDB real (upgrade head em banco vazio, idempotência na 2ª execução, downgrade −1 → upgrade +1): **10/10 passed** com `MIGRATIONS_TEST_URL` | ✅ |
| V5 | **SC-005** — `alembic history` = `0001 → 0002` encadeadas; `current` = `0002 (head)` no banco real; `database.py` sem o mecanismo artesanal (grep = 0) | ✅ |
| V6 | **SC-006/FR-008** — restore de dump pré-Alembic simulado (schema_antes.sql carregado em banco dedicado `..._052legacy`) → boot → convergiu sozinho para `0002` (27 tabelas); workflow documentado (T012/T013) | ✅ |

## Bugs reais pegos pela validação (prova do valor do fluxo)

1. **`NameError: _create_all_tolerante_corrida`** — a edição que substituiu o mecanismo antigo deixou o arquivo com `init_db` duplicado (o antigo, no fim, sombreava o novo). A suíte hermética NÃO pega isso (não roda o init_db real); a validação T009 em banco real pegou na hora. Corrigido e verificado por AST (funções únicas).
2. **Python 3.12** — anotação `Path | None` com import de `Path` apenas dentro da função: import quebraria no Python mínimo do install.sh (o venv local é 3.14, anotações lazy). Corrigido (import no topo) + teste estrutural de guarda.
3. **env.py sobrescrevia a URL do teste** — o teste condicional rodou contra o banco real na 1ª rodada (reversível: revisão passiva; real reconvergido a `0002`). Corrigido com override `ALEMBIC_DATABASE_URL` (padrão de mercado) + garantia no teste de que NUNCA toca o banco do `.env`.

## Higiene

- Bancos de teste dedicados (`_052test`, `_052legacy`) **removidos** ao final; grants criados para a validação permanecem inofensivos (apontam para bancos inexistentes).
- Evidências de schema (antes/depois) versionadas em `specs/052-migracoes-alembic/evidencias/` (sem dados — `--no-data`).
- Nota: dumps de schema contêm o nome de colunas/tabelas (metadados), nenhum dado de negócio.

## Notas operacionais

- O servidor em execução já está na versão `0002`; o próximo restart é no-op.
- No servidor de produção (Linux), após pull: `pip install -r requirements.txt` (alembic entra) → restart do serviço → o boot faz stamp+upgrade sozinho (zero ação manual de schema).
- Futuras mudanças de schema: SEMPRE revisão Alembic (workflow em ARQUITETURA_E_MANUTENCAO.md); nunca mais blocos ALTER em `database.py`.
