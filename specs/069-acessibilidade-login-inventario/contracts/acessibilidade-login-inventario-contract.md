# Contract — Acessibilidade dos fluxos de Login e Inventário (069)

> Contrato de **apresentação semântica** (DOM dos templates). Nenhuma rota, método ou parâmetro novo: só atributos HTML e associação de labels nos templates existentes. Valido por renderização server-side — a suíte atual não executa JavaScript (R5 do research).

## 1. Escopo de páginas

| Página | Rota (existente) | Permissão (inalterada) |
|---|---|---|
| `login.html` | `GET /login` | pública |
| `setup.html` | `GET /setup` | pública (só sem usuário criado) |
| `inventarios/list.html` | `GET /inventarios` | `inventario.visualizar` |
| `inventarios/new.html` | `GET /inventarios/new` | `inventario.criar` |
| `inventarios/detail.html` | `GET /inventarios/{id}` | `inventario.visualizar` |
| `inventarios/conferir.html` | `GET /inventarios/{id}/conferir/{item_id}` | `inventario.conferir` |
| `inventarios/offline.html` | `GET /inventarios/{id}/offline` | `inventario.conferir` |

## 2. Regras de nomenclatura acessível (estado final)

**RN-1 — Todo controle de formulário tem nome acessível.** Para cada `input`/`select`/`textarea` visível, ao menos um de:
`<label for>` correspondente · `<label>` ancestral (implícito) · `aria-label` · `aria-labelledby`.
Placeholder **nunca** é o único nome.

**RN-2 — Labels visíveis existentes ganham `for`/`id`** — nunca são substituídos por `aria-label` (preserva o texto aprovado; exceção: nenhum nos fluxos-alvo).

**RN-3 — Controles compactos sem espaço para label** (buscas, filtros, tombamento): `aria-label` direto, sem label visual novo (layout intocado — I1 do data-model).

**RN-4 — Todo botão só-ícone tem `aria-label`** (`togglePassword`/`toggleConfirmPassword`, botão `bi-funnel` de `detail.html`, link limpar-filtros de `list.html`). Botões toggle recebem também `aria-pressed` sincronizado com o ícone. Botões com texto visível ("Filtrar", "Localizar", "Exportar") **não são só-ícone** — sem intervenção.

**RN-5 — Grupo de rádios "Resultado da conferência"** em `fieldset`+`legend` nos 3 templates (conferir/detail modal/offline); `fieldset` com reset visual inline (`border:0;padding:0;margin:0`) — zero mudança de layout.

**RN-6 — Mensagens de erro server-side mantêm `role="alert"`** (login/setup já têm; o único alerta de erro sem o atributo nos fluxos-alvo é o de `conferir.html`). **Sem `aria-live`** — nenhuma mensagem dos fluxos web é atualizada dinamicamente via JS (R3). Contadores dinâmicos da página **offline** recebem `role="status"` (rev. 2); se entrar AJAX na conferência web no futuro, `aria-live="polite"` é requisito novo.

**RN-7 — IDs únicos por página**: em `detail.html` (modal repetido por item), todo `id` novo leva sufixo `{{ item.id }}`.

**RN-8 — Nada muda de comportamento**: mesmas `action`/`method`/`name`; `autofocus` preservado onde existe (login username, tombamento) e não replicado onde não existe; tab order natural do DOM preservado (nada de `tabindex` positivo).

## 3. Contexto de validação (suíte estática)

`tests/test_acessibilidade_estatica_069.py` — parser `html.parser` (stdlib) sobre o HTML servido:

| Verificação | Aplicada a | Critério |
|---|---|---|
| controles sem nome acessível | todas as 7 páginas | **0 ocorrências** |
| botões só-ícone sem `aria-label`/texto | idem | **0 ocorrências** |
| grupo de rádios sem `fieldset` | conferir/detail/offline | presente |
| `role="alert"` nos alertas de erro | login/conferir (erro vindo da submissão)/offline | presente |
| `id` duplicados | todas | **0 ocorrências** |
| campos com `name=` preservados | todas | lista de `name` == lista de hoje |

## 4. Casos de borda

| Caso | Resultado |
|---|---|
| erro de login (`?error=`) | alerta anunciado por `role="alert"` (já existente) |
| modal de conferência por item em `detail.html` | labels/fieldset com IDs únicos por item (RN-7) |
| inventário ENCERRADO | formulários não renderizam — verificações estáticas do fluxo só avaliam HTML presente; página deve continuar servindo `200` sem violação nas partes visíveis |
| tema escuro | atributos ARIA são tema-independentes — nenhuma alteração de cor é introduzida |
| offline/PWA (`offline.html`) | markup próprio (não usa `base.html`); mesmas regras RN-1..RN-6 |

## 5. O que NÃO muda

- Nenhum caminho de rota, método HTTP ou parâmetro novo (`route_manifest.json` intacto).
- Permissões, autenticação, sessão, validações e handlers (`action`/`name`) idênticos.
- Layout, cores, espaçamento, grid responsivo — nenhuma regra CSS alterada (reset do `fieldset` é inline e local).
- Nenhuma dependência nova (`requirements.txt` intocado); nenhum asset/JS novo.
- Nenhuma alteração em `app/models/`, `app/schemas/`, `migrations/`.
