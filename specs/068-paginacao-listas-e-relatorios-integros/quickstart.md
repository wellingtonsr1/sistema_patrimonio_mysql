# Quickstart — Validação da 068-paginacao-listas-e-relatorios-integros

> Guia executável de verificação da spec. Nada aqui escreve fora do escopo: toda escrita é feita pela aplicação em ambiente de teste e a régua completa usa SQLite in-memory (padrão da casa).

## Pré-requisitos

```bash
# na raiz do repositório, com a venv do projeto
.venv/bin/python -V          # 3.10+
git status --short           # idealmente limpo antes de começar
```

## 1. Validação automatizada (obrigatória)

```bash
# baseline antes de começar (deve ser 1005 passed / 2 skipped — medido em 2026-10-10)
.venv/bin/python -m pytest -q

# suíte nova da feature (AC01–AC15)
.venv/bin/python -m pytest tests/test_paginacao_relatorios_068.py -q

# manifesto de rotas (deve continuar VERDE sem nenhuma alteração no JSON)
.venv/bin/python -m pytest tests/test_route_inventory.py -q

# réguas de regressão dos domínios tocados
.venv/bin/python -m pytest tests/test_report_print_smoke.py tests/test_locations_export.py \
  tests/test_datetime_flows.py tests/test_inventario.py tests/test_inventario_offline.py \
  tests/test_movements_search.py tests/test_assets.py tests/test_api.py tests/test_rbac.py \
  tests/test_central_integracoes.py -q

# régua completa (critério de pronto)
.venv/bin/python -m pytest -q
```

## 2. Validação manual no navegador (recomendada)

Requer dados com **mais de 200 registros** na lista testada (seed de demonstração ou importação CSV).

1. `/assets` — conferir `Mostrando 1–200 de N` e o botão **Próxima**; clicar e conferir `201–400`.
2. Aplicar um filtro (busca + situação) e trocar de página — **filtros continuam na URL e no resultado**.
3. Testar URL inválida: `/assets?page=abc`, `/assets?page=0`, `/assets?page=99999` → sempre página válida, HTTP 200.
4. `/movements`, `/custodians`, `/locations`, `/inventarios` — conferir o indicador novo (`X–Y de Z`) e o pager.
5. `/inventarios/{id}` — conferir paginação dos itens **e** que os contadores globais (esperados/conferidas/restantes/divergências) **não mudam** ao trocar de página; conferenciar um bem e verificar que o fluxo segue normal.
6. `/admin/audit` — paginar e filtrar por **período** e **usuário**; conferir total.
7. `/reports/inventory` — conferir total real (não mais "1.000") e paginação; tentar exportar.
8. Exportações — baixar CSV e XLSX com filtro amplo e conferir **linhas de dados == total exibido**; no PDF com >10.000, conferir o aviso prévio.
9. Responsividade (**AC15**/FR-022): repetir 1, 4 e 7 em **360 px** (pager e indicador não podem quebrar o layout nem sobrepor a tabela).
10. Sem permissão: logar com perfil sem a permissão da lista e abrir `?page=2` → 403 com página amigável.

## 3. Verificação de completude das exportações (somente leitura)

> **Banco e modo**: o script abaixo abre `SessionLocal` de `app.database`, ou seja, lê a **`DATABASE_URL` do `.env`** do ambiente — é **somente leitura** (SELECTs e geração do CSV em memória; **nada é gravado**) e a etapa é **opcional**. Para rodar isolado, exporte `DATABASE_URL` apontando para um banco de teste antes do comando. (Constitution VII: SQLite é restrito à suíte de testes — a aplicação não tem fallback para ele.)

```bash
# total do filtro vs. linhas do CSV exportado (substitua pelo filtro usado na tela)
.venv/bin/python - <<'PY'
from app.database import SessionLocal
from app.services.report_service import ReportService
db = SessionLocal()
assets, total = ReportService.get_filtered_assets(db)          # sem teto
csv = ReportService.generate_inventory_csv(db)
linhas = len([l for l in csv.splitlines() if l.strip()]) - 1    # menos cabeçalho
print("total:", total, "linhas CSV:", linhas, "OK" if total == linhas else "TRUNCADO")
PY
```

> Se o script acima imprimir `TRUNCADO`, o corte de 10.000 **não** foi eliminado — AC06 reprovada.

## 4. Verificação de desempenho (SC-010/SC-011)

- Reproduzir o harness da análise de 2026-10-10 (2.000 bens, TestClient, contagem de queries via `before_cursor_execute`) e registrar antes/depois em `validacao.md`:
  - `/` e `/assets` (página 1): tempo mediano **não pior** que o baseline (24 ms / 33 ms);
  - `/custodians` e `/inventarios`: **número de queries constante** independentes do tamanho da página (sem N+1).
- Harness temporário é **removido** ao final (padrão da 067).

## 5. Verificação de não regressão de contrato

```bash
git diff --stat tests/route_manifest.json   # deve estar VAZIO (nenhuma rota nova)
git diff --stat requirements.txt            # deve estar VAZIO (nenhuma dependência nova)
git diff --stat app/models/ migrations/     # deve estar VAZIO (zero DDL)
```

## 6. Critério de pronto

- [ ] Régua completa verde, com a suíte nova somada (nenhum teste existente editado).
- [ ] `route_manifest.json`, `requirements.txt`, `app/models/` e `migrations/` sem diff.
- [ ] Todos os AC01–AC15 cobertos por teste automatizado ou registro em `validacao.md`.
- [ ] **P1–P5 aprovadas** (P1–P3 em 2026-10-10; P4/P5 em 2026-10-11) constando em `spec.md` Clarifications + §14.
- [ ] `docs/ARQUITETURA_E_MANUTENCAO.md` e central de ajuda atualizados (FR-021).
- [ ] **Commit não criado** sem pedido explícito (padrão da casa).
