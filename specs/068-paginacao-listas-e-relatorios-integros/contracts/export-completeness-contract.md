# Contract — Integridade das exportações (CSV / Excel / PDF) e aviso de corte

> Garantia central: **nenhum arquivo sai truncado sem aviso**. Fonte: `ReportService` + `app/api/reports_api.py` (+ ata de inventário).

## 1. Endpoints (inalterados em rota, permissão, formato e nome)

| Endpoint | Permissão | Formato |
|---|---|---|
| `GET /api/v1/reports/inventory/csv` | `relatorios.exportar` | `text/csv; charset=utf-8-sig` |
| `GET /api/v1/reports/inventory/excel` | `relatorios.exportar` | XLSX (OpenPyXL) |
| `GET /api/v1/reports/inventory/pdf` | `relatorios.exportar` | PDF (ReportLab) |
| `GET /api/v1/reports/movements/csv` · `/custodians/csv` · `/locations/csv` | `relatorios.exportar` | CSV UTF-8 BOM |
| `GET /api/v1/reports/inventarios/{id}/{csv,excel,pdf}` | `inventario.visualizar` **+** `relatorios.exportar` | ata de conferência |

Parâmetros de filtro: **os mesmos** (nenhum novo). A exportação **não** recebe `page`: ela sempre exporta o **conjunto completo filtrado** (FR-009).

## 2. Regras de completude

1. **Sem teto de 10.000**: `ReportService.get_filtered_assets` deixa de aplicar `limit 10000`; todos os registros do filtro entram no arquivo (FR-010).
2. **Varredura em lotes**: iteração por `offset/limit` de 1.000 linhas por passo (mesma query do filtro + `count()` único para o total).
3. **CSV**: gerado em *streaming* (`StreamingResponse`), memória constante.
4. **XLSX**: gerado em modo *write-only* do OpenPyXL (3.1.5 já instalado).
5. **PDF**: gerado sem teto; se `total > 10.000`, a **tela** exibe aviso prévio ("a geração pode demorar") antes do download.

## 3. Aviso de corte residual (FR-013) — obrigatório quando existir

Se por motivo técnico algum corte residual persistir (inclusive em PDF):

| Onde | Conteúdo exigido |
|---|---|
| **Tela** | alerta visível `Exibindo X de Y registros — refine os filtros ou use exportação completa` |
| **CSV** | primeira linha de dados/comentário do cabeçalho com a mesma contagem |
| **XLSX** | célula de aviso no topo da planilha |
| **PDF** | nota em rodapé/página inicial com a mesma contagem |

Nunca: arquivo truncado entregue como completo, nem download silencioso interrompido.

## 4. O que é preservado byte a byte

- Delimitador `;`, encoding `UTF-8` com BOM, cabeçalhos e ordem das colunas.
- Nome de arquivo (`inventario_patrimonio[.filtrado].csv`, ata `...`) e `Content-Disposition`.
- Status HTTP (`200`) e ausência de redirecionamento.
- Bloco de comprovação da ata (código, escopo, status, criado por, carimbo de horário local).
- Conteúdo lido (snapshots × leitura viva) — **P5 da 067 intocada**.

## 5. Casos de borda

| Caso | Comportamento |
|---|---|
| Filtro sem resultados | arquivo com cabeçalho e zero linhas, `200` |
| Base > 10.000 (CSV/XLSX) | arquivo completo (ex.: 12.000 linhas), sem aviso (não houve corte) |
| Base > 10.000 (PDF) | aviso prévio na tela; se houver corte residual, aviso dentro do arquivo |
| Usuário sem `relatorios.exportar` | `403` + registro na trilha (inalterado) |
| Interrupção do download em streaming | resposta parcial no cliente; **nenhuma escrita** no sistema (leitura pura) |
| Exportação durante modo de manutenção (restore) | comportamento atual do middleware de manutenção (inalterado) |

## 6. O que NÃO muda

- Rotas, permissões, schemas de resposta, conteúdo lido dos dados.
- Exportações fora de `ReportService` (etiquetas, ata já existente com formato próprio) — fora do escopo.
- Contrato dos testes existentes: `generate_inventory_csv/excel/pdf` continuam existindo com as assinaturas atuais (internamente passam a consumir o gerador em lotes).
