# Registro de Validação — Feature 058 (Higiene de template e logs)

**Data**: 2026-09-30 · **Feature**: M5 (style quebrado no menu do usuário) + M-N3 (ruído ConnectionResetError nos logs)
**Método**: TDD (8 testes escritos e vistos falhar antes da implementação — RED 8/8 comprovado) + régua completa + réguas de regressão.

## Alteração aplicada (diff confinado — 2 arquivos)

| Arquivo | Mudança |
|---|---|
| `app/web/templates/base.html` | Botão do menu do usuário: `border-color:rgba(255,255,255,.15);` movido para DENTRO do atributo `style` (aspas órfãs eliminadas) |
| `app/logging_config.py` | Novo `_AsyncioNoiseFilter` instalado no logger `asyncio` (idempotente, padrão da casa): suprime apenas desconexões benignas de cliente (`ConnectionResetError`/`ConnectionAbortedError`/`BrokenPipeError` — WinError 10054/10053/10038) |

## Validação (V1–V5)

| # | Critério | Resultado |
|---|---|---|
| V1 | RED comprovado (8/8 failed antes da implementação) | ✅ |
| V2 | SC-001: sem aspas órfãs; `style` íntegro com `color` + `border-color` no mesmo atributo | ✅ (2 testes) |
| V3 | SC-002: filtro suprime 10054/10053/BrokenPipe do `asyncio`; passa `ValueError` do asyncio; passa `ConnectionResetError` de logger de aplicação; passa registro sem exceção; instalação idempotente (1 filtro após 2 chamadas) | ✅ (6 testes) |
| V4 | SC-003: régua completa **903 passed / 0 failed** (61,9s) — 895 + 8 novos, zero regressões | ✅ |
| V5 | Smoke de template: os testes web da suíte renderizam `base.html` em dezenas de páginas autenticadas (todas 200 com asserts de conteúdo) | ✅ |

## Notas

- O filtro atua no **logger** (não no handler): cobre todos os handlers inclusive os do uvicorn, e afeta SOMENTE registros emitidos pelo logger `asyncio` (FR-003).
- O filtro entra em vigor no próximo restart do servidor (a config de logging é capturada no boot); a correção do template é imediata (Jinja2 recarrega).
- Erros reais de event loop (ex.: `ValueError` em callback) continuam logados (FR-004, testado).
