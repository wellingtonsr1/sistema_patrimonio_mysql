# Research: Exportação CSV de Locais (feature 008)

**Data**: 2026-09-16 · Todas as decisões verificadas no código real (somente leitura) antes do desenho.

## R1 — Onde nasce o CSV: **novo método no `ReportService` existente**

- **Decisão**: `ReportService.generate_locations_csv(db, locations=None) -> str`, irmão de `generate_custodians_csv` / `generate_movements_csv` / `generate_inventario_csv`.
- **Rationale**: o input proíbe criar nova forma de geração; todos os CSVs do sistema nascem aqui (`csv.writer` + `io.StringIO`, delimitador `;`, `QUOTE_MINIMAL`, cabeçalhos PT minúsculos). O parâmetro opcional `locations` replica a assinatura flexível dos irmãos (permite injeção em teste) com default que consulta **todos** os locais.
- **Alternativas rejeitadas**: gerar o CSV na rota (violaria II/III); novo serviço dedicado (`location_export_service.py` — fragmentaria o padrão de exportação em dois lugares); biblioteca de terceiros (desnecessária — stdlib basta e é o padrão vigente).

## R2 — Formato das linhas: **precedente estrito de `generate_custodians_csv`**

- **Decisão**: cabeçalho `nome;filial;departamento;predio;andar;sala;gestor`; campos opcionais com `or ""`; ordenação herdada de `LocationService.get_all` (`branch, department, name`).
- **Rationale**: decisão do responsável registrada na spec (sem "Ações", sem "Bens" — colunas de interface); o gêmeo de colaboradores usa exatamente esse desenho (colunas de dados do cadastro, contagens fora, `c.cpf or ""` para vazio). Prédio/Andar/Sala separados casam com o formato de importação de locais (`nome;filial;departamento;predio;andar;sala;gestor;descricao`), mantendo a simetria exportar↔importar que motivou o CSV de colaboradores.
- **Alternativas rejeitadas**: coluna combinada "Prédio/Andar/Sala" como na tela (quebraria a reimportabilidade); incluir a contagem de "Bens" (decisão explícita contrária do responsável); incluir `descricao` (não é coluna da tabela e o input limita às colunas de dados exibidas).

## R3 — Entrega: **download direto da listagem para endpoint CSV na API existente**

- **Decisão**: botão da tela linka direto a `GET /api/v1/reports/locations/csv`, novo endpoint em `reports_api.py` com `Response(media_type="text/csv; charset=utf-8-sig", headers={"Content-Disposition": "attachment; filename=locais.csv"})`.
- **Rationale**: os 3 botões existentes têm o mesmo markup e o de movimentações/dashboard linka a páginas HTML de relatório — mas o download direto de um `<a download href="/api/v1/reports/...">` já é o mecanismo real dentro das páginas de relatório (custodians_report.html L13). Criar página de relatório de locais violaria a proibição de nova tela. Nome `locais.csv` segue o padrão de `colaboradores.csv` (singular, minúsculo, sem acento).
- **Alternativas rejeitadas**: página intermediária `/reports/locations` (nova tela — proibida); endpoint fora de `reports_api.py` (fragmentaria os exports); `StreamingResponse` (sem precedente, desnecessário para o volume).

## R4 — Permissão: **`relatorios.exportar` (reuso), sem permissão nova**

- **Decisão**: endpoint com `dependencies=[Depends(require_permission("relatorios.exportar"))]`; botão com `{% if can('relatorios.exportar') %}`.
- **Rationale**: todos os endpoints CSV existentes usam exatamente esse gate (`export_inventory_csv`, `export_custodians_csv`, ata de inventário); os 3 botões usam o mesmo gate visual. Criar permissão tipo `locais.exportar` violaria o input ("alteração de permissões sem necessidade comprovada") e o Constitution VI (deny by default já satisfeito).
- **Alternativas rejeitadas**: nova permissão `locais.exportar` (necessidade não comprovada; ampliaria o RBAC sem demanda); gate duplo `locais.visualizar` + `relatorios.exportar` no endpoint (sem precedente — o endpoint de colaboradores também não exige `colaboradores.visualizar`).

## R5 — Filtro: **exporta todos os locais (precedente da tela gêmea)**

- **Decisão**: o endpoint não recebe `search` nem qualquer filtro; sempre exporta o conjunto completo.
- **Rationale**: o CSV de colaboradores (única exportação nascida de uma *listagem*, não de relatório) exporta todos via `get_all(db)`. O comportamento "filtrado + sufixo `_filtrado`" é exclusivo do relatório de inventário, que é página de relatório com 11 filtros próprios. Decisão registrada na spec (FR-006) e confirmada pelo responsável.
- **Alternativas rejeitadas**: replicar `search` no endpoint (criaria regra exclusiva para locais e complicaria o botão — o `<a>` não envia filtros da tela sem JS, que está fora de escopo).

## Verificações pontuais (fatos, não decisões)

| Fato | Evidência |
|---|---|
| 3 botões "Exportar CSV" com markup idêntico (`btn-ghost` + `bi-upload me-1`, gate `relatorios.exportar`) | `custodians/list.html` L13-15, `dashboard.html` L13-16, `movements/list.html` L13-15 |
| Geração CSV centralizada no `ReportService` (4 métodos `generate_*_csv`) | `app/services/report_service.py` L66/410/445/517 |
| Resposta padrão: `text/csv; charset=utf-8-sig` + `attachment` | `app/api/reports_api.py` L68-71/112/171-174/223-227 |
| Nome de arquivo real mais próximo: `colaboradores.csv` | `reports_api.py` L226 |
| Endpoint de colaboradores não recebe filtro; o de inventário recebe 11 filtros + `_filtrado` | `reports_api.py` L220-227 / L41-88 |
| Exportações existentes não são auditadas | `grep write_audit app/api/reports_api.py` → 0 |
| Router de reports já incluído no app (novo endpoint publicado sem tocar `main.py`) | `app/main.py` L49 (`api_v1_router`) |
| Fixtures de teste: `client` (admin), `unauth_client` (401), perfil sem `relatorios.exportar` provado no `test_rbac.py` L137-138 | `tests/conftest.py` L76-99, `tests/test_rbac.py` |
| Baseline da suíte: 264 passed / 1 failed (lockout defasado conhecido) | execução pytest na sessão da 007 |
