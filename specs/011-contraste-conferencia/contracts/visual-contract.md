# Contract: Contraste das Opções de Resultado da Conferência (feature 011)

Contrato do único caminho afetado (apresentação). Tudo o que não está listado aqui permanece **byte-idêntico** ao comportamento atual.

## 1. CSS — `app/web/static/css/style.css`

| Aspecto | Contrato |
|---|---|
| Alteração | **Acréscimo** de 1 classe de componente (`.result-option`) na região de componentes do arquivo |
| Regra | `border: 1px solid var(--c-border) !important;` |
| Fonte da cor | Token existente `--c-border` — claro: `#C8C2C0`; escuro: `#3A3335` (mapeamento já existente; **nenhuma variável nova**) |
| `!important` | Necessário para vencer a utilitária `.border` do Bootstrap (que também é `!important`); escopo restrito à classe nova |
| Proibições | NÃO modificar `.border`, `--bs-border-color` nem qualquer outra regra global; NÃO criar arquitetura de temas nova |

## 2. Templates — `inventarios/conferir.html` e `inventarios/detail.html`

| Aspecto | Contrato |
|---|---|
| Alteração | Acréscimo da classe `result-option` ao atributo `class` dos 4 `<label>` de resultado em **cada** template (8 elementos no total) |
| Markup resultante | `class="d-block border rounded p-2 result-option"` |
| Intocado | Estrutura, ordem, textos, emojis, `name="result"`, valores (`ENCONTRADO`, `LOCAL_DIFERENTE`, `NAO_ENCONTRADO`, `SEM_IDENTIFICACAO`), `style="cursor:pointer;"`, demais atributos |

## 3. Teste — guarda de renderização (novo arquivo em `tests/`)

| Aspecto | Contrato |
|---|---|
| Cobertura | Página de conferência renderiza as 4 opções com `result-option` e os 4 valores; **e** o modal de `detail.html` (prova simétrica do FR-008 — obrigatório no mesmo arquivo de teste) |
| Sem asserção de cor | Contraste é validado visualmente (quickstart §3) — a suíte não tem navegador |
| Padrão | Fixtures `client`/`db_session` existentes; sem infraestrutura nova |

## 4. Contratos de não-regressão (garantias explícitas)

1. **Nenhum arquivo Python é alterado** — rotas, services, models, schemas intocados.
2. **Nenhum componente fora das 8 opções muda de aparência** — `.border`, `--bs-border-color` e todas as regras globais permanecem idênticos (US3/SC-004).
3. **Estados preservados**: seleção (rádio Bootstrap), foco (outline nativo) e hover (cursor pointer inline) sem nenhuma regra nova que os afete (FR-005/FR-011).
4. **Comportamento funcional idêntico**: registro de conferência grava os mesmos valores pelos mesmos services (SC-005/Constitution V).
5. **Zero DDL / zero migração / zero rota nova / zero permissão nova** (Constitution VI/VII).
6. **Suíte pytest** permanece verde no patamar baseline + teste novo (Constitution VIII).
7. **Documentação** não muda (R5 — nenhum comportamento documentado alterado; Constitution XI atendida pela invariância).
