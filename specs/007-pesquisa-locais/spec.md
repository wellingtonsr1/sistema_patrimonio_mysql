# Feature Specification: Pesquisa de Locais

**Feature Branch**: `007-pesquisa-locais`
**Status**: Draft
**Input**: Adicionar um campo de pesquisa à tela existente de Locais, pesquisando pelo campo **Nome / Identificação**.

## 1. Contexto do Sistema Existente (análise verificada no código)

Análise de somente leitura realizada antes da especificação (requisito da seção "Implementação" do input):

| Item identificado | Valor real no código |
|---|---|
| Rota da listagem | `GET /locations` — `list_locations_view` (`app/web/routes.py`), protegida por `locais.visualizar` |
| Serviço de consulta | `LocationService.get_all(db)` (`app/services/location_service.py`) — retorna **todos** os locais, ordenados por `branch, department, name`, **sem parâmetro de filtro** |
| Template | `app/web/templates/locations/list.html` — tabela sem campo de pesquisa |
| Coluna alvo da pesquisa | 1ª coluna da tabela, cabeçalho exatamente **"Nome / Identificação"** (atributo `name` do modelo `Location`) |
| Permissão | `locais.visualizar` — **não muda** |
| Paginação | Não existe — a tela carrega a lista completa (mesmo padrão da tela de colaboradores antes da feature 006) |
| Chamadores de `get_all` | **API REST de locais** (`app/api/locations_api.py`), rotas web de formulários e seletor de locais — o filtro precisa ser **aditivo e retrocompatível** (sem `search`, comportamento idêntico ao atual) |
| Testes existentes | Cobertura de locais espalhada (`test_import_asset_location.py`, `test_movements.py`, `test_inventario.py` etc.) — não existe `tests/test_locations.py` dedicado |
| Padrão de pesquisa a seguir | Pesquisa de **bens** (`?search=` server-side, `ilike` parcial, card de filtros separado) e pesquisa de **colaboradores** (feature 006) |

## 2. User Scenarios & Testing

### User Story 1 - Localizar um local rapidamente pelo Nome / Identificação (Priority: P1)

Um usuário que precisa conferir ou referenciar um local específico (ex.: "IPMJP – Acessoria de Controle Interno") hoje rola manualmente a tabela para encontrá-lo. Com a pesquisa, diga parte do nome e a tabela mostra somente os locais correspondentes.

**Why**: A listagem de locais tende a crescer (cada filial/departamento/sala é um registro) e localizar visualmente é lento e propenso a erro.

**Independent Test**: Acessar a tela de locais, digitar um termo que corresponda ao Nome / Identificação e confirmar que somente os locais correspondentes aparecem.

**Acceptance Scenarios**:

1. **Given** existem locais cadastrados, **When** o usuário acessa a tela de locais, **Then** o campo de pesquisa está disponível acima da tabela, dentro do card de filtros.
2. **Given** existe o local "IPMJP – Acessoria de Controle Interno", **When** o usuário pesquisa `Controle`, **Then** somente os locais cujo Nome / Identificação contém "Controle" são exibidos.
3. **Given** existem vários locais da filial IPMJP, **When** o usuário pesquisa `IPMJP`, **Then** todos os locais que contêm "IPMJP" no Nome / Identificação são exibidos.
4. **Given** o usuário pesquisou um termo, **When** a página é reexibida, **Then** o campo permanece preenchido com o termo pesquisado.

### User Story 2 - Pesquisa tolerante e com feedback claro (Priority: P2)

A pesquisa deve se comportar de forma previsível com variações de digitação e informar claramente quando nada é encontrado.

**Why**: Termos parciais, maiúsculas/minúsculas e espaços acidentais não podem impedir o usuário de encontrar o local.

**Independent Test**: Pesquisar variações do mesmo termo (caixa, espaços, termos inexistentes) e confirmar os resultados e a mensagem de estado vazio.

**Acceptance Scenarios**:

1. **Given** existe "IPMJP – Acessoria de Controle Interno", **When** o usuário pesquisa `CONTROLE`, `controle` ou `Controle`, **Then** os resultados são equivalentes (sem diferenciação de maiúsculas/minúsculas).
2. **Given** existe "IPMJP – Acessoria de Gabinete", **When** o usuário pesquisa `gabinete`, **Then** o local correspondente aparece (correspondência parcial em qualquer posição do nome).
3. **Given** o usuário digita o termo com espaços nas extremidades, **When** a pesquisa é executada, **Then** os espaços excedentes são removidos e a pesquisa considera o termo aparado.
4. **Given** o campo está vazio ou contém apenas espaços, **When** a pesquisa é executada, **Then** a lista completa de locais é apresentada.
5. **Given** nenhum local corresponde ao termo, **When** a pesquisa é executada, **Then** a tela apresenta exatamente **"Nenhum local encontrado."** sem erro na aplicação.
6. **Given** uma pesquisa ativa, **When** o usuário limpa o campo e pesquisa novamente, **Then** a lista completa é restaurada.

### User Story 3 - Integridade da tela e dos dados existentes (Priority: P3)

A pesquisa é exclusivamente uma operação de consulta: deve apenas reduzir o conjunto de locais exibidos, sem alterar dados, links, ações, contagem de bens ou permissões.

**Why**: A tela de locais alimenta formulários e seletores de todo o sistema; qualquer alteração acidental de comportamento teria efeito cascata.

**Independent Test**: Comparar a tela com e sem pesquisa ativa e confirmar que estrutura, dados, links e ações permanecem idênticos.

**Acceptance Scenarios**:

1. **Given** a tela sem termo de pesquisa, **When** a página é carregada, **Then** a tabela apresenta exatamente as colunas atuais: Nome / Identificação, Filial, Departamento, Prédio / Andar / Sala, Gestor, Bens e Ações.
2. **Given** um local nos resultados da pesquisa, **When** o usuário utiliza seus links e ações existentes, **Then** o comportamento é o mesmo de antes da feature (ver detalhes, editar, bens vinculados).
3. **Given** um local com bens vinculados, **When** ele aparece nos resultados, **Then** a contagem de bens exibida é a mesma da listagem completa.
4. **Given** o mesmo usuário e a mesma permissão, **When** nenhuma pesquisa é informada, **Then** todos os locais visíveis antes da implementação continuam visíveis (não regressão).

## Edge Cases

- Termo vazio, apenas espaços ou apenas caracteres de espaçamento → lista completa (termo normalizado).
- Termo com espaços no início/fim → aparado antes da pesquisa.
- Termo com acentos ou caracteres especiais (ex.: `%`, `_`) → a página não deve falhar; o comportamento segue o padrão já adotado nas pesquisas de bens e colaboradores.
- Termo que corresponde a outros campos (Filial, Departamento, Gestor) **mas não ao Nome / Identificação** → o registro **não** deve aparecer: o alvo da pesquisa é exclusivamente o Nome / Identificação (decisão explícita do input; pesquisar por "Gabinete" só encontra locais cujo *nome* contém "Gabinete", não os que têm "Gabinete" só no departamento).
- Múltiplas palavras no termo (ex.: `controle interno`) → tratadas como um único texto a localizar dentro do Nome / Identificação, seguindo o padrão das pesquisas existentes.
- Nome / Identificação de locais com formatos mistos (sigla + descrição, ex.: "IPMJP – ...") → correspondência parcial em qualquer posição.

## Requirements

### Functional Requirements

- **FR-001**: A tela de locais deve apresentar um campo de pesquisa acima da tabela, dentro do card de filtros, no padrão visual já utilizado pelo sistema.
- **FR-002**: A pesquisa deve considerar **exclusivamente** o campo exibido como **"Nome / Identificação"** (primeira coluna da tabela).
- **FR-003**: A pesquisa deve aceitar correspondência parcial em qualquer posição do Nome / Identificação.
- **FR-004**: A pesquisa não deve diferenciar maiúsculas de minúsculas.
- **FR-005**: Termos com espaços excedentes no início e no fim devem ser aparados antes da pesquisa.
- **FR-006**: Campo vazio ou contendo apenas espaços deve resultar na exibição da lista completa de locais.
- **FR-007**: Quando nenhum local corresponder à pesquisa, a tela deve apresentar exatamente a mensagem **"Nenhum local encontrado."**, sem erro na aplicação.
- **FR-008**: A pesquisa deve ser executada no servidor, preservando o termo na URL (método GET), para que o resultado possa ser recarregado e compartilhado.
- **FR-009**: O campo deve permanecer preenchido com o termo após a pesquisa.
- **FR-010**: Limpar o campo e pesquisar novamente deve restaurar a lista completa de locais.
- **FR-011**: A pesquisa deve usar a camada de serviço existente de locais — a solução não deve criar uma segunda lógica de consulta; o parâmetro de filtro deve ser **aditivo e retrocompatível** (sem termo, a consulta retorna exatamente o mesmo resultado de hoje, preservando API REST e demais chamadores).
- **FR-012**: A pesquisa deve respeitar a mesma permissão e o mesmo universo de dados já aplicados à tela de locais — nenhum local além dos já visíveis ao usuário pode ser revelado pela pesquisa.
- **FR-013**: Links, ações, contagem de bens e demais comportamentos da tabela devem continuar funcionando exatamente como antes.
- **FR-014**: A tela deve oferecer o par de botões **Filtrar** (com ícone, no padrão visual existente) e **Limpar** (somente texto, sem ícone), seguindo o padrão já estabelecido nas telas de filtros do sistema.
- **FR-015**: Devem existir testes automatizados cobrindo, no mínimo: pesquisa por Nome / Identificação (completa e parcial), sem diferenciação de caixa, termo aparado, termo vazio/só espaços, nenhum resultado com a mensagem exata, preservação do termo no campo, restauração da lista completa ao limpar, não-regressão da tela (colunas, links, contagem de bens, ações), retrocompatibilidade da consulta sem termo, e confirmação de que termos que casam apenas com Filial/Departamento/Gestor não retornam registros (alvo exclusivo do Nome / Identificação).

### Success Criteria

- **SC-001**: Um usuário localiza um local específico pelo Nome / Identificação em menos de 10 segundos, sem usar a barra de rolagem.
- **SC-002**: 100% das variações de caixa (`CONTROLE`, `controle`, `Controle`) produzem o mesmo resultado para o mesmo termo.
- **SC-003**: 100% dos locais visíveis antes da implementação continuam visíveis sem termo de pesquisa, com a mesma permissão (não regressão).
- **SC-004**: 100% dos testes automatizados existentes continuam passando após a implementação.
- **SC-005**: Pesquisas sem correspondência exibem "Nenhum local encontrado." em 100% dos casos, sem erro HTTP 500.
- **SC-006**: A pesquisa devolve resultados perceptivelmente rápidos (< 2 segundos) com o volume atual de locais.

## Key Entities

- **Location** (somente leitura nesta feature): atributo `name` (exibido como "Nome / Identificação") é o único alvo da pesquisa; demais atributos (`branch`, `department`, `building`, `floor`, `room`, `manager_name`) permanecem apenas como colunas de exibição. Nenhuma alteração de modelo, schema ou banco.

## Assumptions

1. O filtro executa no servidor (decisão explícita do input), replicando o padrão das pesquisas de bens e colaboradores (feature 006) — card de filtros separado + parâmetro GET `search`.
2. O campo de pesquisa aplica-se apenas à tela de listagem de locais; a API REST de locais **não** é alterada (recebe retrocompatibilidade automaticamente pelo parâmetro aditivo do serviço, sem expor o filtro).
3. A ordenação atual dos resultados (filial, departamento, nome) permanece inalterada com e sem pesquisa.
4. A mensagem de estado vazio para "nenhum local cadastrado" (sem registros no sistema) permanece distinta da mensagem de pesquisa sem resultado ("Nenhum local encontrado.").

## Out of Scope (não serão tratados nesta feature)

- Nova tela de locais; novo modelo/entidade; novas tabelas ou colunas; qualquer alteração de banco de dados (zero DDL).
- Novas permissões ou alteração do gate `locais.visualizar`.
- Filtros por outros campos (Filial, Departamento, Prédio/Andar/Sala, Gestor, Bens) ou seletor de campo.
- Autocomplete, paginação, pesquisa via JavaScript/client-side.
- Alteração do CRUD de locais, das regras de negócio de locais, da contagem de bens ou das ações existentes.
- Alteração do padrão visual global dos botões do sistema.
