# Feature Specification: Aviso de sobrescrita na re-conferência de inventário

**Feature Branch**: `003-aviso-reconferencia`

**Created**: 2026-09-15

**Status**: Draft — aguardando revisão do responsável antes de `/speckit.plan`

**Input**: User description: "003 — Aviso de sobrescrita na re-conferência de inventário. A re-conferência de itens de inventário (enquanto PLANEJADO/EM_ANDAMENTO) é intencional e deve permanecer. O problema é exclusivamente de experiência de interface: os modais de conferência do detail.html abrem o formulário diretamente, sem deixar claro que o preenchimento poderá substituir uma conferência anterior (sobrescrita silenciosa). Quando o item já tiver sido conferido, informar quem conferiu, quando, qual foi o resultado anterior e que um novo registro substituirá o anterior; exigir confirmação explícita antes do envio. Itens PENDENTE continuam exatamente como hoje. Inventário ENCERRADO permanece travado como está. Alteração exclusivamente de frontend (detail.html e, se necessário, conferir.html). Nenhuma alteração de backend: rotas, services, record_check, modelos, banco, migrações, permissões, autenticação, AD, auditoria permanecem intactos."

---

## 1. Contexto do Sistema Existente (análise obrigatória — verificada no código)

Esta feature **não é greenfield**. A análise confirmou que **todos os dados necessários já chegam aos templates** e que **todo o mecanismo de gravação permanece como está** — a mudança é exclusivamente na camada de apresentação:

| Mecanismo existente | Onde está | Evidência verificada | Papel nesta feature |
|---|---|---|---|
| Modais de conferência por item | `app/web/templates/inventarios/detail.html` — loop `{% for item in expected_itens %}`, um modal por item (`id="modalConferir{{ item.id }}"`), com `<form method="post" action="/inventarios/{{ inv.id }}/conferir/{{ item.id }}">` | Renderizados apenas quando `{% if inv.status.value != 'ENCERRADO' and can_conferir %}`; o corpo abre direto no formulário, **sem nenhum aviso** de resultado anterior | **Único ponto de alteração obrigatória** |
| Dados históricos já disponíveis no template dos modais | Mesmo objeto `item` usado na listagem da página | A listagem já exibe `item.status` (badge), `item.checked_by_name` + `item.checked_at` (linha de metadados, com guard condicional), `item.observation` e `item.found_location_name` | Nenhuma variável nova é necessária para o alerta |
| Página de conferência em campo | `app/web/templates/inventarios/conferir.html` (rota GET `conferir_asset_page` em `app/web/routes.py`) | Já exibe alerta informativo para itens ≠ PENDENTE: "Resultado já registrado: {status.label} ({found_location_name}) — pode ser atualizado abaixo…", **sem** conferente/data — que também já estão disponíveis no contexto da página | Complementar o alerta existente; **sem refatoração** |
| Rota de gravação (inalterada) | `POST /inventarios/{inventario_id}/conferir/{item_id}` → `confer_item` (`app/web/routes.py`) → `InventarioService.record_check` | Sobrescreve `status`, `found_location_*`, `observation`, `checked_by_id/name`, `checked_at` e grava auditoria com antes/depois | Consumido como está — nenhum novo endpoint ou service |
| Bloqueio de inventário encerrado (inalterado) | `record_check` levanta `ValueError("Este inventário está encerrado…")`; `detail.html` não renderiza os modais; `conferir.html` mostra alerta de trava e omite o formulário | Garantia definitiva permanece no backend | Preservado 100% — nada a mudar |
| Regra de re-conferência (inalterada) | `docs/doc_proviśorios/REGRAS_DE_NEGOCIO_INVENTARIO.md` seção 4 | Permitida enquanto o inventário estiver aberto; A conferência anterior vigente é representada pelos campos atuais do item (status, checked_by_name, checked_at, etc.); o histórico completo de alterações permanece disponível na trilha de auditoria. | Preservada — a feature só a torna visível e deliberada |

**Documentos de decisão de produto** (base desta especificação — localizados em `docs/doc_proviśorios/`, não em `docs/`):

- `DECISAO_RECONFERENCIA_INVENTARIO.md` — decisão final de 14/09/2026: **cenário 3 adotado** (re-conferência permitida + confirmação explícita de sobrescrita + aviso do conferente anterior, mantendo o travamento no encerramento). O versionamento de conferências no banco (cenário 4) foi **explicitamente descartado**.
- `REGRAS_DE_NEGOCIO_INVENTARIO.md`, seção 4 — regra da re-conferência e validações por resultado.
- `AUDITORIA_FUNCIONALIDADE_INVENTARIO.md` — auditoria da funcionalidade, incluindo o risco de sobrescrita silenciosa entre conferentes.
- `IMPLEMENTACAO_AVISO_RECONFERENCIA.md` — planejamento conceitual desta mesma feature (declara explicitamente "nada foi implementado no código").

**Conclusão da análise**: o problema é real (sobrescrita silenciosa nos modais do `detail.html`) e é **totalmente solucionável no template/JavaScript**, pois `item.status`, `item.checked_by_name` e `item.checked_at` já estão disponíveis no contexto de renderização dos modais. Nenhuma alteração de backend é necessária ou permitida.

---

## 2. User Scenarios & Testing

### User Story 1 - Conferente vê a conferência anterior antes de preencher o formulário (Priority: P1)

Um usuário com permissão de conferir abre o modal de conferência de um item que **já possui resultado** (por exemplo, conferido por outro conferente dias antes). Antes de preencher qualquer campo, ele vê um alerta visual informando quem realizou a conferência anterior, quando ocorreu e qual foi o resultado — e que registrar um novo resultado **substituirá** o anterior. Com essa informação, ele pode decidir conscientemente se vale a pena registrar novamente (ou confirmar o resultado existente sem nova gravação).

**Why this priority**: é o cerne da decisão de produto — eliminar a sobrescrita silenciosa expondo o histórico que hoje fica enterrado na trilha de auditoria. Sem este aviso, a confirmação da US2 perde contexto.

**Independent Test**: com um item já conferido, abrir o modal e verificar que o alerta aparece com os dados disponíveis (conferente, data/hora, resultado anterior); com um item PENDENTE, abrir o modal e verificar que nenhum alerta aparece.

**Acceptance Scenarios**:

1. **Given** um item `PENDENTE`, **When** o usuário abrir o modal de conferência, **Then** o formulário aparece exatamente como hoje: sem alerta de sobrescrita e sem solicitação de confirmação adicional.
2. **Given** um item já conferido (resultado ≠ `PENDENTE`), **When** o usuário abrir o modal, **Then** um alerta visual acima do formulário exibe quem conferiu anteriormente, a data/hora da conferência e o resultado anterior — sempre que esses dados estiverem disponíveis.
3. **Given** um item já conferido, **When** o usuário abrir o modal, **Then** o alerta informa explicitamente que registrar um novo resultado substituirá o resultado anterior.

---

### User Story 2 - Sobrescrita exige confirmação explícita no envio (Priority: P1)

Um usuário preencheu uma nova conferência para um item que já tinha resultado e clica em registrar. O sistema solicita confirmação explícita ("Este item já foi conferido. Registrar um novo resultado vai substituir o anterior. Continuar?"). Se ele cancela, **nada acontece** — nenhum envio, nenhuma alteração, o formulário permanece aberto para revisão. Se ele confirma, a conferência é gravada normalmente pelo fluxo existente.

**Why this priority**: é a barreira que transforma a sobrescrita em ato deliberado — a segunda metade da decisão de produto. É independente do alerta: mesmo sem tê-lo lido, o usuário é impedido de sobrescrever sem intenção.

**Independent Test**: em um item já conferido, submeter o formulário e verificar o diálogo de confirmação; escolher Cancelar e verificar que nenhuma requisição ocorre e nenhum dado muda; escolher Continuar e verificar que a conferência é gravada normalmente.

**Acceptance Scenarios**:

1. **Given** um item já conferido, **When** o usuário tentar enviar uma nova conferência, **Then** ele recebe uma confirmação explícita antes de qualquer envio.
2. **Given** a confirmação exibida, **When** o usuário escolhe Cancelar, **Then** nenhuma requisição é realizada, nenhum dado é alterado e ele permanece no modal/formulário.
3. **Given** a confirmação exibida, **When** o usuário escolhe Continuar, **Then** o formulário é enviado pela mesma rota existente e o comportamento atual de gravação (service, carimbos de quem/quando, auditoria) é preservado.
4. **Given** um item `PENDENTE`, **When** o usuário enviar a conferência, **Then** nenhum diálogo de confirmação aparece e o registro ocorre diretamente.

---

### User Story 3 - Página de conferência em campo informa quem conferiu antes (Priority: P2)

Um usuário que chegou à conferência pela página dedicada (fluxo QR: ficha do bem → conferir) de um item já conferido já vê hoje o aviso "Resultado já registrado… — pode ser atualizado abaixo". Esse aviso passa a incluir também quem realizou a conferência anterior, quando ocorreu e qual foi o resultado, quando esses dados estiverem disponíveis.

**Why this priority**: complemento de consistência — a página já informa o essencial; enriquecer o aviso alinha os dois caminhos de conferência sem alterar comportamento.

**Independent Test**: abrir a página de conferência de um item já conferido e verificar que o aviso existente continua presente e agora menciona conferente, data/hora e resultado anterior quando disponíveis.

**Acceptance Scenarios**:

1. **Given** um item já conferido, **When** o usuário abrir a página de conferência, **Then** o alerta existente é preservado e complementado com quem conferiu, quando e o resultado anterior, quando esses dados estiverem disponíveis.
2. **Given** a mesma página, **When** o item estiver `PENDENTE`, **Then** a apresentação atual (badge "Pendente de conferência") permanece sem alteração.

---

### Edge Cases

- **Conferência anterior sem nome do conferente** (ex.: snapshot nulo após exclusão do usuário): o alerta omite o trecho "por {nome}" e mantém data/hora, resultado anterior e aviso de substituição. **Nada é inventado.**
- **Conferência anterior sem data/hora**: o alerta omite o trecho "em {data/hora}" e mantém o restante.
- **Item ≠ PENDENTE sem nenhum dado histórico**: o alerta mantém o resultado anterior (sempre derivável do status do item) e o aviso de substituição.
- **Usuário cancela a confirmação**: permanece no formulário, com o que digitou preservado, livre para revisar, cancelar o modal ou reenviar.
- **Inventário transita para ENCERRADO entre abrir o modal e enviar**: a garantia definitiva permanece onde está hoje — o service rejeita a gravação. Tratamento adicional de interface para essa corrida está fora do escopo desta feature.
- **Página renderizada antes de outro usuário conferir o item** (página obsoleta): o alerta/confirmação refletem o estado no momento da renderização; essa limitação é aceita e documentada — a trilha de auditoria continua registrando toda sobrescrita com antes/depois (quem, quando, IP), como hoje.
- **Inventário ENCERRADO**: modais de conferência nem são renderizados e a página de conferência mostra o bloqueio — comportamento atual intocado (cenário de teste de regressão, não de nova funcionalidade).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Para itens `PENDENTE`, o modal de conferência DEVE continuar exatamente como atualmente: sem alerta de sobrescrita, sem confirmação adicional e com registro direto do resultado. (CA-01)
- **FR-002**: Para itens com resultado diferente de `PENDENTE`, o modal de conferência DEVE exibir, acima do formulário, um alerta visual informando que já existe uma conferência registrada para o item. (CA-02, CA-03)
- **FR-003**: O alerta DEVE apresentar, sempre que os dados estiverem disponíveis: o nome de quem realizou a conferência anterior, a data/hora da conferência anterior e o resultado anterior. (CA-02)
- **FR-004**: O alerta DEVE afirmar explicitamente que registrar um novo resultado substituirá o resultado anterior. (CA-03)
- **FR-005**: A interface NÃO DEVE inventar informações: qualquer campo histórico ausente é omitido do alerta, nunca preenchido com valor fictício ou genérico. (CA-08)
- **FR-006**: Para itens com resultado diferente de `PENDENTE`, o envio do formulário DEVE ser precedido de uma confirmação explícita com o sentido: "Este item já foi conferido. Registrar um novo resultado vai substituir o anterior. Continuar?", oferecendo as opções de continuar e cancelar. (CA-04)
- **FR-007**: Ao cancelar a confirmação, o sistema NÃO DEVE realizar nenhuma requisição, NÃO DEVE alterar nenhum dado e DEVE manter o usuário no modal/formulário. (CA-05)
- **FR-008**: Ao confirmar, o formulário DEVE ser enviado pelo fluxo existente (mesma rota e mesmo service atuais), preservando integralmente o comportamento atual de gravação, carimbos de quem/quando e auditoria. (CA-06)
- **FR-009**: O alerta informativo existente na página de conferência em campo DEVE ser preservado e DEVE ser complementado — apenas quando os dados estiverem disponíveis — com o conferente anterior, a data/hora e o resultado anterior; nenhuma outra refatoração da página é permitida. 
- **FR-010**: Para inventários `ENCERRADO`, o comportamento atual de bloqueio DEVE permanecer intacto: conferências indisponíveis na interface e garantia definitiva de não alteração no service existente. (CA-07)
- **FR-011**: A implementação NÃO DEVE exigir nenhuma alteração de rotas, services, `record_check`, modelos, banco de dados, migrações, permissões/RBAC, autenticação, AD ou auditoria. (CA-09)
- **FR-012**: A re-conferência DEVE permanecer permitida enquanto o inventário estiver `PLANEJADO` ou `EM_ANDAMENTO` para usuários com a permissão de conferir: a feature não pode bloquear nem dificultar a re-conferência deliberada — apenas torná-la visível e confirmada. (Regra fundamental)

#### Rastreabilidade dos critérios de aceitação

| Critério de aceitação (briefing) | Requisito(s) | User Story |
|---|---|---|
| CA-01 — Conferência inicial (PENDENTE sem alerta/confirm) | FR-001, FR-012 | US1 (cena 1), US2 (cena 4) |
| CA-02 — Identificação da conferência anterior | FR-002, FR-003 | US1 (cena 2) |
| CA-03 — Aviso de substituição | FR-002, FR-004 | US1 (cena 3) |
| CA-04 — Confirmação no envio | FR-006 | US2 (cena 1) |
| CA-05 — Cancelamento | FR-007 | US2 (cena 2) |
| CA-06 — Confirmação positiva | FR-008, FR-011 | US2 (cena 3) |
| CA-07 — Inventário encerrado | FR-010 | Edge case + US3 |
| CA-08 — Ausência de dados históricos | FR-005 | Edge cases |
| CA-09 — Nenhuma alteração de backend | FR-011 | Todas |

### Key Entities *(include if feature involves data)*

- **Item de inventário** (somente leitura nesta feature): possui um resultado vigente (`PENDENTE`, `ENCONTRADO`, `LOCAL_DIFERENTE`, `NAO_ENCONTRADO`, `SEM_IDENTIFICACAO`) e os carimbos da última conferência — conferente (snapshot do nome), data/hora, local encontrado e observação. Nenhum campo novo; nenhum campo alterado.
- **Inventário** (somente leitura nesta feature): estados `PLANEJADO`, `EM_ANDAMENTO`, `ENCERRADO` governam a disponibilidade da conferência, como hoje. Nenhuma transição nova ou alterada.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos modais de conferência de itens já conferidos exibem, antes do preenchimento, as informações disponíveis da conferência anterior (conferente, data/hora e resultado).
- **SC-002**: 100% das tentativas de re-conferência de itens já conferidos são precedidas de confirmação explícita — nenhuma sobrescrita ocorre sem uma ação deliberada do usuário.
- **SC-003**: Todo cancelamento da confirmação resulta em 0 requisições e 0 alterações de dados.
- **SC-004**: Itens `PENDENTE` mantêm o fluxo atual sem nenhum passo adicional (0 cliques/interações extras).
- **SC-005**: 0 ocorrências de informações inventadas na interface quando dados históricos estão ausentes (o alerta omite, nunca preenche).
- **SC-006**: Comportamento de inventário encerrado, regra de re-conferência, trilha de auditoria e demais fluxos do módulo permanecem 100% inalterados, comprovado pela suíte de testes existente executada sem modificações.

---

## Assumptions

- Os dados necessários ao alerta (`status`, `checked_by_name`, `checked_at`) já estão disponíveis no contexto de renderização dos dois templates — verificado no código; nenhuma variável nova precisa ser criada (consequência direta de FR-011).
- O formato de exibição de data/hora segue o padrão já usado na listagem (`dd/mm/aaaa hh:mm`).
- O mecanismo concreto de confirmação (por exemplo, diálogo nativo do navegador ou componente visual já existente no sistema) será definido em /speckit.plan, mas a confirmação explícita é obrigatória e não poderá ser removida ou substituída apenas por um aviso visual. Para itens que já possuem resultado, o usuário deve necessariamente realizar uma ação explícita de Continuar ou Cancelar antes que o formulário seja enviado.
- A permissão necessária para conferir continua sendo a existente (`inventario.conferir`); nenhuma verificação nova é introduzida.
- Ocorrências de "bens não previstos" estão fora do escopo: não são re-conferência e não possuem risco de sobrescrita (par inventário/bem é único).
- O alerta do `conferir.html` é complementado apenas com dados já presentes no contexto da página; se algum dado não estiver disponível lá, aplica-se FR-005 (omitir, nunca inventar).

## Fora de escopo — explicitamente NÃO implementar

Nenhuma alteração em: rotas FastAPI; services; `record_check`; modelos SQLAlchemy; banco de dados; migrações; permissões/RBAC; autenticação; AD; auditoria; estrutura e estados do inventário; regra de re-conferência; regra de encerramento; relatórios; QR Code; RFID; importação; demais funcionalidades do sistema. Nenhuma tabela, campo, endpoint ou permissão novo. Nenhuma modificação na lógica de persistência existente. Nenhuma refatoração de `conferir.html` além do complemento do alerta existente (FR-009) e nenhuma alteração em templates não relacionados.
