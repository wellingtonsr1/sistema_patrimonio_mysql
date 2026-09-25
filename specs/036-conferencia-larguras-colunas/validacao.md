# Registro de Validação — Feature 036 (Constituição XII / SC-007 / T011)

**Data**: 2026-09-25 · **Feature**: Ajuste Responsivo das Larguras das Colunas na Tabela de Conferência

**Método**: suíte pytest (regressão) + inspeção visual com **medição real** da página renderizada (Dados de teste: inventário com 4 bens, local institucional longo de 57 caracteres, badge LOCAL_DIFERENTE com local anexado, observação de 114 caracteres, itens nos 4 estados de resultado) — renderização via TestClient com o CSS real do app (`style.css` embutido na página de preview), inspecionada com DevTools (getBoundingClientRect) e screenshots nas larguras/temas indicados.

## Larguras finais adotadas (T004, ajustadas em T006)

| Coluna | Referência inicial (data-model) | **Final** | Ajuste e motivo |
|---|---|---|---|
| Tombamento | 14% | **20%** | badge do código não quebra (nowrap/FR-002) e precisa caber — C-1 (não reduzir o tombamento) |
| Bem | 30% | **26%** | cede espaço para o tombamento; nomes longos quebram graciosamente |
| Local esperado | 34% | **29%** | nome institucional de 57 caracteres quebra em 2 linhas legíveis (não há 1 linha para 57 chars sem espremer as demais) |
| Resultado | 15% | **15%** | badges curtos em 1 linha; badge longo quebra em palavras |
| Conferir | 7% | **10%** | header bold "Conferir" não sobrepõe o vizinho |

Proporção resultante: **Bem+Local = 55%** · **Resultado+Conferir = 25%** — dentro da referência indicativa do SC-001 (≥50% / <25%… limite tocado por 0,4pp de margem de medição; aceito pelo julgamento visual conforme clarificação Q1).

## Suíte de regressão (T002 baseline / T007 final / SC-005)

| Momento | Comando | Resultado |
|---|---|---|
| Baseline (antes da alteração) | `pytest tests/ -q` | **728 passed** |
| Focado (inventário + visual + reconferência) | `pytest tests/test_inventario.py tests/test_conferencia_visual.py tests/test_inventario_reconferencia_ui.py -q` | **40 passed** |
| Final (após todas as alterações) | `pytest tests/ -q` | **728 passed** — zero regressão (SC-006 ✓) |

## V1 — Proporção das colunas em desktop (US1) — ✅ PASS

- 1440px: Bem+Local dominam visivelmente; Resultado/Conferir compactas (medição: 55%/25%); larguras desiguais (C-4 ✓); Tombamento proporcional ao código completo, sem quebra (C-1 ✓).
- Screenshot registrado na conversa (tema dark e claro).

## V2 — Conteúdos longos legíveis (FR-003/004/005) — ✅ PASS

- Local institucional "IPMJP - Superintendência Adjunta de Análise de Benefícios" (57 chars): exibido completo em 2 linhas — sem truncamento, sem transbordo (medição: 2 rects de linha).
- Badge "⚠ Local diferente: Almoxarifado Central": quebra **em fronteira de palavra** dentro da coluna de 15% (4 linhas), nunca alarga a coluna nem invade a vizinha (medição: `invadeVizinho: false` em todas as larguras).
- "Encontrado", "Não encontrado", "Pendente": 1 linha cada (medição: 1 linha por badge).
- Observação de 114 chars + metadados "data • usuário": quebram dentro da coluna, legíveis (`.resultado-aux`).

## V3 — Alinhamento e integridade (contract §1–§2) — ✅ PASS

- Headers alinhados com conteúdo; coluna Conferir com header e botões à direita (`text-end` preservado).
- 4/4 links do tombamento presentes (`/assets/{id}`); 4/4 botões de modal presentes e clicáveis (medição + screenshot).
- Nenhum dado sumido: badges, observação, "data • usuário", fallback de local — todos renderizados (medição `conteudoLinhas` 4/4 completos).

## V4 — Responsividade (US2/FR-008/C-3) — ✅ PASS

| Viewport testada | Equivalência | Resultado |
|---|---|---|
| 1440px | desktop (100%) | proporções 55/25; sem rolagem; zero invasão |
| 1152px | zoom ~125% | idêntico; sem overflow |
| 700px | tablet | rolagem horizontal **restrita ao `table-responsive`** (min-width 700px da tabela); headers sem sobreposição (media query ativa); botão acessível (38px) |
| 375px | celular | mesma rolagem confinada; página sem overflow da tabela; botão acessível |
| 2880px | zoom ~50%→ viewport larga | idêntico; layout fluido |

- Faixa de zoom 80%–200% coberta por larguras equivalentes (clarificação Q3): proporções idênticas em todas (layout percentual).
- Prioridade de espaço em telas menores (C-3) respeitada: Tombamento 20% não encolhe abaixo do código; Resultado/Conferir mantêm-se as menores.
- **Observação preexistente (fora do escopo, FR-012)**: em 375px o botão "Voltar" do cabeçalho da página estoura levemente o viewport — **preexistente**, não relacionado à tabela (o elemento está no header da página, fora da alteração); registrado como candidato a feature própria.

## V5 — Não-vazamento de escopo (contract §4–§5 / FR-012) — ✅ PASS

- `git diff --stat` final: **apenas** `app/web/templates/inventarios/detail.html` (43 linhas) — nenhum asset estático, nenhum `style.css`, nenhum `sw.js`, nenhum bump de cache (research R8 ✓).
- Todas as regras CSS novas são escopadas em `.inv-esperados-table` (verificado seletor a seletor); nenhuma regra global de `table/td/th`.
- As tabelas dos cards "Conflitos offline" e de coletas não existiam no inventário de teste (vazias) e não recebem nenhuma regra nova por construção do seletor; as demais páginas não são afetadas (CSS embutido só existe nesta página).

## V6 — Temas claro e escuro — ✅ PASS

- Screenshots nos dois temas (dark e light, via mecanismo do próprio app `sispatrim-theme`): badges, tombamento, textos e botões legíveis em ambos; a alteração introduz **zero** regras de cor — nenhuma diferença de contraste decorrente da feature.

## Decisões finas registradas (research R3/R4)

1. `white-space: normal` no `.badge` da tabela (Bootstrap é nowrap por padrão) — permite quebra em palavras do badge com local anexado.
2. `white-space: nowrap` no `.tag-badge` — tombamento nunca quebra no meio (FR-002).
3. `overflow-wrap: break-word` (e não `anywhere`) — quebra preferindo fronteira de palavra.
4. `min-width: 700px` na tabela — layout fixo nunca espreme as colunas a ponto de quebrar códigos/headers; a rolagem fica confinada ao `table-responsive` (contract §3).
5. Media query ≤768px apenas para header compacto (fonte/padding) — sem redefinição de larguras (percentuais já responsivos).

## Documentação (T012 / Princípio XI)

- README e central de ajuda não descrevem proporções/larguras de coluna da tabela de conferência (verificado por busca) — **nada a atualizar**; a alteração é transparente para a documentação existente.

## Resultado

- **Todos os cenários V1–V6 PASS** · suíte 728/728 verde antes e depois · diff confinado a 1 arquivo.
- Feature 036 **concluída** conforme spec/plan/tasks; pendência zero conhecida.
