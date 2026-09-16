# Research: Pesquisa de Locais (feature 007)

**Data**: 2026-09-16 · Todas as decisões verificadas no código real (somente leitura) antes do desenho.

## R1 — Onde o filtro executa: **server-side, na camada de serviço**

- **Decisão**: parâmetro `search: Optional[str] = None` em `LocationService.get_all`, aplicado como `Location.name.ilike(f"%{termo}%")` após normalização `strip()`.
- **Rationale**: decisão explícita da spec (Assumption 1/FR-008) + precedente idêntico nas telas de bens (`GET /assets?search=`) e colaboradores (feature 006). A Constituição III concentra regras de negócio nos services; a rota só repassa.
- **Alternativas rejeitadas**: filtro client-side/JS (fora do escopo — spec proíbe; criaria um segundo padrão de busca no sistema e exigiria carregar tudo no DOM); filtro na rota (violaria II/III); nova query em template (proibido).

## R2 — Mono-campo vs multi-campo: **mono-campo (`Location.name` apenas)**

- **Decisão**: filtro exclusivamente sobre o atributo `name`, exibido como **"Nome / Identificação"**.
- **Rationale**: decisão central do input do usuário — pesquisar "Gabinete" deve achar locais cujo **nome** contém "Gabinete", não os que têm "Gabinete" apenas no departamento. FR-002 e edge case da spec consolidam; contratesta entra na suíte.
- **Alternativas rejeitadas**: replicar o `or_` multi-campo da 006 (matrícula/nome/cargo/depto/e-mail) — invertiria a intenção explícita e retornaria registros que o usuário não pediu.

## R3 — Retrocompatibilidade do `get_all`: **parâmetro aditivo com default `None`**

- **Decisão**: manter assinatura compatível e branch idêntico quando `search` ausente/vazio.
- **Rationale**: verificação no código — `LocationService.get_all(db)` é chamado pela **API REST** (`app/api/locations_api.py`), por rotas web de formulários e por seletores (`app/web/routes.py` linhas 336/401/600/751…). Qualquer mudança no comportamento sem termo teria efeito cascata. Mesmo padrão aplicado com sucesso na 006.
- **Alternativas rejeitadas**: novo método `search_locations()` paralelo (duplicaria a lógica de consulta — RT-002 da 006/Princípio I); expor `search` na API REST (fora do escopo).

## R4 — Estados vazios: **três estados distintos no template**

- **Decisão**: (a) tabela com resultados; (b) `search` presente sem correspondência → **"Nenhum local encontrado."** (texto exato, FR-007); (c) sem registros e sem pesquisa → "Nenhum local cadastrado" (preservado como está).
- **Rationale**: o template atual só tem os estados (a)/(c); a mensagem (b) é nova e exigida literalmente pelo input. Precedente exato em `custodians/list.html` (feature 006).
- **Alternativas rejeitadas**: reaproveitar "Nenhum local cadastrado" para busca sem resultado (mensagem mentirosa — locais existem, só não casaram).

## R5 — Botões Filtrar/Limpar: **padrão vigente de colaboradores (corrigido nesta conversa)**

- **Decisão**: card de filtros separado (`card p-3 mb-4` + `form.row.g-2`); Filtrar = `btn btn-primary` + `bi-funnel me-1` + texto; Limpar = `btn btn-ghost` **somente texto, sem ícone**, sempre visível, link para `/locations`.
- **Rationale**: decisão explícita do input (Filtrar com ícone; Limpar só texto) — coincide com o padrão já alinhado em `custodians/list.html` e com o par de `movements/list.html`. O card de filtros separado segue `assets/list.html` (e o ajuste de layout feito em colaboradores nesta sessão).
- **Alternativas rejeitadas**: Limpar só-ícone `bi-x-lg` de `assets/list.html` (contraria a decisão explícita do input); condicionar o Limpar à existência de `search` (input pede comportamento do par sempre presente; diferença visual menor, registrada como coerente com o padrão de Movimentações/Colaboradores).

## R6 — Caracteres especiais no termo (`%`, `_`, aspas, acentos)

- **Decisão**: seguir o precedente já aceito do sistema: `ilike` com curingas do termo passam direto (sem escape); a página não deve falhar; acentos funcionam naturalmente com collation existente.
- **Rationale**: as pesquisas de bens e colaboradores já operam assim em produção, sem relato de problema; introduzir escape aqui criaria divergência de comportamento entre telas do mesmo padrão (Constitution X). Teste automatizado confirma ausência de erro (sem congelar o comportamento de curinga como requisito).
- **Alternativas rejeitadas**: implementar escape de curingas só nesta tela (comportamento inconsistente entre telas gêmeas; escopo maior sem necessidade comprovada).

## Verificações pontuais (fatos, não decisões)

| Fato | Evidência |
|---|---|
| Rota única da listagem: `GET /locations`, gate `locais.visualizar` | `app/web/routes.py` L1162 |
| Serviço hoje sem filtro; ordenação `branch, department, name` | `app/services/location_service.py` L9-11 |
| Chamadores de `get_all` além da tela (API REST, formulários, seletores) | greps em `app/api/locations_api.py` L29 e `app/web/routes.py` |
| 1ª coluna da tabela: cabeçalho exato "Nome / Identificação" | `app/web/templates/locations/list.html` L29 |
| Sem paginação na tela (lista completa) | template e rota |
| Não existe `tests/test_locations.py` dedicado; cobertura espalhada | glob em `tests/` |
| Artigo de ajuda existente: `cadastrar-locais` ("Como cadastrar locais e departamentos") | `app/services/help_service.py` L581 |
| Baseline da suíte: 245 passed / 1 failed (lockout defasado conhecido) | execução pytest nesta sessão |
