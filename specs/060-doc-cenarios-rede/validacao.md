# Registro de Validação — Feature 060 (Documentação de cenários de rede)

**Data**: 2026-09-30 · **Feature**: dica do localhost na página offline + artigo "Internet × rede local × servidor" na Central de Ajuda
**Origem**: confusão real do usuário (desligou a rede da máquina servidora e concluiu que o sistema "não funciona sem internet")
**Método**: TDD (4 testes; RED 3 failed comprovado antes) + prova do arquivo servido pelo servidor em execução + régua completa.

## Alteração aplicada

| Arquivo | Mudança |
|---|---|
| `app/web/static/offline-start.html` | Nova dica: "Está no próprio servidor? O sistema continua acessível em `https://localhost:8000` — mesmo com a rede desconectada (o sistema não depende de internet; esta tela indica ausência do *servidor*, não da internet)" |
| `app/web/static/js/sw.js` | `CACHE_VERSION` → **v34** (propaga a dica nova nos aparelhos que precachearam o fallback em v33) |
| `app/services/help_article_rede.py` (novo) | Artigo `internet-rede-servidor` (módulo Primeiros Passos, audiência user): as 3 redes, os 3 cenários de queda, acesso por localhost na máquina do servidor, e o fluxo da coleta offline em 3 passos |
| `app/services/help_service.py` | Import do artigo + listagem na categoria **Primeiros Passos** (primeiro item) + entra no índice de pesquisa |
| `tests/test_doc_rede_060.py` (novo) | 4 testes estruturais |
| `tests/test_vendoring_059.py` / `test_sw_service_worker.py` | Guardas de CACHE_VERSION evoluídos para "mínimo" (>= v33; aceita v34) em vez de valor fixo — bumps futuros deixam de quebrar guardas antigos |

## Validação (V1–V5)

| # | Critério | Prova | Resultado |
|---|---|---|---|
| V1 | **SC-001** — dica no fallback | teste estrutural (4/4 passed) + `curl` no servidor em execução: o HTML servido **contém** `localhost:8000` com o texto completo (prova com `cache: 'reload'` no navegador: trecho exato capturado) | ✅ |
| V2 | **SC-002** — artigo no service | `get_article('internet-rede-servidor')` OK (32 artigos); listado em `primeiros-passos` (primeiro da categoria); no índice de pesquisa com keywords internet/offline/rede/servidor/localhost | ✅ |
| V3 | **SC-003** — régua sem regressão | **923 passed / 1 skipped (condicional MariaDB, por design) / 0 failed** (62,7s) — inclui o 4º teste da 060 (categoria) e guardas de bump evoluídos | ✅ |
| V4 | Higiene | usuário temporário do smoke (`doc060_5910`) desativado | ✅ |
| V5 | Nota de operação | o 404 observado no smoke do artigo era o **processo iniciado às 11:32** rodando código anterior à 060 (Python não recarrega módulos com `reload=False`); o restart seguinte do `run.py` passa a servir o artigo — coberto pelo teste estrutural V2 que valida o código, não o processo | ✅ (observado e explicado) |

## Nota operacional

Para ver o artigo em `/ajuda/internet-rede-servidor` e a dica renderizada na página offline, basta o próximo restart do servidor (o `run.py` habitual) — o conteúdo já está no código provado pelos testes.
