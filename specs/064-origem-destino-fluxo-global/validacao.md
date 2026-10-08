# Validação — Feature 064: Padronização da Apresentação de Origem e Destino no Fluxo Global de Movimentações

**Data**: 2026-10-07 · **Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Tasks**: [tasks.md](./tasks.md) (T001–T013 concluídas; T014 pendente manual) · **Quickstart**: [quickstart.md](./quickstart.md)

**Método**: TDD red→green (US1) + guarda verde-verde (US2) + subconjunto de regressão + régua completa. Zero DDL; zero alteração de backend; dropdown 062 e trilha 063 intocados.

## V1 — Suíte de regressão (Princípio VIII)

| Momento | Resultado |
|---|---|
| **Régua completa (T001/T012)** — `.venv/bin/pytest -q` | **959 passed / 2 skipped / 0 failed** (83.28s, exit 0) |
| **Testes novos da feature** — `tests/test_fluxo_global_064.py -v` | **7 passed** (1.08s, exit 0) |
| **Subconjunto de regressão (T011)** — `test_movements.py + test_movements_search.py + test_import_asset_movements.py + test_departamento_destino_062.py + test_presentacao_trilha_063.py` | **74 passed** (5.60s, exit 0) |

- **Nenhum teste falhou**: 100% verde na suíte completa.
- **Nenhum teste existente foi editado, enfraquecido ou desabilitado** — diff de `tests/`: apenas o arquivo novo `test_fluxo_global_064.py`.

## V2 — Renderização e Deduplicação (US1; AC01–AC04)

| Etapa | Evidência |
|---|---|
| Testes US1 em `tests/test_fluxo_global_064.py` | `test_titulos_sao_departamento_e_contexto_deduplicado` e `test_caso_deduplicado_clube` **PASSED** |

Asserts da US1 cobrem exatamente o `contracts/ui-contract.md` §2–§4:
- (a) Célula Origem e Destino exibem o `department` como linha principal (destaque);
- (b) Contexto exibe `Localização • Unidade` (ex.: `Sede • IPMJP - Sede`) em `.mov-sec`;
- (c) Snapshot redundante cru `IPMJP - Sede - Assessoria de Gabinete (Sede - Assessoria de Gabinete)` NÃO aparece mais no HTML;
- (d) Caso Clube da Pessoa Idosa deduplicado: contexto exibe apenas `Clube` — sem repetições `Clube • Clube` ou `Clube da Pessoa Idosa - Clube da Pessoa Idosa`.

## V3 — Smoke visual (T014; AC01–AC04, AC10)

**PENDENTE (manual)** — abrir `/movements` na aplicação local com usuário autorizado em `movimentacao.visualizar` e conferir:
- Linha principal = departamento, contexto = `Sede • IPMJP - Sede` em `.mov-sec`;
- Caso Clube com contexto apenas `Clube`;
- Entrada inicial `Fornecedor / Entrada Inicial` mantida como texto literal;
- Registro sem origem `Não definido` + `Nenhum / Estoque` mantido byte-a-byte;
- Layout fixo da Feature 039 preservado (larguras e classes `.mov-fluxo` / `.mov-sec` intactas).
Prints a anexar a este arquivo quando a verificação visual em navegador for realizada.

## V4 — Guarda de não-mutação, busca e CSV (US2; AC05–AC13)

Testes de guarda em `tests/test_fluxo_global_064.py`:
- `test_nao_muda_gravacao_nem_historico`: transferência grava `destination_location_name` no formato atual `Unidade B - Dept B (Sala B)` e histórico da aquisição permanece byte-a-byte idêntico (AC08);
- `test_busca_049_continua_casando_pelo_snapshot`: busca 049 por texto de snapshot (`Dept B`, `Sala B`) continua encontrando normalmente (AC09);
- `test_csv_byte_a_byte_antes_e_depois`: `generate_movements_csv` continua exportando os snapshots brutos intactos nas colunas Origem/Destino (AC11);
- `test_dropdown_062_nao_mudou_e_listagem_acessivel`: rota `/movements` responde 200, links íntegros e suite `test_departamento_destino_062.py` verde (AC12);
- `test_fluxo_global_fallbacks_snapshot_e_literais`: movimentações sem FK de localização renderizam fallbacks `Fornecedor / Entrada Inicial`, `Não definido` e `Nenhum / Estoque` como texto puro sem inventar estrutura (AC06/AC07);
- `test_presentacao_trilha_063.py`: 100% verde (AC13).

## V5 — Escopo do diff (T013; AC14/AC15/Princípio I)

`git diff 34077c6 -- app/` = **apenas** `app/web/templates/movements/list.html`:
- Macro `_local_curto` no topo do template: remove o sufixo ` - {department}` do nome da localização quando presente;
- Células Origem e Destino: utilizam a relação quando presente (`m.origin_location` / `m.destination_location`), exibindo o departamento como linha principal e o contexto deduplicado na linha secundária; fallback ao snapshot textual quando sem relação;
- Zero linhas alteradas em backend, models, routers, schemas, services, API ou migrations.

## V6 — Checklist da Constitution (Princípio XII)

- [x] Escopo: nenhuma alteração fora da especificação (apenas `list.html` em `app/`)
- [x] Comportamento existente preservado, exceto a apresentação solicitada (gravação, busca e CSV idênticos)
- [x] Regras de negócio nos services; rotas delegam (nenhuma lógica de negócio no template)
- [x] Integridade patrimonial: trilha imutável e motor de movimentações intocado
- [x] Segurança e RBAC: mesma permissão `movimentacao.visualizar` preservada
- [x] Nenhuma credencial em logs/auditoria/código
- [x] Banco de dados: zero DDL, zero migrações
- [x] Testes existentes intactos e passando (959 passed, 0 failed)
- [x] Documentação e rastreabilidade atualizadas

**Conclusão**: Feature 064 implementada, testada e validada com 100% de sucesso na suíte de testes. Pronta para homologação visual.
