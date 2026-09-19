# Feature Specification: Configuração Administrável do Backup Automático e Política de Retenção

**Feature Branch**: `feature-021-configuracao-backup-administravel`

**Created**: 2026-09-18

**Status**: Draft

**Input**: Tornar as configurações operacionais do Backup Automático e da Política de Retenção administráveis pela aplicação, sem depender de alteração manual do código — avaliando as alternativas (config.py, .env, banco, mecanismo existente) e escolhendo a de menor alteração segura e coerente com a arquitetura.

---

## Realidade verificada (análise obrigatória antes da implementação — briefing §6)

Análise realizada em 2026-09-18 sobre o código pós-feature-020 (commit `cf43cb7`):

### Como a configuração funciona hoje

| Aspecto verificado | Realidade no código |
|---|---|
| `app/config.py` | `load_dotenv()` na linha 28; as 8 configurações operacionais da 020 são lidas por `os.getenv(...)` com defaults, uma única vez, no import do módulo |
| `BACKUP_AUTO_ENABLED` | Default atual é **`"false"`** (runtime confirmado `False`; `.env` do projeto contém apenas `DATABASE_URL`). **A inconsistência comentário×código apontada pelo briefing (§15/§38 — default `"true"`) já não existe no código atual**: comentário ("Default DESATIVADO") e comportamento coincidem |
| `backup_scheduler` | Importa as constantes **no topo do módulo** (por valor, não por referência viva); `_effective_time()`/`_effective_schedule()`/`_effective_weekday()`/`_effective_int()` leem essas constantes de módulo. O loop `_scheduler_loop` captura `hour, minute` **uma vez no start da thread**; `scheduler_status()` recalcula a próxima execução a cada chamada; a retenção lê os limites a cada execução via `_effective_int` |
| Consequência prática | Hoje, alterar `BACKUP_AUTO_TIME` exige editar `.env` (ou código) **e reiniciar a aplicação** — a thread não reavalia horário capturado no start |
| Precedente de configuração persistente | **Existe**: `ADSettings` (singleton `id=1`) + `ad_service.get_ad_settings/_effective_settings` (linha do banco com fallback para env nos campos vazios) + tela "Integração AD" (`GET /admin/ad`, `POST /admin/ad/settings`) + RBAC + evento de auditoria `ALTERACAO_CONFIG_AD` com before/after |
| Auditoria | `audit_service.write_audit` com `new_data`/`previous_data` JSON; rótulos em `ACTION_LABELS`; padrão de eventos de configuração já existente (`ALTERACAO_CONFIG_AD`) |
| RBAC | `require_permission("backup.gerenciar")` protege toda a área de Backups; deny-by-default; nenhuma permissão nova foi criada na 020 |
| UI | Padrão estabelecido: card + `dl` no template `admin/backups.html`; formulários admin usam `Form(...)` + `RedirectResponse` com mensagens `success=`/`error=`; componente de confirmação e `can()` nos templates |
| Banco | `create_all` + `_ensure_schema_migrations` (ALTER aditivo idempotente); tabela `backup_records` da 020 criada sem tocar tabelas existentes |

### Alternativas avaliadas (briefing §8 — decisão a consolidar no planejamento)

| Alternativa | Avaliação | Veredicto |
|---|---|---|
| **A — manter somente `config.py`/env** | Não atende ao objetivo: alterar horário exige acesso ao servidor e reinício — exatamente o problema a resolver | **Descartada** como solução única |
| **B — usar `.env`** | Continua exigindo acesso ao servidor (arquivo) e reinício; apenas troca código por arquivo. O briefing proíbe adicionar variáveis de backup ao `.env` automaticamente | **Descartada** como solução única |
| **C — persistir no banco (tabela nova)** | Viável pelo mecanismo aditivo existente (`create_all`), mas cria estrutura sem precednte próprio | Subsumida por D |
| **D — reutilizar o mecanismo existente de configuração persistente** | O sistema **já possui** o padrão `ADSettings`: registro único em banco + service que resolve configuração efetiva (banco com fallback env/defaults) + tela admin + RBAC + evento de auditoria dedicado. Reutilizá-lo é a alteração de menor impacto e a mais coerente com a arquitetura (Constitution I/III) | **Recomendada** — diretriz para o planejamento |

**Diretriz resultante (a detalhar em `/speckit-plan`)**: seguir o padrão do precedente existente de configuração persistente (registro único, resolução "configuração efetiva" no serviço, tela dentro da área de Backups, evento de auditoria próprio). É PROIBIDO criar um serviço genérico de configuração, um segundo scheduler ou um sistema de parâmetros paralelo (briefing §31): a lógica vive nos módulos de backup existentes.

### Separação técnica × operacional (briefing §24 — decisão de escopo)

| Classe | Configurações | Destino nesta feature |
|---|---|---|
| **Operacionais** (administráveis pela interface) | `BACKUP_AUTO_ENABLED`, `BACKUP_AUTO_SCHEDULE`, `BACKUP_AUTO_TIME`, `BACKUP_AUTO_WEEKDAY`, `BACKUP_RETENTION_DAILY_DAYS`, `BACKUP_RETENTION_WEEKLY_WEEKS`, `BACKUP_RETENTION_MONTHLY_MONTHS`, `BACKUP_RETENTION_KEEP_PRE_RESTORE` | Expostas na tela; significados da 020 preservados |
| **Técnicas** (ambiente de execução) | `DATABASE_URL`, `MYSQLDUMP_PATH`, `BACKUP_DIR`, `BACKUP_IMPORT_TIMEOUT` | **Intocadas** — não aparecem na interface (§28/§29: sem caminhos arbitrários, sem alteração de executáveis/credenciais pela tela) |

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Administrador ajusta o backup automático pela interface (Priority: P1)

Um administrador acessa **Administração → Backups → Configurações de Backup**, altera o horário do disparo automático de 02:00 para 23:00 e salva. O sistema valida, persiste, confirma o sucesso e passa a usar o novo valor — sem acesso ao servidor, sem editar arquivo e sem reiniciar a aplicação. A alteração fica registrada na auditoria com valor anterior e novo valor.

**Why this priority**: é o problema central da feature (hoje exige acesso ao servidor + reinício) e o caso de uso do briefing (§3/§17).

**Independent Test**: Com a aplicação no estado padrão, alterar o horário pela tela e verificar: confirmação de sucesso, valor persistido (sobrevive a reinício), uso do novo valor pelo agendador e registro de auditoria com before/after.

**Acceptance Scenarios**:

1. **Given** administrador autenticado com a permissão adequada, **When** altera o horário de 02:00 para 23:00 e salva, **Then** recebe confirmação de sucesso, a configuração exibida passa a ser 23:00 e o evento de auditoria registra a alteração (valor anterior 02:00, novo 23:00, usuário, data/hora).
2. **Given** configuração alterada e persistida, **When** a aplicação é reiniciada, **Then** a configuração permanece 23:00 (nada volta ao padrão).
3. **Given** configuração alterada, **When** o agendador avalia o próximo disparo, **Then** utiliza 23:00 (sem exigir reinício da aplicação, conforme a arquitetura definida no planejamento).

---

### User Story 2 - Valores inválidos e primeiro uso são seguros (Priority: P1)

Toda alteração passa por validação no backend: frequência inválida, horário fora de HH:MM, dia da semana fora de 0–6, quantidades menores que 1 (ou negativas para pré-restauração) são rejeitadas com mensagem clara e **não** alteram a configuração vigente. Quando ainda não existe configuração salva (primeira inicialização), o sistema aplica exatamente os defaults da Feature 020 — backup automático **desativado** — e o agendador nunca fica em estado indefinido.

**Why this priority**: segurança e previsibilidade antecedem a conveniência: configuração inválida ou estado indefinido pode desativar proteções (ex.: retenção) ou ativar exclusões indevidas.

**Independent Test**: Submeter cada campo com valores inválidos e verificar rejeição (sem persistência, mensagem de erro, configuração anterior intacta); iniciar com estado limpo e verificar defaults da 020 vigentes e backup automático desativado.

**Acceptance Scenarios**:

1. **Given** formulário de configuração, **When** submetido com horário "25:99", **Then** rejeição com mensagem clara e configuração anterior preservada.
2. **Given** retenção diária preenchida com "0" ou negativo, **When** submetido, **Then** rejeição no backend (não apenas no HTML).
3. **Given** instalação sem nenhuma configuração salva, **When** a aplicação inicia, **Then** os valores efetivos são os defaults da 020 (desativado; diário; 02:00; domingo; 30/12/12; pré-restauração preservar todos) e o agendador não dispara backups.

---

### User Story 3 - Única fonte de verdade em execução (Priority: P1)

O sistema possui **uma única fonte de verdade** para a configuração operacional em tempo de execução. Não existem cenários em que arquivo de ambiente e configuração persistida divergentes produzam comportamento indefinido do agendador. A regra de precedência (o que governa: configuração salva, variável de ambiente ou default) é explícita, documentada e idêntica para todos os campos, seguindo o comportamento do mecanismo existente de configuração persistente do sistema.

**Why this priority**: o briefing classifica dupla fonte de verdade como proibição fundamental (§7); ambiguidade aqui quebra a previsibilidade operacional do backup.

**Independent Test**: Definir valores divergentes entre ambiente e configuração persistida e verificar que o comportamento do agendador segue a regra de precedência documentada (nunca indefinido); verificar que a documentação descreve a mesma regra.

**Acceptance Scenarios**:

1. **Given** configuração persistida com horário 23:00 e ambiente indicando 02:00, **When** o agendador calcula o próximo disparo, **Then** aplica a regra de precedência definida — o mesmo valor em toda leitura (agendamento, status na tela, retenção).
2. **Given** nenhuma configuração persistida e ambiente sem variáveis de backup, **When** o sistema opera, **Then** os defaults da 020 governam (mesma fonte única).

---

### User Story 4 - Acesso controlado por RBAC com auditoria obrigatória (Priority: P2)

Somente usuários com a permissão adequada visualizam e alteram as configurações; a validação de autorização é sempre no backend (não basta esconder o formulário). Toda alteração bem-sucedida registra evento na trilha de auditoria existente com usuário, data/hora, campo(s) alterado(s), valor anterior e novo valor — sem nenhum segredo. Acessos negados também seguem o padrão existente (403 auditado).

**Why this priority**: configuração operacional de backup é sensível (pode desativar proteções); RBAC e auditoria são exigências constitucionais, mas dependem de US1 existir para ter o que proteger.

**Independent Test**: Usuário sem permissão recebe 403 nas rotas de leitura/alteração (verificação no backend); usuário autorizado altera e o evento de auditoria contém before/after completo; nenhuma credencial aparece no evento ou na tela.

**Acceptance Scenarios**:

1. **Given** usuário autenticado sem a permissão adequada, **When** tenta acessar a tela ou submeter o formulário (POST direto), **Then** recebe 403 e nada é alterado ou registrado como alteração.
2. **Given** alteração bem-sucedida de dois campos, **When** consultada a auditoria, **Then** o evento identifica usuário, data/hora e os valores anterior/novo de cada campo alterado.

---

### User Story 5 - Funcionalidades existentes intocadas e separação técnica/operacional (Priority: P2)

Backup manual, restauração, backups pré-restauração e retenção continuam funcionando exatamente como na 020 — a alteração muda apenas a **origem** das configurações, não a lógica. Os parâmetros técnicos (`MYSQLDUMP_PATH`, `BACKUP_DIR`, `BACKUP_IMPORT_TIMEOUT`, `DATABASE_URL`) não se tornam campos da interface e nenhum caminho de arquivo ou comando passa a ser editável pela tela.

**Why this priority**: preservação é requisito inegociável (briefing §21–§23, §28–§29), porém é um efeito de não-regressão das stories anteriores — validado pela suíte, não constrói valor novo por si.

**Independent Test**: Executar a suíte de regressão (backup manual, restore, retenção) após as mudanças; inspecionar a tela e confirmar a ausência de campos técnicos; tentar operações manuais/restauração com a nova configuração vigente.

**Acceptance Scenarios**:

1. **Given** configuração operacional alterada pela tela, **When** um backup manual é gerado e uma restauração é executada, **Then** ambos funcionam como antes (inclusive a criação do backup pré-restauração).
2. **Given** a nova tela de configuração, **When** inspecionados seus campos, **Then** contém exclusivamente as 8 configurações operacionais — nenhum caminho, executável ou credencial.

---

### Edge Cases

- **Scheduler executando durante alteração**: o agendador nunca usa uma configuração "pela metade" (ex.: novo horário com frequência antiga). A leitura da configuração pelo ciclo deve ser consistente (briefing §27).
- **Dois administradores salvando simultaneamente**: a última escrita válida prevalece de forma determinística e cada salvamento gera seu evento de auditoria (sem corrupção).
- **Valor dentro da faixa mas limítrofe** (ex.: horário 00:00; retenção diária 1 dia): aceito e aplicado — a validação rejeita apenas o inválido, não o incomum.
- **Configuração salva seguida de remoção da variável correspondente do ambiente**: a configuração persistida continua governando (a regra de precedência não depende de o ambiente ter ou não a variável).
- **Falha de persistência** (banco indisponível): o salvamento falha com mensagem clara e a configuração vigente permanece a anterior — nunca um estado parcial.
- **Reinício da aplicação** (briefing §10/§26/§33 Teste R): a configuração persistida sobrevive; caso alguma parte da aplicação da configuração exija reinício por limitação arquitetural real, essa limitação deve estar **documentada** na tela/documentação — não escondida.

## Requirements *(mandatory)*

### Functional Requirements

**Escopo e preservação**

- **FR-001**: O sistema MUST permitir que as 8 configurações operacionais da Feature 020 (ativado, frequência, horário, dia da semana, retenção diária/semanal/mensal, pré-restauração) sejam visualizadas e alteradas por usuário autorizado pela interface administrativa, sem editar código ou arquivos do servidor.
- **FR-002**: O sistema MUST preservar integralmente o mecanismo de backup automático existente (mesmo scheduler, mesmo serviço de backup, mesmo fluxo de validação/histórico/auditoria) — a feature altera apenas a **origem** das configurações.
- **FR-003**: O sistema MUST preservar a política de retenção existente (significados de diário/semanal/mensal/pré-restauração) — apenas os parâmetros tornam-se administráveis.
- **FR-004**: Backup manual, restauração e criação de backup pré-restauração MUST continuar funcionando exatamente como antes.
- **FR-005**: Parâmetros técnicos (`DATABASE_URL`, `MYSQLDUMP_PATH`, `BACKUP_DIR`, `BACKUP_IMPORT_TIMEOUT`) MUST permanecer configuração de ambiente: não aparecem na interface, não são editáveis por ela e a correção multiplataforma da 018 permanece.

**Fonte única e configuração efetiva**

- **FR-006**: O sistema MUST ter **uma única fonte de verdade** para a configuração operacional em tempo de execução; é PROIBIDO comportamento indefinido quando ambiente e configuração persistida divergem.
- **FR-007**: A regra de precedência entre configuração persistida, variáveis de ambiente e defaults MUST ser única, explícita e idêntica para os 8 campos, seguindo o comportamento do mecanismo existente de configuração persistente do sistema (registro salvo governa; ambiente/default como origem de bootstrap e fallback nos campos não definidos).
- **FR-008**: A primeira inicialização sem configuração persistida MUST aplicar os defaults da Feature 020 (desativado; diário; 02:00; domingo; 30 dias; 12 semanas; 12 meses; pré-restauração preservar todos) — o agendador nunca fica em estado indefinido e o backup automático NÃO é ativado por padrão.
- **FR-009**: O default de "backup automático ativado" MUST ser **desativado**, em consistência com a regra funcional da 020 (spec FR-005 original). Decisão registrada: a inconsistência comentário×código (`"true"`) apontada pelo briefing foi verificada no código atual e **já está corrigida** (default `"false"`); esta feature inclui teste que impede regressão.
- **FR-010**: O agendador, a tela de monitoramento e a retenção MUST ler sempre a **mesma** configuração efetiva (nenhuma leitura de fonte divergente entre si).

**Aplicação dinâmica**

- **FR-011**: Após alteração salva com sucesso, o agendador MUST passar a considerar a nova configuração (próximo disparo, janelas de retenção) **sem reinício da aplicação**, exceto se existir limitação arquitetural real — nesse caso a limitação MUST ser documentada e a aplicação da nova configuração prevista de forma determinística.
- **FR-012**: O ciclo do agendador MUST ler uma configuração consistente (nunca uma combinação parcial de valores antigos e novos) mesmo com alteração concurrente em andamento.
- **FR-013**: Duas alterações administrativas simultâneas MUST resolver de forma determinística (última escrita válida prevalece), cada uma com seu evento de auditoria.

**Validação**

- **FR-014**: O backend MUST validar: frequência ∈ {diário, semanal}; horário em HH:MM válido; dia da semana ∈ 0–6; retenção diária ≥ 1; retenção semanal ≥ 1; retenção mensal ≥ 1; pré-restauração ≥ 0. A validação do serviço existente da 020 (faixas + fallback com log) é preservada.
- **FR-015**: Valores inválidos MUST ser rejeitados com mensagem clara, **sem** alterar a configuração vigente — a validação HTML/JavaScript é apenas conveniência, nunca a única barreira.
- **FR-016**: Valores limítrofes válidos (ex.: 00:00, retenção 1) MUST ser aceitos.

**Interface**

- **FR-017**: A configuração MUST viver dentro da estrutura administrativa existente (área Backup e Restauração), como subárea/seção "Configurações de Backup" — sem módulo administrativo paralelo.
- **FR-018**: A interface MUST usar os componentes, padrões visuais, tema claro/escuro, responsividade e mensagens existentes (sucesso/erro via padrão atual) — sem redesign.
- **FR-019**: A tela MUST exibir os campos exatamente equivalentes às regras da 020: ativado/desativado; frequência (diário/semanal); horário; dia da semana; retenção diária/semanal/mensal; política de pré-restauração (preservar todos / preservar N mais recentes) — e o estado efetivo atual (incluindo o que o monitoramento já mostra).

**Auditoria e RBAC**

- **FR-020**: Toda alteração de configuração MUST registrar evento na trilha de auditoria existente com: usuário, data/hora, campo(s) alterado(s), valor anterior e novo valor (evento dedicado, ex.: `BACKUP_CONFIGURACAO_ALTERADA`, com rótulo em linguagem natural — reutilizando o padrão do evento de configuração existente do sistema).
- **FR-021**: Nenhum segredo (senha, token, credencial, `DATABASE_URL`) MUST aparecer em eventos de auditoria, logs ou na tela de configuração.
- **FR-022**: A leitura da tela de configuração e a alteração MUST exigir a permissão existente `backup.gerenciar` (RBAC deny-by-default, validação sempre no backend). Nenhuma permissão nova é criada; conceder acesso permanece operação administrativa existente (perfis).
- **FR-023**: Acesso negado às rotas de configuração MUST seguir o padrão existente (403 com evento de acesso negado).

**Persistência e compatibilidade**

- **FR-024**: Se a solução exigir persistência nova, ela MUST seguir o mecanismo existente (criação aditiva idempotente), preservar todos os dados existentes e justificar a estrutura no relatório; preferir estrutura/recurso já existente quando atender.
- **FR-025**: A solução MUST funcionar em Linux e Windows (produção MariaDB/MySQL; suíte em SQLite) sem dependência nova de plataforma ou pacote externo.
- **FR-026**: Variáveis de ambiente existentes da 020 MUST continuar suportadas como origem de bootstrap/fallback conforme FR-007 — nenhum deploy atual pode quebrar por causa desta feature; nenhum valor novo é adicionado ao `.env` automaticamente.
- **FR-027**: A configuração persistida MUST sobreviver ao reinício da aplicação e ser reutilizada na inicialização (Teste R).
- **FR-028**: A documentação (README, arquitetura, central de ajuda) MUST ser atualizada para descrever a nova tela, a regra de precedência e o comportamento pós-alteração — fiel ao comportamento real.

### Key Entities *(include if feature involves data)*

- **Configuração de Backup (registro único)**: estado persistido das 8 configurações operacionais (ativado; frequência; horário; dia da semana; retenção diária/semanal/mensal; política de pré-restauração) + metadados de rastreio (quem alterou por último e quando). Criada/valorizada com os defaults da 020 na primeira inicialização. Não contém segredo nem caminho de arquivo.
- **Configuração efetiva**: resultado da resolução única aplicada em runtime (persistida → ambiente → default), consumida pelo agendador, pela tela e pela retenção — conceito análogo ao já existente para a configuração de integração AD.
- **Evento de auditoria de configuração**: registro append-only da alteração (usuário, data/hora, before/after por campo) na trilha existente.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um administrador autorizado altera o horário do backup automático (02:00 → 23:00) pela interface em menos de 1 minuto, sem acesso ao servidor e sem reiniciar a aplicação.
- **SC-002**: 100% das alterações de configuração geram evento de auditoria com valor anterior e novo valor; 0 alterações sem registro.
- **SC-003**: 100% das submissões com valores inválidos (amostra: horário malformado, frequência inexistente, retenção 0/negativa) são rejeitadas pelo backend sem alterar a configuração vigente.
- **SC-004**: Após alteração salva, o próximo disparo calculado pelo agendador reflete o novo valor em 100% das verificações, sem reinício (ou a limitação remanescente está documentada na tela/docs).
- **SC-005**: Em 100% das reinicializações da aplicação, a configuração persistida permanece idêntica à última salva (nada regride a default implicitamente).
- **SC-006**: 0 campos técnicos (caminhos, executáveis, credenciais, URLs de banco) presentes na interface de configuração; 0 segredos em auditoria/logs da feature.
- **SC-007**: Usuários sem a permissão adequada recebem 403 em 100% das tentativas (leitura e escrita, incluindo POST direto).
- **SC-008**: Suíte de regressão existente (497 testes, incluindo backup manual, restauração, retenção e agendador da 020) permanece 100% verde após a feature.

## Assumptions

- **A1**: A permissão existente `backup.gerenciar` é adequada para a configuração (mesma área, mesmo risco operacional); permissão nova só se o planejamento demonstrar indispensabilidade (briefing §19).
- **A2**: O padrão existente de configuração persistente do sistema (registro único + resolução no serviço + tela admin + evento de auditoria próprio) é o mecanismo a reutilizar (Alternativa D); não se cria serviço/arquitetura genérica de configuração (briefing §31).
- **A3**: A regra de precedência adotada segue o precedente existente: configuração salva governa; env/default servem de bootstrap e fallback em campos não definidos (A2).
- **A4**: Os defaults da 020 (desativado; diário; 02:00; domingo; 30/12/12; pré-restauração preservar todos) permanecem inalterados em valor e significado (briefing §15).
- **A5**: A inconsistência do default de `BACKUP_AUTO_ENABLED` apontada pelo briefing já foi corrigida no código atual (default `"false"`); a feature adiciona teste anti-regressão e registra a decisão (FR-009).
- **A6**: O `.env` do projeto continua contendo essencialmente `DATABASE_URL`; nenhuma variável nova é adicionada a ele automaticamente (briefing §8/§26 do fluxo).
- **A7**: Não há necessidade de mudança de schema em tabelas existentes; qualquer estrutura nova é aditiva e criada pelo mecanismo existente (Constitution VII).
- **A8**: A aplicação dinâmica da configuração pelo agendador é viável dentro da arquitetura atual (thread + leitura por ciclo); se o planejamento identificar limitação real (ex.: horário capturado no start da thread), ela será resolvida ou documentada conforme FR-011.
- **A9**: Os eventos de auditoria e rótulos da 020 permanecem; a feature adiciona apenas o evento de alteração de configuração (FR-020).
- **A10**: Escopo limitado às 8 configurações operacionais: qualquer outra configuração do sistema não se torna administrável por esta feature (briefing §5/§35).
