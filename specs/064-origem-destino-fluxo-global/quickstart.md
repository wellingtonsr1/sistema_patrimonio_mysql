# Quickstart — Feature 064: Fluxo Global de Movimentações (Origem/Destino)

**Data**: 2026-10-07 · **Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Contract**: [contracts/ui-contract.md](./contracts/ui-contract.md)

Guia de validação executável da feature. Pré-requisito: working tree na branch `main`/`064-origem-destino-fluxo-global` com a implementação aplicada; ambiente local com o venv do projeto (pytest + TestClient; sem necessidade de MariaDB — os testes usam SQLite em memória).

## 1. Validação automatizada (obrigatória)

```bash
# 1a. Suíte nova da feature (US1 renderização + US2 guarda)
python -m pytest tests/test_fluxo_global_064.py -v
# Esperado: 5 passed (ver spec §19), exit 0

# 1b. Subconjunto de regressão (irmãs 062/063 + movimentações/busca/importação)
python -m pytest tests/test_movements.py tests/test_movements_search.py tests/test_import_asset_movements.py tests/test_departamento_destino_062.py tests/test_presentacao_trilha_063.py -q
# Esperado: 100% passed, exit 0, NENHUM teste editado

# 1c. Régua completa
python -m pytest
# Esperado: 948 + 5 = ~953 passed / 2 skipped / 4 failed PRÉ-EXISTENTES (test_backup_config ×1 + test_migrations_052 ×3,
# ModuleNotFoundError dotenv/alembic em subprocesso — ver 063/validacao.md V1). Exit 1 é ACEITÁVEL somente por esses 4.
```

**Critério de aprovação**: nenhum teste novo ou irmão falha; os 4 failures ambientais são exatamente os mesmos do baseline (comparar nomes).

## 2. Smoke visual (manual — preenche a pendência T008 no padrão da casa)

1. Subir a app local (`python run.py`) e abrir `/movements` com um usuário com `movimentacao.visualizar`.
2. Conferir nas células Origem/Destino:
   - Linha principal = **departamento** (ex.: `Assessoria de Gabinete`); contexto = `Sede • IPMJP - Sede` em fonte menor (`.mov-sec`).
   - Caso deduplicado (Clube): `Clube da Pessoa Idosa` + contexto apenas `Clube` — **sem** `Clube • Clube`.
   - Registro de entrada: `Fornecedor / Entrada Inicial` exibido como está.
   - Registro sem origem: `Não definido` + `Nenhum / Estoque` como está.
3. Conferir que a tabela continua com o layout fixo da Feature 039 (larguras/quebras inalteradas) e que a busca por setor (ex.: `Assessoria`) continua filtrando.
4. Anexar prints antes/depois a `specs/064-origem-destino-fluxo-global/validacao.md` (§V3) — pendência manual, igual à 063.

## 3. Validação da guarda do CSV (automação cobre; verificação manual opcional)

```bash
python -c "from app.database import SessionLocal; from app.services.report_service import ReportService; print(ReportService.generate_movements_csv(SessionLocal()))" | head -3
```

Esperado: colunas "Origem (Local)"/"Destino (Local)" com os snapshots brutos (`branch - department (name)`) — byte-a-byte idêntico ao comportamento pré-feature (prova automatizada pelo teste de guarda §19 da spec).

## 4. Escopo do diff (verificação final)

```bash
git diff main -- app/
```

Esperado: **apenas** `app/web/templates/movements/list.html` (macro + 2 células). Qualquer outro arquivo de produção é violação do AC14/AC15/FR-007.
