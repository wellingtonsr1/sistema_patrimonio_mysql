# Validação — Feature 063: Padronização da Apresentação de Origem e Destino na Trilha de Fluxo & Movimentações

**Data**: 2026-10-07 · **Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Tasks**: [tasks.md](./tasks.md) (T001–T007, T009, T010 concluídas; T008 pendente manual) · **Quickstart**: [quickstart.md](./quickstart.md)

**Método**: TDD red→green (US1) + guarda verde-verde (US2) + subconjunto de regressão + régua completa. Zero DDL; zero alteração de backend; dropdown 062 intocado.

## V1 — Suíte de regressão (Princípio VIII)

| Momento | Resultado |
|---|---|
| **Régua completa (T001/T007)** — `python -m pytest` | **948 passed / 2 skipped / 4 failed** (~67s, exit 1) |
| **Testes novos (T004a)** — `tests/test_presentacao_trilha_063.py -v` | **4 passed** (0.63s, exit 0) |
| **Subconjunto de regressão (T004b)** — `test_movements.py + test_movements_search.py + test_import_asset_movements.py + test_departamento_destino_062.py` | **70 passed** (3.80s, exit 0) |

Os **4 failures** da régua completa são AMBIENTAIS e pré-existentes, fora do escopo 063:

- `tests/test_backup_config.py::test_anti_regressao_default_desativado_no_codigo_real` — subprocesso `C:\Python314\python.exe` sem `dotenv` instalado (`ModuleNotFoundError: No module named 'dotenv'`);
- 3 testes de `tests/test_migrations_052.py` — `ModuleNotFoundError: No module named 'alembic'` no mesmo subprocesso.

Nenhum teste relacionado a 063 falhou; **nenhum teste existente foi editado, enfraquecido ou pulado** — diff de `tests/`: apenas o arquivo novo.

## V2 — TDD red→green comprovado (US1; FR-001/FR-002)

| Etapa | Evidência |
|---|---|
| RED US1 | Docstring de `test_presentacao_trilha_063.py` registra o RED da US1 contra o template que exibia o snapshot cru (`IPMJP - Sede - Divisão de Previdência (Sede - Divisão de Previdência)`) |
| GREEN após T003 | **4 passed** (US1 renderização + US2 guarda) — exit 0 |

Asserts da US1 cobrem exatamente o ui-contract §2/§3: (a) títulos `Setor de Recadastramento` / `Divisão de Previdência` como linha principal; (b) contexto `Sede • IPMJP - Sede`; (c) snapshot cru formatado ausente do HTML; (d) caso deduplicado `Clube da Pessoa Idosa` sem repetição; (e) seção `Custódia & Localização Atual` intacta.

## V3 — Smoke visual (T008; SC-006; AC01–AC04)

**PENDENTE (manual)** — o smoke do quickstart §2 exige a app rodando localmente: abrir `/assets/{id}` de um bem com movimentações e confirmar visualmente: título = departamento, contexto `Localização • Unidade`, "Custódia & Localização Atual" intacta. Prints a anexar a este arquivo quando executado. A renderização server-side já está provada pelos asserts da US1 (V2), que verificam o HTML real produzido pelo TestClient.

## V4 — Não-mutação da gravação/histórico (US2; FR-003/FR-004/FR-005)

`test_nao_muda_gravacao_nem_historico` + `test_dropdown_062_nao_mudou` (verdes ANTES e DEPOIS da mudança de template):

- Transferência grava `destination_location_name` no **formato atual** `Unidade B - Dept B (Sala B)` (FR-003);
- A ENTRADA_AQUISICAO permanece byte-a-byte idêntica após a transferência (nada é regravado — FR-004);
- A busca 049 encontra a transferência por "Dept B" e a entrada por "Dept A" (snapshots casam como antes);
- `GET /assets/{id}` renderiza 200 com o fluxo do dropdown 062 intacto (FR-005);
- Régua já existente reforçada: `test_import_asset_movements.py` L134/L216 seguem verdes (formato de snapshot travado) — dentro dos 70 passed do subconjunto.

## V5 — Escopo do diff (T006; FR-007)

`git diff dd64f37^..dd64f37 -- app/` = **apenas** `app/web/templates/assets/detail.html`:

- Macro `_local_curto` no topo (após o `extends`): remove o sufixo ` - {department}` do name quando presente;
- Card `flow-card`: quando a relação `origin_location`/`destination_location` existe, renderiza `{{ loc.department }}` como linha principal + contexto `local_curto • branch` deduplicado (`parts | join(' • ')`); quando não existe, mantém o snapshot cru com os fallbacks atuais (`Estoque Geral`);
- Rótulos, seta, grid, colaborador (`flow-sub`), badges, termo, motivo e observações byte-a-byte; seção "Custódia & Localização Atual" intocada;
- Nada em models/services/routers/schemas/API/migrations/static. Fora de `app/`: 1 teste novo (`tests/test_presentacao_trilha_063.py`) + artefatos desta spec. Os arquivos alterados em `docs/doc_provisorios/` (`locais.csv` e lock file) são de trabalho do usuário (não da 063).

## V6 — Checklist da Constitution (T010; Princípio XII)

- [x] Escopo: nenhuma alteração fora da especificação (V5)
- [x] Comportamento existente preservado, exceto o previsto (V4; gravação/histórico idênticos)
- [x] Regras de negócio nos services; rotas delegam (nenhuma regra nova; nada em backend)
- [x] Estado/localização/custódia via motor de movimentações (intocado — V4)
- [x] Nenhuma rota/permissão nova (mesma `patrimonio.visualizar` no detalhe)
- [x] Nenhuma credencial em logs/auditoria/código
- [x] Banco: zero DDL, dados preservados (data-model.md; nada a migrar)
- [x] Testes existentes intactos e passando; cobertura nova adicionada (V1/V2)
- [x] Documentação: nenhuma devida — nenhum artigo da ajuda/README menciona o formato atual de Origem/Destino na trilha (spec §1 item 12; Constitution XI)

**Conclusão**: feature 063 implementada, testada e validada — pronta para commit (sob pedido do usuário, fluxo git da casa). Pendência única: smoke visual manual (T008/V3).
