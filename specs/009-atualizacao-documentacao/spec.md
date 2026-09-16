# Feature Specification: Atualização da Ajuda/Manual e do README.md

**Feature Branch**: `009-atualizacao-documentacao`

**Created**: 2026-09-16

**Status**: Draft

**Input**: Atualizar a Ajuda/Manual da aplicação e o README.md para alinhá-los ao funcionamento real do SisPatrimônio Pro: corrigir informações desatualizadas, incluir funcionalidades existentes não documentadas e remover/ajustar instruções que não correspondem ao comportamento atual. Feature exclusivamente documental — nenhum código de produção é alterado.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ajuda/Manual reflete as funcionalidades reais (Priority: P1) 🎯 MVP

Um usuário do sistema abre a central de ajuda embutida (`/ajuda`) para aprender a usar uma funcionalidade e encontra instruções que correspondem exatamente às telas, botões, filtros e permissões que existem hoje — incluindo as funcionalidades recentes (pesquisa de colaboradores e de locais, exportação de locais) que a ajuda atual não menciona.

**Why this priority**: A ajuda embutida é o manual que o usuário final consome dentro da aplicação; instruções desatualizadas geram dúvidas operacionais imediatas e desconfiança do manual. É o escopo mínimo de valor da feature.

**Independent Test**: Percorrer os artigos da `/ajuda` e comparar cada instrução com a tela real correspondente; nenhum passo deve descrever botão, filtro ou fluxo inexistente, e toda funcionalidade existente relevante deve estar coberta por algum artigo.

**Acceptance Scenarios**:

1. **Given** o usuário abre o artigo "Como exportar os dados em CSV", **When** compara com as telas reais, **Then** o artigo menciona o botão "Exportar CSV" presente nas telas de Colaboradores, Dashboard (Relatório Contábil-Físico), Movimentações **e Locais**, o download direto do arquivo pelo botão e a permissão necessária (`relatorios.exportar`).
2. **Given** o usuário abre o artigo "Como cadastrar locais e departamentos", **When** compara com a tela real, **Then** o artigo documenta a pesquisa de locais (campo único por Nome / Identificação, Filtrar/Limpar, correspondência parcial e case-insensitive) e a exportação CSV de locais, além do passo a passo de cadastro existente.
3. **Given** o usuário abre o artigo "Como cadastrar colaboradores (custodiantes)", **When** compara com a tela real, **Then** o artigo documenta a pesquisa de colaboradores conforme o comportamento real (termo único correspondendo a matrícula, nome, cargo, departamento ou e-mail).
4. **Given** o usuário consulta os artigos de inventário, patrimônio, movimentação, manutenção e administração, **When** compara com as telas reais, **Then** nenhum artigo descreve botão, campo, filtro ou fluxo que não exista, e nenhuma funcionalidade existente relevante fica sem cobertura.
5. **Given** qualquer atualização de artigo, **When** a ajuda é aberta no navegador, **Then** o artigo renderiza normalmente na estrutura existente (categoria, pesquisa, FAQ e tooltips funcionando como antes).

---

### User Story 2 - README.md reflete o estado real do projeto (Priority: P2)

Um desenvolvedor ou administrador que chega ao repositório encontra no `README.md` informações corretas sobre a contagem da suíte de testes, comportamento padrão do servidor, variáveis de ambiente e funcionalidades existentes — sem instruções que contradigam o código.

**Why this priority**: O README é a porta de entrada do projeto; erros factuais nele (números defasados, comportamentos diferentes do real) custam tempo de configuração e validação, mas afetam menos o dia a dia do usuário final que a ajuda embutida.

**Independent Test**: Verificar cada afirmação factual do README contra o código/fonte correspondente (config, testes, rotas): nenhuma contradição deve permanecer, e as seções de funcionalidades devem listar o que existe.

**Acceptance Scenarios**:

1. **Given** a seção de testes do README, **When** a suíte é executada (`pytest`), **Then** a contagem citada corresponde à realidade atual e a nota sobre a falha conhecida de lockout reflete o estado real.
2. **Given** a seção "Como Executar o Sistema", **When** o README descreve o endereço de acesso, **Then** os padrões citados correspondem aos valores reais de configuração do projeto (`APP_HOST`/`APP_PORT` reais, não valores presumidos).
3. **Given** a lista de endpoints protegidos e o catálogo de permissões no README, **When** comparados com o código, **Then** a nova exportação de locais (`/api/v1/reports/locations/csv`) aparece entre os endpoints gated por `relatorios.exportar` e o catálogo corresponde ao catálogo real de permissões.
4. **Given** a seção "Principais Funcionalidades", **When** comparada com o sistema, **Then** as funcionalidades existentes não listadas (pesquisa de colaboradores, pesquisa de locais, exportação CSV de locais, CLI `reset-password`, tela de Etiquetas) passam a constar, e nenhuma funcionalidade inexistente é adicionada.

---

### User Story 3 - Guia único de instalação em máquina nova (Priority: P3)

Um administrador prepara uma máquina nova seguindo exclusivamente o README: do zero — pré-requisitos, obtenção do projeto, ambiente Python, banco de dados, `.env`, primeiro administrador, inicialização, primeiro acesso e validação — sem recorrer a fontes externas.

**Why this priority**: É o maior acréscimo de conteúdo (procedimento completo passo a passo), mas depende das correções factuais da US2 e é menos urgente que a ajuda do usuário final; o procedimento real já existe no projeto e hoje está disperso ou ausente.

**Independent Test**: Seguir o guia do README em uma máquina sem o projeto instalado, executando apenas os comandos documentados; ao final, o sistema deve estar acessível, conectado ao banco e com o primeiro administrador criado.

**Acceptance Scenarios**:

1. **Given** a máquina nova com o banco instalado e o `.env` configurado conforme o guia, **When** o operador executa o comando de inicialização documentado, **Then** a estrutura do banco é criada automaticamente pelo mecanismo real do projeto e a aplicação sobe no endereço documentado.
2. **Given** a aplicação recém-inicializada, **When** o operador segue a seção de primeiro administrador, **Then** consegue criar o admin por um dos caminhos reais documentados (variável de ambiente, tela de primeiro acesso `/setup` ou CLI) e efetua login.
3. **Given** a instalação concluída, **When** o operador executa a validação documentada (health check, acesso web e suíte de testes), **Then** todas as verificações passam ou o guia indica como diagnosticar o problema de configuração mais comum (variável de conexão ausente, banco inacessível).

---

### Edge Cases

- **Artigo cujo conteúdo permanece válido** → não é reescrito gratuitamente; ajustes são cirúrgicos, preservando tom, formato e estrutura das listas existentes (`ARTICLES`, `FAQ`, `CATEGORIES`).
- **Divergência entre README e código em ponto não listado nesta spec** → registrada no relatório da análise e corrigida também, pois a regra de consistência cobre o documento inteiro (não apenas os itens listados); sem alterar código.
- **Contagem de testes citada em documento** → expressa de forma que não envelheça a cada novo teste (ex.: quantitativo verificado nesta revisão + instrução de como obter o número atual com `pytest`).
- **Instrução dependente de sistema operacional** (caminho de ativação de ambiente virtual, serviço do banco) → documentada com as variantes relevantes ao ambiente real do projeto (Linux/Windows), sem expandir para plataformas não usadas.
- **Informação sensível** (senhas, credenciais, IPs reais de produção) → nunca presente nos documentos; exemplos usam valores de exemplo claramente fictícios.
- **Endpoint ou permissão "reservada"** documentada hoje (ex.: `movimentacao.cancelar`) → mantida com a marcação real de que é reservada/não exposta, sem apresentá-la como funcionalidade disponível.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A Ajuda/Manual (artigos, FAQ e categorias da central de ajuda embutida) DEVE ser atualizada para refletir o comportamento real verificado no código — telas, botões, filtros, permissões e fluxos —, não o planejado.
- **FR-002**: O artigo de exportações da ajuda DEVE cobrir a exportação CSV de locais (`locais.csv`, botão no cabeçalho da tela de Locais, gate `relatorios.exportar`, conjunto completo sem colunas de interface), que hoje não é mencionado.
- **FR-003**: O artigo de locais da ajuda DEVE documentar a pesquisa de locais (feature 007) e a exportação CSV (feature 008), coerentes com o comportamento real dessas telas.
- **FR-004**: O artigo de colaboradores da ajuda DEVE manter/documentar a pesquisa de colaboradores (feature 006) conforme o comportamento real (termo único, correspondência parcial e case-insensitive em matrícula/nome/cargo/departamento/e-mail).
- **FR-005**: O README DEVE ter suas afirmações factuais corrigidas para corresponder ao estado real: contagem de testes, padrões reais de `APP_HOST`/`APP_PORT`, lista de endpoints protegidos (incluindo a exportação de locais), catálogo de permissões e lista de funcionalidades.
- **FR-006**: O README DEVE conter uma seção específica e completa de **Instalação em uma máquina nova**, cobrindo, a partir da configuração real do projeto: pré-requisitos (SO, Python 3.10+, Git, MariaDB/MySQL), obtenção do projeto, ambiente virtual, instalação de dependências, instalação e inicialização do banco, criação do banco/usuário/permissões, criação e configuração do `.env` (sem credenciais reais), inicialização da estrutura do banco pelo mecanismo real (`init_db` automático no start — sem inventar comandos de migração), criação do primeiro administrador pelos 3 caminhos reais (env `AUTH_ADMIN_*`, tela `/setup`, CLI `create-user`), inicialização da aplicação (`run.py`, host/porta), primeiro acesso e validação da instalação (health check, acesso web, suíte de testes, diagnóstico de problemas comuns).
- **FR-007**: O README DEVE documentar as variáveis de ambiente necessárias à instalação (`DATABASE_URL` obrigatória; `APP_HOST`/`APP_PORT`; `AUTH_*` relevantes ao primeiro acesso; menção às `AD_*` para quem for integrar AD), com descrição, padrão real e exemplo fictício — sem inventar variáveis inexistentes.
- **FR-008**: Nenhum documento DEVE apresentar funcionalidade inexistente como disponível; permissões/telas reservadas (não expostas) devem permanecer marcadas como tal.
- **FR-009**: Nenhum documento DEVE conter instruções que contradigam o funcionamento atual; identificada a divergência, a documentação é atualizada para o comportamento real, sem alterar código.
- **FR-010**: Nenhuma funcionalidade existente relevante DEVE ficar ausente da documentação: pesquisa de colaboradores, pesquisa de locais, exportação CSV de locais, CLI (`create-user`, `reset-password`, `stats`, `list`, `show`, `move`), tela de Etiquetas, provisionamento AD e demais fluxos verificados nesta análise.
- **FR-011**: A atualização DEVE preservar o mecanismo existente da ajuda (listas de artigos/FAQ/categorias em `app/services/help_service.py`, rotas `/ajuda` e `/ajuda/{article_id}`, tooltips, `test_help.py` verde) — apenas conteúdo textual é alterado.
- **FR-012**: A atualização DEVE ser exclusivamente documental: nenhum arquivo de código de produção, teste, template funcional, permissão, configuração ou banco pode ser alterado; arquivos de documentação permitidos: app/services/help_service.py pode ser alterado somente em conteúdo textual das estruturas ARTICLES, FAQ e CATEGORIES; nenhuma lógica, estrutura, rota ou comportamento do serviço pode ser alterado.
- **FR-013**: A suíte de testes existente DEVE permanecer verde após a atualização (nenhum teste de ajuda/menu pode regredir), preservando a falha pré-existente e conhecida de lockout no patamar atual.
- **FR-014**: A documentação DEVE registrar as fontes verificadas (código/config consultados) ao menos no relatório de análise da feature, garantindo rastreabilidade das afirmações.
- **FR-015**: O README DEVE manter a marcação de afirmações não verificáveis (se existirem), no estilo dos docs existentes, e não conter credenciais nem informações sensíveis reais.

### Key Entities *(include if feature involves data)*

- **Ajuda/Manual**: conteúdo centralizado em `app/services/help_service.py` — listas `ARTICLES` (21 artigos atuais), `FAQ` (12 perguntas) e `CATEGORIES` (7 categorias); apresentado nas rotas `/ajuda` e `/ajuda/{article_id}` (`app/web/help_routes.py`, templates `ajuda/index.html` e `ajuda/article.html`), com pesquisa client-side (serialização de busca) e tooltips contextuais; artigos `audience="admin"` exigem permissões administrativas.
- **README.md**: documentação principal na raiz do repositório (seções: funcionalidades, tecnologias, arquitetura, execução, autenticação, AD, RBAC, CLI, ajuda, banco/backup, testes, estrutura, segurança, licença).
- **Documentação complementar (fonte de referência, FORA do escopo de alteração)**: `docs/ARQUITETURA_E_MANUTENCAO.md`, `docs/GUIA_DE_MANUTENCAO.md`, `docs/INVENTARIO_TECNICO.md`, `SPEC-KIT-SISTEMA-ATUAL.md`, specs em `specs/` (001–008).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos artigos da central de ajuda revisados contra o código; zero instruções contraditórias com as telas reais após a atualização.
- **SC-002**: As funcionalidades 006 (pesquisa de colaboradores), 007 (pesquisa de locais) e 008 (exportação CSV de locais) constam da ajuda e do README em 100% dos casos aplicáveis.
- **SC-003**: O README contém uma seção de instalação em máquina nova que cobre os 11 pontos do guia (pré-requisitos → validação), 100% verificados contra a configuração real.
- **SC-004**: Zero afirmações factuais contraditórias com o código no README (contagens, padrões de host/porta, endpoints, permissões, variáveis de ambiente).
- **SC-005**: A suíte de testes existente permanece no patamar verificado nesta análise (281 aprovados / 1 falha conhecida de lockout) após a atualização, com os testes da central de ajuda 100% aprovados.
- **SC-006**: Escopo de arquivos alterados restrito a `app/services/help_service.py` e `README.md` (verificável por `git status`), sem qualquer alteração de comportamento.

## Assumptions

- **Documentação alvo**: os dois alvos foram identificados na análise (não presumidos): ajuda = `app/services/help_service.py` (conteúdo), apresentada via `/ajuda`; documentação principal = `README.md` na raiz. Demais docs (`docs/*.md`) ficam FORA do escopo.
- **Estilo e idioma**: novos textos seguem o estilo dos conteúdos existentes (português, tom direcionado ao usuário, "Passo a passo"/"body"/"note" já usados no `help_service.py`).
- **Mecanismo de ajuda preservado**: não há mudança estrutural (nenhum artigo novo obrigatório além do necessário para cobertura; ajustes preferencialmente nos artigos existentes por módulo).
- **Comportamento real como fonte única**: quando documento e código divergem, o código vence; dúvidas de comportamento são resolvidas lendo o código, não inferindo.
- **Suíte de referência**: patamar atual verificado nesta sessão (281 passed / 1 failed — lockout defasado conhecido); a atualização documental não altera esse patamar.
- **Credenciais**: nenhum valor real de senhas/credenciais/IP de produção será incluído nos documentos; exemplos usam placeholders fictícios.
- **Validação final**: revisão por percorrida dos artigos vs. telas + `pytest` verde + `git status` com escopo restrito.

## Out of Scope

- Qualquer alteração de código de produção, testes, templates funcionais, permissões, autenticação, banco ou configuração.
- Novas funcionalidades, correção de bugs, refatoração, alteração de arquitetura, migrações, novas telas, instalação de dependências.
- Atualização de outras documentações (`docs/ARQUITETURA_E_MANUTENCAO.md`, `docs/GUIA_DE_MANUTENCAO.md`, `docs/INVENTARIO_TECNICO.md`, specs) — apenas o README e a ajuda embutida.
- Reescrita completa dos artigos cujo conteúdo já está correto.
- Documentação de funcionalidades planejadas ou inexistentes.
