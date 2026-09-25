# Registro de Validação — Feature 040 (Constituição XII / SC-007 / T010)

**Data**: 2026-09-25 · **Feature**: Ajuste Responsivo da Tabela "Colaboradores & Custodiantes"

**Método**: suíte pytest (regressão) + **medição real da página renderizada** — `/custodians` renderizado via TestClient (banco de teste SQLite em memória, Constitution VII) com o CSS real do app (Bootstrap vendor + `style.css`) e o `<style>` escopado do template, medido com layout engine WeasyPrint 70.0. Dados de teste semeados cobrindo os edge cases do quickstart: **matrícula provisória** (`PROV-000001` — badge "provisória"), nome completo longo (39 chars), cargo extenso ("Analista Administrativo Sênior de Controladoria"), departamento institucional extenso (74 chars), e-mail longo (61 chars), contagens de bens 0/3/12.

**Limitação registrada**: sessão headless — screenshots e a conferência visual subjetiva (estética/zoom em navegador real) seguem como cenários do `quickstart.md` para o validador humano; todas as **larguras** abaixo são medições determinísticas reais.

## Alteração aplicada

**Arquivo único**: `app/web/templates/custodians/list.html` (+32/−1)
- `table-layout: fixed` + `<colgroup>` com 7 `<col>`: rígidas em **px** (Matrícula 128 · Bens 92 · Ações 138) e textuais (Nome/Cargo/Departamento/E-mail) **dividindo o restante** igualmente
- CSS 100% escopado em `.cust-lista-table` (nenhuma regra global; nenhum asset tocado — sem bump de cache)
- `min-width: 1150px` com rolagem confinada ao `.table-responsive`; media query ≤768px (header compacto, min-width 1080px)
- Proteções: `overflow-wrap: break-word` nas células; `nowrap` no `tag-badge` da Matrícula; `white-space: normal` nos badges; **NENHUM clamp/ellipsis/nowrap nas textuais** (texto completo — clarificação da spec, FR-004..007)
- Elementos preservados sem alteração: badge "provisória" condicional (`is_provisional`), link do Nome com `bi-person-circle`, pill de Bens com `text-center`, "Editar Colaborador" condicional a `colaboradores.editar`, "Ver Bens" com texto, `text-end` de Ações, ambos os estados vazios

## V0/V1 — Aproveitamento horizontal (AC-01 / SC-001 / SC-002)

Medições por viewport:

| Viewport | Tabela | Rígidas (px) | Textuais (igualmente divididas) |
|---|---|---|---|
| 1440px (desktop) | **1440px = 100%** | Matrícula 128 · Bens 92 · Ações 138 | Nome/Cargo/Depto/E-mail: **270,2px cada** (75%) |
| 1280px (desktop médio) | 1280px = 100% | idem | 230,2px cada |
| 1024px (notebook) | 1024px = 100% | idem | 166,2px cada |
| 700px (tablet) | 700px = 100% | idem | 85,2px cada |

Textuais somam **75%** da largura (SC-002 indicativo ✓ com folga); Ações 138px acomoda "Editar" (32px) + "Ver Bens" (~90px com texto) + gap.

## V2 — Integridade de conteúdo (AC-02..AC-08 / AC-11)

- **Matrícula**: `tag-badge` com `nowrap` — código integral sem quebra; badge "provisória" renderizado ao lado (verificado no render com `PROV-000001`).
- **Nome/Cargo/Departamento/E-mail**: **texto completo, sem clamp nem reticências** (clarificação) — quebra apenas em fronteira de palavra quando o texto excede a coluna; a linha cresce conforme o conteúdo.
- **Bens**: pill centralizado íntegro (contagens 0, 3 e 12 testadas).
- **Ações**: 2 botões ("Editar" + "Ver Bens") lado a lado em 138px; com 1 botão a coluna permanece estável.

## V3 — Alinhamento (AC-09)

- `<colgroup>` único define as larguras para thead e tbody (FR-010/seções 17–18 do pedido) — PASS por construção; confirmado na renderização.

## V4 — Responsividade e temas (AC-10 / FR-011)

| Viewport | Comportamento medido |
|---|---|
| 1440 (desktop) | tabela 100% do container, sem rolagem |
| 1024 (notebook) | tabela 100% (min-width 1150 escalado); rígidas fixas, textuais 166px |
| 700 (tablet) | min-width ativo → rolagem confinada ao `table-responsive`; media query ≤768px compacta o header |
| Celular (<576px) | rolagem confinada; `max-width:140px` do `tag-badge` global (≤479px, **preexistente**, style.css L1027) pode truncar matrículas muito longas — comportamento anterior à 040, fora do escopo (F3 do analyze) |
| Zoom 80%–200% | fluida; rígidas fixas, textuais proporcionais |

**Temas claro/escuro**: nenhuma cor nova adicionada (nenhuma regra de cor no `<style>` escopado); contraste preservado por herança (R7).

## V5 — Não-vazamento / escopo (FR-012/FR-014 / AC-12/AC-13)

- `git diff --stat`: **apenas** `app/web/templates/custodians/list.html` (+32/−1) — PASS
- 0 referências a `.inv-equip-table` (038), `.mov-lista-table` (039), `.inv-lista-table` (037), `.inv-esperados-table` (036) no diff — PASS
- Pesquisa, botões do header e ambos os estados vazios: nenhum toque — PASS
- `style.css`/`sw.js`/assets estáticos: nenhum toque — sem bump de cache — PASS

## Regressão funcional (SC-006)

| Momento | Comando | Resultado |
|---|---|---|
| Baseline pré-alteração (T002) | `python -m pytest tests/ -q` | **728 passed** em 74,73s |
| Focado pós-alteração (T006) | `pytest tests/test_help.py tests/test_custodians_search.py tests/test_custodian_provisional.py -q` | **53 passed** (inclui render da página, pesquisa e badge "provisória") |
| Suíte completa pós-alteração (T006) | `python -m pytest tests/ -q` | **728 passed** em 75,28s — zero regressão |

## Decisões finas registradas

1. **Textuais sem corte** (clarificação da spec): diferentemente da 039 (Motivo em linha única), aqui Nome/Cargo/Departamento/E-mail exibem o texto completo — as linhas crescem conforme o conteúdo. O `table-layout: fixed` não trunca nada porque não há `nowrap`/ellipsis nessas células.
2. **Ações em 138px** (a mais larga da família 036–039): "Ver Bens" é um botão **com texto** (~90px) e não apenas ícone; 138px acomoda "Editar" (32px) + gap + "Ver Bens" sem aperto.
3. **Rígidas em px** (Matrícula 128, Bens 92, Ações 138): absorvem a largura real da Plus Jakarta Sans por construção (lição da 039).
4. **Textuais em partes iguais**: Nome, Cargo, Departamento e E-mail têm naturezas semelhantes (texto variável completo) e dividem o restante igualmente — o excedente de qualquer uma beneficia as demais.

## Resultado

**V0–V5: PASS nos critérios mensuráveis** — suíte 100% verde (728/728), textuais dominando com 75% da largura e texto completo, zero regressão, escopo cirúrgico confirmado (1 arquivo). Inspeção visual subjetiva (screenshots/zoom em navegador real) segue procedimento do `quickstart.md` como etapa de aceitação humana.
