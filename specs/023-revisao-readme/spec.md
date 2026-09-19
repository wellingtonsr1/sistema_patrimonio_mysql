# Feature Specification: Revisão e Melhoria do README.md — SisPatrimônio Pro

**Feature Branch**: `feature-revisao-readme`

**Created**: 2026-09-18

**Status**: Draft

**Input**: Revisar e melhorar o `README.md` como **porta de entrada do projeto**, com detalhes técnicos permanecendo em `docs/`. A revisão é uma **auditoria documental contra o código atual**: o funcionamento real e verificável do sistema é a fonte principal; informações desatualizadas, incompletas, contraditórias ou genéricas demais são corrigidas. **Feature exclusivamente documental** — nenhum código, banco ou configuração é alterado.

## Realidade verificada (premissas do briefing)

*Analisar antes de editar — nada presumido. A lista abaixo define o que DEVE ser confirmado no código, não o que já está confirmado.*

1. **Escopo-fonte**: somente `README.md` será alterado (briefing §3).
2. **Fonte de verdade, em ordem**: implementação atual (`app/main.py`, `app/config.py`, `app/database.py`, `app/cli.py`) → models/schemas → rotas/APIs → services → configuração → `requirements.txt` → testes → `docs/` → README atual (briefing §4).
3. **Análise obrigatória antes de editar** (briefing §5): `README.md`, `app/` (config, database, main, cli, models/, schemas/, services/, api/, web/), `tests/`, `requirements.txt`, `run.py`, `.env.example`, `docs/`, `specs/`.
4. **Estado do projeto a determinar do código** (briefing §6): nome, versão real, status, stack, banco de produção (MariaDB/MySQL) e de testes (SQLite), mecanismo de inicialização, configuração, autenticação, AD, RBAC, auditoria, inventário, movimentações, equipamentos, colaboradores, locais, manutenções, relatórios/exportações, backup/restauração, CLI, testes, estrutura de diretórios. **Não preencher o que não puder ser confirmado.**
5. **Pontos de conferência obrigatória no README atual** (alerta do requisitante): documentação de `/setup`, backup automático, restauração, CLI e regras de AD — não preservar nenhuma informação antiga sem verificar se ainda corresponde ao sistema.
6. **Regras de negócio já formalizadas na Constitution** (base de conferência): inventário não altera cadastro (Princípio V); movimentações pelo motor `MovementService` com tipos controlados (IV); RBAC deny-by-default e AD autentica-mas-não-autoriza (VI); auditoria sem credenciais (IX); UTC persistido / America/Recife apresentado (a confirmar na Feature 004 — briefing §21); suíte sem números fixos documentáveis (VIII).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Auditoria documental README ↔ código (Priority: P1)

Um mantenedor do projeto solicita a revisão do README. Antes de qualquer edição, cada afirmação do README atual é confrontada com a implementação: comandos do CLI, endpoints (`/setup`, rotas de backup…), variáveis de configuração (`AUTH_*`, `AD_*`, `BACKUP_*`, `DATABASE_URL`), permissões e perfis, regras de AD → perfil, banco de produção/testes, bibliotecas/versões em `requirements.txt`, estrutura de diretórios. O resultado da auditoria é um inventário de divergências (obsoleto / incorreto / incompleto / correto) que orienta a reescrita.

**Why this priority**: sem a auditoria, a reescrita corre o risco de preservar informação antiga — o problema central que esta feature existe para resolver.

**Independent Test**: para cada seção do README, existe uma verificação citável no código (arquivo/linha ou teste) confirmando ou refutando a afirmação; divergências estão listadas antes da edição.

**Acceptance Scenarios**:

1. **Given** o README atual, **When** cada comando CLI documentado é conferido em `app/cli.py`, **Then** cada comando é classificado como existente (com parâmetros corretos) ou obsoleto (a remover/corrigir).
2. **Given** a menção a `/setup` no README atual, **When** as rotas são conferidas em `app/`, **Then** o mecanismo real do primeiro administrador é documentado somente conforme encontrado (CLI `create-user`, `AUTH_ADMIN_*` e/ou `/setup` — somente o que existir).
3. **Given** qualquer afirmação sobre backup/restauração/automático/configurável, **When** conferida contra rotas, services e specs 016–022, **Then** a descrição reflete o comportamento real atual.

---

### User Story 2 - Reescrita do README como porta de entrada (Priority: P1)

Com a auditoria em mãos, o README é reescrito/reorganizado na sequência lógica do briefing §37 (introdução objetiva → status → funcionalidades reais → modelo conceitual → tecnologias → arquitetura → instalação → configuração → primeiro acesso → autenticação → AD → RBAC → auditoria → banco → CLI → testes → estrutura → segurança → backup/restauração → documentação complementar → pontos de atenção → licença). Regras inegociáveis da reescrita: linguagem clara e técnica sem marketing (§36); inventário descrito como **conferência física comprobatória que não altera bens** (§9); tipos reais de movimentação com suas finalidades (§10); AD **não concede acesso automaticamente** — grupo mapeado → perfil → permissões do perfil (§18); RBAC deny-by-default com autorização no backend (§19); UTC/Recife documentado somente se a Feature 004 estiver implementada (§21); instalação reproduzível em máquina nova com comandos verificados (§25); sem segredos nem `.env` real (§24); sem números fixos de testes — usar `pytest -q` (§28); estrutura de diretórios real (§29); segurança separada em "implementado" vs "recomendação operacional" (§31); referências a `docs/`/`specs/` somente para arquivos que existem (§32).

**Why this priority**: é a entrega da feature — o README melhorado e fiel.

**Independent Test**: ler o README final do início ao fim e verificar cada afirmação contra a auditoria da US1; seguir o guia de instalação passo a passo em máquina nova (ou simulação) sem tropeços.

**Acceptance Scenarios**:

1. **Given** um desenvolvedor novo, **When** lê o README, **Then** entende o que o sistema é, qual problema resolve, o estado atual e onde encontrar a documentação técnica — sem afirmações promocionais.
2. **Given** um administrador, **When** segue a seção de instalação, **Then** consegue preparar ambiente, configurar `.env` (exemplos seguros), criar o primeiro administrador pelo mecanismo real e iniciar o sistema.
3. **Given** o README reescrito, **When** as regras de AD/RBAC/inventário são lidas, **Then** estão consistentes entre si e com o código (§35 — nenhuma contradição interna).

---

### User Story 3 - Validação final e relatório (Priority: P2)

Após a reescrita, o checklist de validação do briefing §39 é executado (comandos, caminhos, endpoints, arquivos, tecnologias, banco, autenticação, AD, RBAC, inventário, movimentações, backup/restauração, CLI, testes, links internos, blocos de código, Markdown) e o relatório final do §41 é produzido: principais melhorias, verificações realizadas, confirmações de que código/banco/configuração não foram alterados e limitações (informações não confirmáveis).

**Why this priority**: garante que a entrega esteja verificável e que divergências insolúveis documentalmente fiquem registradas (em "Pontos de atenção" ou no relatório).

**Independent Test**: conferir o relatório contra o diff (apenas README.md) e executar o checklist item a item.

**Acceptance Scenarios**:

1. **Given** a revisão concluída, **When** `git diff` é inspecionado, **Then** somente `README.md` foi alterado.
2. **Given** o relatório final, **When** lido, **Then** declara explicitamente o que foi verificado e o que permanece como limitação.

---

### Edge Cases

- **Informação não confirmável**: se algo do README atual não puder ser confirmado nem refutado no código, sai do README (ou fica marcado como não confirmado no relatório) — nunca é documentado como fato (briefing §6/§41).
- **Divergência README ↔ código insolúvel documentalmente** (ex.: README descreve comportamento que exigiria correção de código): o código não é tocado; a divergência é registrada em "Pontos de atenção" e no relatório (briefing §38).
- **Documentação complementar necessária mas inexistente em `docs/`**: NÃO criar arquivos automaticamente nesta feature; registrar a necessidade no relatório, salvo caso indispensável e explicitamente justificado (briefing §3/§32).
- **README atual com informação correta**: preservar (a revisão não é reescrita por reescrita — é correção fundamentada).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Somente `README.md` é alterado nesta feature — nenhum arquivo Python/HTML/CSS/JS, banco, models, services, APIs, rotas, autenticação, AD, RBAC, auditoria, testes, requirements, `.env`, configuração ou infraestrutura (briefing §3/§38).
- **FR-002**: Toda afirmação do README final DEVE ser verificável na implementação atual (código/implementação = fonte de verdade, salvo regra explicitamente aprovada já em implementação — briefing §4).
- **FR-003**: Nenhum comando, endpoint, configuração, tabela, permissão, regra de negócio, número de testes ou versão pode ser inventado; nada não-confirmado é documentado como fato (briefing §2/§6).
- **FR-004**: Divergência README ↔ código é corrigida SEMPRE no README, nunca no código (briefing §38).
- **FR-005**: A introdução explica objetivamente o que é o sistema, para que serve, qual problema resolve, o foco e o estado atual — sem texto promocional (briefing §7).
- **FR-006**: As funcionalidades documentadas correspondem exatamente aos módulos implementados: equipamentos, patrimônio, movimentações, inventário, colaboradores, locais, manutenções, relatórios, exportações, central de ajuda, autenticação, AD, RBAC, auditoria, backup, restauração (briefing §8).
- **FR-007**: O inventário é descrito como **conferência física comprobatória que não altera automaticamente os bens patrimoniais**, cobrindo somente o que o código confirmar (criação, escopo, snapshot, conferência, QR Code, divergências, re-conferência, encerramento, travamento, ata, exportações) — sem atribuir ao inventário responsabilidades das movimentações (briefing §9).
- **FR-008**: As movimentações são documentadas com os tipos reais encontrados no código (alocação/cautela, transferência, manutenção, devolução, baixa) e suas finalidades — nenhum tipo novo é criado para "melhorar" a documentação (briefing §10).
- **FR-009**: Autenticação e autorização são descritas separadamente: local (hash/sessão/lockout/primeiro acesso/CLI) e AD, com a regra **AD autentica mas não autoriza** — grupos AD precisam estar explicitamente mapeados a perfis existentes; usuários AD sem mapeamento não recebem acesso; permissões vêm do RBAC interno; nenhum segredo/servidor interno é exposto (briefing §17/§18).
- **FR-010**: O RBAC é descrito como usuário → perfil → permissões com **deny by default** e autorização sempre no backend; perfis listados conferidos um a um com a implementação (briefing §19).
- **FR-011**: A auditoria é descrita com os campos realmente gravados (usuário, data/hora, IP, resultado, recurso, before/after quando aplicável) e a regra de que **credenciais/segredos jamais são registrados** (briefing §20).
- **FR-012**: A regra de data/hora (persistência UTC → apresentação America/Recife) só é documentada se a Feature 004 estiver efetivamente implementada — não por existir spec (briefing §21).
- **FR-013**: A tabela de tecnologias reflete `requirements.txt`, código e configuração reais — versões específicas só quando confirmáveis (briefing §22).
- **FR-014**: A arquitetura é apresentada como visão simples (Interface Web / API REST → auth → services → models → MariaDB/MySQL), ajustada às diferenças reais, sem mapa completo de classes (briefing §23).
- **FR-015**: A configuração documenta somente as variáveis relevantes reais (`DATABASE_URL`, `APP_HOST`, `APP_PORT`, `AUTH_*`, `AD_*`, `BACKUP_*`) com exemplos seguros — nunca valores secretos nem o `.env` real (briefing §24).
- **FR-016**: A instalação cobre máquina nova de ponta a ponta (pré-requisitos, Git, Python, MariaDB/MySQL, clone, venv, dependências, banco, `.env`, primeiro administrador, inicialização, primeiro acesso, validação) com comandos verificados contra a implementação (briefing §25).
- **FR-017**: O primeiro administrador é documentado somente pelos mecanismos reais (CLI `create-user`, `AUTH_ADMIN_*` e/ou `/setup` — apenas o que existir no código), explicando quando cada um se aplica (briefing §26).
- **FR-018**: Cada comando CLI documentado é confirmado (nome, parâmetros, comportamento); comandos obsoletos são removidos (briefing §27).
- **FR-019**: A seção de testes não contém números fixos; usa `pytest -q` e descreve resumidamente a cobertura (briefing §28).
- **FR-020**: A árvore de estrutura do projeto corresponde aos diretórios reais — sem arquivos/diretórios inventados e sem listagem exaustiva (briefing §29).
- **FR-021**: A seção de banco é resumida (produção MariaDB/MySQL, ORM, inicialização, mecanismo de migração existente, grupos de tabelas úteis) — sem colunas e sem sugerir migração de banco (briefing §30).
- **FR-022**: A segurança separa **implementado** (hash, sessões, cookies, lockout, RBAC, backend, AD, auditoria, open redirect, proteção de credenciais) de **recomendação operacional** (ex.: HTTPS em produção) — recomendação nunca é apresentada como funcionalidade (briefing §31).
- **FR-023**: O README referencia `docs/` e `specs/` existentes como complemento — nenhuma estrutura de documentação fictícia (briefing §32).
- **FR-024**: "Pontos de atenção" contém somente limitações reais e verificadas — sem lista de bugs, problemas já corrigidos ou especulações (briefing §33).
- **FR-025**: Conteúdo obsoleto (comandos, nomes, banco, versões, funcionalidades removidas, números de testes, caminhos/endpoints inexistentes, configurações antigas) é corrigido ou removido (briefing §34).
- **FR-026**: O README é internamente consistente (MariaDB como produção em todas as menções; AD sem conceder permissões diretas; inventário sem transferir bens — §35).
- **FR-027**: A organização final segue a sequência lógica do §37 (ajustável se a estrutura real justificar) e o README permanece objetivo — porta de entrada, não manual gigantesco (briefing §36/§37).

### Non-Functional Requirements

- **NFR-001** (Fidelidade): zero afirmação não-verificável; quando o briefing do README atual não puder ser confirmado, marcado no relatório como limitação.
- **NFR-002** (Escopo): diff da feature contém somente `README.md`.
- **NFR-003** (Linguagem): português claro e técnico, frases objetivas, sem marketing, compreensível por quem acaba de entrar no projeto (briefing §36).
- **NFR-004** (Durabilidade): nenhuma informação sujeita a desatualização rápida como fato (números de testes, contagens) (briefing §28/§34).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `git diff` da feature altera somente `README.md` (código/banco/configuração intocados).
- **SC-002**: Cada comando, endpoint e variável de configuração citados no README existe na implementação (verificação um a um na US3).
- **SC-003**: A instalação, executada como documentada, leva a um sistema funcional (pré-requisitos → primeiro acesso) sem comandos inexistentes.
- **SC-004**: As regras críticas aparecem corretas e sem contradição interna: inventário ≠ alteração de bens; AD → grupo mapeado → perfil → permissões; RBAC deny-by-default; MariaDB/MySQL como produção; UTC/Recife somente se implementado.
- **SC-005**: Nenhum número fixo de testes permanece no README; a orientação é `pytest -q`.
- **SC-006**: Nenhum segredo/valor real de `.env` aparece no README; exemplos usam placeholders.
- **SC-007**: Toda referência a `docs/`/`specs/` aponta para caminhos existentes.
- **SC-008**: O relatório final (briefing §41) é produzido com melhorias, verificações, confirmações (código/banco/configuração NÃO alterados) e limitações.

## Assumptions

1. O README atual já passou por revisão recente — por isso a **auditoria obrigatória** (US1) é o diferencial desta spec: nenhuma informação antiga é preservada sem verificação (ponto explícito do requisitante: `/setup`, backup automático, restauração, CLI e regras de AD merecem conferência).
2. A Constitution v1.0.0 descreve comportamento formalizado e verificado; pode servir de referência cruzada, mas o código continua sendo a fonte final.
3. `docs/` já contém documentação técnica a ser referenciada (a confirmar na análise — nada de estrutura fictícia).
4. Testes não serão modificados; execução de testes só para confirmar informação documentada (briefing §39).
5. Esta feature não resolve divergências via código — divergências estruturais viram registro em "Pontos de atenção"/relatório para tarefa própria (Princípio I da Constitution).
