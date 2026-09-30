# Plan — Feature 058 (higiene M5 + M-N3)

## Decisões

**D1 — Correção do M5 (1 linha)**: mover `border-color:rgba(255,255,255,.15);` para DENTRO do atributo `style` existente, eliminando as aspas órfãs. Resultado: `style="color:var(--color-primary);border-color:rgba(255,255,255,.15);"`. Sem mudança visual (o navegador já ignorava o atributo órfão; o `border-color` agora é de fato aplicado ao botão, o que é o comportamento pretendido original — borda sutil no dropdown).

**D2 — Filtro de ruído como `logging.Filter` no logger `asyncio`**: instalado em `configure_logging()` via `logging.getLogger("asyncio").addFilter(...)`. Um `Filter` num *logger* (e não num handler) roda para TODOS os handlers — inclusive os do uvicorn — e afeta apenas registros emitidos pelo logger `asyncio`, satisfazendo FR-002/FR-003 de uma vez.

**D3 — Escopo do filtro**: suprime apenas registros com `exc_info` cujo tipo seja `ConnectionResetError`/`ConnectionAbortedError`/`BrokenPipeError` (desconexões benignas de cliente). Qualquer outro erro do asyncio (ex.: `ValueError` em callback) passa íntegro (FR-004). Registro sem exceção não é afetado.

**D4 — Idempotência**: a instalação usa o mesmo padrão do arquivo (flag `_sispatrimonio_logging_configured` estendido) para não duplicar o filtro em chamadas repetidas de `configure_logging()` (testes chamam o módulo várias vezes).

## Alternativas rejeitadas

- *Filtrar no handler de arquivo apenas*: não cobriria o console e acoplaria o filtro a handlers específicos.
- *Elevar o logger `asyncio` a ERROR/crítico global*: esconderia erros reais do event loop (FR-004 violado).
- *Corrigir no nível do uvicorn (loop=asyncio, WindowsSelectorEventLoopPolicy)*: muda comportamento de I/O em produção; fora de escopo para higiene de log.
- *Silenciar `uvicorn.error`*: os tracebacks vêm do logger `asyncio`, não do uvicorn — alvo errado.

## Riscos

- **R1**: filtro suprimindo erro real de conexão que importe. Mitigado: escopo é apenas desconexão iniciada pelo cliente (10054/10053/10038 no Windows; primos POSIX mapeiam para as mesmas classes de exceção).
- **R2**: template renderiza diferente após a correção. Mitigado: SC-001 + suíte de templates (já existente) + smoke visual no servidor em execução.
