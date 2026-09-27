# Phase 0 — Research & Technical Decisions: 049-pesquisa-movimentacoes

**Feature**: Campo de Pesquisa no Fluxo Global de Movimentações  
**Date**: 2026-09-27  
**Branch**: `049-pesquisa-movimentacoes`  

Todas as decisões abaixo foram baseadas na análise direta do código existente do SisPatrimônio Pro, em conformidade estrita com a [Constitution do projeto](file:///home/wellington/IA/sistema_patrimonio_mysql/.specify/memory/constitution.md) e com os requisitos do usuário.

---

## R1 — Onde a filtragem deve ocorrer: servidor (banco de dados) ou navegador (JavaScript)?

- **Decision**: **Server-side (no banco de dados)**, aplicando a filtragem diretamente na cláusula `WHERE` da query SQLAlchemy em `MovementService.get_all_movements`.
- **Rationale**:
  1. **Desempenho e Volume**: O histórico de movimentações é um registro auditável de crescimento contínuo. Carregar todos os registros para a memória do navegador apenas para filtrar com JavaScript consumiria banda desnecessária e causaria travamentos no DOM em bases volumosas.
  2. **Paginação e Limite Preservados**: A rota atual aplica `limit=200`. A query no banco realiza a filtragem antes do fatiamento e ordenação cronológica (`order_by(desc(Movement.timestamp))`), garantindo que o usuário visualize os 200 registros mais recentes *compatíveis com a pesquisa*.
  3. **Conformidade Arquitetural**: Segue o padrão já adotado em `AssetService.get_all` e `audit_service.get_audit_logs`, mantendo consistência no sistema (Constitution II, III e X).
- **Alternatives considered**:
  - *Filtro client-side em JavaScript*: Rejeitado. Exigiria transferir todo o banco ou centenas de registros desnecessariamente, violando a regra de não carregar todos os dados no navegador.
  - *Novo endpoint de busca paralelo*: Rejeitado. Criaria lógica duplicada; a listagem existente já atende à tela.

---

## R2 — Como compor a query SQLAlchemy para cobrir todos os campos solicitados sem problemas de N+1?

- **Decision**: Compor um bloco `or_` com condições `ilike(f"%{term}%")` sobre as colunas da tabela `movements`, sobre as entidades relacionadas já carregadas (`Asset`, `Custodian`, `Location`) e sobre valores/rótulos do enum `MovementType`.
- **Campos e Mecanismos mapeados**:
  1. `Asset.tag` (tombamento) e `Asset.name` (descrição): via `Movement.asset.has(or_(Asset.tag.ilike(term), Asset.name.ilike(term)))`.
  2. Snapshot de Local de Origem / Destino: `Movement.origin_location_name.ilike(term)` e `Movement.destination_location_name.ilike(term)`.
  3. Snapshot de Colaborador de Origem / Destino: `Movement.origin_custodian_name.ilike(term)` e `Movement.destination_custodian_name.ilike(term)`.
  4. Matrícula do Colaborador: via `Movement.origin_custodian.has(Custodian.registration_code.ilike(term))` e `Movement.destination_custodian.has(Custodian.registration_code.ilike(term))`.
  5. Entidades de Local vinculadas: `Movement.origin_location.has(Location.name.ilike(term))` e `Movement.destination_location.has(Location.name.ilike(term))`.
  6. Operador e Termo: `Movement.operator_name.ilike(term)` e `Movement.term_code.ilike(term)`.
  7. Tipo de Movimentação: Comparação dinâmica em Python para identificar quais membros de `MovementType` possuem valor ou rótulo compatível com o termo informado (ex.: "Transferência", "Alocação", "Devolução", "AQUISIÇÃO"); se houver compatibilidade, adiciona `Movement.movement_type.in_(matching_types)` ao `or_`.
- **Rationale**:
  - Cobre exatamente todos os itens solicitados pelo usuário (tombamento, descrição, colaborador, matrícula, local origem, local destino, tipo, operador e termo).
  - Utiliza `joinedload` existente em `get_all_movements` evitando consultas N+1.
  - O uso de `.has()` gera subconsultas `EXISTS` eficientes em bancos SQL (MariaDB/MySQL e SQLite).
- **Alternatives considered**:
  - *Full-text search nativo do MySQL*: Rejeitado. Incompatível com o ambiente de testes em SQLite (`sqlite:///:memory:`) e violaria o Princípio VII e VIII da Constitution.
  - *Filtro em memória Python após carregar 200 registros*: Rejeitado. Deixaria de encontrar registros compatíveis que estivessem além da página inicial.

---

## R3 — Como estender os modelos e schemas sem quebrar compatibilidade?

- **Decision**: Adicionar o campo opcional `search: Optional[str] = None` ao schema Pydantic `MovementFilter` em `app/schemas/movement.py`.
- **Rationale**:
  - `MovementFilter` já encapsula os filtros aceitos por `MovementService.get_all_movements`.
  - Campo opcional com default `None` não quebra nenhum teste existente nem chamadas anteriores.
  - Nenhuma modificação estrutural de tabelas no banco de dados (sem migrações, sem `ALTER TABLE`, sem índices novos precipitados).
- **Alternatives considered**:
  - *Passar `search` como argumento avulso em `get_all_movements`*: Rejeitado. `filters: Optional[MovementFilter]` é o objeto padrão já utilizado para todos os critérios de filtragem em movimentações.

---

## R4 — Como integrar a rota e preservar permissões e query strings?

- **Decision**: Na função `list_movements_view` (`GET /movements`) em `app/web/routes.py`:
  1. Declarar o parâmetro opcional `search: Optional[str] = None`.
  2. Normalizar o termo com `.strip()`; se vazio, considerar `None`.
  3. Repassar ao contexto do template `search=clean_search or ""`.
  4. Manter inalterada a dependência `Depends(require_permission("movimentacao.visualizar"))`.
- **Rationale**:
  - Mantém convenção GET transparente `?search=valor&movement_type=tipo`.
  - Permite recarregar a página mantendo a busca ativa, usar histórico do navegador e compartilhar URLs.
  - Garante segurança rigorosa RBAC (Constitution VI).
- **Alternatives considered**:
  - *Requisição POST para busca*: Rejeitado. Viola convenções REST para telas de listagem e impede navegação por histórico e compartilhamento de URL.

---

## R5 — Como estruturar a interface no template HTML e o estado vazio?

- **Decision**:
  1. No card de filtros de `app/web/templates/movements/list.html`, reorganizar os campos em grid responsiva Bootstrap (`col-12 col-md-6 col-lg-5` para o campo de pesquisa, `col-12 col-md-4 col-lg-4` para o tipo, `col-12 col-md-2 col-lg-3` para as ações).
  2. Utilizar `input-group` com ícone `<i class="bi bi-search"></i>` e placeholder descritivo.
  3. No estado sem resultados (`empty-state`), diferenciar:
     - Se `search` estiver preenchido: exibir "Nenhuma movimentação encontrada para a pesquisa informada.", texto explicativo e botão de atalho "Limpar Pesquisa".
     - Se não houver pesquisa: exibir o estado vazio padrão atual ("Nenhuma movimentação encontrada").
- **Rationale**:
  - Segue exatamente a identidade visual de `assets/list.html`, `custodians/list.html` e `admin/audit/list.html`.
  - Total compatibilidade com tema claro e escuro (variáveis CSS do projeto).
  - Atende plenamente à Regra 15 do usuário (feedback claro de ausência de registros sem tratar como erro do sistema).
