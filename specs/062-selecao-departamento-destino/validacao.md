# Validação — Feature 062: Seleção de Destino por Departamento/Setor

**Data**: 2026-10-06 · **Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Tasks**: [tasks.md](./tasks.md) (remediadas pós-analyze F1–F5) · **Quickstart**: [quickstart.md](./quickstart.md)

**Método**: TDD red→green (US1/US2) + guarda verde-verde (US3) + régua completa + smoke visual com artefatos autônomos. Zero DDL; zero alteração de backend.

## V1 — Suíte de regressão (Princípio VIII)

| Momento | Resultado |
|---|---|
| **Baseline (T001)** — antes de qualquer alteração | **939 passed / 2 skipped / 0 failed** (~70s) |
| **Final (T010)** — após os 2 templates + 3 testes novos | **942 passed / 2 skipped / 0 failed** (~66s) |

- Nota de baseline (F8): o patamar 939/2/0 corresponde à árvore atual do usuário (commits `e7fc20a`→`d29a71a` — 061 commitada, +16 testes desde o 923/1/0 das 059/060); os 2 skips são os condicionais `MIGRATIONS_TEST_URL` da 052 (Princípio VIII — zero DDL na suíte).
- **Nenhum teste existente foi editado, enfraquecido ou pulado** — diff de `tests/`: apenas o arquivo novo.
- Subconjuntos de regressão por história (T004/T007): `test_movements.py + test_help.py` = 32 passed; `test_assets.py` = 1 passed.

## V2 — TDD red→green comprovado (US1/US2; FR-010)

| Etapa | Evidência |
|---|---|
| RED US1 (`test_movements_new_groups_by_branch_with_department_first`) | FAILED contra o template plano (sem `optgroup`) |
| RED US2 (`test_assets_new_groups_by_branch_preserving_custodian_select`) | FAILED contra o template plano |
| GREEN após T003 (movements) | US1 PASSED + guarda PASSED + regressão 32 passed |
| GREEN após T006 (assets) | **3 passed** (US1+US2+US3) |

Ajustes no PRÓPRIO teste durante o RED (o sistema estava correto; o teste é que previu errado): (1) origem da ENTRADA_AQUISICAO é o literal `"Fornecedor / Entrada Inicial"` (Feature 029), não `None`; (2) o TestClient segue o redirect 303 → resposta 200 (sucesso provado no banco); (3) membro do enum é `MovementType.TRANSFER` (valor do form `TRANSFERENCIA_LOCAL`).

## V3 — Smoke visual (SC-005; AC-01/AC-02/AC-06; quickstart §2)

Artefatos autônomos (CSS do app embutido, convenção da 038) em [smoke/](./smoke/):

| Artefato | Conteúdo |
|---|---|
| [antes-movements-new.html](./smoke/antes-movements-new.html) | Estado ANTES: opções planas no formato antigo (demo) |
| [antes-assets-form.html](./smoke/antes-assets-form.html) | Estado ANTES: select de Localização plano (demo) |
| [depois-movements-new.html](./smoke/depois-movements-new.html) | **Página REAL** `/movements/new` renderizada pelo app (TestClient) com dados de teste: grupos `Clube` → `IPMJP - Sede`, rótulo `Divisão de Previdência (IPMJP - Sede)`, opção vazia primeira |
| [depois-assets-form.html](./smoke/depois-assets-form.html) | **Página REAL** `/assets/new`: mesma apresentação |

Verificado nos artefatos: 4 ocorrências de `optgroup` por página (abre/fecha × 2 grupos); `-- Manter Local Atual --` e `-- Estoque Central / Almoxarifado --` presentes e fora dos grupos.

## V4 — Não-mutação da gravação/histórico (US3; FR-006/FR-007)

`test_transferencia_nao_muda_gravacao_nem_historico` (verde antes E depois da mudança de template):
- Transferência via POST do form web grava `destination_location_id` = id escolhido e snapshot **no formato atual** `Unidade B - Dept B (Sala B)`;
- A ENTRADA_AQUISICAO permanece byte-a-byte idêntica após a transferência (nada é regravado);
- A busca 049 encontra a transferência por "Dept B" e a entrada por "Dept A" (snapshots casam como antes).
- Régua já existente reforçada: `test_import_asset_movements.py` L134/L216 seguem verdes (formato de snapshot travado).

## V5 — Escopo do diff (T009 remediado; FR-009)

`git diff app/` = **apenas** os 2 templates (+8/−2 cada, somente o corpo do loop):
- `app/web/templates/movements/new.html` — loop `groupby('branch')` + optgroup + rótulo `Departamento (Unidade)`; `<select name="destination_location_id">` e opção vazia byte-a-byte;
- `app/web/templates/assets/form.html` — mesmo padrão; `<select name="location_id">`, opção vazia e select de **colaborador** intocados;
- Nada em models/services/routers/schemas/API/migrations/static. Fora de `app/`: 1 teste novo + artefatos desta spec. Os 2 CSVs alterados em `docs/doc_provisorios/` são de trabalho do usuário (não da 062).

## V6 — Checklist da Constitution (T013; Princípio XII)

- [x] Escopo: nenhuma alteração fora da especificação (V5)
- [x] Comportamento existente preservado, exceto o previsto (V4; gravação/histórico idênticos)
- [x] Regras de negócio nos services; rotas delegam (nenhuma regra nova; nada em template)
- [x] Estado/localização/custódia via motor de movimentações (intocado — V4)
- [x] Nenhuma rota/permissão nova (mesmas `movimentacao.criar` e `patrimonio.criar`)
- [x] Nenhuma credencial em logs/auditoria/código
- [x] Banco: zero DDL, dados preservados (data-model.md; nada a migrar)
- [x] Testes existentes intactos e passando; cobertura nova adicionada (V1/V2)
- [x] Documentação: nenhuma devida — nenhum artigo da ajuda/README menciona o formato atual das opções (verificado no analyze; Constitution XI)

**Conclusão**: feature 062 implementada, testada e validada — pronta para commit (sob pedido do usuário, fluxo git da casa).
