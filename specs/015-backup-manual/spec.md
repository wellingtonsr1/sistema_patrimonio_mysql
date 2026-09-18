# Feature Specification: Backup Manual do SisPatrimônio Pro

**Feature Branch**: `015-backup-manual`

**Created**: 2026-09-17

**Status**: Draft

**Input**: Implementar o mecanismo de criação e gerenciamento básico de backups do sistema, permitindo que um usuário autorizado gere manualmente um backup do estado atual do sistema e consulte/baixe os backups disponíveis. Preservar integralmente o funcionamento atual do sistema; registrar a operação na Auditoria existente.

---

## 1. Contexto e análise do sistema atual (somente leitura, verificada nesta especificação)

Fatos confirmados no código — nenhum nome abaixo é presumido:

| # | Ponto investigado | Realidade atual verificada |
|---|---|---|
| 1 | Mecanismo de backup existente | **Inexistente** — nenhum código, rota, service ou tela de backup. O README (seção 💾) orienta apenas backups **operacionais** do MariaDB/MySQL por mecanismos do ambiente, como política do servidor — não há funcionalidade no sistema. |
| 2 | Camada de services | Padrão estabelecido: regras de negócio em `app/services/` (Constitution II/III); 17 services precedentes (movimentações, inventário, importações, permissões etc.) |
| 3 | Página de administração | Fluxo administrativo existente em `app/web/admin_routes.py` (usuários, sessões, auditoria, eventos AD — leitura), com permissões `modulo.acao` deny-by-default (Constitution VI) |
| 4 | Auditoria | Trilha `audit_logs` imutável, escrita somente via `audit_service.write_audit` (Princípio IX); eventos atuais: login, criação/alteração/bloqueio, movimentações, **importações CSV**, acessos negados (403) |
| 5 | Download/exportação de arquivos | Precedente: exportações CSV via StreamingResponse (Relação de Colaboradores etc.); nenhum download de arquivo binário hoje |
| 6 | Diretório de dados | `data/` (raiz do projeto, `DATA_DIR` em `app/config.py`) já existe e abriga `data/logs/` — padrão de artefatos de runtime do sistema |
| 7 | Interface consistente | Templates Jinja2 + Bootstrap 5, menu conforme permissões (Princípio X); central de ajuda `/ajuda` (help_service) |
| 8 | Testes | Suíte pytest com TestClient autenticado (`client` admin); padrão: rotas novas exigem autenticação + permissão |

**Consequências da análise**: trata-se de funcionalidade **nova** (não correção), que deve nascer aderente à arquitetura existente: service de negócio, rota web protegida por permissão própria, artefatos em `data/`, evento de auditoria via `write_audit` e documentação fiel (Princípios II, III, VI, IX, X, XI).

---

## 2. Problema e objetivo

### Problema

O sistema não oferece nenhum mecanismo de backup acionável pelo administrador: a proteção dos dados depende exclusivamente de procedimentos externos ao sistema, sem registro, sem rastreabilidade e sem artefatos consultáveis pelos administradores pela interface.

### Objetivo

Permitir que um administrador autorizado **gere manualmente um backup do estado atual do sistema**, armazene-o em local apropriado com identificação por data/hora, **consulte os backups disponíveis** com informações básicas do arquivo, **baixe** um backup quando permitido e tenha **cada operação registrada na Auditoria existente** — preservando integralmente o funcionamento atual do sistema.

---

## 3. User Scenarios & Testing

### User Story 1 — Gerar backup manualmente (Priority: P1) 🎯 MVP

Um administrador autorizado aciona, pela interface, a geração manual de um backup do estado atual do sistema. O sistema produz um arquivo de backup válido, armazena-o em local apropriado com identificação por data/hora e registra a operação na Auditoria.

**Why this priority**: É a função central — sem geração não há consulta nem download.

**Independent Test**: Usuário com permissão aciona a geração → arquivo criado em local apropriado, identificável por data/hora, com informações básicas consultáveis e evento na Auditoria.

**Acceptance Scenarios**:

1. **Given** um administrador autenticado e autorizado, **When** solicita a geração manual do backup, **Then** um arquivo de backup é criado em local apropriado, identificável por data/hora.
2. **Given** um backup recém-gerado, **When** o administrador consulta os backups disponíveis, **Then** o novo backup aparece na listagem com informações básicas do arquivo.
3. **Given** qualquer geração de backup (bem-sucedida ou falha), **When** a operação ocorre, **Then** um evento é registrado na Auditoria existente com o resultado.

### User Story 2 — Listar e consultar backups (Priority: P1)

**Independent Test**: Após gerar 2+ backups, a listagem os apresenta ordenados por data/hora com informações básicas do arquivo.

**Acceptance Scenarios**:

1. **Given** backups armazenados, **When** o administrador acessa a listagem, **Then** cada backup apresenta identificação por data/hora e informações básicas do arquivo (tamanho; demais metadados conforme Edge Cases).
2. **Given** a listagem, **When** ordenada, **Then** os backups mais recentes aparecem primeiro.
3. **Given** um usuário autenticado **sem** a permissão de backup, **When** tenta acessar geração/listagem/download, **Then** o acesso é negado (RBAC deny-by-default) e o acesso negado é auditado (comportamento existente de 403).

### User Story 3 — Baixar backup (Priority: P2)

**Independent Test**: Backup existente é baixado com o conteúdo do arquivo armazenado; tentativa de baixar arquivo inexistente resulta em erro adequado (404).

**Acceptance Scenarios**:

1. **Given** um backup armazenado, **When** o administrador solicita o download, **Then** o arquivo é servido com o conteúdo armazenado.
2. **Given** um identificador inexistente, **When** o download é solicitado, **Then** o sistema responde com erro adequado (404), sem expor caminhos internos.

### User Story 4 — Segurança e rastreabilidade (Priority: P2)

**Independent Test**: Todas as rotas exigem autenticação + permissão; eventos de auditoria contêm resultado e metadados sem credenciais.

**Acceptance Scenarios**:

1. **Given** qualquer rota da funcionalidade, **When** acessada sem autenticação, **Then** é exigido login (comportamento existente).
2. **Given** uma operação de backup bem-sucedida, **When** registrada na Auditoria, **Then** o evento identifica a ação, o operador e o resultado (sem credenciais — Princípio VI).
3. **Given** uma falha na geração (ex.: disco indisponível), **When** registrada na Auditoria, **Then** o evento registra a falha com mensagem de erro apropriada.

---

## 4. Edge Cases

- **Falha de disco/espaço insuficiente**: a geração falha de forma controlada — erro apropriado ao usuário + evento de auditoria da falha; nenhum artefato parcial é apresentado como backup válido.
- **Gerações repetidas em sequência**: cada geração produz um artefato distinto (identificação por data/hora; precisão suficiente para não colidir, conforme §5).
- **Usuário não autorizado**: nenhuma ação é possível (deny-by-default); acesso negado auditado (mecanismo existente).
- **Download de arquivo inexistente/removido**: erro 404 sem expor caminhos internos do servidor.
- **Artefatos alheios no diretório de backup**: a listagem deve considerar apenas artefatos reconhecíveis como backups desta funcionalidade (padrão de nome próprio).
- **Sem autenticação**: todas as rotas exigem login (Princípio VI).
- **Limites do mecanismo**: o escopo desta feature é o **backup manual** (não agendado); restauração e políticas de retenção ficam fora (Seção 8), conforme briefing.

## 5. Requirements

### Functional Requirements

- **FR-001**: O sistema DEVE permitir que um usuário autorizado inicie manualmente a geração de um backup do estado atual do sistema (AC-01).
- **FR-002**: A geração DEVE produzir um arquivo de backup válido (contendo o estado atual do sistema) — AC-02; o formato mínimo aceitável é o dump consistente do banco de dados do sistema; o empacotamento adicional de artefatos segue o briefing (Seção 11).
- **FR-003**: O backup DEVE ser armazenado em local apropriado do servidor (repositório dedicado no diretório de dados do sistema, fora dos artefatos de runtime existentes) — AC-03.
- **FR-004**: Cada backup DEVE ser identificável por data/hora de geração (AC-04); a precisão do nome deve ser suficiente para não colidir em gerações repetidas na mesma operação (Edge Cases).
- **FR-005**: O sistema DEVE apresentar a listagem dos backups disponíveis, com informações básicas do arquivo — AC-05/AC-06: identificação por data/hora e tamanho (metadados adicionais, ex. número de registros, somente se tecnicamente viável — ver Seção 11).
- **FR-006**: A listagem DEVE permitir baixar um backup quando permitido (usuário autorizado; arquivo existente) — AC-07.
- **FR-007**: Toda operação de backup (geração; falha; download) DEVE ser registrada na Auditoria existente via mecanismo padrão, sem credenciais (AC-08; Princípio IX).
- **FR-008**: Toda a funcionalidade DEVE estar protegida por autenticação e por permissão RBAC **nova e específica** de backup (deny-by-default), seguindo o padrão `modulo.acao` existente — AC-09 (Princípio VI).
- **FR-009**: A funcionalidade DEVE preservar integralmente o funcionamento atual do sistema: nenhuma alteração de comportamento, dados ou telas existentes (AC-10).
- **FR-010**: A interface DEVE seguir os padrões visuais e de navegação existentes (administração, menu conforme permissões, 403/404 amigáveis) — Princípio X.
- **FR-011**: A documentação (README e central de ajuda embutida) DEVE ser atualizada de forma fiel: o que o backup contém, como gerar, listar e baixar, onde os arquivos ficam e as limitações do mecanismo (Princípio XI).
- **FR-012**: Testes automatizados DEVEM cobrir: geração (arquivo criado + identificação por data/hora), listagem, download (conteúdo correto), 404 de arquivo inexistente, RBAC (negado sem permissão; permitido com permissão) e auditoria da geração — AC-01..AC-10.

### Regras (síntese operacional)

- R1 — Backup é ação **manual e explícita** de usuário autorizado; nada é automático/agendado nesta feature.
- R2 — Todo backup é identificável por data/hora e consultável na listagem.
- R3 — Toda operação deixa rastro na Auditoria existente (sucesso e falha), sem credenciais.
- R4 — Acesso negado por padrão: só quem tem a permissão específica de backup age (Princípio VI).

## Key Entities

- **Backup (artefato de runtime)**: arquivo gerado pela funcionalidade, identificado por data/hora, com informações básicas consultáveis (tamanho; demais metadados conforme viabilidade técnica). Persistência como registros de banco NÃO é requisito — a listagem pode derivar do repositório de arquivos (decisão de design no plan; ver Seção 11).
- **Permissão RBAC**: nova permissão específica de backup no padrão `modulo.acao` do vocabulário existente, concedida somente a perfis que devem operar backups.
- **Evento de auditoria**: registro na trilha `audit_logs` existente para cada operação de backup (geração/falha/download) via `write_audit`.

## 6. Critérios de Aceitação (rastreabilidade)

| AC | Enunciado (objetivo do briefing) | Coberto por |
|---|---|---|
| AC-01 | Administrador autorizado inicia manualmente um backup | US1/AS1; FR-001 |
| AC-02 | Geração produz um arquivo de backup válido | US1/AS1; FR-002 |
| AC-03 | Backup armazenado em local apropriado | US1/AS1; FR-003 |
| AC-04 | Backup identificável por data/hora | US1/AS2; FR-004 |
| AC-05 | Visualizar os backups disponíveis | US2/AS1; FR-005 |
| AC-06 | Verificar informações básicas do arquivo | US2/AS1; FR-005 |
| AC-07 | Baixar um backup quando permitido | US3/AS1; FR-006 |
| AC-08 | Operação registrada na Auditoria existente | US1/AS3, US4/AS2-3; FR-007 |
| AC-09 | Acesso protegido (RBAC deny-by-default) | US2/AS3, US4/AS1; FR-008 |
| AC-10 | Funcionamento atual preservado integralmente | US4; FR-009 |

### Cenários de teste do briefing (mapa)

| # | Cenário | Onde |
|---|---|---|
| 1 | Administrador autorizado gera backup com sucesso | US1/AS1; US4/AS2 |
| 2 | Listagem apresenta backups com data/hora e tamanho | US2/AS1-2 |
| 3 | Download serve o conteúdo armazenado; inexistente → 404 | US3/AS1-2 |
| 4 | Sem permissão: geração/listagem/download negados e auditados | US2/AS3; US4/AS1 |
| 5 | Falha de geração → erro controlado + auditoria da falha | US4/AS3; Edge Cases |

---

## 7. Success Criteria

- **SC-001**: Um administrador autorizado conclui uma geração manual de backup em uma única operação pela interface, recebendo confirmação clara do resultado.
- **SC-002**: 100% dos backups gerados aparecem na listagem com data/hora e tamanho, ordenados do mais recente para o mais antigo.
- **SC-003**: O download de um backup retorna exatamente o conteúdo do arquivo armazenado (verificável por integridade no teste).
- **SC-004**: 100% das operações de backup (geração/falha/download) possuem evento correspondente na Auditoria.
- **SC-005**: Zero alteração de comportamento nas funcionalidades existentes (suíte completa verde; único gate da suíte).
- **SC-006**: Nenhum usuário sem a permissão específica consegue acionar qualquer operação de backup (verificado por testes RBAC).

---

## 8. Escopo

### Incluído

- Geração manual de backup do estado atual do sistema (usuário autorizado, via interface);
- Armazenamento em repositório dedicado no diretório de dados do sistema;
- Identificação por data/hora; listagem com informações básicas (data/hora, tamanho);
- Download de backup por usuário autorizado;
- Registro das operações na Auditoria existente;
- Permissão RBAC nova e específica; interface nos padrões existentes;
- Documentação fiel (README + ajuda embutida); testes automatizados.

### Não incluído (limites de escopo)

- Backup automático/agendado (cron, timer de aplicação) — a periodicidade continua sendo política operacional do servidor;
- **Restauração** de backup (fluxo de restore) — fora do briefing;
- Políticas de retenção/rotação/limpeza automática de backups antigos;
- Upload de backup para armazenamento externo/nuvem;
- Backup dos arquivos de log ou de artefatos do sistema de arquivos além do previsto no briefing (Seção 11);
- Alterações em qualquer funcionalidade, tela, permissão ou consulta existente (além do acréscimo aditivo do novo item de menu e da nova permissão).

---

## 9. Casos de erro (comportamento definido)

| Situação | Comportamento |
|---|---|
| Usuário sem permissão aciona qualquer operação | Acesso negado (403, deny-by-default) + auditoria do acesso negado (mecanismo existente) |
| Falha de disco/espaço na geração | Erro controlado ao usuário + auditoria da falha; nenhum artefato parcial apresentado como backup válido |
| Download de arquivo inexistente/removido | 404 amigável, sem exposição de caminhos internos |
| Gerações em sequência rápida | Artefatos distintos (precisão de data/hora suficiente; Edge Cases) |
| Artefato não reconhecível no repositório | Ignorado pela listagem (considera só o padrão de nome próprio) |

---

## 10. Premissas e dependências

- A permissão nova será concedida ao perfil administrativo existente (e a qualquer outro perfil que o administrador desejar, pela gestão de permissões atual).
- O repositório de backups fica no diretório de dados do sistema (`data/`), seguindo o padrão de artefatos de runtime já existente (`data/logs/`).
- O mecanismo de dump do banco é o utilitário/tecnologia do próprio banco de produção (MariaDB/MySQL), executado pela aplicação; a viabilidade técnica detalhada será confirmada no plan (research).
- A listagem deriva do repositório de arquivos (sem tabela nova), respeitando "não criar nova estrutura no banco sem necessidade" — confirmação no plan.

---

## 11. Impacto esperado (componentes confirmados pela análise — nada inventado)

| Arquivo/Componente | Alteração esperada |
|---|---|
| `app/services/` | **NOVO** service de backup (regras de geração, listagem, download e auditoria — Princípios II/III) |
| `app/web/` | **NOVA** rota(s) web protegida(s) pela permissão nova (geração, listagem, download) + template(s) novo(s) nos padrões existentes; acréscimo de item de menu conforme permissões |
| Permissão | **NOVA** permissão `modulo.acao` específica de backup, integrada ao vocabulário/seed existente |
| Auditoria | Uso do `audit_service.write_audit` existente para os eventos da funcionalidade |
| `data/` | Repositório dedicado para os arquivos de backup (padrão `data/logs/`) |
| Documentação | README (seção 💾) + central de ajuda embutida |
| Testes | **NOVO** módulo de testes da funcionalidade |

**Definição de "estado atual do sistema" (a detalhar no plan)**: no mínimo, dump consistente do banco de dados de produção; o briefing indica o mecanismo de backup do MariaDB/MySQL como o esperado. O empacotamento de artefatos adicionais (ex.: logs) não é requisito e será decidido no plan com base em viabilidade — a spec NÃO obriga inclusão de arquivos além do banco.

---

*Esta especificação segue o fluxo Spec Kit (specify → plan → tasks → implement). Nada foi implementado nesta etapa; os componentes listados na Seção 11 derivam exclusivamente da análise de código verificada.*
