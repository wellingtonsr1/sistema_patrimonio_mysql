# Feature Specification: Migrações de Schema com Alembic (052)

**Feature Branch**: `052-migracoes-alembic`

**Created**: 2026-09-28

**Status**: Draft

**Input**: Substituir o mecanismo artesanal de migração (`_ensure_schema_migrations` em `app/database.py` — `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` em Python) por Alembic, adotando versionamento de schema com risco controlado para as instalações existentes. Regra máxima: **ZERO DDL no deploy de adoção** — nenhuma instalação existente pode ter seu schema alterado pelo simples upgrade do código.

---

## 1. Contexto (fonte: código real, 2026-09-28)

### 1.1 Mecanismo atual

Fluxo de `init_db()` (`app/database.py` L143–158):

1. `_register_all_enums()` — registro de enums customizados.
2. `_create_all_tolerante_corrida()` — `Base.metadata.create_all` com tolerância à corrida entre processos (erro 1050, feature 027: crash-loop do systemd).
3. `_ensure_schema_migrations()` (L64–120) — **migrações aditivas manuais** via SQL cru:
   - `users`: `failed_login_attempts`, `locked_until`, `ad_object_guid`, `ad_dn`, `ad_last_sync`
   - `user_roles`: `assigned_by`
   - `inventario_offline_coletas`: `evidence_metadata JSON` + 2 índices compostos

### 1.2 Problemas do mecanismo atual

| # | Problema | Evidência |
|---|---|---|
| P1 | **Sintaxe dependente de versão**: `ADD COLUMN IF NOT EXISTS` exige MariaDB 10.5+; MySQL não suporta — o mecanismo quebra silenciosamente em qualquer motor não-MariaDB | `database.py` L67 |
| P2 | **Sem versionamento**: impossível saber qual migração um banco já recebeu; o idempotente `IF NOT EXISTS` é a única defesa | arquivo inteiro |
| P3 | **Sem histórico/auditabilidade**: `ALTER TABLE` não fica registrado em nenhuma timeline consultável; cada feature empilha um bloco novo no mesmo arquivo | blocos 033, AD, etc. |
| P4 | **Limitado**: não suporta rename, alter de tipo, drop, data migration — só ADD | todas as instruções |
| P5 | **Risco de drift**: quem instala do zero (create_all com models atualizados) recebe schema diferente de quem atualiza (create_all antigo + ALTERs acumulados) — diferenças sutis ficam invisíveis | comparar fresh vs. atualizado |

### 1.3 Restrições do ambiente (não negociáveis)

- **Produção**: MariaDB via `mariadb+pymysql://` (requirements.txt).
- **Testes**: SQLite em memória (`DATABASE_URL_TEST="sqlite:///:memory:"`) — SQLite **não suporta** a maioria dos ALTERs; a suíte pytest NÃO pode exigir execução de migrações reais.
- **Instalador** (feature 027): `install.sh` + systemd; múltiplos processos podem chamar `init_db()` concorrentemente (tolerância 1050 já implementada).
- **Restore** (features 017/019): restauração substitui o banco inteiro por dump mysqldump — o dump restaurado pode ser de uma versão anterior do sistema.
- **Constituição VII (Banco protegido)**: mudanças de schema são aditivas, revisadas e nunca destrutivas sem decisão explícita.

## 2. Objetivo

Adotar Alembic como mecanismo oficial de migrações incrementais, mantendo o fluxo de instalação nova (`create_all`) intocado nesta versão, com:

1. **Baseline por stamp**: bancos existentes recebem apenas a tabela `alembic_version` (marcação), zero DDL de colunas/tabelas.
2. **Deltas futuros exclusivamente via Alembic**: cada feature nova que exigir schema cria uma revisão versionada — o fim dos blocos `ALTER TABLE` em `database.py`.
3. **Compatibilidade com restore**: banco restaurado de dump antigo deve convergir ao schema atual no próximo boot.

## 3. Decisões de escopo (clarifications)

- **Q1 — Baseline completo (autogenerate do schema inteiro como revisão inicial) vs. baseline vazio (stamp)?** → A: **Baseline vazio (stamp)** — a revisão base é um no-op; bancos existentes são marcados, instalações novas continuam via `create_all`. Justificativa: baseline completo exigiria provar que o autogenerate reproduz fielmente dezenas de tabelas com enums customizados (risco alto, ganho zero imediato); a dupla fonte (models/create_all + migrations) é aceita nesta versão e documentada como dívida consciente. Evolução para baseline completo fica como candidato a spec futura (decisão 2026-09-28).
- **Q2 — As migrações Python atuais (`_ensure_schema_migrations`) viram revisão Alembic?** → A: **Sim, como primeira revisão real, idempotente** (`IF NOT EXISTS` via `op.execute`) — bancos que nunca receberam os ALTERs convergem; bancos já alterados executam no-ops. A função Python é removida de `database.py` na mesma feature (decisão 2026-09-28).
- **Q3 — Quem executa `alembic upgrade head`?** → A: `init_db()`, no boot, após `create_all`, com tolerância à corrida (mesmo espírito do erro 1050): upgrade concorrente falho é retentado uma vez; erro persistente é relançado (decisão 2026-09-28).
- **Q4 — Testes automatizados das migrações?** → A: A suíte SQLite continua não executando DDL de migração. Novo teste **condicional**: quando `DATABASE_URL_TEST` aponta para MariaDB (ou variável dedicada), executa `upgrade head` em banco vazio, segunda execução idempotente e cadeia `downgrade -1 → upgrade +1` da última revisão; em SQLite, o teste valida apenas a construção das revisões (importável, `revision` encadeada, `down_revision` único) e é pulado com skip claro (decisão 2026-09-28).

## 4. Requisitos

### Functional Requirements

**US1 — Infraestrutura Alembic (P1)**

- **FR-001**: `alembic` MUST ser adicionado a `requirements.txt`; diretório `migrations/` na raiz com `alembic.ini` e `env.py` apontando para a URL real do app (`app.config.DATABASE_URL`) e `target_metadata` = `Base.metadata` (com `_register_all_enums()` executado no env para enums).
- **FR-002**: A revisão base MUST ser no-op ("baseline — stamp only"), com mensagem documentando a decisão Q1.
- **FR-003**: Em `init_db()`, após `create_all`, o sistema MUST garantir o estado Alembic: banco sem `alembic_version` → `stamp head` da revisão base (zero DDL além da própria tabela de versão); banco já versionado → `upgrade head`. A suíte SQLite (Princípio VIII) NÃO PODE ter seu comportamento alterado: em `DATABASE_URL_TEST="sqlite:///:memory:"` o `stamp`/`upgrade` é no-op seguro — com o banco em memória e o create_all acabado de rodar, o schema já é o estado-alvo e não há delta a aplicar (a tabela `alembic_version` nem precisa persistir; ver D2 do plan).
- **FR-004**: A primeira revisão real MUST reproduz idempotentemente os ALTERs atuais (Q2) e `_ensure_schema_migrations` MUST ser removida de `database.py`.
- **FR-005**: O upgrade no boot MUST ser tolerante à corrida (Q3) e a falha persistente MUST ser logada com ação recomendada, não engolida. Em SQLite de teste, nenhuma dessas rotas é exercida (no-op — ver FR-003/D2).

**US2 — Fluxo do desenvolvedor (P1)**

- **FR-006**: Documentação MUST definir o workflow: `alembic revision -m "0XX-descricao"` (padrão de nome com número de feature), revisões sempre escritas à mão com `op.*` (autogenerate permitido apenas como rascunho, revisão obrigatória antes do commit), proibição de DDL destrutivo sem justificativa na mensagem da revisão.
- **FR-007**: Cada revisão MUST ter `downgrade()` implementado (mesmo que documentado como no-op quando impossível — ex.: downgrade de ADD COLUMN).

**US3 — Compatibilidade restore e testes (P2)**

- **FR-008**: Banco restaurado de dump **anterior ao Alembic** (sem `alembic_version`) MUST convergir via fluxo do FR-003 (stamp da base + upgrade da revisão idempotente — no-ops seguros). Banco restaurado de dump **versionado antigo** converge via `upgrade head`. Cenário documentado em quickstart.
- **FR-009**: Teste condicional conforme Q4, incluindo a validação de encadeamento de todas as revisões existentes. A parte estrutural (encadeamento, importabilidade) roda sempre — inclusive SQLite — garantindo cobertura de CI sem MariaDB.

### Não-requisitos

- Nenhuma migração de schema nova nesta feature além da revisão idempotente do Q2 (nenhum comportamento de negócio muda).
- Autogenerate como fonte oficial, baseline completo do schema (Q1 — futuro), multi-tenancy, migrações online/zero-downtime.

## 5. Critérios de sucesso

| # | Critério |
|---|---|
| SC-001 | Banco de produção atualizado pela primeira vez após a adoção: única diferença de schema é a criação de `alembic_version` com `version_num` = revisão base (prova: dump de schema antes/depois) |
| SC-002 | Instalação nova: `create_all` + stamp + upgrade — aplicação funcional, suíte verde |
| SC-003 | Suíte pytest completa verde (mesmo baseline atual: 2 failures pré-existentes de `test_backup_externo.py` fora de escopo) |
| SC-004 | Teste condicional MariaDB executa a cadeia completa quando ambiente disponível (registro em validacao.md) |
| SC-005 | `database.py` sem `_ensure_schema_migrations`; `alembic history` mostra base + revisão 001 encadeadas |
| SC-006 | `docs/ARQUITETURA_E_MANUTENCAO.md` com workflow de migração (como criar, revisar, validar) |
