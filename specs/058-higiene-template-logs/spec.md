# Feature Specification: Higiene de template e de logs (M5 + M-N3)

**Feature Branch**: `058-higiene-template-logs`
**Created**: 2026-09-30
**Status**: Implemented

## Visão geral

Micro-feature de higiene derivada da análise profunda de 2026-09-30, corrigindo dois achados de baixo custo:

1. **M5** — atributo `style` quebrado no botão do menu do usuário (`base.html:271`): as aspas extras fecham o atributo cedo e `;border-color:rgba(255,255,255,.15);"` vira um atributo inválido (renderiza por tolerância do navegador, mas é marcação latente).
2. **M-N3** — ruído `ConnectionResetError [WinError 10054]` (e primos 10053/10038) poluindo o `app.error.log`: toda desconexão abrupta de cliente (celular dormindo, keep-alive cortado) vira traceback de ~15 linhas do logger `asyncio`, podendo esconder erros reais.

## Requisitos funcionais

- **FR-001**: o botão do menu do usuário em `base.html` deve ter o atributo `style` íntegro, com `color` e `border-color` dentro do MESMO atributo, e nenhum resquício de aspas órfãs.
- **FR-002**: registros do logger `asyncio` cujo contexto de exceção seja `ConnectionResetError`, `ConnectionAbortedError` ou `BrokenPipeError` devem ser suprimidos dos handlers de arquivo (app.log/app.error.log) e de console.
- **FR-003**: o filtro de ruído deve afetar APENAS o logger `asyncio` — qualquer erro de aplicação (services, uvicorn, sqlalchemy) segue íntegro, mesmo que seja desses tipos.
- **FR-004**: erros do logger `asyncio` que NÃO sejam desconexão benigna (ex.: `ValueError` em callback) continuam sendo logados.

## Critérios de aceitação

- **SC-001**: teste estrutural prova ausência do padrão quebrado e presença do `style` íntegro em `base.html`.
- **SC-002**: teste unitário do filtro: suprime `ConnectionResetError` do logger `asyncio`; passa `ValueError` do `asyncio`; passa `ConnectionResetError` de logger de aplicação.
- **SC-003**: régua completa permanece 100% verde (895 + novos).
