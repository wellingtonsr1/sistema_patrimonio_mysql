# Contract — Interface Web (rotas Jinja2) — estado atual

**Fidelidade**: espelho das rotas reais de `app/web/routes.py`, `app/web/admin_routes.py`,
`app/web/help_routes.py`. **Nenhum contrato novo; nenhum alterado.** Serve de referência
de não-regressão: toda rota futura deve seguir o padrão de auth/permissão aqui registrado.

## Convenções vigentes
- Autenticação web: `require_web_auth` → redirect `303 /login?next=<caminho>` quando
  não autenticado; caminhos públicos: `/login`, `/logout`, `/setup`.
- Autorização: `Depends(require_permission("modulo.acao"))` por rota; sem permissão →
  403 (página amigável `403.html`) + auditoria `ACESSO_NEGADO`.
- `can('modulo.acao')` nos templates controla apenas apresentação (menu/botões).
- Mensagens de feedback via redirect com `?error=` / `?search=`.
- CSRF: não identificado token CSRF no código analisado (registrado como observação na
  análise técnica; fora do escopo).

## Rotas públicas
| Método | Rota | Função |
|---|---|---|
| GET/POST | `/login` | Tela e submissão de login (local/AD, lockout 423 na API; mensagem na web) |
| POST | `/logout` | Revoga sessão no servidor e limpa cookie |
| GET/POST | `/setup` | Primeiro acesso (só instalação nova, idempotente via setup_claims) |
| GET | `/health` | Health check (em `app/main.py`) |
| GET | `/ajuda`, `/ajuda/{article_id}` | Central de ajuda (artigos admin exigem permissão) |

## Rotas de negócio (auth + permissão)
| Rota | Permissão |
|---|---|
| GET `/` (dashboard) | (autenticado) |
| GET `/assets` · `/assets/{id}` · `/assets/labels` | `patrimonio.visualizar` |
| GET/POST `/assets/new` · `/assets/import`(GET/POST/confirm) | `patrimonio.criar` |
| GET `/movements` · `/movements/{id}/term` | `movimentacao.visualizar` |
| GET/POST `/movements/new` | `movimentacao.criar` |
| GET `/custodians` · `/custodians/{id}` | `colaboradores.visualizar` |
| GET/POST `/custodians/new` · `/custodians/import`(3 rotas) | `colaboradores.criar` |
| GET/POST `/custodians/{id}/edit` | `colaboradores.editar` |
| GET `/locations` | `locais.visualizar` |
| GET/POST `/locations/new` · `/locations/import`(3 rotas) | `locais.criar` |
| GET `/maintenances` | `manutencao.visualizar` |
| GET/POST `/maintenances/new` | `manutencao.criar` |
| POST `/maintenances/{id}/complete` | `manutencao.finalizar` |
| GET `/reports/inventory` · `/reports/movements` · `/reports/custodians` | `relatorios.visualizar` |
| GET `/inventarios` · `/inventarios/{id}` | `inventario.visualizar` |
| GET/POST `/inventarios/new` | `inventario.criar` |
| POST `/inventarios/{id}/buscar` · `/iniciar` · `/conferir/{asset_id}`(GET) · `/conferir/{item_id}`(POST) · `/nao-previsto` | `inventario.conferir` |
| POST `/inventarios/{id}/encerrar` | `inventario.encerrar` |

## Rotas de administração
| Rota | Permissão |
|---|---|
| GET `/admin` | (autenticado) |
| GET `/admin/users` | `usuarios.visualizar` |
| GET/POST `/admin/users/new` | `usuarios.criar` |
| GET/POST `/admin/users/{id}/edit` · POST `/admin/users/{id}/reset-password` | `usuarios.editar` |
| POST `/admin/users/{id}/toggle-active` | `usuarios.bloquear` |
| GET `/admin/roles` | `perfis.visualizar` |
| GET/POST `/admin/roles/new` | `perfis.criar` |
| GET/POST `/admin/roles/{id}/edit` | `perfis.editar` |
| POST `/admin/roles/{id}/delete` | `perfis.excluir` (perfis de sistema não-excluíveis) |
| GET `/admin/audit` | `auditoria.visualizar` |
| GET `/admin/ad` · POST `/admin/ad/settings` · `/admin/ad/test` · `/admin/ad/mappings` · `/admin/ad/mappings/{id}/delete` | superusuário OU (`usuarios.editar` + `perfis.editar`) |
| GET/POST `/profile/password` | (autenticado; exige senha atual) |

## Regras de não-regressão da interface
1. Nenhuma rota existente pode perder sua permissão ou ficar pública.
2. Páginas 403/404 amigáveis mantidas (handler central).
3. Menu dinâmico via `can()` permanece apenas apresentacional.
4. Termo (`/movements/{id}/term`) e etiquetas (`/assets/labels`) permanecem imprimíveis
   com QR Code.
