# Contract — API REST `/api/v1` — estado atual

**Fidelidade**: espelho dos endpoints reais de `app/api/*.py` (agregados por
`v1_router.py`, prefixo `/api/v1`). Nenhum endpoint novo; nenhum alterado.

## Autenticação da API
- Sessão por cookie (mesma da web). Sem sessão → `401` em **todas** as rotas de
  negócio (inclusive GET e exportações — decisão documentada no README: dados sensíveis).
- `403` autenticado sem permissão (auditado) · `404` não encontrado · `423` conta
  bloqueada · `503` AD indisponível.

## Endpoints

### Auth (`auth_api.py`) — públicos (são o ponto de autenticação)
| Método | Rota | Notas |
|---|---|---|
| POST | `/api/v1/auth/login` | form username/password; cria sessão; 423 em lockout |
| POST | `/api/v1/auth/logout` | revoga sessão |
| GET | `/api/v1/auth/me` | 401 sem sessão; retorna usuário + permissões |

### Assets (`assets_api.py`)
| Método | Rota | Permissão |
|---|---|---|
| GET | `/api/v1/assets` | `patrimonio.visualizar` |
| GET | `/api/v1/assets/{id}` · `/tag/{tag}` · `/{id}/timeline` · `/{id}/depreciation` | `patrimonio.visualizar` |
| POST | `/api/v1/assets` · `/api/v1/assets/import/csv` | `patrimonio.criar` |
| PUT | `/api/v1/assets/{id}` | `patrimonio.editar` |

### Movements (`movements_api.py`)
| Método | Rota | Permissão |
|---|---|---|
| GET | `/api/v1/movements` · `/{id}` · `/{id}/term` | `movimentacao.visualizar` |
| POST | `/api/v1/movements` | `movimentacao.criar` |

### Custodians (`custodians_api.py`)
| Método | Rota | Permissão |
|---|---|---|
| GET | `/api/v1/custodians` · `/{id}` · `/{id}/assets` | `colaboradores.visualizar` |
| POST | `/api/v1/custodians` · `/api/v1/custodians/import/csv` | `colaboradores.criar` |
| PUT | `/api/v1/custodians/{id}` | `colaboradores.editar` |

### Locations (`locations_api.py`)
| Método | Rota | Permissão |
|---|---|---|
| GET | `/api/v1/locations` · `/{id}` | `locais.visualizar` |
| POST | `/api/v1/locations` | `locais.criar` |
| PUT | `/api/v1/locations/{id}` | `locais.editar` |

### Reports (`reports_api.py`)
| Método | Rota | Permissão |
|---|---|---|
| GET | `/api/v1/reports/dashboard-stats` | `relatorios.visualizar` |
| GET | `/api/v1/reports/inventory/{csv,excel,pdf}` | `relatorios.exportar` |
| GET | `/api/v1/reports/movements/csv` · `/api/v1/reports/custodians/csv` | `relatorios.exportar` |
| GET | `/api/v1/reports/inventarios/{id}/{csv,excel,pdf}` | `inventario.visualizar` **+** `relatorios.exportar` |

## Formatos de exportação (estáveis)
- CSV: UTF-8 **com BOM** (abre direto no Excel).
- Excel: `.xlsx` via OpenPyXL. PDF: ReportLab (inclui ata de inventário).

## Regras de não-regressão da API
1. Nenhum endpoint pode ficar público ou perder a permissão atual.
2. Corpos de erro seguem o padrão atual (`detail` com mensagem em português).
3. Schemas Pydantic existentes (`app/schemas/`) definem os contratos de entrada/saída
   (Asset/Movement/Custodian/Location/Maintenance — Create/Update/Read).
4. Swagger (`/docs`) permanece público com "Try it out" exigindo sessão.
