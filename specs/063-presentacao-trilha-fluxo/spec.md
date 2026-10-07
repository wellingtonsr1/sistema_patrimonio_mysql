# Feature Specification: Padronização da Apresentação de Origem e Destino na Trilha de Fluxo & Movimentações

**Feature Branch**: `063-presentacao-trilha-fluxo`

**Created**: 2026-10-06

**Status**: Draft

**Input**: Corrigir exclusivamente a apresentação visual de "Origem" e "Destino" na seção "Trilha de Fluxo & Movimentações" da janela do equipamento, padronizando-a com o padrão já aceito da seção "Custódia & Localização Atual". A SPEC 062 (`062-selecao-departamento-destino`) já foi implementada e NÃO deve ser refeita, revertida ou modificada. Mudança de APRESENTAÇÃO (somente template): o snapshot gravado, o identificador enviado e todo o histórico permanecem intocados, com teste de não-mutação.

---

## 1. Contexto e análise do sistema atual (somente leitura, verificada nesta especificação)

| # | Ponto investigado | Realidade verificada |
|---|---|---|
| 1 | Seção "Custódia & Localização Atual" (padrão desejado) | `app/web/templates/assets/detail.html` L109–114: título `{{ asset.location.name }}` (ex.: `Sede - Divisão de Previdência`) + linha secundária `{{ asset.location.branch }} • {{ asset.location.department }}` (ex.: `IPMJP - Sede • Divisão de Previdência`) |
| 2 | Seção "Trilha de Fluxo & Movimentações" (problema) | Mesmo template, L257–268: `flow-value` exibe `{{ item.data.origin_location_name or 'Estoque Geral' }}` e `{{ item.data.destination_location_name or 'Estoque Geral' }}` — ex.: `IPMJP - Sede - Divisão de Previdência (Sede - Divisão de Previdência)` |
| 3 | Origem do texto redundante | O snapshot `origin_location_name`/`destination_location_name` é gravado no formato `f"{branch} - {department} ({name})"` (`movement_service.py` L136/L148). Como o `name` do local já contém unidade+setor (ex.: `Sede - Divisão de Previdência`), a exibição atual mostra o dado 2× |
| 4 | Fonte da trilha | `view_asset_detail` (`app/web/routers/assets.py` L478/L497) passa `timeline = MovementService.get_timeline_for_asset(db, asset_id)` ao template |
| 5 | O que o snapshot realmente guarda | `Movement` guarda `origin_location_id`/`destination_location_id` (FK) + snapshots de texto imutáveis. O template recebe o objeto `Movement` completo — incluindo as relações `origin_location`/`destination_location` (joinedload em `get_timeline_for_asset`, `movement_service.py` L417–422) — mas hoje só exibe os snapshots de texto |
| 6 | Colaborador exibido | `flow-sub` exibe `origin_custodian_name`/`destination_custodian_name` (snapshot `Nome (Matrícula)`) — permanece como está |
| 7 | Outras telas que exibem os mesmos snapshots | `movements/list.html` L129/133, `dashboard.html` L287, `reports/movements_report.html` L92/96, termo (`get_term_details` L613), busca 049 — TODAS fora do escopo desta spec (recebem o snapshot cru e têm formatação própria aprovada) |
| 8 | Dropdown "Novo Local / Departamento" | Já padronizado pela Feature 062 (optgroups por unidade + rótulo `Departamento (Unidade)`); testado por `tests/test_departamento_destino_062.py` — intocado |
| 9 | Departamento no cadastro | `Location.department` (`String(100)`, NOT NULL, texto livre) — fonte do setor; `Custodian.department` é coluna distinta, sem FK entre si (não unificar) |
| 10 | Dados de produção (2026-10-06) | 36 localizações; `department` NOT NULL; typos registrados (`Acessoria`, `Assist}ência`, branch `IPMJP – Sede` com travessão) — higiene de dados fora do escopo |
| 11 | Testes existentes | NENHUM teste trava o TEXTO exibido na trilha do `assets/detail.html`; os testes travam o FORMATO do snapshot gravado (`test_import_asset_movements.py` L134/L216) e a renderização dos dropdowns 062 — permanecem verdes sem edição |
| 12 | Ajuda central | A trilha do equipamento não tem artigo que descreva o formato atual de Origem/Destino (sem atualização obrigatória de ajuda) |

**Consequências da análise** (refletidas nos requisitos):

- O template já recebe, junto com cada movimentação da timeline, as **relações** `origin_location`/`destination_location` (objetos `Location` completos, com `name`, `branch`, `department`) — carregadas por joinedload no service. A padronização visual pode usar essas relações quando existirem, **sem nenhuma consulta nova e sem tocar o backend**.
- Quando a relação não existir (local excluído do cadastro, registro sem FK), o **snapshot de texto** continua sendo a fonte da apresentação — o significado histórico nunca se perde (Princípio IV da Constitution).
- Portanto a proposta é realizável como **alteração de apresentação**: 1 template + testes, **zero DDL, zero backend, zero migração** (Princípio I da Constitution).
- A guarda da feature é **não alterar gravação, histórico, busca e dropdown 062**, comprovada por teste de não-mutação.

---

## 2. Problema e Objetivo

### Problema

Existe inconsistência visual e semântica dentro da **mesma janela** do equipamento:

| Seção | Apresentação hoje |
|---|---|
| Custódia & Localização Atual (referência) | **Sede - Divisão de Previdência** / `IPMJP - Sede • Divisão de Previdência` |
| Trilha de Fluxo & Movimentações (problema) | **IPMJP - Sede - Divisão de Previdência (Sede - Divisão de Previdência)** / Jackceline Dias (PROV-000074) |

A trilha atual gera: (1) duplicação de informação; (2) excesso de texto; (3) inversão da prioridade visual (a unidade aparece antes do setor); (4) dificuldade para identificar rapidamente o setor de origem/destino; (5) duas representações diferentes para o mesmo conceito na mesma janela; (6) dificuldade para visualizar o fluxo real `Setor de Recadastramento → Divisão de Previdência`.

### Objetivo

Apresentar cada ponto de Origem/Destino da trilha no mesmo padrão da seção "Custódia & Localização Atual":

```
## Origem
Setor de Recadastramento          ← Departamento/Setor (linha principal)
Sede • IPMJP - Sede               ← Localização • Unidade Administrativa (contexto)
Jackceline Dias (PROV-000074)     ← colaborador (inalterado)

## Destino
Divisão de Previdência
Sede • IPMJP - Sede
Jackceline Dias (PROV-000074)
```

A leitura deve permitir identificar imediatamente `Setor de Recadastramento → Divisão de Previdência`, sem perder a localização física e a unidade administrativa.

---

## 3. User Scenarios & Testing

### User Story 1 - Trilha de Fluxo com a mesma linguagem visual da Custódia (Priority: P1) 🎯 MVP

Um usuário com permissão de visualizar patrimônio abre o detalhe de um equipamento com movimentações e, na seção "Trilha de Fluxo & Movimentações", lê cada Origem e Destino no formato `Departamento/Setor` (destaque) + `Localização • Unidade Administrativa` (contexto) + colaborador — o mesmo padrão da seção "Custódia & Localização Atual" exibida logo acima na mesma página. Nenhuma tela, filtro, dropdown ou gravação muda.

**Why this priority**: É o núcleo do pedido — eliminar a duplicação e a inversão de prioridade visual dentro da mesma janela.

**Independent Test**: Renderizar `/assets/{id}` com uma transferência registrada entre locais de dados conhecidos → Origem e Destino exibem o setor como título e `Localização • Unidade` como contexto; o restante da página permanece idêntico.

**Acceptance Scenarios**:

1. **Given** um equipamento com uma movimentação registrada entre dois locais, **When** o detalhe é aberto, **Then** a Origem exibe o Departamento/Setor como linha principal e `Localização • Unidade` como contexto.
2. **Given** o mesmo detalhe, **When** o Destino é lido, **Then** segue o mesmo padrão — ex.: `Divisão de Previdência` + `Sede • IPMJP - Sede`.
3. **Given** o mesmo detalhe, **When** a seção "Custódia & Localização Atual" é comparada, **Then** as duas seções usam a mesma hierarquia visual (setor em destaque, contexto físico abaixo).
4. **Given** o texto antigo redundante, **When** a página é renderizada, **Then** o formato `IPMJP - Sede - Divisão de Previdência (Sede - Divisão de Previdência)` não aparece mais na trilha.

### User Story 2 - Integridade do histórico, da busca e do dropdown 062 (Priority: P1)

Qualquer usuário — inclusive auditoria — continua vendo o histórico com o mesmo significado: os snapshots gravados não são regravados nem reformatados, a busca de movimentações encontra pelos mesmos termos, o dropdown "Novo Local / Departamento" continua exatamente como a Feature 062 o entregou, e novas movimentações gravam no formato atual.

**Why this priority**: É a guarda da feature (Princípio IV da Constitution — trilha imutável) e condição para a US1 ser segura.

**Independent Test**: Registrar uma transferência após a mudança e comparar, campo a campo, com o formato gravado antes: FK, snapshot, busca e dropdown idênticos; registros anteriores intocados.

**Acceptance Scenarios**:

1. **Given** movimentações já existentes, **When** qualquer tela de histórico/termo/relatório/dashboard/busca é exibida, **Then** os textos exibidos têm o mesmo significado e os snapshots no banco permanecem byte-a-byte idênticos (nada é regravado nem reformatado).
2. **Given** uma movimentação nova registrada após a feature, **When** seu destino é gravado, **Then** o formato do snapshot gravado é idêntico ao atual (mesmo padrão já travado pelos testes existentes).
3. **Given** a busca de movimentações (Feature 049), **When** o usuário pesquisa por um termo que casava antes, **Then** o mesmo registro continua sendo encontrado.
4. **Given** o dropdown "Novo Local / Departamento" em `/movements/new` e `/assets/new`, **When** o formulário é renderizado, **Then** grupos, rótulos, values e opções vazias são idênticos ao entregue pela Feature 062 (testes da 062 verdes sem edição).

### Edge Cases

- **Departamento vazio ou só espaços**: impossível nos dados atuais (`department` é NOT NULL); mesmo assim, a apresentação NÃO cria texto artificial — sem `undefined`, `null`, `-` ou parênteses vazios; usa a melhor identificação disponível (snapshot/relação) e exibe só o contexto quando o setor não existir.
- **Localização com nome igual ao Departamento** (ex.: `Shopping 4400` / department `Shopping 4400`): a apresentação NÃO produz duplicação (`Shopping 4400 - Shopping 4400` nunca aparece; o nome repetido é exibido uma única vez).
- **Unidade Administrativa igual à Localização**: sem repetição desnecessária — o contexto exibe cada valor uma única vez.
- **Registro sem localização / FK quebrada (local excluído)**: o fallback atual (`Estoque Geral` / snapshot de texto) é preservado; a página não quebra e não inventa setor.
- **Movimentação de entrada (origem literal `Fornecedor / Entrada Inicial`)**: texto sem estrutura `branch - department (name)` é exibido como está (linha principal = o próprio snapshot; sem contexto artificial).
- **Dados históricos antigos**: preservam integralmente o significado — a mudança é só de apresentação; nenhum registro é alterado.
- **Todos os tipos de movimentação** (entrada, cautela, transferência, manutenção, devolução, baixa, atualização): o mesmo padrão se aplica, sem exceção nem mudança de modelo.

---

## 4. Requirements

### Functional Requirements

- **FR-001**: A seção "Trilha de Fluxo & Movimentações" DEVE apresentar Origem e Destino com o **Departamento/Setor como identificação principal** (linha de destaque) e **`Localização • Unidade Administrativa` como contexto** (linha secundária), no mesmo padrão visual da seção "Custódia & Localização Atual" (Princípio X da Constitution).
- **FR-002**: A apresentação DEVE derivar dos dados JÁ carregados na timeline (relações `origin_location`/`destination_location` e snapshots `origin_location_name`/`destination_location_name`); NENHUMA consulta nova, endpoint novo ou campo novo é criado.
- **FR-003**: O sistema NÃO DEVE alterar o formato dos snapshots gravados nas movimentações (`"{branch} - {department} ({name})"`) — nem para novos registros, nem para antigos (US2).
- **FR-004**: O sistema NÃO DEVE regravar, reescrever ou reformatar snapshots de movimentações já existentes; a busca (Feature 049), termo, relatórios e dashboard continuam exibindo/consultando os textos originais (Princípio IV da Constitution).
- **FR-005**: O dropdown "Novo Local / Departamento" (`movements/new.html`, `assets/form.html`), o cadastro de Localização e o cadastro de Colaborador permanecem BYTE-A-BYTE inalterados — a Feature 062 não é refeita, revertida nem modificada.
- **FR-006**: A seção "Custódia & Localização Atual" (incluindo o bloco "Localização Física") permanece inalterada.
- **FR-007**: NENHUMA alteração de banco (zero DDL), rotas, permissões, schemas, services, API REST, integrações (1Doc, AD, SMTP) ou auditoria é permitida como consequência desta feature.
- **FR-008**: A apresentação DEVE evitar textos inválidos/artificiais em todos os casos: sem `undefined`, `null`, `-` órfão, parênteses vazios ou separadores duplicados (ver Edge Cases).
- **FR-009**: Toda alteração desta feature DEVE vir acompanhada de testes novos nos padrões existentes, incluindo o teste de não-mutação (US2) e a suíte completa verde (Princípio VIII).
- **FR-010**: Quando o snapshot de texto não seguir o padrão `Unidade - Departamento (Nome)` (ex.: origem literal de entrada), ele DEVE ser exibido como texto único, sem tentativa de decomposição que invente informação.

### Regras (síntese operacional)

- R1 — Somente apresentação: muda o render de Origem/Destino na trilha; NADA muda em valores gravados, contratos, banco, histórico e dropdown 062 (FR-003/FR-004/FR-005/FR-007).
- R2 — Fonte única: os dados já carregados na timeline (relações + snapshots); nada de consulta nova (FR-002).
- R3 — Hierarquia única: `Departamento/Setor` em destaque, `Localização • Unidade` como contexto (FR-001; parágrafo Objetivo).
- R4 — Sem textos artificiais: casos vazios/iguais/sem estrutura caem no melhor dado disponível, nunca em lixo visual (FR-008/FR-010).
- R5 — Não-mutação comprovada: teste específico prova que gravação, snapshots, busca e dropdown 062 permanecem idênticos (US2; FR-003/FR-004/FR-005).

### Key Entities

- **`Movement` (existente, intocada)**: snapshots imutáveis `origin_location_name`/`destination_location_name` + FKs `origin_location_id`/`destination_location_id` + `origin_custodian_name`/`destination_custodian_name`.
- **`Location` (existente, estruturalmente intocada)**: `name`, `branch`, `department` alimentam o novo render quando a relação está disponível.
- **`Asset` (existente, intocado)**: contexto da página (`location_id`, `custodian_id`).
- **`Custodian` (existente, intocado)**: `department` do colaborador NÃO é unificado com o departamento da localização — apenas documentado que são colunas distintas, sem FK.

---

## 5. Success Criteria

### Measurable Outcomes

- **SC-001**: 100% dos itens de movimentação da trilha exibem Origem/Destino no padrão `Departamento/Setor` + `Localização • Unidade` (verificável por inspeção da página renderizada e por teste).
- **SC-002**: O formato redundante `Unidade - Departamento (Nome - Departamento)` não aparece mais na trilha do detalhe do equipamento.
- **SC-003**: Zero alteração no comportamento de gravação: identificador enviado, snapshot gravado, histórico, termo, relatórios, dashboard e busca produzem resultados idênticos aos atuais (comprovado pelo teste de não-mutação).
- **SC-004**: Zero mudança nos dropdowns da Feature 062 (testes `test_departamento_destino_062.py` verdes sem edição) e nas seções "Custódia & Localização Atual" / "Localização Física".
- **SC-005**: Zero DDL, zero mudança de rota/permissão/API/service; suíte completa verde no patamar atual + testes novos da feature.
- **SC-006**: Operador identifica o fluxo `Setor de Origem → Setor de Destino` lendo a trilha — validação com o usuário em smoke visual (print antes/depois).

---

## 6. Assumptions

- O padrão visual de "Custódia & Localização Atual" (`Nome do local` em destaque + `branch • department`) é o aceito pelo negócio e é a referência desta spec; a equivalência com o pedido do usuário (`Departamento` em destaque + `Localização • Unidade`) será resolvida no plan/smoke com dados reais (o `name` atual já contém `unidade - departamento`, o que permite compor o contexto sem consulta nova).
- As relações `origin_location`/`destination_location` já chegam carregadas à template via joinedload (`movement_service.py` L417–422) — nenhuma alteração de service é necessária para usá-las.
- Higiene de dados (typos de `locations.department`/`branch`, drift de `custodians.department`) permanece feature própria (análise de 2026-10-06 §12) — fora do escopo.
- Os demais pontos que exibem snapshots (`movements/list.html`, `dashboard.html`, `reports/movements_report.html`, termo, busca) têm formatação própria aprovada e NÃO fazem parte desta feature.
- Documentação: nenhum artigo da ajuda central descreve o formato atual da trilha — nenhuma atualização obrigatória (verificado).

---

## 7. Impacto esperado (componentes confirmados pela análise — nada inventado)

| Componente | Alteração esperada |
|---|---|
| `app/web/templates/assets/detail.html` (bloco Trilha, L257–268) | **SIM** — render de Origem/Destino no padrão setor-primeiro + contexto; colaborador, badges, termo e motivo inalterados |
| `Custódia & Localização Atual` (mesmo template, L109–114) | **NENHUM** (FR-006) |
| Dropdowns `movements/new.html` e `assets/form.html` (Feature 062) | **NENHUM** (FR-005) |
| Backend (routers, services, schemas) | **NENHUM** — as relações já chegam carregadas à template |
| Banco / migrations | **NENHUM** (zero DDL) |
| `movements/list.html`, `dashboard.html`, `reports/movements_report.html`, termo, busca 049 | **NENHUM** (fora do escopo — formatação própria aprovada) |
| API REST / integrações (1Doc, AD, SMTP) / permissões / auditoria | **NENHUM** |
| Testes | **NOVOS** — renderização da trilha + não-mutação; suíte existente intacta |
| Documentação | **NÃO REQUERIDA** — nenhum artigo descreve o formato atual da trilha (verificado) |

---

## 8. Critérios de Aceitação (rastreabilidade)

| AC | Enunciado | Coberto por |
|---|---|---|
| AC01 | "Custódia & Localização Atual" permanece exatamente como está | US2/AS1; FR-006; SC-004 |
| AC02 | Origem exibe `Departamento/Setor` como título + `Localização • Unidade` + colaborador | US1/AS1; FR-001; SC-001 |
| AC03 | Destino exibe o mesmo padrão | US1/AS2; FR-001; SC-001 |
| AC04 | O formato `IPMJP - Sede - Divisão de Previdência (Sede - Divisão de Previdência)` não aparece mais na trilha | US1/AS4; SC-002 |
| AC05 | Dropdown "Novo Local / Departamento" permanece sem alteração funcional (Feature 062 intacta) | US2/AS4; FR-005; SC-004 |
| AC06 | Nenhum registro histórico é alterado | US2/AS1; FR-004; SC-003 |
| AC07 | Nenhuma alteração desnecessária no banco de dados | FR-007; SC-005 |
| AC08 | A solução reutiliza os dados já carregados na timeline (sem duplicar lógica nem criar consulta nova) | FR-002; SC-005 |
| AC09 | Casos especiais (campos vazios, nomes iguais, entrada literal) não geram textos inválidos | Edge Cases; FR-008/FR-010 |

---

## 9. Riscos

| # | Risco | Mitigação |
|---|---|---|
| 1 | Decompor o snapshot com regex/split e inventar informação quando o texto não casa com o padrão | FR-010: snapshot sem estrutura é exibido como texto único; preferência pelas relações `Location` quando existirem |
| 2 | Quebrar a busca 049 mudando o snapshot "para modernizar" | FR-003/FR-004 proíbem; teste de não-mutação (US2) é a sentinela |
| 3 | Arrastar a mudança para as outras telas que exibem snapshots (lista, dashboard, relatório, termo) | Fora do escopo declarado (§10); cada tela tem formatação própria aprovada — feature própria se houver demanda |
| 4 | Divergência visual entre `name` do local e contexto montado (dados com typos) | Higiene de dados é feature própria; a apresentação exibe o que existe, sem normalizar (edge case) |
| 5 | Alterar acidentalmente o bloco "Custódia & Localização Atual" ao editar o mesmo template | AC01/SC-004 com teste de renderização específico; diff restrito ao bloco da trilha (T de revisão de escopo) |

---

## 10. Escopo

### Incluído

- Padronização do render de **Origem** e **Destino** na "Trilha de Fluxo & Movimentações" do `assets/detail.html` (setor-primeiro + `Localização • Unidade` + colaborador inalterado);
- Preservação explícita dos fallbacks atuais (`Estoque Geral`, `Nenhum`, snapshot cru quando sem estrutura);
- Testes de renderização e de não-mutação (gravação, busca, histórico, dropdown 062).

### Não incluído (limites de escopo)

- Qualquer alteração de banco, backend, API, permissões, migração ou integrações (FR-007);
- Alteração do formato dos snapshots de movimentação (presente ou passado) (FR-003/FR-004);
- As demais telas que exibem snapshots (`movements/list.html`, `dashboard.html`, `reports/movements_report.html`, termo) — formatação própria aprovada, feature própria se houver demanda;
- Dropdown "Novo Local / Departamento" e selects da Feature 062 — intocados (FR-005);
- Seção "Custódia & Localização Atual" e "Localização Física" — intocadas (FR-006);
- Higiene/normalização de dados (typos, travessão, drift de colaboradores) — feature própria;
- Entidade de departamentos / unificação `Custodian.department` × `Location.department` — não prevista; relacionamento apenas documentado.

> **Nota de escopo**: o plano de implementação mínimo (ordem de tarefas, TDD red→green, checkpoints) segue o padrão da casa em `tasks.md` desta pasta; a decisão de estrutura técnica fina fica para o `/speckit-plan`.

*Esta especificação descreve SOMENTE o comportamento desejado e a análise verificada do código atual. Nada foi implementado — nenhum template, model, service, rota ou teste foi alterado na elaboração deste documento.*
