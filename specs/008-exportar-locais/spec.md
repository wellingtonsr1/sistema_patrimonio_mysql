# Feature Specification: Exportação CSV de Locais

**Feature Branch**: `008-exportar-locais`
**Status**: Draft
**Input**: Adicionar botão **"Exportar CSV"** na tela existente de Locais, exportando os locais cadastrados em CSV, seguindo exatamente o padrão de exportação já existente no sistema.

## 1. Contexto do Sistema Existente (análise verificada no código — Regra de Análise)

Análise de somente leitura realizada antes da especificação. **Nenhum arquivo da aplicação foi alterado.**

| Pergunta do input | Fato real verificado no código |
|---|---|
| 1. Onde está a tela de Locais | `app/web/templates/locations/list.html`; rota `GET /locations` → `list_locations_view` (`app/web/routes.py` ~L1162), gate `locais.visualizar`; dados via `LocationService.get_all` (+ pesquisa `search` da feature 007); ordenação `branch, department, name` |
| 2. Botões "Exportar" existentes | **3, com markup idêntico**: `custodians/list.html` L13-15, `dashboard.html` L13-16, `movements/list.html` L13-15 — todos `<a class="btn btn-ghost"><i class="bi bi-upload me-1"></i> Exportar CSV</a>`, visíveis somente com `can('relatorios.exportar')`, posicionados no `page-header` da tela |
| 3. Como os botões são implementados | O de colaboradores leva à página de relatório `/reports/custodians` (gate `relatorios.visualizar`), que contém o link de **download direto** `<a class="btn btn-success" download href="/api/v1/reports/custodians/csv">`; dashboard → `/reports/inventory`; movements → `/reports/movements` |
| 4. Como o sistema gera CSV | `app/services/report_service.py` — métodos `generate_*_csv` (`generate_inventory_csv`, `generate_custodians_csv`, `generate_movements_csv`, `generate_inventario_csv`): `csv.writer` sobre `io.StringIO`, **delimitador `;`**, `csv.QUOTE_MINIMAL`, **cabeçalhos em português minúsculo** (ex.: `matricula;nome;email;cargo;setor;cpf;ativo` — o CSV de colaboradores é "formato compatível com a importação") |
| 5. Resposta HTTP da exportação | `app/api/reports_api.py`: `media_type="text/csv; charset=utf-8-sig"` (BOM para Excel) + `Content-Disposition: attachment; filename=...`; nomes reais: `colaboradores.csv`, `inventario_patrimonio[_filtrado].csv`, `ata_{codigo}.csv` |
| 6. Permissões das exportações | Endpoints CSV exigem `relatorios.exportar` (`require_permission`); botões nas telas exigem `can('relatorios.exportar')` — o usuário precisa também poder ver a tela (`locais.visualizar` para Locais) |
| 7. Comportamento de filtro nas exportações | **Dois precedentes**: (a) CSV de inventário — **exporta o resultado filtrado** e acrescenta sufixo `_filtrado` ao arquivo quando há filtros; (b) CSV de colaboradores — **exporta todos** (`get_all(db)`, sem filtro, na tela gêmea desta feature). Não existe exportação de locais hoje |
| 8. Formato de importação de locais | `location_import_service.py`: colunas `nome;filial;departamento;predio;andar;sala;gestor;descricao` (obrigatórias: nome, filial, departamento) — mesmo desenho "CSV de exportação compatível com importação" adotado para colaboradores |
| 9. Colunas da tabela de Locais | Nome / Identificação, Filial, Departamento, Prédio / Andar / Sala, Gestor, Bens (contagem calculada via `LocationService.count_assets`), Ações — **"Bens" (contagem) e "Ações" são elementos de interface, não dados cadastrais** (o CSV de colaboradores, gêmeo, não exporta contagens) |

## 2. User Scenarios & Testing

### User Story 1 - Exportar os locais em CSV a partir da tela (Priority: P1) 🎯 MVP

Um usuário que precisa compartilhar ou arquivar a lista de locais (ex.: para auditoria, para carga em outra ferramenta, para reimportação) clica em "Exportar CSV" na tela de Locais e baixa o arquivo, sem copiar/colar a tabela.

**Why**: Hoje não há caminho de saída dos dados de locais; a importação CSV existe (`/locations/import`), mas a exportação não — o fluxo é assimétrico.

**Independent Test**: Autenticado com as permissões corretas, acessar `/locations`, clicar no botão "Exportar CSV" e receber um download de arquivo `.csv` contendo todos os locais.

**Acceptance Scenarios**:

1. **Given** usuário com `locais.visualizar` e `relatorios.exportar`, **When** acessa a tela de Locais, **Then** o botão **"Exportar CSV"** está visível no cabeçalho da tela, com o mesmo ícone, estilo, tamanho e posicionamento dos botões de exportação existentes (bens/colaboradores/movimentações).
2. **Given** o usuário clica no botão, **When** a requisição é processada, **Then** o navegador recebe um download de arquivo com extensão **`.csv`**, seguindo o padrão de nome de arquivo das exportações existentes.
3. **Given** o download é aberto, **When** o arquivo é inspecionado, **Then** ele contém todos os locais cadastrados (não apenas os de um filtro ativo na tela).
4. **Given** a exportação foi concluída, **When** o usuário continua usando a tela de Locais, **Then** pesquisa, tabela, links e ações funcionam normalmente.

### User Story 2 - Conteúdo fiel e no padrão do sistema (Priority: P2)

O CSV gerado deve seguir exatamente o padrão das exportações existentes: separador, quoting, cabeçalhos, codificação e nome de arquivo — e conter os dados patrimoniais das colunas da tabela, sem a coluna de interface.

**Why**: Arquivos que não seguem o padrão quebram a abertura no Excel (sem BOM) e a reimportação (colunas incompatíveis), criando retrabalho.

**Independent Test**: Inspecionar o arquivo baixado: cabeçalho correto, uma linha por local, colunas de dados presentes, colunas de interface ausentes ("Ações" e "Bens"), codificação e delimitador idênticos aos das exportações existentes.

**Acceptance Scenarios**:

1. **Given** o arquivo gerado, **When** a primeira linha é lida, **Then** o cabeçalho segue o padrão do sistema (rótulos em português, minúsculos, separados por `;`), cobrindo Nome / Identificação, Filial, Departamento, Prédio, Andar, Sala e Gestor — **sem colunas de interface** (sem "Ações", sem "Bens").
2. **Given** locais com valores contendo `;`, vírgulas, acentos ou quebra de linha na descrição, **When** o CSV é gerado, **Then** os valores são adequadamente escapados pelo mecanismo padrão (o arquivo abre corretamente no Excel com a codificação padrão do sistema — UTF-8 com BOM).
3. **Given** o arquivo gerado, **When** as colunas são inspecionadas, **Then** nenhuma coluna de interface aparece: sem "Ações" e sem a contagem de "Bens" (precedente estrito do CSV de colaboradores).
4. **Given** o conjunto de locais, **When** o CSV é gerado, **Then** a ordenação das linhas é a mesma da listagem (filial, departamento, nome).

### User Story 3 - Proteção e preservação (Priority: P3)

A exportação é uma operação de consulta protegida: só acessível a quem pode exportar relatórios, sem alterar qualquer dado, e sem afetar nada do que já existe na tela.

**Why**: O endpoint de exportação expõe dados patrimoniais e não pode abrir brecha fora do RBAC; a tela de Locais acabou de receber a pesquisa (feature 007) e não pode regredir.

**Independent Test**: Sem a permissão de exportação, o botão não aparece e o endpoint nega; com ela, a exportação não muta dados; a tela permanece idêntica com o botão como única adição.

**Acceptance Scenarios**:

1. **Given** usuário autenticado **sem** `relatorios.exportar`, **When** acessa a tela de Locais, **Then** o botão "Exportar CSV" **não** é renderizado (mesmo comportamento dos demais botões de exportação), e uma chamada direta ao endpoint de exportação é negada pelo mecanismo existente (403).
2. **Given** qualquer exportação executada, **When** o banco é inspecionado, **Then** nenhum local foi criado, alterado ou excluído (operação read-only).
3. **Given** a tela de Locais após a feature, **When** comparada à anterior, **Then** a única diferença é o botão no cabeçalho: pesquisa (007), tabela, colunas, contagem de bens e ações permanecem idênticos.

## Edge Cases

- **Nenhum local cadastrado** → o download é entregue contendo apenas a linha de cabeçalho (padrão CSV; sem erro na aplicação).
- **Nome de local contendo `;` ou aspas** → escapamento padrão do `csv.writer` (mesmo mecanismo das exportações existentes); a página não falha.
- **Valores vazios** (prédio/andar/sala/gestor não preenchidos) → campos em branco na linha (padrão do CSV de colaboradores: `c.cpf or ""`).
- **Usuário com `locais.visualizar` mas sem `relatorios.exportar`** → botão oculto + endpoint negado (403) — sem acesso indevido aos dados de exportação.
- **Filtro de pesquisa ativo na tela** (ex.: `?search=IPMJP` da feature 007) → a exportação **não** é afetada: segue exportando conforme a decisão de filtro (ver FR-006), como nas demais exportações do sistema.
- **Chamada direta ao endpoint sem autenticação** → bloqueio pelo mecanismo existente de autenticação da API (padrão de todos os endpoints `/api/v1/reports/*`).

## Requirements

### Functional Requirements

- **FR-001**: A tela de Locais deve apresentar um botão com o texto exato **"Exportar CSV"**, com o mesmo markup, ícone, classe, tamanho, espaçamento e posicionamento do padrão existente (`<a class="btn btn-ghost"><i class="bi bi-upload me-1"></i> Exportar CSV</a>` no `page-header`), exibido somente para usuários com a permissão de exportação já usada pelos demais botões (`relatorios.exportar`).
- **FR-002**: A exportação deve ser entregue como **download direto** de arquivo **CSV (`.csv`)** a partir de um endpoint no padrão dos endpoints existentes de exportação (`/api/v1/reports/.../csv`), **sem criar nova tela HTML** (restrição do input; precedente interno de download direto já usado nas páginas de relatório).
- **FR-003**: A geração do CSV deve reutilizar o mecanismo existente (`ReportService`, no padrão dos métodos `generate_*_csv`): `csv.writer`, delimitador `;`, quoting mínimo, cabeçalhos em português minúsculo — **sem criar nova forma de geração de CSV**.
- **FR-004**: O arquivo deve conter os **dados das colunas de dados da tabela de Locais**: Nome / Identificação, Filial, Departamento, Prédio, Andar, Sala e Gestor, uma linha por local. **Colunas de interface não devem ser exportadas**: nem "Ações", nem a contagem de "Bens" — precedente estrito do CSV de colaboradores (a tela gêmea), que não inclui contagens. Prédio/Andar/Sala são exportados como campos separados (mesmo desenho do formato de importação de locais), não como a coluna combinada de exibição.
- **FR-005**: A resposta HTTP deve seguir o padrão existente: `media_type` CSV com **UTF-8 BOM** (`text/csv; charset=utf-8-sig`) e `Content-Disposition: attachment`, com nome de arquivo no padrão das exportações existentes (`locais.csv`, análogo a `colaboradores.csv`).
- **FR-006**: A exportação deve conter **todos os locais**, independentemente do filtro de pesquisa ativo na tela. **Decisão por precedente** (o input manda seguir o padrão das demais exportações e não criar regra exclusiva): a tela gêmea (colaboradores — mesma estrutura de listagem com pesquisa e botão "Exportar CSV") exporta **todos** via seu endpoint; o comportamento de "exportar filtrado + sufixo `_filtrado`" é exclusivo do relatório de inventário, que é uma página de relatório com filtros próprios, não uma listagem.
- **FR-007**: O endpoint de exportação deve exigir a permissão **`relatorios.exportar`** (padrão dos endpoints CSV existentes), além da autenticação já aplicada a toda a API — nenhuma permissão nova é criada, e nenhum usuário sem essa permissão obtém acesso à exportação.
- **FR-008**: A exportação é **exclusivamente read-only**: não cria, altera ou exclui locais, bens ou qualquer outro registro.
- **FR-009**: A tela de Locais deve permanecer funcionalmente intacta — pesquisa (007), tabela, colunas, contagem de bens, links e ações inalterados; o botão é uma adição isolada no cabeçalho, no mesmo ponto onde as demais telas posicionam seus botões de exportação.
- **FR-010**: Devem existir testes automatizados cobrindo, no mínimo: botão visível com a permissão e oculto sem ela; download com content-type, disposition e nome de arquivo no padrão; cabeçalho do CSV correto; uma linha por local com os dados esperados; ausência das colunas de interface ("Ações" e "Bens"); exportação contendo todos os locais (inclusive com filtro de pesquisa ativo na chamada da tela); negação do endpoint sem `relatorios.exportar`; read-only; e tela de Locais funcionando após a exportação.

### Success Criteria

- **SC-001**: 100% dos usuários com `relatorios.exportar` conseguem baixar o CSV em um clique a partir da tela de Locais.
- **SC-002**: O arquivo abre corretamente no Excel com a codificação padrão do sistema (UTF-8 BOM), com separador `;`, em 100% dos casos testados.
- **SC-003**: O CSV contém 100% dos locais cadastrados e nenhuma coluna de interface ("Ações" e "Bens").
- **SC-004**: 100% das tentativas de usuários sem `relatorios.exportar` são negadas (botão ausente + endpoint 403).
- **SC-005**: Zero alterações de dados resultantes da exportação (verificável por contagem/snapshot antes e depois).
- **SC-006**: Suíte de testes existente permanece verde; a tela de Locais não apresenta nenhuma regressão.

## Key Entities

- **Location** (somente leitura): todos os atributos exportados já existem — `name` ("Nome / Identificação"), `branch`, `department`, `building`, `floor`, `room`, `manager_name`; a contagem de bens é derivada (`count_assets`), não armazenada. Nenhuma entidade, tabela ou coluna nova.

## Assumptions

1. **Download direto, sem página de relatório intermediária**: o botão da tela linka ao endpoint CSV (padrão de download já usado dentro das páginas de relatório). O caminho de duas etapas dos colaboradores (tela → página de relatório → download) exigiria criar uma nova tela HTML, que o input proíbe explicitamente ("Não criar nova tela"). Desvio mínimo, documentado, que preserva o markup e o gate do botão.
2. **Colunas do CSV**: seguem o **precedente estrito do CSV de colaboradores (gêmeo)** — dados das colunas da tabela **sem colunas de interface** ("Ações" e contagem de "Bens" ausentes); decisão confirmada pelo responsável nesta revisão. Prédio/Andar/Sala permanecem campos separados, no mesmo desenho do formato de importação de locais.
3. **Filtro**: exporta todos (precedente do CSV de colaboradores); a exportação filtrada com `_filtrado` é padrão do relatório de inventário, não das listagens.
4. **Ordenação das linhas**: a mesma da listagem (filial, departamento, nome) — coerente com "dados correspondentes à tabela".
5. **Codificação/delimitador/nome de arquivo**: idênticos aos das exportações existentes (`utf-8-sig`, `;`, minúsculas sem acento), sem nenhuma novidade de formato.

## Out of Scope (não serão tratados nesta feature)

- Excel/XLSX, PDF ou qualquer outro formato além de CSV.
- Nova tela HTML (inclui página de relatório de locais), novo CRUD, novas regras patrimoniais.
- Novos campos, novos filtros, alteração da pesquisa existente (007), alteração da importação de locais.
- Migração de banco, novas tabelas/colunas/entidades (zero DDL).
- Alteração de permissões existentes, do RBAC ou do cadastro/edição/exclusão de locais.
- Alteração das demais exportações existentes (inventário, colaboradores, movimentações).
