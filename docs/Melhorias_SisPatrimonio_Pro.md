# Melhorias do SisPatrimônio Pro (backlog)

Registro de problemas/melhorias identificados durante o desenvolvimento, pendentes
de especificação própria. Não constituem obrigações automáticas (Constitution v1.0.0,
seção "Restrições de Tecnologia e Dados"): cada item vira feature pelo fluxo Spec Kit.

---

## M-001 — Flakiness: `test_ata_csv_exibe_horario_local` (tests/test_datetime_flows.py)

**Status**: aberto (2026-09-24) · **Prioridade**: baixa (falha esporádica, sem impacto em produção)

### Sintoma observado

Na primeira execução da suíte completa após a implementação da feature 032
(2026-09-24 ~00:56 UTC ≈ 21:56 Recife), o teste falhou 1×:

```
FAILED tests/test_datetime_flows.py::TestUS4Exports::test_ata_csv_exibe_horario_local
1 failed, 678 passed
```

Nas re-execuções seguintes (isolada ×5, arquivo completo e suíte completa 2×),
o teste passou **sempre** — inclusive com o mesmo código (o stash/re-pop da 032
confirmou que a falha não depende das mudanças da 032).

### O que o teste faz

- Fixa `checked_at = 2026-09-15 22:30 UTC` (`FIXED_UTC`) e afirma que o CSV da ata
  exibe `19:30` (Recife) e **não contém** `22:30` (`tests/test_datetime_flows.py:292`).

### Causa provável (a confirmar na próxima ocorrência)

1. **Janela de carimbo real**: além do `checked_at` fixo, o CSV inclui
   `Criado em: format_local(inventario.created_at)` com `created_at = now_utc()` REAL.
   O assert negativo (`"22:30" not in body`) varre o CSV inteiro — se a suíte rodar
   exatamente quando o horário em Recife for **22:30** (janela de ~1 min/dia),
   o carimbo real contém "22:30" e o assert quebra.
2. **Não bate com o horário observado** (21:56 Recife na falha registrada) —
   hipóteses alternativas a investigar quando reproduzir com traceback completo:
   - contaminação de estado entre testes via `StaticPool` (SQLite em memória
     compartilhado) + `expire_all` do fixture;
   - variação de `tzdata` do SO na conversão `ZoneInfo` (descartado em verificação
     pontual: `22:30 UTC → 19:30 Recife` estável na máquina atual).

### Evidência de não-relação com a feature 032

- `git stash` (removendo todas as mudanças da 032) → teste passou isolado;
- suíte completa reexecutada 2× com a 032 aplicada → **680 passed** nas duas;
- nenhum arquivo tocado pela 032 interfere em `report_service`, `time_utils` ou
  no fluxo de exportação de atas.

### Ação recomendada (quando especificado)

Tornar o teste determinístico (feature pequena, mudança apenas de teste):

- capturar o traceback completo na próxima falha (rodar com `-x --tb=long`);
- isolar o carimbo real: `monkeypatch` em `now_utc`/`datetime` usado pelo
  `InventarioService` na criação, OU restringir o assert negativo às linhas do
  item conferido (em vez do corpo inteiro do CSV);
- alternativa mais simples: trocar o assert negativo para validar apenas a linha
  do item fixo (`pandas`/parse do CSV) — elimina a dependência do "agora".

**Regra vigente enquanto aberto**: a falha esporádica NÃO bloqueia entregas;
reexecutar a suíte para confirmar (o teste passa isolado e em re-execuções).
Registro aqui cumpre o Princípio I da Constitution (problemas encontrados no
caminho são registrados e tratados em tarefa própria).

---

## M-002 — Contraste ilegível da sidebar responsiva no modo escuro — **RESOLVIDO** (2026-09-24)

**Status**: resolvido · commit `d73bd03` · **Prioridade**: média (usabilidade do menu em mobile/tablet)

### Sintoma

No modo responsivo (< 1200px) com tema escuro, o menu lateral (`.mobile-sidebar`)
ficava com **fundo quase branco e texto branco** — texto ilegível (relato do
usuário: "os textos não dão pra ler; o painel lateral continua usando fundo claro
no modo escuro, mas os textos/ícones permanecem com cores claras").

### Causa raiz

```css
[data-theme="dark"] .mobile-sidebar { background: var(--dark-primary); }
/* --dark-primary: #fcf1f2  → quase BRANCO */

.mobile-sidebar .sidebar-nav-item { color: rgba(255,255,255,.85); }  /* texto branco herdado */
```

A variável `--dark-primary` não é uma cor de fundo escura: é a tonalidade
"primária" clara do tema escuro (#fcf1f2). Usá-la como fundo de um contêiner
que herda texto branco resultava em contraste de **1.11:1** (WCAG — falha
total; mínimo AA = 4.5:1).

### Correção aplicada (`app/web/static/css/style.css`)

- Fundo da sidebar dark → `var(--dark-surface)` (#211D1E) com borda coerente;
- Itens/seção/dividers/botão fechar/marca → cores de texto do tema escuro;
- Item ativo mantém destaque institucional (fundo `dark-primary-hover` + branco);
- Regras legadas que forçavam `rgba(255,255,255,*)` nos itens removidas;
- Cache-buster do CSS atualizado (`v=20260924`) para invalidar cache de navegador.

**Contraste após a correção**: `dark-surface` vs `dark-text` = **14.89:1** (AAA).

### Varredura da mesma classe de bug (todos os usos de `var(--dark-primary)`)

| Uso | Contraste | Veredito |
|---|---|---|
| L1107 — remapeamento `--c-primary-text` no dark | — | ✔ uso correto (texto claro sobre escuro) |
| L1201 — `btn-ghost:hover`: `dark-primary-light` + texto `dark-primary` | 13.45:1 | ✔ fundo escuro + texto claro |
| L1207 — timeline `::before` (gradiente decorativo) | — | ✔ decorativo, sem texto |
| L1255 — `dark-toggle`: `dark-primary-light` + ícone amarelo | — | ✔ |
| L1256 / L1377 — hover e item ativo: `dark-primary-hover` (#D14A5D) + branco | 4.33:1 | ⚠ AA-large — intencional (vermelho institucional, mesmo padrão do light) |

Varredura adicional do padrão inverso (fundo claro + texto branco forçado):
únicos `color: #fff` fora da navbar/sidebar estão em `.btn-primary` e no ícone
da marca — fundo **vermelho institucional** por design (`btn-primary` no dark:
3.50:1, AA-large, idêntico ao light — não é bug de tema). Nenhum template usa
`dark-primary` em estilo inline.

**Conclusão**: o bug era isolado à sidebar responsiva (única regra que usava a
variável primária clara como fundo de contêiner com texto branco herdado).
Regressão: teste `test_mobile_sidebar_dark_mode_contrast` (tests/test_navbar.py)
impede a regressão; suíte completa **682 passed**.

### Observação registrada (não-bug)

`btn-primary` no dark (3.50:1) fica abaixo de AA para texto normal (4.5:1).
É a identidade institucional vigente também no modo claro; se algum dia se
decidir por escurecer o vermelho dos botões no dark, fazer em feature própria
com varredura de impacto em todos os botões primários.
