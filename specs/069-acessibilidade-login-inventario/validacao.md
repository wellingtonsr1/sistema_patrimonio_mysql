# Validação — 069-acessibilidade-login-inventario

**Execução**: 2026-10-12 | **Estado**: **implementação completa** (Fase 5, T018–T027) com **P1/P2/P3 aprovadas**. Suíte final: **1051 passed / 3 skipped** (baseline 1023/2 na 068 + 26 novos desta feature + 2 skips preexistentes recontados); `exit=0`.

**Decisões aprovadas (registro)**: **P1** = `aria-label` nos controles compactos (preserva layout); **P2** = incluir skip-link global no `base.html`; **P3** = incluir indicador de foco dos `.result-option`. Todas conforme recomendações da rev. 2 do `research.md`.

## 1. T018 — suíte estática RED

`tests/test_acessibilidade_estatica_069.py` (novo; parser `html.parser` da stdlib, zero dependência) escrito primeiro: **11 failed, 6 passed, 1 skipped** — as 11 falhas correspondiam exatamente aos achados do `research.md` rev. 2 (new/list/detail/conferir/offline sem nome acessível; toggle de senha; fieldset ausente nos 3 templates; `conferir.html` sem `role=alert`).

**O que o RED revelou além do research** (registrado para o revisor, Constitution XII):
- com **sessão autenticada**, `GET /login` injeta o header do `base.html` (a página standalone é o estado público); os testes de login usam `unauth_client` (fluxo real);
- o botão `sidebar-close` do `base.html` era um só-ícone **global** sem nome — corrigido (*aria-label="Fechar menu"*), achado que a análise de origem não listava.

## 2. T019–T024b — fixes aplicados (sem rota/dependência/DDL)

| Tarefa | Arquivo(s) | Conteúdo |
|---|---|---|
| T019 | `inventarios/new.html` | `for`/`id` nos 4 campos (labels visíveis preservados) |
| T020 | `conferir.html` (2 forms), `detail.html` (modal + bem não previsto + encerrar), `offline.html` | `for`/`id` em Local/Observação; **sufixo `{{ item.id }}`** nos ids do modal (RN-7); labels `visually-hidden` onde o placeholder visível era o único texto (bem não previsto) |
| T021 | `conferir.html`, `detail.html`, `offline.html` | grupo de rádios em `fieldset`+`legend` com reset visual inline (zero mudança de layout) |
| T022 | `inventarios/list.html`, `detail.html` | `aria-label` em busca/status/filtro da lista/tombamento; `aria-label="Aplicar filtros"` no `bi-funnel`; `aria-label="Limpar filtros"` no link |
| T023 | `login.html`, `setup.html` | `aria-label="Mostrar senha"` + `aria-pressed="false"` iniciais (o `main.js` já sincronizava estado no clique — verificado L172-202) |
| T024 | `conferir.html` | `role="alert"` no alerta de erro (único caso dos fluxos-alvo) |
| T024a (P2) | `base.html` | skip-link `#conteudo-principal` (invisível até foco) + `aria-label="Fechar menu"` no `sidebar-close` |
| T024b (P3) | `style.css` | `.result-option:has(input:focus-visible)` com outline (apenas no foco, sem efeito em repouso) + regra `.skip-link` |
| — | `inventarios/offline.html` | `role="status"`/`aria-live="polite"` nos 5 contadores dinâmicos (`cntConferidas`, `cntRestantes`, `cntDivergencias`, `cntNaoPrevistos`, `syncStatusLinha`) |

## 3. T025 — réguas

```bash
.venv/bin/python -m pytest tests/test_acessibilidade_estatica_069.py -q   # 17 passed, 1 skipped
.venv/bin/python -m pytest <réguas de inventário/rbac/help/rotas/etc> -q  # 127 passed
.venv/bin/python -m pytest -q                                            # 1051 passed, 3 skipped (103,87s)
```

Todas com `exit=0`. **Zero regressão**: as 3 skips são do estado pré-existente (2 do baseline + 1 do próprio setup skip do `/setup` com usuário já criado — comportamento documentado no teste). Nenhum teste existente editado.

## 4. T026 — documentação

- `docs/ARQUITETURA_E_MANUTENCAO.md` **§12.9** (nova): acessibilidade dos fluxos, arquivos, regras RN-1..RN-8 e limite da guarda estática.
- Artigo da central de ajuda: `app/services/help_article_069.py` (novo), integrado em `app/services/help_service.py` (import + lista `ARTICLES`); id `acessibilidade`, 4 seções (teclado, leitor de tela, foco/contraste, o que não mudou). `tests/test_help.py` → 9 passed; article resolvido por `get_article('acessibilidade')`.

## 5. T027 — guardas de escopo (verificados por `git diff`)

| Guarda | Verificação | Resultado |
|---|---|---|
| `tests/route_manifest.json` intocado | `git diff --stat` | vazio ✅ |
| `requirements.txt` intocado (zero dependência) | idem | vazio ✅ |
| `app/models/`, `app/schemas/`, `migrations/` intocados | idem | vazio ✅ |
| Nenhum teste existente modificado | `git diff --name-only tests/` | só o arquivo novo da feature ✅ |
| Diff funcional | 9 templates + `style.css` (+12 linhas) + `base.html` (+7) + `help_service.py` (+2) + docs §12.9 | dentro do escopo (data-model §1: `style.css` só P3, `base.html` só P2 — ambos aprovados) ✅ |

**Escopo completo do diff**: `app/web/templates/{login,setup,base,inventarios/*}.html`, `app/web/static/css/style.css`, `app/services/help_article_069.py` (novo), `app/services/help_service.py` (+2 linhas), `docs/ARQUITETURA_E_MANUTENCAO.md` (§12.9), `tests/test_acessibilidade_estatica_069.py` (novo), `specs/069-.../` (artefatos).

## 6. Limitações desta validação

- **Verificação com leitor de tela / navegação de teclado real não executada** (ambiente sem browser — padrão da casa): a cobertura equivalente foi estática (parser) + JS do toggle revisado por leitura. A validação manual do `quickstart.md` §4 (leitor de tela, 360 px) fica para o operador com o ambiente gráfico.
- **Contraste não medido**: o único fix de foco foi `.result-option` (evidência concreta); os demais estados dependem de varredura axe com browser — registrada como evolução futura (`data-model.md` §4; backlog M-00x a criar em `docs/Melhorias_SisPatrimonio_Pro.md` se o responsável desejar).
- `role="status"` nos contadores da página offline só é exercitável com JS — a suíte não o valida dinamicamente (declarado no `research.md` R9).
- **Commit não criado** — alterações no diretório de trabalho; commit apenas sob pedido explícito.

## 7. Pós-validação — ajuste do carimbo de cache do CSS (2026-10-12)

Com o novo `.skip-link` no `style.css`, o usuário relatou o link "Pular para o conteúdo"
aparecendo visível após F5. Causa: **cache de stylesheet** — os templates carregam o CSS com
carimbo de versão (`style.css?v=…`), que continuava apontando a versão anterior (sem a regra
Corretiva `left:-9999px`). Corrigido pelo padrão da casa (bump da data):
`?v=20261012` nos 4 templates que linkam o CSS diretamente (`base.html`,
`inventarios/offline.html`, `login.html`, `setup.html` — os demais herdam do base).
Verificado: suíte da 069 + `test_help` + `test_conferencia_visual` → **28 passed, 1 skipped**
(exit=0). Lição registrada: **qualquer mudança em `style.css` exige bump do carimbo nos
templates que o linkam diretamente** (padrão da casa também aplicado em features passadas).

**Achado da rodada completa (corrigido na causa)**: a régua completa pós-carimbo detectou
**1 falha** — `tests/test_navbar.py::test_mobile_sidebar_dark_mode_contrast` fixava o
literal `style.css?v=20260924` como guarda de cache-buster (feature 061, lição M-002) e
quebrou com o bump legítimo para `20261012`. Correção na causa (sem enfraquecer a guarda):
asserção generalizada para `style.css?v=\d{8}` com mensagem explicando o porquê — o teste
continua falhando se o carimbo **desaparecer**, mas deixa de quebrar em bumps de data.
`tests/test_navbar.py` → **5 passed**; régua completa → **1051 passed / 3 skipped**
(100,79s, exit=0).
