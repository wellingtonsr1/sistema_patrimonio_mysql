# Feature Specification: Conferência de Inventário Offline — PWA + Service Worker + IndexedDB

**Feature Branch**: `033-inventario-offline-pwa`

**Created**: 2026-09-24

**Status**: Draft

**Input**: Implementar modo de **conferência física de inventário offline** no SisPatrimônio Pro: preparação de pacote offline enquanto conectado, coleta em campo sem conexão (com leitura de QR Code), fila de sincronização local, sincronização posterior validada pelo servidor, idempotência, tratamento de conflitos, auditoria e preservação integral do banco oficial MariaDB. A funcionalidade é uma extensão do módulo de Inventário — não transforma o sistema em aplicativo offline, não cria segunda base patrimonial e não altera regras patrimoniais existentes.

## Estado atual analisado (fatos do repositório, Seção 40 do input)

Análise prévia obrigatória — mecanismos existentes que esta spec **reutiliza** (não reimplementa):

| Mecanismo existente | Fato verificado | Relevância |
|---|---|---|
| `InventarioService.create_inventario` + `generate_items` | A lista de bens esperados é **snapshot gerado na criação** (`expected_*` em `inventario_itens`), imune a edições posteriores | O pacote offline derivará do mesmo snapshot; nada de nova fonte de verdade |
| `InventarioService.record_check` | Registra conferência e **nunca altera o cadastro do bem** (Princípio V); divergências (`LOCAL_DIFERENTE`, `NAO_ENCONTRADO`, `SEM_IDENTIFICACAO`) são apenas registradas | Destino oficial dos resultados sincronizados |
| `InventarioService.register_unlisted_asset` | Registra bem não previsto no inventário | Destino do "bem não previsto" escaneado offline |
| `InventarioService.close_inventario` + `summary` | Encerramento exige bens esperados conferidos; trava itens; ata exportável | Fluxo de fechamento **inalterado**; offline alimenta o mesmo fluxo |
| Conferência atual (`/inventarios/{id}`, `buscar_bem_inventario`) | Web-form síncrono (POST), **sem API REST de inventário** | A sincronização exigirá endpoints novos em `/api/v1`, seguindo o padrão existente |
| QRCode.js | **Gera** QR para etiquetas; **não lê** | Leitura de QR é capacidade nova; o conteúdo/identificador do QR existente é a base |
| RBAC (`permission_service`, deny by default), auditoria (`audit_service`), autenticação híbrida local+AD | Padrões vigentes (Princípios VI e IX) | Reutilizados integralmente; nada de novo RBAC/auditoria/auth |
| Stack (FastAPI + SQLAlchemy + MariaDB + Jinja2/Bootstrap) | Constitution, Restrições de Tecnologia | Intocável; offline é **camada adicional** de coleta, não substituição |

**Regra fundamental preservada (Princípio V)**: o inventário registra a realidade encontrada em campo; **nunca altera automaticamente o cadastro patrimonial**. MariaDB continua sendo a única fonte oficial; o armazenamento local do dispositivo é área temporária de coleta.

## Clarifications

### Session 2026-09-24

- Q: Como o dispositivo deve se autenticar na API de sincronização quando a rede retornar? → A: Pela **sessão web existente** (mesmo mecanismo de login/cookie atual); nenhum token ou credencial dedicada é armazenada no dispositivo; se a sessão expirar em campo, o usuário reautentica pelo login normal antes de sincronizar (decisão C-1).
- Q: Quais estados do inventário permitem preparar o pacote offline e o que acontece com coletas pendentes quando o inventário avança de estado? → A: **PLANNED e IN_PROGRESS**; a preparação em PLANNED não altera o estado do inventário; se o inventário for encerrado ou re-preparado, coletas pendentes ficam bloqueadas para coleta e a sincronização será rejeitada com motivo claro — nada é perdido localmente (decisão C-2).
- Q: Quais resultados a conferência offline deve aceitar para um bem encontrado? → A: **Espelhar o fluxo online**: presença confirmada + situação encontrada + local/responsável encontrados + observação; divergências derivadas automaticamente pelas mesmas regras do fluxo online (sem vocabulário de status novo) (decisão C-3).
- Q: Durante a coleta offline prolongada (dias em campo), o que deve acontecer quando o cookie de sessão expirar no dispositivo e o usuário tentar salvar uma coleta? → A: **A coleta continua sendo salva localmente** mesmo com a sessão expirada; o servidor valida a sessão apenas na sincronização — coletas feitas com sessão expirada podem ser rejeitadas no sync com motivo claro, e permanecem preservadas localmente; reautenticação só é exigida para sincronizar (decisão C-4).
- Q: Quando uma coleta offline chega para sincronizar e o item já foi conferido pelo fluxo online (ou por outra coleta já sincronizada) com resultado diferente, o que o servidor deve fazer? → A: Resultado **igual** ao já registrado → reconhecido como já processado (idempotente, sem segunda gravação); resultado **diferente** → registrado como CONFLITO na área "Conflitos offline" (P-3), preservando os dois resultados para reconciliação; nenhuma sobrescrita silenciosa entre canais online/offline (decisão C-5).

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Preparar inventário para coleta offline (Priority: P1)

Um usuário autorizado, **conectado**, abre um inventário em planejamento/em andamento e solicita "Preparar coleta offline". O servidor valida autenticação, autorização e o estado do inventário, gera o pacote com **somente** os dados necessários à conferência (identificação dos bens e expectativas do snapshot) e o entrega ao dispositivo, que o guarda no armazenamento local. O usuário recebe a confirmação "Pronto para uso offline".

**Why this priority**: sem o pacote preparado, nenhuma outra parte do fluxo offline existe. É o primeiro elo entre o módulo de Inventário existente e o modo de coleta em campo.

**Independent Test**: prepara-se o pacote conectado, verifica-se no dispositivo que os dados mínimos estão presentes e que **nenhum** dado além do necessário (nem dados administrativos, nem credenciais) foi baixado. Não requer estar offline nem sincronizar.

**Acceptance Scenarios**:

1. **Given** usuário com permissão apropriada e inventário em estado preparável, **When** solicita a preparação offline, **Then** o servidor valida autorização, gera o pacote versionado do snapshot e o dispositivo o armazena localmente, exibindo confirmação.
2. **Given** usuário sem permissão, **When** tenta preparar, **Then** recebe acesso negado (403) e nada é gerado; a tentativa é auditada.
2a. **Given** inventário encerrado com coletas pendentes no dispositivo, **When** o usuário tenta coletar ou sincronizar, **Then** a coleta é bloqueada com orientação para reconectar e a sincronização é rejeitada com motivo claro — coletas permanecem preservadas localmente (decisão C-2).
3. **Given** inventário encerrado ou em estado não preparável, **When** solicita a preparação, **Then** a operação é recusada com mensagem clara.
4. **Given** pacote preparado, **When** inspecionado o conteúdo local, **Then** constam apenas: identificação do inventário, versão/snapshot do pacote, identificador do item, tombamento, descrição mínima de identificação, número de série (quando existente), local esperado, responsável esperado e o identificador usado pelo QR Code — e nada de usuários, permissões, administração ou credenciais.

---

### User Story 2 - Coletar em campo sem conexão (Priority: P1)

Com o pacote preparado, o usuário sai da rede (ou o servidor fica inacessível) e continua a conferência física: abre o inventário no dispositivo, lista/pesquisa os itens, escaneia o QR Code da etiqueta, confirma presença, informa o que encontrou (situação, local, responsável quando aplicável), registra observações e divergências. Cada coleta é registrada localmente com estado próprio e entra na fila de sincronização.

**Why this priority**: é o coração funcional do pedido — a coleta em campo sem internet.

**Independent Test**: com o pacote no dispositivo e sem conexão, realiza-se uma sequência de conferências (inclusive divergências e um bem não previsto), fecha-se o navegador e reabre-se: tudo continua lá e consistente.

**Acceptance Scenarios**:

1. **Given** dispositivo sem conexão com o servidor, **When** o usuário abre a área de coleta offline, **Then** a interface carrega (servida localmente), exibindo o inventário preparado e o indicador de modo offline.
2. **Given** QR Code de um bem do snapshot, **When** escaneado (ou tombamento digitado manualmente), **Then** o item é identificado e a conferência pode ser registrada.
3. **Given** local encontrado diferente do esperado, **When** a coleta é registrada, **Then** uma **divergência de local** é registrada e o cadastro oficial **não é alterado**.
4. **Given** QR válido de bem **fora** do snapshot, **When** escaneado, **Then** o sistema registra a ocorrência de "bem não previsto" (identificador, tombamento quando disponível, data/hora, usuário, dispositivo, local encontrado, observação) sem alterar o cadastro.
5. **Given** itens pendentes, **When** o usuário consulta o painel da coleta, **Then** vê conferidas, restantes, divergências e bem não previstos.
6. **Given** coletas registradas, **When** o navegador é fechado e reaberto (ou o dispositivo reinicia), **Then** todas as coletas ainda não sincronizadas permanecem disponíveis, com seus estados locais preservados.

---

### User Story 3 - Sincronização confiável quando a rede retorna (Priority: P1)

De volta à rede, o dispositivo envia a fila de coletas ao servidor, que revalida **tudo** (autenticação, autorização, inventário, usuário, dispositivo, snapshot, patrimônio, operação, duplicidade, integridade) antes de gravar pelos services existentes. O resultado é estruturado por operação (aceita, duplicada, conflito, rejeitada) e refletido nos estados locais. A sincronização é idempotente, parcial (reenvia só o pendente) e nunca apaga a coleta local antes de confirmação inequívoca.

**Why this priority**: de nada adianta coletar se os dados não chegam ao sistema oficial com garantias. É o fechamento do ciclo de valor.

**Independent Test**: com coletas pendentes, sincroniza-se contra o servidor (incluindo cenários de reenvio, queda de rede no meio e conflitos entre dispositivos) e verifica-se no banco oficial que coletas aceitas estão registradas uma única vez, rejeitadas estão explicadas e nada foi perdido.

**Acceptance Scenarios**:

1. **Given** N coletas pendentes e servidor acessível, **When** a sincronização executa, **Then** o servidor valida e grava as coletas aceitas pelo fluxo oficial do inventário, retorna resultado estruturado e os estados locais passam a "sincronizada".
2. **Given** o mesmo pacote enviado duas vezes, **When** o servidor processa o reenvio, **Then** nenhuma coleta é duplicada (idempotência por identificadores únicos gerados no dispositivo).
2a. **Given** coleta offline de item já conferido no servidor, **When** sincronizada, **Then** resultado igual → reconhecida como já processada (idempotente); resultado diferente → CONFLITO registrado na área "Conflitos offline" preservando os dois resultados — nunca sobrescrita silenciosa (decisão C-5).
3. **Given** 1.000 coletas com queda de rede após 300 aceitas, **When** a conexão retorna, **Then** somente as 700 pendentes são reenviadas e as 300 permanecem sincronizadas.
4. **Given** sessão expirada durante o offline, **When** o usuário volta à rede e sincroniza, **Then** a sessão é revalidada conforme a política existente antes de aceitar coletas.
5. **Given** coleta que falha na validação (ex.: inventário encerrado, patrimônio fora do snapshot, integridade), **When** o servidor responde, **Then** a operação é marcada como rejeitada com motivo compreensível e **preservada localmente** (nunca apagada silenciosamente).
6. **Given** dois dispositivos que coletaram resultados diferentes para o mesmo bem, **When** ambos sincronizam, **Then** o servidor **não escolhe** um resultado silenciosamente: registra conflito e preserva as informações das duas coletas para tratamento posterior.

---

### User Story 4 - Múltiplos dispositivos no mesmo inventário (Priority: P2)

O mesmo inventário pode ser preparado em mais de um dispositivo (Tablet-01, Tablet-02…). Cada dispositivo tem identificação própria e gera coletas próprias; o servidor consolida tudo no mesmo inventário, mantendo a origem rastreável.

**Why this priority**: cenário real de equipes grandes; depende do ciclo P1 estar funcionando, mas é uma extensão natural.

**Independent Test**: prepara-se o mesmo inventário em dois dispositivos (identificadores distintos), coleta-se em ambos, sincroniza-se e verifica-se a consolidação com rastreabilidade de origem.

**Acceptance Scenarios**:

1. **Given** inventário preparado em dois dispositivos, **When** cada um coleta bens distintos e sincroniza, **Then** todas as coletas aparecem consolidadas no mesmo inventário oficial.
2. **Given** coletas consolidadas, **When** consultadas, **Then** é possível identificar o dispositivo de origem de cada coleta.
3. **Given** dois dispositivos com coletas sobre o **mesmo** bem, **When** sincronizam, **Then** aplica-se a regra de conflito da US3 (nunca sobrescrever silenciosamente).

---

### User Story 5 - Controles de ciclo de vida: expiração, limpeza e evidências (Priority: P3)

O pacote offline tem controle de expiração; após sincronização completa, o usuário pode encerrar a coleta no dispositivo e limpar os dados locais de forma segura (informando o que será removido). A arquitetura prevê evidências/fotos (metadados associados à coleta) sem implementar, nesta etapa, um sistema completo de imagens, dado que não existe infraestrutura de armazenamento de fotos no sistema atual.

**Why this priority**: higiene e governança do ciclo de vida; o valor principal já está entregue nas US1–US4.

**Independent Test**: com coletas sincronizadas, encerra-se a coleta local e verifica-se a limpeza segura; prepara-se um pacote, aguarda-se/força-se a expiração e verifica-se o bloqueio de uso e a orientação ao usuário.

**Acceptance Scenarios**:

1. **Given** todas as coletas sincronizadas e confirmadas pelo servidor, **When** o usuário encerra a coleta local, **Then** o sistema informa exatamente o que será removido e, após confirmação, limpa os dados temporários do dispositivo.
2. **Given** coletas ainda pendentes, **When** o usuário tenta encerrar/limpar, **Then** o sistema alerta e impede a perda de dados pendentes.
3. **Given** pacote expirado (inventário encerrado ou re-preparado), **When** o usuário tenta coletar, **Then** o uso é bloqueado com orientação para reconectar e re-preparar o pacote.
4. **Given** ausência de infraestrutura de fotos no sistema atual, **When** a coleta é registrada, **Then** a arquitetura aceita metadados de evidência associados à coleta e a limitação está documentada para o usuário.

---

### Edge Cases

- **Conexão instável durante a sincronização**: coletas já confirmadas permanecem confirmadas; as demais voltam a pendente; nenhuma duplicidade (reenvio idempotente).
- **Item conferido online enquanto havia coleta offline pendente**: resolvido pela regra do FR-021 (igual → idempotente; diferente → conflito preservado em "Conflitos offline") — sem sobrescrita silenciosa nem perda de informação (decisão C-5).
- **Dispositivo compartilhado**: o identificador do dispositivo é da instância de coleta; a coleta registra o usuário autenticado que a realizou.
- **Armazenamento local cheio / indisponível** (navegador com cota excedida ou dados limpos pelo usuário): o sistema avisa claramente antes de iniciar a coleta e durante, sem corromper coletas existentes; a recuperação não é possível se o usuário limpar os dados do navegador — o risco é comunicado.
- **Leitor de câmera indisponível** (permissão negada, navegador sem suporte): coleta continua por digitação manual do identificador/tombamento.
- **Inventário encerrado por outro usuário enquanto há coletas pendentes**: o servidor rejeita as coletas tardias com motivo claro; nada é gravado fora do fluxo oficial; coletas permanecem preservadas localmente para consulta.
- **Relógio do dispositivo incorreto**: a coleta preserva data/hora local declarada, mas o servidor registra o momento do recebimento como referência oficial; eventos oficiais nunca dependem exclusivamente do relógio do dispositivo.
- **Service Worker desatualizado** (HTML novo + código local antigo): versionamento de cache e de estrutura local impedem misturas incompatíveis; coletas pendentes jamais são apagadas em atualizações.
- **Múltiplas preparações do mesmo inventário** (re-preparo): nova versão de pacote substitui a anterior no dispositivo de forma controlada, preservando coletas pendentes compatíveis e explicando incompatibilidades ao usuário.

## Requirements *(mandatory)*

### Functional Requirements

**Preparação e pacote offline**

- **FR-001**: O sistema MUST permitir que um usuário autenticado e autorizado prepare um inventário para coleta offline a partir da tela do inventário, enquanto conectado.
- **FR-002**: O servidor MUST validar autenticação, autorização e o estado do inventário antes de gerar qualquer pacote offline: preparação permitida nos estados **PLANNED e IN_PROGRESS** (não altera o estado do inventário); inventário encerrado é recusado (decisão C-2).
- **FR-003**: O pacote offline MUST conter somente os dados necessários à conferência: identificação do inventário, versão/data do snapshot, identificador do item/bem, tombamento, descrição mínima para identificação, número de série (quando existente), local esperado, responsável esperado e o identificador usado pelo QR Code.
- **FR-004**: O pacote MUST ser identificável por inventário + versão de snapshot, permitindo ao servidor saber com quais dados vigentes a coleta foi feita.
- **FR-005**: A geração do pacote MUST NOT alterar dados oficiais (nenhum write no cadastro decorrente da preparação).
- **FR-006**: O dispositivo MUST armazenar o pacote e as coletas exclusivamente no armazenamento local do navegador (IndexedDB); `localStorage` MUST NOT ser usado como base principal da coleta.
- **FR-007**: O modo offline MUST NOT replicar o banco oficial nem permitir edição geral do cadastro patrimonial: somente coleta de inventário da área previamente autorizada.

**Coleta offline**

- **FR-008**: O sistema MUST disponibilizar a área de coleta offline funcional **sem conexão** (recursos carregados localmente pelo Service Worker), restrita aos inventários previamente preparados naquele dispositivo.
- **FR-009**: A coleta MUST permitir listar e pesquisar os itens do pacote e exibir contadores: conferidos, restantes, divergências, bens não previstos e pendências de sincronização.
- **FR-010**: A conferência MUST aceitar identificação por leitura de QR Code e, como alternativa, digitação manual do identificador/tombamento.
- **FR-011**: O conteúdo do QR Code MUST se limitar ao identificador seguro do bem, seguindo o padrão existente das etiquetas; MUST NOT conter credenciais, dados pessoais desnecessários ou informações administrativas.
- **FR-012**: A coleta MUST espelhar o vocabulário do fluxo online existente: confirmação de presença, situação encontrada, local encontrado, responsável encontrado (quando aplicável) e observação; as divergências MUST ser derivadas automaticamente pelas **mesmas regras do fluxo online** (ex.: local encontrado diferente do esperado → LOCAL_DIFERENTE), sem criar vocabulário de status patrimonial novo (decisão C-3).
- **FR-013**: Quando o dado encontrado divergir do esperado (ex.: local), o sistema MUST registrar a **divergência** e MUST NOT alterar automaticamente o cadastro patrimonial (local, responsável, estado) — nem criar movimentação ou alteração cadastral automática.
- **FR-014**: O sistema MUST registrar ocorrência de **bem não previsto** (QR válido fora do snapshot) com no mínimo: identificador, tombamento quando disponível, data/hora, usuário, dispositivo, local encontrado e observação.
- **FR-015**: O sistema MUST NOT marcar automaticamente um bem como "não encontrado" por omissão de leitura; a situação final dos itens continua definida pelo fluxo de fechamento/consolidação existente do inventário.
- **FR-016**: As coletas registradas MUST sobreviver ao fechamento do navegador e à reinicialização do dispositivo (persistência local durável), sem perda de coletas pendentes.
- **FR-017**: Se a infraestrutura atual não suportar fotos, o sistema MUST limitar-se a prever a arquitetura de evidências (metadados associados à coleta) e documentar a limitação; MUST NOT criar nesta feature um sistema completo de armazenamento de imagens.

**Fila e sincronização**

- **FR-018**: Toda operação de coleta MUST entrar em uma fila local com estado explícito (ex.: pendente, sincronizando, sincronizada, falhada, conflito), que orienta o que ainda precisa ser enviado.
- **FR-019**: O sistema MUST NUNCA apagar uma coleta local antes de confirmação inequívoca do servidor sobre o destino dela (aceita, duplicada ou rejeitada com motivo).
- **FR-020**: Cada coleta/operação MUST possuir identificador único gerado no dispositivo, usado para idempotência na sincronização.
- **FR-021**: A sincronização MUST ser idempotente: o reenvio do mesmo pacote/operação não cria segunda coleta no servidor. Para item já conferido no servidor: resultado **igual** → reconhecido como já processado (idempotente); resultado **diferente** → CONFLITO na área "Conflitos offline" (P-3), preservando os dois resultados — nenhuma sobrescrita silenciosa entre canais online/offline (decisão C-5).
- **FR-022**: O sistema MUST suportar sincronização parcial: apenas coletas pendentes são enviadas; confirmadas não são reenviadas desnecessariamente.
- **FR-023**: Falhas de rede durante a sincronização MUST preservar os dados locais e permitir nova tentativa, com limite controlado de tentativas (sem retry infinito e sem bloquear o usuário).
- **FR-024**: O sistema MUST expor endpoint(s) de sincronização na API existente, seguindo o padrão atual (`/api/v1`), que recebem as coletas e retornam resultado estruturado por operação (ex.: aceitas, duplicadas, conflitos, rejeitadas — ou o equivalente do padrão de resposta vigente).
- **FR-025**: O servidor MUST revalidar **tudo** no recebimento: autenticação, autorização, inventário, usuário, dispositivo, snapshot, patrimônio, operação, duplicidade, integridade e conflito — o cliente offline é considerado não confiável.
- **FR-026**: Coletas aceitas MUST ser gravadas **exclusivamente pelos services existentes do Inventário** (conferência/bem não previsto), sem novo caminho que contorne as regras oficiais (Princípios III e V).
- **FR-027**: O servidor MUST detectar conflito quando coletas de dispositivos diferentes trouxerem resultados divergentes para o mesmo bem do mesmo snapshot, registrando o conflito e preservando as informações das duas coletas — sem escolha silenciosa (primeiro/último/qualquer). O conflito MUST ficar visível em **área própria na tela do inventário** (seção "Conflitos offline"), com as coletas concorrentes lado a lado para decisão e reconciliação por usuário autorizado (decisão P-3).
- **FR-028**: O sistema MUST identificar cada dispositivo/instância de coleta com identificador próprio gerado localmente e persistente, sem uso de IMEI, número de telefone ou dados pessoais; coletas consolidadas devem ser rastreáveis à origem.

**Sessão, permissões e segurança**

- **FR-029**: A preparação offline e a sincronização MUST exigir a sessão válida e as **permissões de inventário já existentes** do RBAC (deny by default), sem criar permissão nova no catálogo nem mecanismo paralelo: quem pode conferir um inventário online pode prepará-lo e coletá-lo offline, e nenhum acesso offline concede mais do que a permissão existente já concede (decisão P-1).
- **FR-030**: No modo offline, o acesso no dispositivo MUST ficar restrito à coleta dos inventários previamente autorizados; MUST NOT ser possível acessar administração, usuários, perfis, permissões, edição/movimentação patrimonial ou quaisquer funcionalidades administrativas.
- **FR-031**: É PROIBIDO armazenar localmente: senhas, credenciais AD, tokens secretos persistentes, dados de sessão sensíveis e qualquer dado além do mínimo necessário à conferência.
- **FR-032**: A sincronização MUST usar a **sessão web existente** (mesmo mecanismo de login atual), sem token ou credencial dedicada armazenada no dispositivo (decisão C-1); ao retornar à rede, o servidor MUST revalidar a sessão conforme a política de autenticação existente antes de aceitar coletas — se expirada, o usuário reautentica pelo login normal antes de sincronizar. Durante a coleta local, a expiração da sessão MUST NOT bloquear o registro de coletas (decisão C-4): a validação acontece somente na sincronização, e coletas eventualmente rejeitadas por sessão permanecem preservadas localmente com motivo claro.
- **FR-033**: Em produção, o PWA MUST operar em contexto seguro (HTTPS via arquitetura existente de servidor/reverse proxy), sem desabilitar mecanismos de segurança do navegador e sem certificados embutidos no código da aplicação.

**PWA e Service Worker**

- **FR-034**: O sistema MUST expor manifest de aplicativo (nome, nome curto, start_url, display, ícones, tema/background) compatível com a identidade visual existente, sem criar nova interface visual.
- **FR-035**: O Service Worker MUST cachear apenas os recursos necessários à área de coleta offline do inventário, com cache versionado e remoção segura de caches antigos, sem interferir nas demais rotas do sistema.
- **FR-036**: O Service Worker MUST NUNCA cachear respostas sensíveis: usuários, permissões, sessões, dados administrativos, credenciais, tokens ou qualquer endpoint não relacionado à coleta offline.
- **FR-037**: A atualização do Service Worker MUST seguir versionamento controlado (nova versão → novo cache → cache antigo removido), evitando misturas incompatíveis (HTML novo + código local antigo).
- **FR-038**: Mudanças de estrutura do armazenamento local MUST ter migração versionada que preserve coletas pendentes; nenhuma atualização pode apagar coletas ainda não sincronizadas.

**Ciclo de vida do pacote**

- **FR-039**: O pacote offline MUST expirar quando o **inventário for encerrado ou re-preparado** (nova versão de snapshot) — política que coincide com a vida útil real dos dados coletados, sem prazo arbitrário em código; ao expirar, a coleta é bloqueada com orientação para reconectar (decisão P-2).
- **FR-040**: A limpeza local MUST ocorrer somente após sincronização completa confirmada, mediante ação do usuário informando claramente o que será removido, e MUST ser impedida se houver coletas pendentes.

**Interface e observabilidade**

- **FR-041**: A interface MUST indicar claramente o estado de conectividade (online/offline), o modo de coleta offline, a quantidade de coletas aguardando sincronização, o estado "sincronizando" e a conclusão ("Sincronização concluída N/N").
- **FR-042**: A indicação de disponibilidade do servidor MUST NÃO depender somente do sinal nativo do navegador; quando relevante, o sistema MUST realizar verificação leve real de conectividade com o servidor.
- **FR-043**: Todas as telas do modo offline MUST seguir o padrão visual existente (tema claro/escuro, componentes, contraste, resoluções menores), sem interface paralela.

**Auditoria, datas e não-regressão**

- **FR-044**: Os eventos relevantes MUST ser registrados no módulo de Auditoria **existente** (nenhum segundo sistema), seguindo o padrão de eventos vigente — no mínimo: preparação do pacote offline, sincronização (com resultado), conflito detectado, coleta rejeitada — sempre sem credenciais.
- **FR-045**: As datas/horas MUST seguir a política de data/hora existente do sistema (sem segunda política de timezone): a coleta preserva data/hora local declarada; o servidor registra o momento do recebimento como referência oficial da sincronização.
- **FR-046**: Nenhuma funcionalidade existente (login local/AD, usuários, perfis, permissões, equipamentos, colaboradores, locais, movimentações, manutenções, relatórios, auditoria, backups, Central de Integrações) pode ter comportamento alterado por esta feature.

### Key Entities *(include if feature involves data)*

- **Pacote offline de inventário**: materialização, no dispositivo, do snapshot de bens esperados de um inventário (derivado da lista `expected_*` existente), com inventário de origem, versão/data do snapshot, itens mínimos para identificação e validade. Nunca é fonte oficial.
- **Coleta offline**: resultado registrado em campo para um item (presença, situação/local/responsável encontrados, observação, divergências), com estado local próprio, data/hora local declarada, usuário que coletou, dispositivo de origem e identificadores únicos de coleta/operação para idempotência.
- **Fila de sincronização local**: lista de operações pendentes/confirmadas com estados e contagem de tentativas; orienta o reenvio parcial e impede perda de dados.
- **Dispositivo de coleta**: identificador local persistente da instância de coleta (não invasivo), usado para rastreabilidade de origem e consolidação multi-dispositivo.
- **Ocorrências de sincronização**: resultados do servidor por operação — aceitas, duplicadas (idempotência), conflitos (preservados para tratamento posterior) e rejeitadas com motivo.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A preparação offline de um inventário de até 1.000 bens conclui em até 1 minuto em rede local, com confirmação visível ao usuário.
- **SC-002**: Uma coleta individual (escanear + registrar) é concluída em menos de 10 segundos, sem conexão, incluindo divergências.
- **SC-003**: 100% das coletas pendentes permanecem íntegras após fechamento do navegador e após reinicialização do dispositivo (zero perdas em teste dirigido).
- **SC-004**: O reenvio do mesmo pacote de coletas gera zero duplicidades no banco oficial (100% das operações reconhecidas como já processadas).
- **SC-005**: Em sincronização de 1.000 coletas interrompida após 300 aceitas, o retorno da rede reenvia exatamente as 700 pendentes — nenhuma a mais, nenhuma a menos.
- **SC-006**: 100% dos conflitos entre dispositivos sobre o mesmo bem são detectados, registrados e preservados sem sobrescrita silenciosa.
- **SC-007**: Zero alterações automáticas no cadastro patrimonial decorrentes de coletas e divergências registradas (verificável por inspeção do cadastro antes/depois).
- **SC-008**: Zero respostas sensíveis (usuários, permissões, administração, credenciais) em cache local do dispositivo, verificado por inspeção do armazenamento.
- **SC-009**: Atualização de versão do Service Worker preserva 100% das coletas pendentes e a compatibilidade dos dados locais (migração testada).
- **SC-010**: A suíte de testes existente permanece 100% verde (regressão), com novos testes cobrindo os 19 cenários obrigatórios da especificação de origem (preparação, permissão negada, coleta offline, QR previsto/não previsto, divergências de local e responsável, fechamento do navegador, reinício do dispositivo, sincronização, duplicidade, sincronização parcial, conflito, múltiplos dispositivos, queda de rede durante sync, atualização do Service Worker, inventário não altera patrimônio, auditoria e segurança).
- **SC-011**: Um usuário consegue completar o ciclo ponta a ponta (preparar → coletar N bens offline → sincronizar → ver resultados no inventário oficial) sem assistência, na primeira tentativa.

## Assumptions

- **Navegadores-alvo**: navegadores modernos com suporte a Service Worker e IndexedDB (Chrome/Edge atuais, incluindo Android); leitura de QR pela câmera do dispositivo com degradação para digitação manual.
- **QR Code**: as etiquetas existentes são geradas pelo sistema (QRCode.js); a leitura reutiliza o padrão de conteúdo atual das etiquetas — a definição exata do identificador contido no QR (se tombamento, tag ou outro) será confirmada no planning a partir do código existente, sem inventar novo formato.
- **Permissões** (decisão P-1, registrada em 2026-09-24): **reutilizar as permissões de inventário existentes** — quem confere online prepara e coleta offline; nenhuma permissão nova no catálogo.
- **Fotos/evidências**: o sistema atual não possui infraestrutura de armazenamento de imagens; conforme instrução de origem, esta feature apenas prevê a arquitetura (metadados) e documenta a limitação.
- **Conflitos** (decisão P-3, registrada em 2026-09-24): não existe hoje mecanismo de conflitos no Inventário (a re-conferência do mesmo item é intencionalmente sobrescrita pelo fluxo existente); o mínimo necessário será implementado para detectar e preservar conflitos **entre dispositivos** no contexto offline, sem alterar a semântica da re-conferência online já estabelecida. Destino decidido: **área própria na tela do inventário** ("Conflitos offline"), com as coletas concorrentes visíveis e reconciliação por usuário autorizado.
- **Expiração** (decisão P-2, registrada em 2026-09-24): não existe hoje política de validade de pacote (o conceito é novo); decidido que o pacote **expira ao encerramento ou re-preparo do inventário**, alinhado à vida útil real do snapshot — sem prazo em dias escondido em configuração.
- **Volume**: meta de suportar pacotes e filas de até 1.000 coletas por inventário no dispositivo (cenário dos testes de origem).
- **Produção**: acesso externo em HTTPS pela arquitetura existente (proxy reverso → aplicação); a aplicação não assume gestão de certificados.
- **Scope**: o modo offline cobre **somente** conferência de inventário; movimentação, edição patrimonial, manutenções e demais módulos permanecem exclusivamente online.

## Dependências externas / informações pendentes

Como exigido pela especificação de origem (princípio: nada inventado), registram-se as informações que devem ser confirmadas **antes da implementação definitiva** dos pontos dependentes:

1. **Leitura de QR Code** — a capacidade atual é apenas *geração* (QRCode.js). A escolha do mecanismo de leitura (API nativa do navegador vs. biblioteca) e a compatibilidade com os navegadores-alvo dos tablets serão definidas no planning, com verificação do conteúdo real das etiquetas existentes no sistema.
2. **Conteúdo atual do QR das etiquetas** — confirmar no código/template qual identificador o QR atualmente codifica, para que a leitura identifique o mesmo patrimônio sem novo formato.
3. **Capacidades do ambiente de produção** — confirmar HTTPS efetivo no acesso externo (requisito de PWA/Service Worker) e política de proxy/cache reverso que não prejudique o versionamento do Service Worker.
4. ~~Política de expiração (P-2) e destino dos conflitos (P-3)~~ — **decididos** nesta especificação (ver Assumptions): expiração ao encerramento/re-preparo do inventário; conflitos em área própria na tela do inventário.

Nenhum endpoint, payload ou comportamento de sistema externo foi presumido nesta spec — todos os pontos externos listados acima são internos ao SisPatrimônio ou decisões já registradas.

## Fora de escopo

- Transformar o SisPatrimônio em aplicativo offline completo (apenas a conferência de inventário é offline).
- Banco de dados local alternativo (SQLite no dispositivo), réplica do MariaDB, aplicativos nativos (Android/iOS).
- Migração/reescrever o frontend, trocar frameworks, templates, banco ou autenticação (stack da Constitution intocável).
- Edição patrimonial, movimentações, alteração de responsáveis/locais, manutenções — online, como hoje.
- Sistema de armazenamento de fotos/evidências (apenas arquitetura e metadados, conforme FR-017).
- Novo sistema de autenticação, RBAC ou auditoria — os existentes são reutilizados.
- Regras novas de fechamento/consolidação de inventário — o fluxo existente permanece autoridade.
