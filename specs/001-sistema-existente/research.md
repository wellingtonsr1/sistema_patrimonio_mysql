# Phase 0 — Research & Decisions: 001-sistema-existente

**Feature**: SisPatrimônio Pro — Baseline do Sistema Existente | **Date**: 2026-09-14

> Objeto desta pesquisa: **verificar no código real** cada decisão técnica do plano.
> Não há unknowns de tecnologia (stack existente e confirmada). Toda decisão abaixo foi
> validada por leitura dos arquivos citados.

---

## R1. O plano deve alterar código da aplicação?

- **Decision**: Não. A feature entrega apenas artifacts de documentação em
  `specs/001-sistema-existente/`.
- **Rationale**: A spec (§12) exclui implementação/correção/refatoração do escopo; a
  Constitution (I, XII) exige evolução incremental guiada por especificação; o briefing
  do plano proíbe reescrita e refatorações não relacionadas.
- **Alternatives considered**: incluir correção dos problemas conhecidos
  (SPEC-KIT-SISTEMA-ATUAL.md §25) — rejeitada por ampliar escopo.
- **Verificação no código**: `git status` confirma que nenhum arquivo de `app/`,
  `tests/`, `docs/` foi modificado nas etapas anteriores desta feature.

## R2. Stack — há necessidade de nova dependência ou troca de tecnologia?

- **Decision**: Nenhuma. Stack existente mantida 100%.
- **Rationale**: Todos os requisitos da spec (preservação) são atendidos pela stack
  atual; não há funcionalidade nova que exija recurso adicional.
- **Alternatives considered**: introduzir Alembic para migrações versionadas —
  rejeitada: sem DDL nesta feature e o mecanismo existente (`_ensure_schema_migrations`)
  é o padrão do projeto.
- **Verificação**: `requirements.txt` (fastapi, uvicorn, sqlalchemy, pydantic, jinja2,
  python-multipart, pytest, requests, ldap3, pymysql, python-dotenv, openpyxl,
  reportlab) — nenhuma adição necessária.

## R3. Banco de dados — há necessidade de alteração de schema?

- **Decision**: NÃO. Nenhuma alteração de schema nesta feature.
- **Rationale**: A baseline documenta; não escreve. As 17 tabelas existentes atendem
  todos os FRs de preservação (FR-001..FR-014).
- **Alternatives considered**: normalizar "setor" em entidade própria — rejeitada:
  mudança estrutural sem necessidade de requisito (Constitution VII; regra 6/11 do
  briefing).
- **Verificação**: `app/models/` (17 arquivos), `app/database.py`
  (`init_db`, `_ensure_schema_migrations` — `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`,
  MariaDB 10.5+), `app/config.py` (DATABASE_URL obrigatória, sem fallback SQLite).

## R4. Onde vivem as regras de negócio que a baseline deve documentar?

- **Decision**: Nos services (`app/services/`), conforme arquitetura em camadas.
- **Rationale**: Verificado: `movement_service.create_movement` concentra transições de
  estado/custódia (validações de bem baixado, custodiante obrigatório, termo);
  `inventario_service.record_check/close_inventario` concentram as regras de
  conferência/encerramento; `permission_service` concentra RBAC (catálogo, seed,
  helpers); `auth_service`/`session_service` concentram autenticação/sessão/lockout;
  `audit_service` concentra a trilha.
- **Alternatives considered**: documentar regras nas rotas — rejeitada: rotas apenas
  orquestram (exceção conhecida: consultas ORM curtas inline em `admin_routes.py` e na
  busca do inventário — registrada como problema, não corrigida).
- **Verificação**: leitura direta dos 17 módulos; rotas chamam services
  (ex.: `app/web/routes.py` importa `MovementService`, `InventarioService`,
  `AssetService`, etc.).

## R5. Como a validação de "não-regressão" deve ser executada nesta feature?

- **Decision**: Executar a suíte pytest existente (154 testes) em banco isolado
  (SQLite in-memory por padrão), sem qualquer configuração extra.
- **Rationale**: `tests/conftest.py` já isola o banco por teste
  (`create_all`/`drop_all`), usa PBKDF2 reduzido (1000 iterações) e não toca o banco de
  produção. É o protocolo mais simples e fiel.
- **Alternatives considered**: criar suíte nova de smoke — rejeitada: redundante sem
  mudança de código.
- **Verificação**: `tests/conftest.py:26-40` (`DATABASE_URL_TEST` default
  `sqlite:///:memory:`, StaticPool); contagem `def test_` = 154.
- **Risco conhecido**: `test_rbac.py::test_lockout_after_failed_attempts` falha hoje
  (espera 5 tentativas; `AUTH_MAX_FAILED_ATTEMPTS` default = 10). Pré-existente, fora
  do escopo. O quickstart registra o resultado esperado (153/154) para não mascarar.

## R6. A baseline deve documentar contratos de API/UI/CLI como estão?

- **Decision**: Sim — fielmente, incluindo proteções por permissão de cada rota.
- **Rationale**: O valor da baseline é a não-regressão; um contrato "melhorado" deixaria
  de ser referência do real.
- **Alternatives considered**: documentar apenas a API REST — rejeitada: o sistema tem
  três contratos vivos (web, API, CLI) e todos precisam de proteção contra regressão.
- **Verificação**: 74 ocorrências de `require_permission` em `app/web/*.py`;
  prefixo `/api/v1` em `app/api/v1_router.py`; subcomandos em `app/cli.py`.

## R7. Quais pontos NÃO puderam ser confirmados (e ficam marcados, não resolvidos)?

- **Decision**: Manter como "não confirmado" (spec §11), sem criar requisito:
  1. Assinatura de termo (`term_signed` nunca setado `True` — nenhum fluxo).
  2. Consumo real das permissões `movimentacao.editar`, `movimentacao.cancelar`,
     `patrimonio.excluir` (nenhuma rota encontrada).
  3. Página web dedicada de edição de bem/local (edição confirmada apenas na API).
  4. Valor de produto correto para o lockout (5 no teste vs 10 na config).
- **Rationale**: Constitution — não inventar funcionalidades; problemas encontrados
  viram tarefas próprias futuras.
- **Verificação**: grep por `term_signed` (apenas model/schema/service default False);
  grep por rotas com as permissões reservadas (nenhuma); listagem de
  `app/web/templates/assets/` (sem template de edição dedicado).

## R8. Idioma e formato dos artifacts

- **Decision**: Português (pt-BR), Markdown, no padrão dos docs existentes
  (`docs/ARQUITETURA_E_MANUTENCAO.md`).
- **Rationale**: Consistência com o projeto; leitores são a equipe e agentes que
  executarão as próximas etapas do Spec Kit.
- **Alternatives considered**: inglês — rejeitada por quebrar a convenção.

---

## Resumo de resolução de unknowns

| Unknown/decisão | Resolução |
|---|---|
| Alterar código? | Não (R1) |
| Nova dependência? | Não (R2) |
| DDL/migração? | Não (R3) |
| Fonte das regras | Services (R4) |
| Protocolo de validação | Suíte pytest existente (R5) |
| Escopo dos contratos | Web + API + CLI, fiéis (R6) |
| Não-confirmados | Marcados, sem requisito (R7) |
| Idioma/formato | pt-BR Markdown (R8) |
