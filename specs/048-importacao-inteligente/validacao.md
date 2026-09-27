# Validação: 048 — Importação Inteligente

**Data**: 2026-09-26/27 · **Feature**: `048-importacao-inteligente` · **Constitution XII**: validação parte da definição de pronto.

## 1. Suíte de testes

| Momento | Resultado |
|---|---|
| Baseline (pós-047, T001) | **775 passed** |
| Após a feature (T018) | **815 passed** (775 + 40 novos), 0 falhas |

- Suíte executada: `.venv/bin/python -m pytest tests/ -q` → `815 passed, 3 warnings` (~85 s).
- **R9/SC-007**: todos os testes existentes dos importadores passam **sem alteração de regras**
  (`test_import_asset_location.py`, `test_import_asset_movements.py`, `test_custodian_import.py`,
  `test_custodian_import_optional_matricula.py`, testes da API `import/csv` — ver exceção na §5).
- Diff confinado aos arquivos previstos (contrato §8): 3 `*_import_service.py` (extensões),
  `import_intelligence.py` (novo), `routes.py` (3 rotas de import, mesmas URLs), 3 `import.html`
  + 2 parciais novos, `tests/test_importacao_inteligente.py` (novo), docs/ajuda.
  **Intocados**: `movement_service`, modelos, `permission_service`, auditoria (mecanismo),
  backup/AD/e-mail/1Doc/GLPI/inventário, `style.css`/`base.html`.

## 2. Testes do quickstart (A–Q) — `tests/test_importacao_inteligente.py` (40 testes)

| Teste | Cenário | Resultado |
|---|---|---|
| A | `test_csv_totalmente_valido_importa_todos` | ✅ |
| B | `test_registros_parciais_aceitos_sem_fabricar_valores` | ✅ |
| C | `test_csv_misto_classifica_por_linha` | ✅ |
| D | `test_tombamento_duplicado_classificado_antes_gravacao` | ✅ |
| E | `test_duplicidade_interna_do_arquivo` | ✅ |
| F | `test_responsavel_inexistente_resolucao_interativa` | ✅ |
| G | `test_local_inexistente_avisos_e_regras_atuais` | ✅ |
| H | `test_colunas_desconhecidas_marcadas_nao_utilizadas` | ✅ |
| I | `test_mapeamento_manual_alterado_e_aplicado` | ✅ |
| J | `test_arquivo_vazio_erro_compreensivel` | ✅ |
| K | `test_csv_corrompido_erro_controlado` | ✅ |
| L | `test_encoding_utf8_sig_e_acentos_preservados` | ✅ |
| M | `test_upload_nao_grava_no_banco` + `test_cancelar_*` (links Cancelar em todas as fases) | ✅ |
| N | `test_us3_erro_na_gravacao_rollback_da_linha` | ✅ |
| O | `test_us3_auditoria_com_quantidades_por_classificacao` | ✅ |
| P | `test_importacao_bloqueada_sem_permissao` | ✅ |
| Q | Suíte completa → 815 passed | ✅ |

Extras: camada `analyze_columns` (10 testes T002), classificação colaboradores/locais,
linhas em branco, resoluções R4 (skip/sem_custodia/assign), reenvio FR-018, relatório por linha,
extensão não-CSV, consistência tabela↔parser.

## 3. Comprovações dos SC

- **SC-001** (zero escrita na análise/preview): `test_analise_nao_grava_no_banco` (contagens
  Asset/Custodian/Location antes/depois) e `test_upload_nao_grava_no_banco` (rota). ✅
- **SC-002** (classificação por linha): `test_csv_misto_classifica_por_linha` — zero rejeição em bloco. ✅
- **SC-003** (nada silenciado/criado): colunas desconhecidas renderizadas como "não utilizada"
  (`data-confidence="desconhecida"`); ambíguas exigem seleção; zero coluna/field novo no banco. ✅
- **SC-004** (zero valor fabricado): `test_registros_parciais_aceitos_sem_fabricar_valores` —
  sem "Estoque Central"/"Sem responsável"; ausências permanecem ausentes. ✅
- **SC-005** (100% duplicidades): banco (tag/serial/matrícula/email/nome) + interna
  (`internal_dup_of`) nos 3 kinds. ✅
- **SC-006** (0 ERRO gravado; 0 duplicação no reenvio): `test_us3_confirmacao_grava_validos_e_nunca_erros`,
  `test_us3_duplicados_com_skip_duplicates`, `test_us3_reenvio_mesmo_arquivo_classifica_duplicado`. ✅
- **SC-007**: suíte 815/815; URLs preservadas (`/assets|/custodians|/locations/import` + `/confirm`). ✅
- **SC-008** (auditoria sem segredos): `test_us3_auditoria_com_quantidades_por_classificacao`
  (descrição com `ERRO: 1, AVISO: 1`; asserts de "senha"/"token"). ✅
- **SC-009** (relatório por linha): `test_us3_relatorio_final_por_linha` — bloco
  "Relatório da Importação" com Linha/Situação/Identificador/Motivo de `row_results`. ✅

## 4. Decisões registradas em execução

1. **Colisões de aliases em runtime**: nos dicts Python, chaves literais duplicadas ficam com o
   último valor — as 3 tabelas vigentes **não têm colisões** (o parser atual resolve `descricao`
   → `description` em locais desde a 047). A maquinaria de ambiguidade (FR-003/A1) foi
   implementada e é exercitada por teste via `monkeypatch` (injeção de colisão sem tocar nas
   fontes), mais um teste que garante consistência camada↔parser com a tabela real.
2. **Teste web adaptado (decisão do usuário)**: `test_web_import_upload_preview_and_confirm`
   (`test_custodian_import.py`) foi atualizado ao novo fluxo (upload → mapear → preview →
   confirmar), pois o passo dedicado de mapeamento é sempre exibido (decisão clarify). Nenhum
   outro teste existente precisou mudança; todos os testes de regras de negócio permanecem
   originais. O confirm continua aceitando o payload legado (lista canônica) — R9.
3. **Teste A** ("totalmente válido") inclui local e responsável preenchidos: a linha sem os
   opcionais é **AVISO informacional** (F3), não VALIDO — alinhado ao Teste B do pedido.
4. **Resoluções** coletadas como campo único `resolutions` (JSON `{row_num: ação}`) no confirm;
   linhas NAO_ENCONTRADO sem resolução são **removidas** do lote (nenhuma escolha silenciosa).

## 5. Limitações

- Atribuição por `assign:<id>` na UI ainda não oferece autocomplete/busca client-side de
  colaboradores (o select aponta para informe do colaborador; a busca existe como
  `search_custodian_candidates` para uso próximo). Nenhuma atribuição automática, como exige a spec.
- `row_results` cobre os resultados processados pelo `execute_*`; linhas removidas antes da
  gravação (ERRO/IGNORADO/skip) não aparecem no relatório final (aparecem na preview).
- Validação manual de UI (browser) não executada neste ambiente; a interface é exercitada pelos
  testes de integração via TestClient.

## 6. Tasks marcadas

Todos os itens T001–T020 de `tasks.md` marcados como `[X]` (ver tasks.md).
