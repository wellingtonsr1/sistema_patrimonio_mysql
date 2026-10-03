# Feature Specification: Auditoria e padronização do ecossistema SisPatrimônio Pro (dev × produção × instaladores × HTTPS × MariaDB/MySQL)

**Feature Branch**: `061-auditoria-padronizacao-ecossistema`

**Created**: 2026-10-02

**Status**: Draft

**Input**: Prompt estruturado do responsável: criar spec de auditoria, correção e padronização de todo o ecossistema (desenvolvimento `sistema_patrimonio_mysql`, produção `SisPatrimonioPro`, instaladores Linux/Windows, deploy `deploy.sh`/`deploy.bat`), garantindo MariaDB (Linux) e MySQL Server nativo (Windows, sem XAMPP) e HTTPS funcionando em todos os cenários — diagnosticando antes de alterar, com alterações mínimas, cirúrgicas e necessárias.

## Regra fundamental

> **O ambiente de desenvolvimento `sistema_patrimonio_mysql` já funciona e é a referência funcional principal.** Nenhuma alteração indiscriminada é permitida. A Fase 1 (Diagnóstico) é somente leitura; somente depois da análise completa são propostas alterações, sempre mínimas, cirúrgicas e limitadas ao que o diagnóstico comprovar necessário (Constitution I — preservação do sistema existente, evolução incremental).

## Realidade verificada (somente leitura, 2026-10-02)

*Observado diretamente antes de escrever esta spec; a implementação DEVE reconfirmar tudo na época da execução, não presumir.*

1. **Este repositório é a dev**: `origin = git@github.com:wellingtonsr1/sistema_patrimonio_mysql.git`, branch `main`. O diretório `SisPatrimonioPro` é um repositório GitHub separado (`git@github.com:wellingtonsr1/SisPatrimonioPro.git`), não presente no workspace atual.
2. **Fluxo de deploy real** (documentado nos próprios scripts `deploy.sh`/`deploy.bat`, com paridade Linux/Windows pretendida): (1) commit local na dev; (2) push do histórico completo → GitHub da dev; (3) snapshot filtrado por **whitelist** (via `git archive`) → branch `main` do `SisPatrimonioPro`, com subcomandos `pre`, `historico` e `rollback` (rollback usa hash da dev citado na mensagem do snapshot). As duas whitelists (`.sh` e `.bat`) precisam de auditoria de equivalência.
3. **Instalador Linux** existe (`install.sh` na raiz, spec 027): Debian/Ubuntu, MariaDB, systemd, idempotente, banco existente nunca apagado (`--recreate-db` com dupla confirmação interativa e proibido em modo não interativo). HTTPS foi deliberadamente **fora do escopo** da 027 (decisão D4) — produção inicial em HTTP na rede interna.
4. **HTTPS de referência** (spec 056): SSL **nativo no Uvicorn** (`APP_SSL_CERTFILE`/`APP_SSL_KEYFILE`), CA local + certificado de servidor com SAN (`IP:<ip-lan>`, `DNS:localhost`, `DNS:sispatrimoniopro.local`) gerados em `data/ssl/` (fora do versionamento); sem proxy reverso; **redirect HTTP→HTTPS explicitamente não implementado** na 056 (decisão do operador) — esta spec revisita essa decisão para instalação/produção (ver D-002).
5. **`install.bat` não existe na raiz atual** — a existência, localização e conteúdo de um instalador Windows é fato a confirmar na Fase 1 (o relato do operador indica que um processo de instalação Windows existe e consome o PRO). **Atualização (clarify, 2026-10-02)**: o responsável confirmou que o instalador Windows **existe e está versionado** (PRO ou dev) — a Fase 1 o localiza. **Atualização (plan, 2026-10-02)**: localizado — há um **terceiro repositório** `SisPatrimonioPro-install` (`install no windows/nativa/install.ps1`, PowerShell, 982 linhas, serviço via Tarefa Agendada, firewall já previsto; **sem nenhuma configuração de SSL/certificado** — causa provável nº 1 da perda do HTTPS, a confirmar na Fase 1).
6. **Baseline funcional a descobrir**: o HTTPS funciona na dev Windows atual — quais arquivos, variáveis, certificados e serviços produzem esse funcionamento é o inventário central da Fase 1.

## Clarifications

### Session 2026-10-02

- Q: Quando o HTTPS estiver ativo na instalação/produção, quais portas o sistema deve usar? → A: **porta 8000** — TLS na própria porta da aplicação (`APP_PORT`), modelo nativo da 056, sem porta HTTP separada no mesmo processo.
- Q: Com o HTTPS ativo na porta 8000, o que acontece com acessos via `http://...:8000`? → A: **sem redirect nativo** — mantém a política da 056 (o cliente recebe falha de handshake); redirect externo (proxy/roteador) permanece opção documentada, fora da aplicação.
- Q: Existe hoje algum instalador Windows em uso (script/rotina que instala a partir do repositório de produção)? → A: **sim — existe e está versionado** (no PRO ou na dev); a Fase 1 o localiza/audita e a Fase 3 corrige a causa raiz nele.
- Q: Quando o HTTPS estiver ativo na instalação, o instalador deve configurar automaticamente o cookie de sessão como seguro (`AUTH_COOKIE_SECURE=true`)? → A: **sim** — o instalador grava no `.env` sempre que ativa o HTTPS (coerência TLS + cookie seguro; a dev sem HTTPS permanece como está).
- Q: Os instaladores devem abrir as portas necessárias no firewall automaticamente? → A: **sim** — abrem automaticamente regra nomeada e idempotente (ex.: "SisPatrimonioPro HTTPS 8000"), apenas para as portas da aplicação, sem tocar em outras regras; sem privilégio, falham com orientação clara.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Diagnóstico completo e baseline, sem alterar nada (Priority: P1)

O responsável pelo projeto solicita uma auditoria do ecossistema. A equipe/agente realiza um diagnóstico **exclusivamente de leitura**: inventário da arquitetura real (dev, PRO, deploy, instaladores), rastreamento de todas as configurações de banco e de HTTPS, comparação integral `sistema_patrimonio_mysql` × `SisPatrimonioPro` × resultado da instalação Windows, classificação de cada divergência (intencional / necessária / obsoleta / erro / risco de produção), execução da suíte de testes existente para registrar o baseline, e investigação com causa raiz de por que o HTTPS funciona na dev mas não é preservado/ativado na instalação Windows. O resultado é um relatório de diagnóstico (Entregável A) com causas prováveis e confirmadas — **nenhum arquivo é modificado** nesta fase.

**Why this priority**: é o gate de toda a feature — sem diagnóstico confirmado, qualquer alteração viola a regra fundamental e arrisca quebrar o que já funciona (Constitution I).

**Independent Test**: pode ser validado sozinho verificando que (a) o relatório existe e cobre todos os itens do escopo obrigatório, (b) `git status` está limpo após a fase (nenhuma alteração), (c) o baseline de testes está registrado com resultado, e (d) cada causa apontada para a perda do HTTPS no Windows está evidenciada por arquivo/linha ou teste reprodutível.

**Acceptance Scenarios**:

1. **Given** o ecossistema atual, **When** a Fase 1 é concluída, **Then** existe relatório com: arquitetura atual, fluxo de deploy real (verificado, não presumido), fluxo de instalação, fluxo do banco, fluxo HTTPS completo, divergências dev×PRO classificadas uma a uma, problemas encontrados, causas prováveis e confirmadas.
2. **Given** o relato de HTTPS perdido na instalação Windows, **When** o diagnóstico rastreia o caminho (certificado → geração → armazenamento → inicialização do servidor → serviço), **Then** o ponto exato em que a configuração HTTPS é perdida está identificado com evidência (arquivo/configuração/execução), distinguido de causas apenas prováveis.
3. **Given** a suíte de testes existente, **When** o baseline é registrado, **Then** o resultado (aprovados/falhos) está anotado no relatório e serve de referência para comparação pós-alteração.
4. **Given** a Fase 1 concluída, **When** o workspace é inspecionado, **Then** nenhum arquivo funcional foi modificado (`git status` limpo).

---

### User Story 2 - HTTPS sobrevive à instalação no Windows (Priority: P1)

O administrador instala o sistema em um Windows com MySQL Server nativo usando o instalador. Ao final, o sistema é acessível via HTTPS exatamente como na dev: mesma estratégia de TLS (baseline 056), certificado com SAN coerente com o hostname/IP da máquina, CA instalável nos clientes, e o acesso `http://servidor:8000` tratado conforme a política HTTPS da aplicação (sem redirect nativo — decisão D-002). O HTTPS continua funcionando após reinicialização do servidor, reinício do serviço, atualização e reinstalação — sem depender de ajuste manual esquecido ou específico de uma máquina.

**Why this priority**: é a dor central relatada — a configuração funcional existe na dev e se perde no processo de instalação Windows; reproduzi-la fielmente é o objetivo principal (regra especial §21 do briefing).

**Independent Test**: em uma máquina Windows de teste, executar o instalador e validar HTTPS (página abre via `https://` com cadeia validada em cliente com a CA instalada); repetir após reboot do servidor, reinício do serviço, atualização e reinstalação — HTTPS permanece em todos.

**Acceptance Scenarios**:

1. **Given** instalação limpa no Windows com MySQL nativo, **When** o instalador termina, **Then** o sistema responde via HTTPS com o certificado associado ao hostname/IP da máquina (SAN válido) sem configuração manual pós-instalação.
2. **Given** o servidor Windows reiniciado, **When** o serviço sobe automaticamente, **Then** o HTTPS volta a funcionar sem intervenção (certificado/chave no mesmo lugar, serviço referenciando-os corretamente).
3. **Given** uma atualização ou reinstalação sobre instalação existente, **When** o processo termina, **Then** o HTTPS permanece configurado e os certificados existentes não são invalidados/apagados sem motivo documentado.
4. **Given** `http://servidor:8000`, **When** o acesso é feito com HTTPS ativo, **Then** o cliente recebe falha de handshake (política da aplicação: sem redirect nativo — decisão D-002), sem estados de erro confusos causados pelo serviço.
5. **Given** a causa raiz corrigida, **When** o mecanismo HTTPS é comparado entre dev e instalação Windows, **Then** é o mesmo mecanismo (baseline da dev reproduzido), sem segunda implementação paralela.

---

### User Story 3 - Windows com MySQL Server nativo, sem XAMPP (Priority: P1)

O administrador com um Windows sem XAMPP (ou onde o XAMPP será descontinuado) instala/executa o sistema apoiado apenas no **MySQL Server nativo**. O instalador detecta MySQL já instalado (versão, serviço), inicia/valida o serviço, testa a conexão, cria banco/usuário somente quando faltarem, e valida credenciais, schema e aplicação. Toda dependência real de XAMPP no código/scripts/instalador é identificada no diagnóstico e substituída pela solução nativa; referências históricas/documentationais são atualizadas sem destruir contexto útil.

**Why this priority**: elimina a dependência acidental de terceiros (XAMPP) que torna a instalação Windows não reproduzível; é pré-condição da US2 (o HTTPS Windows precisa conviver com o MySQL nativo).

**Independent Test**: em máquina Windows sem XAMPP, com MySQL Server nativo, executar instalação e validação completa (banco, sistema, HTTPS) sem que qualquer etapa exija XAMPP.

**Acceptance Scenarios**:

1. **Given** Windows sem XAMPP e com MySQL Server nativo, **When** o instalador roda, **Then** detecta o serviço MySQL, valida versão/estado, inicia se parado, testa conexão e prossegue sem nenhuma etapa XAMPP.
2. **Given** referências a XAMPP inventariadas, **When** cada uma é tratada, **Then** apenas as que constituem dependência real são substituídas — e cada substituição está justificada no relatório (nenhuma remoção às cegas).
3. **Given** a instalação concluída, **When** o sistema é validado, **Then** banco, aplicação, serviço e HTTPS funcionam apenas com MySQL nativo (arquitetura `Windows → MySQL Server nativo → SisPatrimônio Pro`).
4. **Given** a faixa de versões de MySQL, **When** o diagnóstico a determina, **Then** a versão mínima suportada e compatibilidades estão documentadas (e versões incompatíveis produzem mensagem clara do instalador).

---

### User Story 4 - Deploy reproduzível e PRO consistente com a dev (Priority: P2)

O mantenedor publica uma alteração a partir do Linux (`deploy.sh`) ou do Windows (`deploy.bat`). Em ambos os casos: o commit/push da dev ocorre corretamente com tratamento de erros, e o snapshot publicado no `SisPatrimonioPro` contém tudo que a produção precisa, nada gerado localmente indevido, e é **equivalente para a mesma dev independentemente do SO que publica** (whitelists equivalentes, line endings e caminhos tratados). Divergências residuais dev×PRO são intencionais e documentadas.

**Why this priority**: o PRO é a fonte do instalador — inconsistência aqui contamina toda instalação; mas depende do diagnóstico (US1) para saber o que é intencional.

**Independent Test**: a partir da mesma dev commitada, gerar o snapshot pelos dois scripts (ou comparar a whitelist dos dois) e verificar equivalência; auditar o snapshot contra a lista do que a produção precisa.

**Acceptance Scenarios**:

1. **Given** a mesma dev commitada, **When** o snapshot é gerado por `deploy.sh` e por `deploy.bat`, **Then** os conteúdos publicados são equivalentes (mesmos arquivos, line endings tratados).
2. **Given** o snapshot publicado, **When** ele é comparado com a dev, **Then** cada diferença é classificada (intencional/necessária/obsoleta/erro/risco) e nenhuma diferença acidental permanece.
3. **Given** arquivos gerados localmente (venv, `data/`, certificados privados, logs, `.env`), **When** o snapshot é gerado, **Then** nada indevido é incluído; e nada necessário para produção é omitido.
4. **Given** falha em qualquer etapa do deploy, **When** o erro ocorre, **Then** o script para com mensagem clara e estado consistente (sem publicar snapshot parcial).

---

### User Story 5 - Paridade MariaDB × MySQL sem editar código (Priority: P2)

O mesmo código-fonte executa em Linux + MariaDB e Windows + MySQL apenas mudando configuração (variáveis de ambiente/`.env`). A `DATABASE_URL` é montada corretamente nos dois bancos (driver PyMySQL, percent-encoding de senha com caracteres especiais, host/porta/banco) por scripts, instaladores e aplicação. A matriz de compatibilidade MariaDB×MySQL é preenchida com análise real (não inventada) e todo achado de incompatibilidade recebe tratamento documentado.

**Why this priority**: garante a meta "mesma base de código/configuração" nos 4 cenários; começa no diagnóstico (auditoria completa da camada de banco) e se materializa em correções mínimas.

**Independent Test**: com a mesma aplicação, apontar para MariaDB (Linux) e para MySQL (Windows) apenas via configuração e validar funcionamento equivalente (schema, operações, backup/restore quando aplicável).

**Acceptance Scenarios**:

1. **Given** a aplicação, **When** conectada a MariaDB e a MySQL com o driver estabelecido, **Then** o comportamento é equivalente (criação de schema idempotente, operações, transações) sem edição de código entre ambientes.
2. **Given** senha de banco com caracteres especiais, **When** a `DATABASE_URL` é montada por qualquer script/instalador, **Then** o percent-encoding é aplicado programaticamente e a conexão funciona.
3. **Given** a matriz de compatibilidade preenchida, **When** cada célula é verificada, **Then** reflete análise real do código (SQLAlchemy/PyMySQL/DDL/tipos/transações/pool/charset/collation), com achados de incompatibilidade tratados ou registrados.

---

### User Story 6 - Instaladores idempotentes, seguros e documentação fiel (Priority: P3)

O administrador reexecuta os instaladores (Linux e Windows) sobre uma instalação existente: banco e dados nunca são apagados/recriados sem ação explícita (política atual preservada), `.env` existente não é sobrescrito silenciosamente, nenhuma credencial aparece em logs/argv/saída de comandos, e a documentação reflete a arquitetura final sem instruções XAMPP obsoletas (arquitetura, bancos, requisitos por SO, instalação, atualização, HTTPS, certificados, deploy, recuperação de erro, troubleshooting).

**Why this priority**: fecha o ciclo com segurança e sustentabilidade; não bloqueia as USs anteriores, mas é indispensável para o critério de conclusão.

**Independent Test**: executar cada instalador duas vezes seguidas; conferir que dados/configurações permanecem, logs não contêm segredos, e a documentação corresponde ao comportamento real observado.

**Acceptance Scenarios**:

1. **Given** instalação existente com dados, **When** o instalador é executado novamente, **Then** banco/usuários/dados são preservados e apenas o que falta é completado (idempotência).
2. **Given** qualquer execução de instalador ou deploy, **When** logs, comandos e saídas são inspecionados, **Then** nenhuma senha/segredo/chave privada aparece.
3. **Given** a documentação final, **When** cada procedimento é seguido, **Then** corresponde ao comportamento real (Constitution XI) e não existe instrução operacional de XAMPP.

---

### Edge Cases

- Senha do MySQL/MariaDB com caracteres especiais (`@`, `#`, `/`, `%`) quebrando a `DATABASE_URL` montada manualmente em algum script/instalador.
- Banco já existente com dados reais durante atualização/reinstalação — nenhuma operação destrutiva pode ocorrer (nem `DROP`, nem recriação silenciosa).
- Certificado expirado ou hostname/IP da máquina alterado após a instalação (SAN não bate mais) — comportamento esperado e roteiro de regeneração documentados.
- MySQL já instalado no Windows com versão incompatível ou serviço parado/quebrado — detecção clara em vez de falha sigilosa.
- Porta da aplicação/porta do banco em uso por outro processo — diagnóstico e mensagem específica.
- `deploy` executado com árvore suja ou dev à frente/atrás do GitHub — comportamento definido (avisar/abortar), consistente entre `.sh` e `.bat`.
- Arquivo necessário à produção ausente da whitelist do deploy (regressão de conteúdo) — detecção por comparação dev×snapshot.
- Chave privada/certificado em local diferente do esperado pelo serviço após instalação (permissões, caminhos com espaço, caminho relativo × absoluto).
- Firewall bloqueando a porta HTTPS — o instalador abre a regra automaticamente (idempotente); se não puder (falta de privilégio), falha com orientação clara em vez de deixar o sistema "instalado e inacessível".
- Acesso `http://` (sem o `https://`) à porta 8000 com TLS ativo — falha de handshake é o comportamento esperado e documentado (sem redirect nativo; opção de redirect externo registrada).
- Line endings (CRLF/LF) e caminhos Windows/Linux quebrando scripts publicados no snapshot PRO.
- SQLite residual: apenas em testes, nunca como fallback da aplicação (Constitution VII) — verificar se nenhum caminho de instalação o introduz.
- `.env` com valores parcialmente preenchidos na reinstalação — nunca apagar valores existentes sem confirmação.

## Requirements *(mandatory)*

### Diagnóstico e processo (Fases 1–5)

- **FR-001**: A Fase 1 (Diagnóstico) MUST preceder qualquer alteração funcional e produzir o relatório de diagnóstico (Entregável A: arquitetura atual, fluxos de deploy/instalação/banco/HTTPS, divergências classificadas, problemas, causas prováveis e confirmadas) **sem modificar nenhum arquivo do projeto**.
- **FR-002**: O diagnóstico MUST tratar `sistema_patrimonio_mysql` como baseline funcional — inventariando exatamente o que faz banco, deploy e HTTPS funcionarem (arquivos, variáveis, scripts, certificados, serviços) — e comparar esse baseline com `SisPatrimonioPro` e com o resultado da instalação Windows.
- **FR-003**: A suíte de testes existente MUST ser executada antes (baseline) e depois de cada lote de alterações, com resultados registrados e comparados; regressão silenciosa não é aceitável (Constitution VIII).
- **FR-004**: A Fase 2 (Planejamento) MUST listar os arquivos a **Alterar/Criar/Remover/Não alterar** com justificativa técnica; a Fase 3 (Implementação) MUST aplicar somente essas mudanças, mínimas e cirúrgicas; nenhuma refatoração/correção não relacionada é permitida (Constitution I).
- **FR-005**: O diagnóstico MUST usar os comandos apropriados ao ambiente real (`git status/branch/remote/log/diff`, buscas por `xampp`, `mysql`, `mariadb`, `DATABASE_URL`, `pymysql`, `https/ssl/tls/cert`, `uvicorn`, `nginx/apache/systemd`; no Windows `Get-Service`, `mysql --version`, `where.exe mysql`; no Linux `systemctl`, `mariadb --version`, `which mysql`), adaptados ao que for encontrado.

### Banco de dados e DATABASE_URL

- **FR-006**: A camada de banco MUST ser auditada integralmente: SQLAlchemy (engine, conexão, pool, transações, commits/rollback), `DATABASE_URL` (todos os pontos de montagem: aplicação, scripts `.sh`/`.bat`, instaladores), driver, charset/collation, timezone, criação/alteração de schema, índices, constraints, tipos (datetime, boolean, enum), `AUTO_INCREMENT`, e o SQL executado em instalação/inicialização — registrando tudo que for específico de um banco.
- **FR-007**: A matriz de compatibilidade MariaDB × MySQL (Entregável B) MUST ser preenchida **a partir da análise real do código** (driver, SQLAlchemy, PyMySQL, CREATE/ALTER TABLE, índices, constraints, datetime, boolean, enum, JSON, transações, pool, charset, collation) — compatibilidade não verificada não pode ser afirmada.
- **FR-008**: Todo código que assumir comportamento exclusivo de MySQL ou de MariaDB MUST ser identificado na matriz e receber tratamento compatível com os dois bancos (ou registro explícito de limitação, com aprovação).
- **FR-009**: A mesma base de código MUST funcionar com `mariadb+pymysql` e `mysql+pymysql` apenas por configuração (variáveis de ambiente/`.env`), sem editar código da aplicação ao trocar de banco.
- **FR-010**: A montagem da `DATABASE_URL` MUST tratar corretamente usuário, senha (percent-encoding de caracteres especiais), host, porta, banco, driver e ambiente (Windows/Linux, instalação), de forma padronizada e segura — sem montagem manual duplicada em múltiplos pontos.
- **FR-011**: O SQL executado na instalação/inicialização MUST permanecer idempotente e aditivo; nenhuma migração destrutiva automática; dados existentes são intocáveis (Constitution VII).

### XAMPP e Windows nativo

- **FR-012**: Todas as referências a XAMPP (`xampp`, `XAMPP`, `C:\xampp`, `mysql\bin`, Apache do XAMPP) MUST ser inventariadas com local e propósito, e classificadas como: necessária / histórica / usada por instalador / usada por scripts / usada por testes / documentação / controle de serviço de banco. **Somente** referências que constituem dependência real são substituídas — remoção sem compreensão do propósito é proibida.
- **FR-013**: O resultado Windows MUST ser a arquitetura `Windows → MySQL Server nativo → SisPatrimônio Pro` (nunca via XAMPP); o instalador Windows MUST detectar MySQL já instalado (versão/serviço), iniciar o serviço quando parado, validar conexão, criar banco/usuário somente quando faltarem, testar credenciais/schema/aplicação, e documentar a faixa de versões de MySQL suportada.

### Deploy e sincronização dev → PRO

- **FR-014**: `deploy.sh` e `deploy.bat` MUST ser auditados integralmente (git/branch/commit/push, ordem das operações, tratamento de erros, whitelist de inclusão/exclusão, arquivos temporários/gerados, arquivos de ambiente, certificados, permissões, line endings, caminhos, divergências de branches) e o fluxo real documentado como verificado — caso a arquitetura real difira de `dev → commit → GitHub → SisPatrimonioPro → instalador → produção`, o fluxo real é o documentado.
- **FR-015**: O snapshot publicado no PRO MUST conter tudo que a produção precisa, nada gerado localmente indevido, e as whitelists dos dois scripts MUST produzir conteúdo equivalente para a mesma dev (independente do SO que publica).
- **FR-016**: Toda diferença dev × PRO MUST ser enumerada e classificada (intencional/necessária/obsoleta/erro/risco de produção); diferenças acidentais são eliminadas e as intencionais documentadas (Entregável D).

### Instaladores

- **FR-017**: O instalador Linux (`install.sh`) MUST ser auditado integralmente (distribuição, Python, venv, pip, dependências, MariaDB, banco/usuário, `.env`, permissões, systemd, usuário/diretórios/logs, firewall, certificados, HTTPS, HTTP→HTTPS, hostname/IP, portas, Uvicorn, proxy) e permanecer idempotente: reexecução NÃO destrói instalação/banco sem autorização explícita (política atual de preservação de dados mantida).
- **FR-018**: O instalador Windows MUST ser auditado integralmente (Python, venv, dependências, MySQL Server, banco/usuário/permissões, `.env`, serviço, firewall, certificados, HTTPS, hostname/IP, portas, HTTP/HTTPS/redirecionamento, Uvicorn, proxy, armazenamento e permissões da chave privada) e a **causa raiz** da perda do HTTPS MUST ser identificada e corrigida — sem solução superficial.
- **FR-019**: O instalador Windows versionado (existência confirmada pelo responsável em 2026-10-02; localização exata a confirmar na Fase 1) MUST ser auditado e corrigido; somente se a auditoria concluir inadequação estrutural é que um novo MUST ser criado alinhado ao fluxo real, sem arquitetura paralela.
- **FR-020**: Ambos os instaladores MUST aplicar a mesma base de código/configuração compatível com MariaDB e MySQL e NÃO podem depender de configuração manual específica de máquina nem de etapas esquecidas fora do script. Quando o instalador ativa o HTTPS, ele MUST também gravar `AUTH_COOKIE_SECURE=true` no `.env` (segurança por padrão; a dev, que roda sem envs de TLS por padrão, permanece inalterada). Os instaladores MUST ainda abrir automaticamente as portas necessárias no firewall (regra nomeada e idempotente, ex.: "SisPatrimonioPro HTTPS 8000"), apenas para as portas da aplicação — sem alterar outras regras; sem privilégio suficiente, falham com orientação clara.

### HTTPS e certificados

- **FR-021**: O mecanismo HTTPS funcional da dev MUST ser documentado como **baseline funcional**: onde certificado/chave vivem, quem gera, quem instala, quem inicia HTTPS, quem termina TLS (aplicação vs proxy), como HTTP é tratado, como portas/firewall são abertas, como hostname/IP são determinados e associados ao SAN, e como isso difere entre Linux e Windows.
- **FR-022**: A configuração HTTPS funcional da dev MUST ser corretamente reproduzida pelo processo de instalação (Linux e Windows) — **reutilizando a implementação existente adequada** (não criar segunda implementação de HTTPS) — e o HTTPS MUST sobreviver a: instalação, reinicialização do servidor, reinício do serviço, atualização e reinstalação. Com HTTPS ativo, o TLS escuta na própria porta da aplicação (**porta 8000**, `APP_PORT`) — modelo nativo da 056, sem porta HTTP separada no mesmo processo.
- **FR-023**: Ao final, o acesso `http://servidor:8000` com HTTPS ativo segue a política da aplicação **sem redirect nativo** (mantém a 056): o cliente recebe falha de handshake (erro de conexão segura); redirect externo (proxy/roteador/firewall do cliente) pode ser documentado como opção, mas NÃO é implementado na aplicação (decisão D-002).
- **FR-024**: Certificados MUST ser auditados (CA, certificado do servidor, cadeia, formatos PEM/CRT/KEY, PFX/P12 se usado, armazenamento, permissões da chave privada, trust store do SO e dos navegadores quando aplicável) e a estratégia atual NÃO substituída automaticamente — primeiro compreender, depois propor.
- **FR-025**: Chaves privadas e certificados privados NUNCA vão ao Git (nem ao snapshot PRO); a verificação do `.gitignore`/whitelist quanto a `data/ssl/` e equivalentes é parte do diagnóstico.

### Segurança

- **FR-026**: Nenhum segredo (senhas, credenciais, tokens, `.env` de produção, chaves privadas) vai ao Git; os scripts de deploy/instalação são auditados contra exposição de segredos por: argumentos, logs, mensagens de erro, comandos executados, histórico do shell, saída do PowerShell e arquivos temporários (Constitution VI).

### Testes, validação e documentação

- **FR-027**: O plano de testes (Entregável F) MUST cobrir: dev Linux (MariaDB+HTTPS), dev Windows (MySQL+HTTPS), produção Linux (MariaDB+HTTPS), produção Windows (MySQL+HTTPS), instalação limpa, atualização sobre instalação existente, reinstalação sem perda indevida de dados, banco existente e banco inexistente — com comandos concretos para Linux e Windows.
- **FR-028**: A validação final (Fases 4–5) MUST provar o funcionamento integrado de: código + Git + deploy + produção + MariaDB + MySQL + instalador Linux + instalador Windows + HTTPS + certificados + serviço + persistência + atualização — "a aplicação abre", "o banco conecta" ou "o instalador termina sem erro" NÃO são critérios suficientes.
- **FR-029**: A documentação MUST ser atualizada somente onde necessário (arquitetura, MariaDB, MySQL, requisitos Windows/Linux, instalação, atualização, HTTPS, certificados, deploy, recuperação de erro, troubleshooting), instruções XAMPP obsoletas removidas, e tudo fiel ao comportamento real (Constitution XI).

### Não-requisitos (fora de escopo)

- Não reescrever módulos, trocar stack ou remover funcionalidades (Constitution I).
- Não introduzir proxy reverso obrigatório, containers orquestrados ou nova ferramenta de empacotamento — o diagnóstico pode documentar alternativas, mas a implementação segue o mecanismo existente.
- Não migrar certificados para autoridade certificadora pública/Let's Encrypt nesta feature (permanece como alternativa documentada).
- Não alterar regras de negócio, permissões RBAC, trilha de auditoria da aplicação ou fluxos de tela.
- Não executar migrações destrutivas nem apagar dados — em nenhum cenário automático.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Suíte de testes 100% comparável ao baseline registrado na Fase 1 antes e depois das alterações — zero regressão silenciosa (falhas só quando a especificação prevê a mudança de comportamento).
- **SC-002**: 100% das diferenças dev × PRO classificadas (intencional/necessária/obsoleta/erro/risco), com as acidentais eliminadas — comprovado por comparação direta dos dois conteúdos.
- **SC-003**: Instalação Windows limpa com MySQL Server nativo resulta em sistema acessível via HTTPS (página abre em `https://` com cadeia validada em cliente com a CA instalada) **sem nenhuma configuração manual pós-instalação**.
- **SC-004**: O HTTPS (SC-003) permanece funcionando após: reinicialização do servidor, reinício do serviço, atualização e reinstalação — 4 verificações, todas passando.
- **SC-005**: Zero referências funcionais a XAMPP na arquitetura final (restantes apenas históricas/documentadas e identificadas no relatório).
- **SC-006**: O mesmo código-fonte executa nos 4 cenários (dev/prod × Linux-MariaDB/Windows-MySQL) sem edição de código — apenas configuração de ambiente.
- **SC-007**: `deploy.sh` e `deploy.bat`, aplicados à mesma dev, produzem snapshots equivalentes no PRO (mesmos arquivos, line endings tratados).
- **SC-008**: Reexecução dos instaladores sobre instalação existente preserva banco, dados e `.env` (idempotência provada nos dois SOs).
- **SC-009**: Varredura de segurança aprova: nenhum segredo/chave privada no Git, nos logs, no argv, no histórico ou nas saídas dos scripts.
- **SC-010**: A documentação final não contém instruções operacionais de XAMPP e cada procedimento documentado corresponde ao comportamento real verificado.

## Key Entities

- **Ambiente de desenvolvimento** (`sistema_patrimonio_mysql`, repositório GitHub da dev): baseline funcional; contém a implementação de referência de banco, HTTPS, deploy.
- **Repositório de produção** (`SisPatrimonioPro`, branch `main`): snapshot filtrado da dev publicado por `deploy.sh`/`deploy.bat`; fonte dos instaladores.
- **Scripts de deploy**: `deploy.sh`/`deploy.bat` (publicar/pre/historico/rollback), com whitelist de snapshot a auditar por equivalência.
- **Instaladores**: `install.sh` (existente, spec 027) e instalador Windows (a auditar/criar — FR-018/FR-019); idempotentes; preservação de dados.
- **Configuração de banco**: `DATABASE_URL` (driver PyMySQL; MariaDB no Linux, MySQL no Windows), `.env`/variáveis de ambiente, percent-encoding de senha.
- **Certificados HTTPS**: CA local + certificado do servidor com SAN (IP/hostname) gerados fora do versionamento; chave privada com permissões restritas; trust store dos clientes.
- **Serviço**: execução da aplicação como serviço de sistema (systemd no Linux; equivalente no Windows), com reinício automático e dependência do banco correto.

## Assumptions

- `sistema_patrimonio_mysql` (este repositório) é o baseline funcional; `SisPatrimonioPro` é o snapshot whitelist publicado pelos scripts deploy (confirmado nos cabeçalhos dos scripts; a whitelists completas serão auditadas na Fase 1).
- O HTTPS de referência é o mecanismo nativo estabelecido pela spec 056 (SSL no servidor da aplicação, CA local, SAN com IP/hostname, `data/ssl/` fora do Git); a implementação da correção reutiliza esse mecanismo em vez de criar outro.
- MariaDB é o banco padrão no Linux (instalador 027 instala MariaDB quando nada existe); MySQL Server nativo é o banco exigido no Windows; a faixa de versões suportada será documentada a partir do diagnóstico real.
- Não há proxy reverso obrigatório; o TLS termina no próprio servidor da aplicação (mantendo a alternativa com proxy documentada como hoje).
- Dados de produção nunca são apagados sem ação explícita do administrador (Constitution VII); reinstalação/atualização preservam banco e `.env`.
- Há acesso a uma máquina Windows de teste e a uma máquina/ambiente Linux de teste para validar instalação limpa, atualização e reinstalação (sem elas, os critérios de aceite de instalação só podem ser parcialmente demonstrados — registrado como limitação).

## Decisões registradas

- **D-001 — Sequência rígida**: Fase 1 (Diagnóstico, somente leitura) → Fase 2 (Planejamento com lista de arquivos) → Fase 3 (Implementação mínima) → Fase 4 (Validação completa) → Fase 5 (Deploy/validação ponta a ponta). Nenhuma fase começa sem a anterior concluída e documentada.
- **D-002 — Política HTTP→HTTPS (resolvida em 2026-10-02)**: **sem redirect nativo** — mantém a decisão da 056. Com HTTPS ativo na porta 8000, acessos `http://` à mesma porta falham no handshake do cliente (comportamento esperado e documentado); o briefing "preferencialmente redirecionando" é atendido pela política da aplicação em vigor, e redirect externo (proxy/roteador) permanece opção documentada — sem criar novo mecanismo de servidor.
- **D-003 — Baseline HTTPS**: a correção Windows reutiliza a implementação da 056 (baseline funcional da dev); criar segunda implementação de HTTPS é proibido (briefing §21).
- **D-004 — Instalador Windows (resolvido em 2026-10-02)**: **existe e está versionado** (confirmado pelo responsável); a Fase 1 localiza-o no PRO/dev e a auditoria nele é a base da correção da causa raiz (FR-018); novo instalador somente se a auditoria concluir inadequação estrutural (FR-019).
- **D-005 — Alterações cirúrgicas**: a lista de arquivos da Fase 2 é o contrato da Fase 3; qualquer arquivo fora da lista exige atualização do plano antes da mudança.
- **D-006 — Porta com HTTPS ativo**: TLS escuta na própria porta da aplicação — **8000** (`APP_PORT`), conforme decisão do responsável (2026-10-02); sem porta HTTP separada no mesmo processo (modelo nativo 056). Instalação/produção ajustam via `.env` sem nova implementação.

## Risks

- **Quebrar a dev funcionando** (maior risco do projeto): mitigação — Fase 1 somente leitura, baseline de testes, alterações mínimas auditadas, suíte verde após cada lote (SC-001).
- **Instalador Windows inexistente ou muito divergente do fluxo real**: mitigação — FR-018/FR-019 tratam ambos os casos sem arquitetura paralela.
- **Ambiente Windows de validação indisponível**: mitigação — critérios de aceite de instalação Windows exigem máquina de teste; sem ela, a feature não pode ser declarada concluída (registrada como limitação).
- **Diferenças MariaDB × MySQL descobertas tarde**: mitigação — matriz preenchida na Fase 1 e testes nos dois bancos na Fase 4 (SC-006).
- **Whitelist do deploy omitindo arquivo necessário**: mitigação — comparação dev × snapshot e validação da instalação a partir do PRO (FR-015, SC-002).
- **Certificados expirados/SAN desatualizado no pós-instalação**: mitigação — roteiro de regeneração documentado e verificação de SAN no diagnóstico (FR-021/FR-024).
- **Senhas com caracteres especiais quebrando scripts**: mitigação — percent-encoding programático em todos os pontos (FR-010).
