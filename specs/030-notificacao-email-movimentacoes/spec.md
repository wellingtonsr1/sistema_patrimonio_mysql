# Feature Specification: Notificação por E-mail ao Setor de Patrimônio após Movimentação

**Feature Branch**: `030-notificacao-email-movimentacoes`

**Created**: 2026-09-23

**Status**: Draft

**Input**: Notificação automática por e-mail ao setor de Patrimônio após a conclusão de movimentações patrimoniais. E-mail é mecanismo de ciência/aviso: nunca altera o resultado da movimentação. Arquitetura desacoplada do domínio de movimentações, preparada para reuso futuro em outros eventos. Sem link de consulta nesta versão, mas com modelo preparado para adicioná-lo depois.

---

## 1. Objetivo e Escopo

### 1.1 Objetivo

Quando uma movimentação patrimonial for concluída com sucesso e persistida no banco de dados, o sistema deve enviar automaticamente uma notificação por e-mail ao(s) endereço(s) configurado(s) do setor de Patrimônio, informando os dados da movimentação.

A notificação é um mecanismo de **ciência/aviso institucional**:

- **Movimentação concluída + e-mail enviado** → sucesso;
- **Movimentação concluída + e-mail falhou** → a movimentação continua válida e concluída; a falha é registrada (notificação + auditoria).

### 1.2 Incluído

- Disparo de notificação por e-mail após movimentação persistida com sucesso;
- Cobertura dos 3 tipos principais de movimentação (ver RN-002);
- Configuração de ativação e destinatários (não hardcoded);
- Configuração SMTP por variáveis de ambiente (credenciais fora do código);
- Registro de falhas de envio e eventos de auditoria;
- Proteção contra notificações duplicadas por movimentação;
- Tela administrativa de configuração seguindo o padrão existente;
- Testes automatizados com mocks/fakes de SMTP.

### 1.3 Fora de Escopo

- **Link de consulta à movimentação no e-mail** (não implementar nesta versão; arquitetura preparada — ver RN-008);
- Recuperação de senha por e-mail, notificações para usuários, resumos/digests;
- Notificações para inventários, baixas além das movimentações, manutenções como eventos próprios (o reuso futuro é facilitado, mas não implementado aqui);
- Envio assíncrono com fila/worker dedicado (arquitetura preparada, não implementado na v1);
- Painel/alerta dedicado de falhas de notificação na administração (a ciência da falha é pela trilha de auditoria — Clarifications 2026-09-23);
- Retry automático agendado (pendência P-1 — ver Seção 17);
- Alteração de regras patrimoniais, tipos de movimentação, RBAC ou fluxos existentes;
- Novos tipos de movimentação.

---

## Clarifications

### Session 2026-09-23

- Q: Quais tipos de movimentação concluída devem gerar e-mail? → A: Apenas os 3 principais — `ALOCACAO_CAUTELA`, `TRANSFERENCIA_LOCAL` e `DEVOLUCAO_ESTOQUE` (demais tipos não notificam nesta versão).
- Q: Movimentações criadas em lote pela importação de CSV devem gerar e-mail? → A: Não — o lote da importação fica fora do escopo da notificação na v1 (ciência pelo relatório da importação).
- Q: Onde o administrador toma ciência de falhas de envio? → A: Exclusivamente na trilha de auditoria (evento de falha) — nenhum painel/alerta dedicado na v1.
- Q: Quem aparece como “usuário que realizou a movimentação” no e-mail quando a conclusão é via API? → A: O usuário autenticado da API — mesmo dado já gravado em `operator_name` na movimentação (consistência e-mail × registro).

---

## 2. Estado Atual da Arquitetura (análise somente leitura)

Fatos verificados no código em 2026-09-23. A spec se baseia nestes fatos — não inventa mecanismos.

| # | Fato | Evidência |
|---|---|---|
| F1 | `MovementService.create_movement` valida (VAL-002..VAL-008), grava o `Movement` com origem/destino completos e faz `db.commit()` **atômico por movimentação**. Chamadores: rotas web (`app/web/routes.py`), API (`app/api/movements_api.py`), CLI (`app/cli.py`), manutenção (`maintenance_service.py`) e carga demo (`seed_demo.py`). | `app/services/movement_service.py` (L79–288) |
| F2 | Existem 8 tipos de movimentação: `ENTRADA_AQUISICAO`, `ALOCACAO_CAUTELA`, `TRANSFERENCIA_LOCAL`, `ENVIO_MANUTENCAO`, `RETORNO_MANUTENCAO`, `DEVOLUCAO_ESTOQUE`, `BAIXA_DESCARTE`, `ATUALIZACAO_ESTADO` (vocabulário controlado — Constitution). | `app/models/enums.py` (L35–39, L144–148) |
| F3 | **Não existe** infraestrutura de e-mail/SMTP no projeto (nenhuma ocorrência de smtplib/envio no código). A feature cria a infra a partir do zero, como serviço isolado. | busca no código |
| F4 | Trilha de auditoria via `write_audit(db, user=, action=, module=, resource=, resource_id=, ip_address=, result=, description=, previous_data/new_data=)`; constantes `ACTION_*` com rótulos em `ACTION_LABELS`; resultados `RESULT_SUCCESS`/`RESULT_FAILURE`; trilha imutável (Constitution IX). | `app/services/audit_service.py` |
| F5 | Precedente de configuração persistida editável em tela: `backup_config_service` (feature 021) — linha singleton no banco, precedência **persistido → variável de ambiente (bootstrap) → default**, com senhas **exclusivamente em ambiente** (`AD_BIND_PASSWORD`, Princípio VI). | `app/services/backup_config_service.py`, `app/config.py` |
| F6 | O `Movement` registrado contém: `asset_id`, tipo, timestamp UTC, origem/destino de local (ids + nomes formatados), origem/destino de custodiante (ids + nomes), `operator_name`, `reason`, `term_code`, status anterior/novo. O `Asset` possui `tag` (tombamento) e identificação. | `app/services/movement_service.py` (L253–283), models |
| F7 | A importação CSV (feature 029) gera movimentações **em lote** chamando `create_movement` em loop (`execute_import`) — uma importação pode criar dezenas/centenas de movimentações de uma vez. | `app/services/import_service.py`, specs/029 |
| F8 | Alterações de banco são **aditivas e idempotentes** via `init_db` + mecanismo existente de migração condicional (Constitution VII). MariaDB em produção; SQLite só em testes. | Constitution VII |
| F9 | RBAC deny by default; telas de administração existentes (backup 021/022, AD) já estabelecem o padrão de tela de configuração com permissão administrativa. | Constitution VI, `app/web/admin_routes.py` |
| F10 | Apresentação de datas segue a feature 004: UTC na máquina, horário local (`America/Recife`) na apresentação. | specs/004, `app/utils/time_utils.py` |

---

## 3. User Scenarios & Testing *(mandatory)*

### User Story 1 — Setor de Patrimônio toma ciência da movimentação (Priority: P1)

Um servidor do setor de Patrimônio precisa saber, sem consultar o sistema, que um bem foi movimentado (entrega/cautela, transferência de local, devolução etc.). Quando uma movimentação é concluída no sistema, o setor recebe um e-mail objetivo com os dados que permitem identificar a movimentação (bem, tipo, origem, destino, responsáveis, operador, data/hora).

**Why this priority**: é o valor central da feature — ciência institucional automática.

**Independent Test**: com a notificação ativada e destinatários configurados, concluir uma movimentação válida e verificar que os destinatários configurados recebem exatamente um e-mail com os dados da movimentação.

**Acceptance Scenarios**:

1. **Given** notificações ativadas com destinatário válido, **When** o operador conclui uma `ALOCACAO_CAUTELA` válida, **Then** o e-mail é enviado após a persistência e contém tombamento, identificação do bem, tipo, origem/destino, custodiantes, data/hora e operador.
2. **Given** notificações ativadas, **When** o operador conclui uma `TRANSFERENCIA_LOCAL` válida, **Then** o setor recebe a notificação correspondente.
3. **Given** notificações ativadas, **When** o operador conclui uma `DEVOLUCAO_ESTOQUE` válida, **Then** o setor recebe a notificação correspondente.
4. **Given** notificações ativadas, **When** o operador conclui uma movimentação de tipo **fora do alcance** (ex.: `ENTRADA_AQUISICAO`, `BAIXA_DESCARTE`), **Then** nenhum e-mail é enviado e nenhum registro de notificação é criado (RN-002).

---

### User Story 2 — Falha de e-mail nunca afeta a movimentação (Priority: P1)

O servidor de e-mail pode estar indisponível a qualquer momento. O sistema patrimonial continua operando normalmente: a movimentação é concluída e persistida; a falha de notificação é registrada para ciência posterior do administrador.

**Why this priority**: protege a integridade da operação patrimonial (regra fundamental do briefing).

**Independent Test**: com o servidor SMTP simulado como indisponível, concluir uma movimentação válida e verificar que ela persiste concluída, que a falha é registrada (status da notificação + auditoria) e que nenhum erro sensível é exposto.

**Acceptance Scenarios**:

1. **Given** SMTP indisponível, **When** uma movimentação válida é concluída, **Then** a movimentação é persistida com sucesso (comportamento idêntico ao atual) e a falha de envio é registrada.
2. **Given** SMTP indisponível, **When** a movimentação é concluída, **Then** a resposta ao operador não expõe mensagem técnica de SMTP/credenciais.

---

### User Story 3 — Administrador configura a notificação (Priority: P2)

O administrador precisa poder ativar/desativar as notificações de movimentação e definir os endereços de e-mail do setor de Patrimônio, pela interface de administração, seguindo o padrão visual e de permissões existente. As credenciais SMTP ficam no ambiente do servidor (`.env`), nunca no banco nem no código.

**Why this priority**: sem configuração, a feature não entra em operação; mas é um passo único após a implantação.

**Independent Test**: como administrador, acessar a tela de configuração, ativar e salvar destinatários; concluir uma movimentação e verificar o envio; desativar e verificar que nenhum e-mail é enviado.

**Acceptance Scenarios**:

1. **Given** usuário com permissão administrativa, **When** ativa as notificações e salva destinatários válidos, **Then** a configuração persiste e passa a valer sem reiniciar o sistema.
2. **Given** usuário sem a permissão administrativa, **When** tenta acessar/alterar a configuração, **Then** o acesso é negado (padrão RBAC existente).
3. **Given** notificações desativadas, **When** qualquer movimentação é concluída, **Then** nenhum e-mail é enviado e nenhum erro é gerado.

---

### User Story 4 — Trazibilidade e não duplicidade (Priority: P3)

A auditoria permite responder: qual movimentação gerou notificação, quando, para quem, com sucesso ou falha. Uma mesma movimentação nunca gera mais de um e-mail, mesmo em cenários de reprocessamento.

**Independent Test**: concluir uma movimentação, inspecionar a trilha de auditoria (eventos de notificação presentes, sem segredos) e confirmar que existe no máximo uma notificação vinculada à movimentação.

**Acceptance Scenarios**:

1. **Given** movimentação concluída com envio bem-sucedido, **When** a auditoria é consultada, **Then** existe evento de notificação enviada com destinatários e resultado, sem credenciais.
2. **Given** movimentação concluída, **When** o fluxo de notificação é executado novamente para a mesma movimentação (ex.: reprocesso futuro), **Then** nenhum segundo e-mail é gerado (idempotência).

---

### Edge Cases

- SMTP fora do ar no momento do envio → US2 (falha registrada, movimentação intacta);
- SMTP lento → envio com limite de tempo curto configurável; a operação do usuário não pode ficar bloqueada de forma perceptível além desse limite;
- Lista de destinatários vazia ou com e-mails inválidos → a ativação deve ser bloqueada na configuração (validação ao salvar); em runtime, configuração ativada sem destinatário válido não deve gerar erro visível nem envio (registra evento de falha de configuração);
- Importação CSV em lote (F7) → nenhuma notificação por linha (RN-002 — decisão confirmada, Clarifications 2026-09-23);
- Movimentações originadas da CLI ou da carga demo (`seed_demo.py`) → não devem gerar e-mails na prática (a configuração nasce desativada; ver RN-006/D1);
- Tipos fora do alcance (ex.: `BAIXA_DESCARTE`, `ENTRADA_AQUISICAO`, manutenção) → movimentação concluída válida, porém **sem notificação** nesta versão (RN-002) — nenhum e-mail, nenhum registro;
- Fuso horário → data/hora no e-mail no padrão da feature 004 (local `America/Recife` para pessoas, UTC na máquina).

## Requirements *(mandatory)*

### 4. Requisitos Funcionais

- **FR-001**: O sistema MUST disparar uma notificação por e-mail ao(s) destinatário(s) configurado(s) **somente depois** que a movimentação tiver sido validada, gravada e **persistida com sucesso** (pós-commit — F1).
- **FR-002**: O sistema MUST NOT enviar notificação para movimentações que falharam na validação ou que tenham sofrido rollback (nenhuma movimentação gravada → nenhum e-mail).
- **FR-003**: A falha de envio de e-mail MUST NOT alterar o resultado da movimentação, MUST NOT gerar rollback e MUST NOT propagar erro para o operador além de um comportamento idêntico ao atual (envio best-effort, isolado da transação principal).
- **FR-004**: A notificação MUST cobrir **exatamente** os tipos definidos em RN-002 (`ALOCACAO_CAUTELA`, `TRANSFERENCIA_LOCAL`, `DEVOLUCAO_ESTOQUE`), sem criar novos tipos e sem notificar os demais tipos nesta versão.
- **FR-005**: Os destinatários MUST ser configuráveis (não hardcoded), permitindo **múltiplos destinatários** e ativação/desativação da notificação (ver D3).
- **FR-006**: As notificações MUST nascer **desativadas por default** (conservador, precedente `BACKUP_AUTO_ENABLED=false`): sem configuração explícita, o comportamento do sistema é idêntico ao atual.
- **FR-007**: O assunto do e-mail MUST seguir padrão institucional único e centralizado (ver RN-005), nunca definido pontualmente em cada fluxo.
- **FR-008**: O conteúdo do e-mail MUST identificar a movimentação com, quando disponíveis: título; tombamento (tag); identificação do equipamento; tipo da movimentação (rótulo legível); local de origem; local de destino; custodiante anterior; custodiante atual; data e hora da movimentação (padrão 004); usuário que realizou a movimentação.
- **FR-009**: O e-mail MUST NOT conter link de consulta ao sistema nesta versão; o modelo de dados MUST guardar o vínculo com a movimentação de forma que o link possa ser adicionado futuramente **sem reestruturar** o serviço (ver RN-008/D7).
- **FR-010**: Falhas de envio MUST ser registradas com: evento, data/hora da tentativa, destinatários, resultado e mensagem técnica de erro quando apropriado (sem segredos), e quantidade de tentativas realizadas.
- **FR-011**: O sistema MUST garantir **no máximo uma notificação por movimentação** (idempotência — ver Seção 13).
- **FR-012**: O sistema MUST registrar eventos na trilha de auditoria existente conforme Seção 11 (padrão `ACTION_*` + rótulo), sem credenciais.
- **FR-013**: As credenciais SMTP MUST ficar exclusivamente fora do código-fonte (ambiente/`.env`) e NUNCA aparecer em logs, auditoria, mensagens de erro, banco ou argumentos de linha de comando.
- **FR-014**: A configuração de notificações (ativação/destinatários) MUST ser alterável apenas por usuários com a permissão administrativa existente (RBAC deny by default); o destinatário efetivo do envio SEMPRE vem da configuração oficial do sistema, nunca de dados enviados pelo navegador em uma movimentação.
- **FR-015**: A implementação MUST reutilizar os mecanismos existentes (camada de services, `write_audit`, precedente de configuração persistida F5, apresentação de datas F10) e MUST NOT duplicar infraestrutura equivalente.
- **FR-016**: Com o serviço de e-mail indisponível, o sistema patrimonial MUST continuar 100% operante; o envio deve ter limite de tempo curto configurável para não prender a resposta ao operador.
- **FR-017**: Na v1 NÃO deve existir reenvio automático agendado (ver P-1); o registro de falha (FR-010) deve conter o estado necessário para viabilizar retry futuro sem mudança de modelo.
- **FR-018**: A documentação (README/docs/central de ajuda) MUST ser atualizada na mesma tarefa (Constitution XI): variáveis de ambiente novas, tela de configuração e comportamento de falha.

### Requisitos Não Funcionais

- **NFR-001 (Desempenho)**: o disparo não pode degradar perceptivelmente a conclusão da movimentação além do limite de tempo de envio configurável (default curto — da ordem de segundos);
- **NFR-002 (Disponibilidade)**: indisponibilidade de e-mail não pode gerar erro 500 em nenhuma rota de movimentação;
- **NFR-003 (Segurança)**: nenhuma credencial/segredo em logs, auditoria, telas, respostas de API ou repositório (Constitution VI);
- **NFR-004 (Manutenibilidade/Evolução)**: a infraestrutura de notificação deve ser um serviço isolado, reutilizável por outros eventos futuros (inventários, pendências etc.) sem alteração do domínio de movimentações;
- **NFR-005 (Compatibilidade)**: funcionamento idêntico nos ambientes Windows e Linux já suportados pelo projeto;
- **NFR-006 (Banco)**: eventuais estruturas novas são aditivas e idempotentes (F8/Constitution VII), sem alterar tabelas/colunas existentes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Com notificações ativadas e SMTP operacional, 100% das movimentações dos tipos notificados (RN-002) concluídas geram exatamente **1** e-mail para os destinatários configurados, em até 30 segundos após a conclusão.
- **SC-002**: Com SMTP indisponível, **100%** das movimentações válidas continuam persistidas e concluídas (zero perda/invalidação por causa de e-mail).
- **SC-003**: **Zero** e-mails duplicados por movimentação (no máximo 1 notificação por movimentação, verificável na trilha/registros).
- **SC-004**: O administrador altera ativação/destinatários pela tela de administração em menos de 2 minutos, sem alterar código e sem reiniciar o sistema.
- **SC-005**: **Zero** ocorrências de senha SMTP ou credenciais em logs, auditoria e mensagens de erro (verificável por inspeção/busca).
- **SC-006**: Com SMTP indisponível, o tempo adicional percebido na conclusão da movimentação fica dentro do limite de timeout configurado (default da ordem de 10 segundos) e a operação conclui com sucesso.
- **SC-007**: Com notificações desativadas (estado default), o comportamento do sistema é idêntico ao atual — zero e-mails, zero erros novos, suíte existente 100% verde.

---

## 5. Regras de Negócio

- **RN-001 (ciência, não parte da operação)**: a notificação é mecanismo de aviso. Ela nunca participa da transação da movimentação de forma que sua falha provoque rollback, erro ou alteração de estado.
- **RN-002 (tipos notificados)**: a notificação cobre **somente os três tipos principais** concluídos pelos fluxos manuais do sistema (web e API): entrega/cautela `ALOCACAO_CAUTELA`, transferência `TRANSFERENCIA_LOCAL` e devolução `DEVOLUCAO_ESTOQUE`. Os demais tipos existentes (`ENTRADA_AQUISICAO`, `ENVIO_MANUTENCAO`, `RETORNO_MANUTENCAO`, `BAIXA_DESCARTE`, `ATUALIZACAO_ESTADO`) **não geram e-mail nesta versão** (decisão de negócio — Clarifications 2026-09-23; a ciência dessas operações permanece nas telas/trilha do sistema). **Movimentações criadas em lote pela importação CSV (F7) não geram e-mail na v1** (decisão confirmada — Clarifications 2026-09-23) — a ciência dessas operações já é dada pelo relatório/resultados da própria importação.
- **RN-003 (ordem garantida)**: nenhum e-mail antes do commit; se a movimentação não foi gravada, não há notificação. O disparo acontece imediatamente após a persistência bem-sucedida.
- **RN-004 (destinatário oficial)**: o destinatário é sempre o configurado pelo administrador na configuração oficial do sistema. Dados do navegador nunca definem destinatário.
- **RN-005 (assunto padronizado)**: padrão institucional centralizado, no formato: `[SisPatrimônio Pro] Nova movimentação patrimonial - <TAG do bem>` (ex.: `[SisPatrimônio Pro] Nova movimentação patrimonial - PAT-000123`). Definido em um único ponto, reutilizado por qualquer envio futuro.
- **RN-006 (default desativado)**: sem configuração explícita do administrador, nenhuma notificação é enviada (FR-006). Isso protege também carga demo, CLI e suítes de teste.
- **RN-007 (um e-mail por movimentação)**: cada movimentação concluída gera no máximo uma notificação (Seção 13).
- **RN-008 (link futuro)**: nesta versão o e-mail NÃO contém link/URL. O registro da notificação guarda a referência única da movimentação que a originou; a futura inclusão de "URL da movimentação" deve ser uma mudança apenas de conteúdo do e-mail (template), sem reestruturar serviço ou modelo. Não gerar URLs "de preparação" agora.
- **RN-009 (conteúdo institucional)**: o corpo do e-mail é objetivo, em linguagem institucional, sem dados além dos necessários para identificar a movimentação (FR-008), sem credenciais e sem dados sensíveis desnecessários.
- **RN-010 (operador exibido)**: o campo “usuário que realizou a movimentação” do e-mail é sempre o **usuário autenticado** que concluiu a operação (web ou API), exatamente o mesmo já registrado em `operator_name` da movimentação — nunca um rótulo de canal (ex.: "API") (Clarifications 2026-09-23).

---

## 6. Fluxo da Movimentação + Notificação

```text
Operador conclui movimentação (web/API — fluxos manuais)
        │
        ▼
MovementService.create_movement
  valida (VAL-002..008) → grava Movement → db.commit()   ← ponto de não-retorno
        │
        ├─ commit FALHOU/rollback → FIM (nenhum e-mail)  ← RN-003/FR-002
        │
        ▼ (pós-commit, somente se notificações ativadas e fluxo elegível — RN-002)
NotificationService.notify_movement(movimentação)
  1. já existe notificação p/ esta movimentação? → sai (idempotência, RN-007)
  2. registra notificação vinculada à movimentação
  3. monta assunto (RN-005) e conteúdo (FR-008) a partir do registro da movimentação
  4. envia via provedor de e-mail (timeout curto — FR-016)
        │
        ├── ENVIADO → marca ENVIADA + evento de auditoria de sucesso
        └── FALHOU  → marca FALHOU (tentativas, erro técnico sem segredos)
                      + evento de auditoria de falha
                      → a movimentação permanece concluída (RN-001)
```

Pontos obrigatórios do fluxo: (a) o disparo é **solicitado** pelo serviço de movimentação, não montado por rotas (Constitution II/III); (b) qualquer exceção do passo de notificação é capturada no próprio serviço de notificação — nada escapa para o chamador.

---

## 7. Arquitetura Proposta

Desacoplada do domínio, seguindo a divisão em camadas (Constitution II/III) e o desenho do briefing:

```text
MovementService (domínio)
      │  solicita notificação após o commit (única responsabilidade)
      ▼
NotificationService  (app/services — orquestra: idempotência, configuração,
      │               registro, auditoria)
      ▼
Provedor de envio de e-mail  (único ponto que conhece SMTP; substituível
                              por fake em testes e por outros canais no futuro)
```

Diretrizes (nomes finais de módulos/classes/eventos serão fixados no `/speckit-plan`, respeitando as convenções existentes):

- O serviço de movimentação apenas **dispara/solicita** a notificação após a conclusão; nenhuma lógica de SMTP nele;
- O serviço de notificação é genérico o suficiente para, no futuro, ser acionado por inventários, pendências etc. **sem alteração** do mecanismo (NFR-004) — mas nada disso é implementado agora;
- O provedor de e-mail é isolado e injetável/substituível (facilita mock nos testes e futura troca por envio assíncrono);
- Configuração segue o precedente F5 (persistido → ambiente → default); credenciais só no ambiente (F5/FR-013).

---

## 8. Configuração SMTP

- Variáveis de ambiente (bootstrap — nomes finais no plan, seguindo o padrão `SMTP_*` do briefing): `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_USE_TLS`, além de timeout de envio configurável;
- **`SMTP_PASSWORD` é segredo**: exclusivamente em `.env`/ambiente do servidor (Constitution VI — precedente `AD_BIND_PASSWORD`), nunca em banco, código, logs, auditoria, mensagens de erro ou argumentos de processo;
- As demais (host/porta/from/TLS) ficam no ambiente como bootstrap; sem valor configurado, a notificação permanece inoperante (e o default desativado — RN-006 — evita qualquer tentativa indevida);
- O sistema não deve introduzir uma segunda fonte de verdade para segredos; não duplicar configuração entre banco, `.env` e código (D3).

---

## 9. Modelo de Configuração/Dados

### Key Entities

- **Configuração de notificação** (singleton, precedente F5): ativação (default desativado), lista de destinatários do setor de Patrimônio (um ou mais e-mails), rastro de quem alterou e quando. Editável pela administração; fallback no ambiente para bootstrap; default conservador final.
- **Registro de notificação** (entidade nova, aditiva): referência única da movimentação que a originou (vínculo um-para-um — base da idempotência RN-007), estado (ex.: enviada / falhou), destinatários usados, assunto, quantidade de tentativas, data/hora da tentativa e do envio, mensagem técnica de erro quando houver (sem segredos), e campo de texto reservado para conteúdo/evolução futura (ex.: URL quando o link for adicionado — RN-008).
- **Movimentação** (existente, somente leitura para esta feature): fonte dos dados do e-mail (F6). Nenhuma alteração de modelo na movimentação.

Requisitos do modelo: criação **aditiva e idempotente** pelo mecanismo existente (F8); unicidade do vínculo notificação↔movimentação (garantia estrutural da idempotência); nenhum dado de credencial no modelo.

---

## 10. Auditoria (integração à trilha existente)

Novas ações no padrão do projeto (constantes `ACTION_*` + rótulos em `ACTION_LABELS`, módulo próprio — nomes finais no plan):

| Evento (proposto) | Quando | Conteúdo |
|---|---|---|
| `NOTIFICACAO_ENVIADA` | envio bem-sucedido | movimentação de origem (recurso + id), destinatários, resultado `SUCCESS` |
| `NOTIFICACAO_FALHOU` | envio falhou | movimentação de origem, destinatários, resultado `FAILURE`, descrição técnica do erro **sem segredos** |
| `ALTERACAO_CONFIG_NOTIFICACAO` | admin salva configuração | before/after da configuração (sem segredos — não há segredo nela), padrão `write_change_audit` |

Decisão D6: não é criado evento separado de "solicitada" — o par enviado/falhou já responde integralmente as perguntas exigidas (qual movimentação gerou, quando, para quem, sucesso/falha) e evita ruído na trilha. A trilha permanece imutável e somente-leitura (Constitution IX). Nenhuma senha, token ou credencial SMTP em qualquer evento.

---

## 11. Tratamento de Falhas

| Falha | Comportamento obrigatório |
|---|---|
| SMTP indisponível/timeout | movimentação permanece concluída; notificação marcada como falhada (tentativas + erro técnico); evento `NOTIFICACAO_FALHOU`; nenhum erro propagado ao operador |
| Erro na montagem do conteúdo | idem acima (falha registrada); a movimentação não é afetada |
| Configuração ativada sem destinatário válido | nenhum envio; registrar falha de configuração (auditoria/log) sem erro visível ao operador |
| Qualquer exceção inesperada no serviço de notificação | capturada no serviço; nunca sobe para a rota; registrada como falha de notificação |
| Erro ao gravar o registro/auditoria da notificação | não altera a movimentação; registrado no log da aplicação |

A mensagem de erro técnica registrada não deve conter credenciais, senha, nem dados sensíveis além do necessário para diagnóstico.

A ciência da falha para o administrador, nesta versão, é **exclusivamente a trilha de auditoria** (evento de falha com destinatários e descrição técnica) — nenhum painel ou alerta dedicado é criado (Clarifications 2026-09-23).

---

## 12. Idempotência e Duplicidade

- **Garantia estrutural**: no máximo **um registro de notificação por movimentação** (vínculo único — Seção 9). Antes de enviar, o serviço verifica a existência do registro; existente → não reenvia (RN-007);
- Cenário do briefing (`movimentação concluída → notificação gerada → processo falha após envio → nova tentativa`): a nova tentativa encontra o registro existente e não gera segundo e-mail;
- Efeitos colaterais esperados: o mesmo e-mail nunca é enviado duas vezes para a mesma movimentação; a auditoria registra apenas o resultado efetivo;
- Sem mecanismo de fila na v1, não há cenário de concorrência de reprocesso; a unicidade estrutural cobre a evolução futura (retry/fila) sem mudança de modelo.

---

## 13. Segurança

- Credenciais SMTP só no ambiente (FR-013); nunca em logs/auditoria/erros/telas/repositório;
- Configuração de notificação alterável apenas por administrador autorizado (RBAC existente; deny by default); a tela segue o padrão das telas de configuração existentes (F9);
- Destinatário sempre da configuração oficial (RN-004); nenhum endpoint de movimentação aceita destinatário do navegador;
- Validação dos endereços de destinatário ao salvar a configuração (rejeita lista vazia/inválida quando ativado);
- Conteúdo do e-mail restrito aos dados institucionais da movimentação (RN-009); sem dados de usuários/senhas/sessões;
- Auditoria sem segredos (Constitution VI/IX).

---

## 14. Estratégia de Testes

Testes automatizados com **mocks/fakes do provedor de e-mail** — nunca servidor SMTP real. Padrões existentes da suíte (TestClient/pytest, fixtures de banco em memória).

Cobertura mínima:

1. **Sucesso**: movimentação válida → persistida → notificação registrada → e-mail enviado com assunto (RN-005) e conteúdo (FR-008) corretos para os destinatários configurados;
2. **Falha de SMTP** (fake levanta erro): movimentação persistida e concluída; falha registrada (estado + auditoria); nenhuma exceção propagada;
3. **Movimentação inválida**: validação falha/rollback → nenhum e-mail e nenhum registro de notificação;
4. **Notificações desativadas** (default): movimentação concluída → nenhum e-mail, nenhum registro;
5. **Destinatários**: envio somente para os configurados (múltiplos destinatários);
6. **Conteúdo**: campos do FR-008 presentes e corretos — incluindo operador = usuário autenticado, consistente com `operator_name` da movimentação, tanto via web quanto via API (RN-010);
7. **Idempotência**: segunda solicitação para a mesma movimentação não gera novo envio;
8. **Segurança**: senha/credenciais ausentes de logs, auditoria e mensagens de erro;
9. **Importação CSV em lote**: nenhuma notificação individual por linha (RN-002/P-2);
10. **Tipos fora do alcance**: movimentação válida de tipo não notificado (ex.: `ENTRADA_AQUISICAO`, `BAIXA_DESCARTE`) → nenhum e-mail e nenhum registro de notificação (RN-002);
11. **Configuração**: validação de destinatários ao salvar; permissão administrativa exigida (RBAC); usuário sem permissão → acesso negado;
12. **Auditoria**: eventos com destinatários/resultado, sem segredos;
13. **Não regressão**: suíte existente 100% verde (Constitution VIII).

---

## 15. Critérios de Aceite

- [ ] Movimentação concluída dos tipos `ALOCACAO_CAUTELA`, `TRANSFERENCIA_LOCAL` e `DEVOLUCAO_ESTOQUE` gera automaticamente notificação por e-mail quando ativada (RN-002);
- [ ] Envio ocorre somente após persistência bem-sucedida;
- [ ] Falha de e-mail não cancela/invalida a movimentação e não gera erro ao operador;
- [ ] Destinatários e ativação configuráveis pela administração (padrão visual e permissões existentes);
- [ ] Conteúdo do e-mail identifica corretamente a movimentação (FR-008);
- [ ] E-mail sem link de consulta nesta versão; modelo preparado para o link futuro;
- [ ] Falhas de envio registradas (estado + auditoria, sem segredos);
- [ ] Eventos de auditoria conforme Seção 10;
- [ ] Credenciais SMTP não expostas em lugar algum;
- [ ] Proteção contra notificações duplicadas (1 por movimentação);
- [ ] Testes automatizados dos cenários da Seção 14; suíte existente verde;
- [ ] Regras patrimoniais, tipos de movimentação e RBAC inalterados;
- [ ] Sistema 100% operante com serviço de e-mail indisponível;
- [ ] Somente os arquivos necessários alterados; documentação atualizada.

---

## 16. Arquivos/Módulos Provavelmente Afetados (estimativa — confirmar no plan)

| Área | Arquivo/providência | Natureza |
|---|---|---|
| Novo serviço de notificação | `app/services/` (novo módulo) | criação |
| Novo provedor de e-mail | `app/services/` (novo módulo isolado) | criação |
| Novo modelo de registro de notificação | `app/models/` (novo) + mecanismo aditivo do banco (F8) | criação aditiva |
| Ponto de disparo | `app/services/movement_service.py` — chamada pós-commit | alteração pontual |
| Configuração de ambiente | `app/config.py` — variáveis `SMTP_*` (bootstrap) | alteração aditiva |
| Configuração persistida | serviço/modelo da configuração (precedente F5) | criação |
| Tela de configuração | administração (padrão 021/022) — rota + template | alteração aditiva |
| Auditoria | `app/services/audit_service.py` — constantes + rótulos | alteração aditiva |
| Testes | novo módulo de testes | criação |
| Documentação | README/docs/ajuda | atualização |

Nenhum arquivo é alterado fora do necessário; nenhuma regra de movimentação, tipo, RBAC ou tela não relacionada é modificada.

---

## 17. Pendências de Decisão (não inventadas — registradas para revisão)

- **P-1 (política de retry)**: a v1 não terá reenvio automático agendado (FR-017): o registro guarda tentativas/estado/erro para viabilizar retry futuro, mas a política (frequência, limite, gatilho — ciclo do backup? worker?) é decisão de negócio que deve ser tomada em spec própria. **Default adotado nesta spec: sem retry automático na v1.**
- **P-2 (lote de importação CSV) — RESOLVIDA (Clarifications 2026-09-23)**: decisão confirmada pelo negócio — lote da importação CSV **não gera e-mail na v1**; eventual e-mail-resumo do lote fica para feature futura.
- **P-3 (alcance de tipos) — RESOLVIDA (Clarifications 2026-09-23)**: o negócio decidiu notificar **apenas os 3 tipos principais** (`ALOCACAO_CAUTELA`, `TRANSFERENCIA_LOCAL`, `DEVOLUCAO_ESTOQUE`); os demais tipos permanecem sem e-mail nesta versão (ver RN-002/FR-004).

---

## Assumptions

- O sistema possui um servidor SMTP institucional disponível no ambiente de produção (dados fornecidos via `.env` pelo administrador do servidor);
- O volume de movimentações manuais é compatível com envio síncrono pós-commit com timeout curto (fila assíncrona é evolução futura);
- Os endereços do setor de Patrimônio são caixas institucionais gerenciadas fora do sistema (o sistema não cria/gerencia caixas postais);
- O default desativado (RN-006) é aceitável como estado inicial de implantação;
- A configuração persistida segue o precedente F5 (singleton + fallback de ambiente), sem introduzir nova arquitetura de configuração.
