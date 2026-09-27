# Validação: 048 — Importação Inteligente

**Data**: 2026-09-26/27 · **Feature**: `048-importacao-inteligente` · **Constitution XII**: validação parte da definição de pronto.

## 1. Suíte de testes

| Momento | Resultado |
|---|---|
| Baseline (pós-047, T001) | **775 passed** |
| Após a feature (T018) | **815 passed** (775 + 40 novos), 0 falhas |
| Correção do fluxo real de UI (pós-homologação) | **817 passed** (775 + 42 novos), 0 falhas |
| Dropdown "Atribuir a…" (pós-homologação) | **818 passed** (775 + 43 novos), 0 falhas |
| Duplicado + responsável inexistente (pós-homologação) | **819 passed** (775 + 44 novos), 0 falhas |
| Orientação das 3 opções na preview + ajuda (pós-homologação) | **820 passed** (775 + 45 novos), 0 falhas |
| Filtros da preview corrigidos (pós-homologação) | **821 passed** (775 + 46 novos), 0 falhas |
| Filtro Erros separado de Não encontrados (pós-homologação) | suíte mantida verde (46 novos) |

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
5. **Correção pós-homologação (bug do fluxo real de UI)**: o formulário do passo de mapeamento
   envia um select por coluna (`mapping_<coluna>`), e a preview real envia as resoluções como
   selects por linha (`resolution_<row_num>`) — a primeira versão da rota esperava apenas os
   campos JSON agregados, produzindo "Dados do mapeamento ausentes" no uso real (os testes
   originais postavam o JSON diretamente e não exercitavam o formulário). Correção server-side:
   a rota monta o mapeamento a partir dos campos dinâmicos do formulário (lendo o formulário
   já parseado pelo FastAPI em `request._form` — nenhuma leitura duplicada do stream, sem JS
   novo). Dois testes de regressão do fluxo real foram adicionados (submit exatamente como o
   navegador envia): `test_fluxo_real_do_formulario_mapeamento` e
   `test_fluxo_real_resolucao_por_linha_no_confirm`.
6. **Dropdown "Atribuir a…" (correção pós-homologação)**: a opção original era um placeholder
   sem ação ("informe o colaborador exato") cujo valor apontava para nome e não id — a linha
   seria descartada. Agora cada linha NAO_ENCONTRADO recebe um `<optgroup>` com os colaboradores
   ativos do cadastro (nome + matrícula, valor `assign:<id>`); o `apply_resolutions` resolve por
   id e aceita fallback defensivo por matrícula/nome exato via `_resolver_custodiante` (nunca por
   aproximação); a matrícula escolhida é o valor repassado à gravação (identificador único).
   Teste: `test_preview_renderiza_dropdown_atribuir_a`.
7. **Duplicado com responsável inexistente (correção pós-homologação)**: a classificação
   retornava cedo ao encontrar tombamento já cadastrado e nunca verificava o responsável —
   linhas duplicadas com responsável inexistente passavam como "DUPLICADO" e o problema só
   estourava na execução ("Linha 20: colaborador ... não encontrado"), quando o usuário optou
   por reimportação com atualização (skip desmarcado). Agora o responsável é verificado em
   TODAS as linhas; a prioridade de status é NAO_ENCONTRADO > DUPLICADO > AVISO > VALIDO, com
   todos os motivos visíveis (também na duplicidade interna ao arquivo). A resolução
   interativa (atribuir/sem custódia/pular) passa a ser oferecida nessas linhas. Teste:
   `test_duplicado_com_responsavel_inexistente_revela_ambos`.
8. **Orientação das três opções (Princípio XI)**: o aviso da preview passou a explicar a
   diferença entre Importar sem custódia (cadastra o bem sem responsável; alocação depois no
   Fluxo), Pular linha (nada é gravado; corrigir o CSV e reenviar) e Atribuir a… (custódia do
   colaborador escolhido); a Central de Ajuda (artigo "importar-equipamentos") ganhou seção
   com a mesma explicação.   Teste: `test_preview_explica_as_tres_opcoes_de_resolucao`.
9. **Filtros da preview (correção pós-homologação)**: os filtros eram links GET
   (`?filtro=...`), que caíam na rota GET (formulário de upload) — a preview é resultado de
   POST e seu estado não existe em GET. Redesenho server-side: um único formulário por fase
   (csv_content + mapping como estado), filtros como **botões submit** com badge de contagem
   que reenviam a fase analyze (reclassificação somente leitura — sempre contra o estado atual
   do banco) e botão Confirmar com `formaction` para o /confirm. O confirm agora **reexecuta a
   classificação server-side** a partir de csv_content + mapping (nunca confia em payload do
   cliente — defesa em profundidade), aplicando as resoluções escolhidas. Testes:
   `test_filtros_da_preview_reenviam_post_e_nao_vao_para_upload` e ajustes dos testes US3 ao
   fluxo real do formulário.
10. **Filtro Erros separado de Não encontrados (ajuste pós-homologação)**: o filtro "Erros"
    combinava ERRO + NAO_ENCONTRADO (igualando-o ao filtro "Não encontrados" quando não havia
    ERRO de verdade). Cada botão agora mostra apenas a própria situação e o resumo passou a ter
    cartões separados (Erros / Não encontrados), em grade de 7 cartões.
11. **Homologação HTTP real (servidor isolado)**: cenário executado contra uvicorn na porta
    8001 com SQLite temporário (`scripts/homolog_048_serve.py` — nada toca no banco de
    produção), via HTTP real (requests), cobrindo: upload → mapeamento → preview com CSV
    misto (1 VÁLIDO, 2 AVISO, 1 ERRO, 1 NAO_ENCONTRADO, 1 DUPLICADO), cartões do resumo
    separados e corretos, filtros ERRO/NAO_ENCONTRADO/VALIDO/DUPLICADO mostrando exatamente
    a própria situação, dropdown "Atribuir a…" com `assign:<id>`, confirmação com resolução
    aplicada (TMB-H-NE gravado custodiado para Helena), ERRO nunca gravado (TMB-H-ERR
    ausente), duplicado pulado (TMB-SEED-X/Y únicos) e relatório por linha presente.

## 5. Limitações

- ~~Atribuição por `assign:<id>` na UI ainda não oferece busca de colaboradores~~ **Resolvida**:
  a preview agora lista os colaboradores ativos do cadastro no dropdown "Atribuir a…" (item 6
  acima).
- `row_results` cobre os resultados processados pelo `execute_*`; linhas removidas antes da
  gravação (ERRO/IGNORADO/skip) não aparecem no relatório final (aparecem na preview).
- Validação manual de UI (browser) não executada neste ambiente; a interface é exercitada pelos
  testes de integração via TestClient.

## 6. Tasks marcadas

Todos os itens T001–T020 de `tasks.md` marcados como `[X]` (ver tasks.md).
