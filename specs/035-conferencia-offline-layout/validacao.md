# Validação — Feature 035 (Conferência Offline — responsividade e padronização visual)

**Data**: 2026-09-24 · **Suíte**: `.venv/bin/python -m pytest tests/ -q` → **727 passed** (nenhum teste alterado) — FR-015/SC-005 ✓

## Checagens estruturais automatizadas (shell renderizada via TestClient — 12/12 PASS)

| # | Checagem (cenário do quickstart) | Resultado |
|---|---|---|
| V1a | Marca empilhada no CSS (`flex-direction: column` + `row-gap: .3rem` — D1) | ✅ PASS |
| V1b | Título dentro do bloco `.offbar-brand` (logo acima, nome abaixo — US1) | ✅ PASS |
| V1c | `.offbar-line1` removido (estado do commit 30d051e revertido) | ✅ PASS |
| V2a | `main` = `px-lg-5` + `max-width: 90%` ≥768px (idêntico ao base.html — D2) | ✅ PASS |
| V2b | `main` mobile = 100% + padding `.75rem` ≤767px (C-1) | ✅ PASS |
| V2c | `body { overflow-x: hidden }` preservado (FR-007) | ✅ PASS |
| V3a | Quebra controlada nas células (`#itensBody td { overflow-wrap: anywhere }` — D3) | ✅ PASS |
| V3b | Linha de pesquisa com `flex-wrap` + `min-width: 10rem` (reorganiza em telas estreitas — US4/FR-008) | ✅ PASS |
| V3c | `#btnLerQR` mantém contorno `btn-outline-primary` + `flex-shrink-0` (C-2) | ✅ PASS |
| V4a | Header quebra: código+status = 2ª linha ≤767px (`flex: 1 1 100%; order: 3` — C-3) | ✅ PASS |
| V4b | `table-responsive` preservado (rolagem restrita à tabela — FR-007) | ✅ PASS |
| V5a | Estados do indicador de conexão íntegros (`st-ok/st-off/st-wait` — US5) | ✅ PASS |

## Contrato DOM (§1 do contract) — verificado por script

Todos os 24 IDs, o atributo `name="m_result"` e todas as classes funcionais (13) existem com a mesma função — **contrato íntegro**. Nenhum teste pytest foi alterado; suíte completa verde.

## Escopo das alterações (SC-006/FR-016)

`git status`: `app/web/templates/inventarios/offline.html` (template+CSS), `app/web/static/js/sw.js` (apenas `CACHE_VERSION` v24→v25) e artefatos da spec — exatamente o previsto. Nenhum service, model, rota, permissão ou JS funcional alterado.

## Pendências visuais (não automatizáveis nesta sessão)

A inspeção visual final em dispositivo/emulação DevTools (roteiro 320→1920px, claro/escuro, retrato/paisagem — quickstart.md) **não pôde ser executada nesta sessão** (sem navegador disponível). As checagens estruturais acima cobrem todas as regras de layout implementadas; recomenda-se executar o roteiro visual na primeira abertura da página e complementar este registro.

## Ajuste pós-feedback (C-4 — supera C-3, 2026-09-24)

Na validação em celular real constatou-se que a quebra para a 2ª linha (C-3) colocava o código do inventário e o indicador "Online · Em andamento" **abaixo da logo** — indesejado. Corrigido: código e status permanecem na **mesma linha** da marca empilhada em todas as larguras; quando falta espaço encolhem com ellipsis (`.offbar-code`/`.offbar-status` com `flex-shrink: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis` em ≤767px; regra `order: 3` removida). Spec (FR-002/Clarifications C-4) atualizada. `tests/test_inventario_offline.py` 34 passed após o ajuste.

## Ajuste 2 pós-feedback (sticky no F5, 2026-09-24)

Com a tela reduzida, ao rolar/recarregar (F5) a barra superior **subia junto com a página** em vez de fixar no topo. Causa: `body { overflow-x: hidden }` cria um scroll container no body, o que desativa o `position: sticky` do `.offbar` (comportamento conhecido de CSS). Correção: `overflow-x: clip` via `@supports` (recorta sem criar scroll container — sticky volta a fixar), com `hidden` mantido como fallback. SW `CACHE_VERSION` v25 → **v26** para propagar o HTML corrigido (servido cache-first na navegação). `tests/test_inventario_offline.py` 34 passed.

## Ajuste 3 pós-feedback (botão de tema, 2026-09-24)

O botão claro/escuro da shell usava estilo próprio (círculo branco `.offbar-dark`), diferente do sistema. Corrigido para usar o **`.dark-toggle` padrão** do `style.css` (34px, raio 8px, hover e variantes do tema escuro já definidas — Princípio X/FR-016): a classe padrão foi adicionada ao botão (`class="dark-toggle offbar-dark"`) e o CSS local ficou apenas com o posicionamento (`margin-left: auto`). SW v26 → **v27**. `tests/test_inventario_offline.py` 34 passed.

## Notas

- Dados criados para a renderização de validação foram **removidos** do banco de dev ao final (inventário, bem e local temporários).
- Bump do SW propagará o novo layout aos dispositivos na próxima visita online (sem limpeza manual).
- README (seção 3.1) não exigiu alteração: nenhum comportamento funcional mudou (Princípio XI).
