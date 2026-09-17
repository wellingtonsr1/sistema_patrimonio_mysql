# Research: Identificador Provisório de Colaborador (feature 010)

**Data**: 2026-09-17 · Todas as decisões verificadas no código real (somente leitura) antes do desenho.

## R1 — Onde vive a geração: **`CustodianService.create`** (service), padrão do precedente `InventarioService.next_code`

- **Decisão**: a geração do `PROV-%06d` acontece exclusivamente no `CustodianService.create` quando `registration_code` chega vazio/ausente (após `strip()`), consultando o maior `PROV-` existente + 1, com loop limitado de retentativa apoiado na constraint `UNIQUE` (rollback → regenerar → inserir).
- **Evidência**: `app/services/inventario_service.py` L32–43 (`next_code`: prefixo + `LIKE` + ordena desc + `int(seq)+1` + formatação) — precedente idiomático do próprio sistema; `custodian_service.create` já valida e comita no service; `Custodian.registration_code` é `unique=True, index=True`.
- **Alternativas rejeitadas**: gerar na rota (viola II/III); sequência/sequence de banco (requer DDL e mudaria a estratégia dos testes SQLite); UUID (contraria o formato fixo `PROV-000001` do input); timestamp (não sequencial, revela momento do cadastro).

## R2 — Marcador da condição provisória: **o próprio prefixo `PROV-`** (sem coluna nova)

- **Decisão**: nada de coluna `is_provisional`/`matricula_status`. Helper `is_provisional(code)` = `code.startswith("PROV-")` no service, usado pelos contextos de template.
- **Rationale**: zero DDL (SC-007/Constitution VII); não existe estado a sincronizar (um `PROV-*` é provisório até ser substituído por valor que não casa com o prefixo); a `String(50)` comporta o formato.
- **Alternativas rejeitadas**: coluna booleana nova (DDL + migration + sincronização de estado + risco de divergência prefixo×flag); tabela separada de colaboradores provisórios (quebra FKs de `assets.custodian_id` e dobra a complexidade — viola o escopo mínimo).
- **Risco aceito e mitigado**: uma matrícula oficial que, por acaso, começasse com `PROV-` (hipótese remota e controlável) — mitigada pela **anti-fabricação** (ninguém digita `PROV-*`: nem oficial, nem provisória), que torna o prefixo exclusivo do sistema.

## R3 — Criação sem matrícula: **`CustodianCreate.registration_code` passa a `Optional[str] = None`**

- **Decisão**: o schema de criação aceita ausência (ou vazio após trim) do campo; o service decide (gera `PROV-*`).
- **Evidência**: `app/schemas/custodian.py` L7 (`registration_code: str`); web `Form(...)` L897; API `CustodianCreate` no `POST /api/v1/custodians`.
- **Alternativas rejeitadas**: novo schema `CustodianCreateProvisional` (duplicaria o contrato e os validadores); rota web separada para "cadastro provisório" (cria dois fluxos para o mesmo cadastro — viola X/escopo mínimo).
- **Retrocompatibilidade**: chamadores que enviam matrícula (`custodian_import_service`, `seed_demo.py`, testes `MAT-xxxx`) continuam idênticos — comportamento inalterado, provado por testes de não-regressão.

## R4 — Substituição `PROV-*` → oficial: **service com guard; web edita somente quando atual é `PROV-*`; API mantém validações atuais**

- **Decisão**: o service permite a mudança de matrícula no `update` quando (i) a atual é `PROV-*` (novo; exige permissão `colaboradores.editar` — a existente) ou (ii) é o caso oficial→oficial **pela API**, que hoje já aceita `registration_code` no `CustodianUpdate` com unicidade (comportamento atual documentado, preservado conforme a spec §4/FR-010). Pela **web**, o POST de edição passa a receber matrícula apenas quando a atual é `PROV-*`; oficiais seguem readonly (estado atual).
- **Evidência**: `routes.py` L933–941 (docstring explícita do bloqueio: "não pode ser alterada pela interface, preservando o vínculo dos bens custodiados"); `PUT /api/v1/custodians/{id}` já aceita o campo com `write_change_audit` before/after (L105–132). O vínculo de bens é por `assets.custodian_id` (FK pelo `id` do colaborador) — substituição in-place preserva custódia.
- **Alternativas rejeitadas**: endpoint dedicado `POST /custodians/{id}/confirmar-matricula` (novo contrato sem necessidade — o fluxo de edição é o caminho natural); liberar edição geral de matrícula (contraria a decisão de design existente registrada no docstring e a spec FR-010).
- **Imutabilidade**: `Movement` guarda FK + snapshot textual da época — a substituição não reescreve nada (Constitution IV/FR-011); termos futuros leem a matrícula viva (`term.html` L56).

## R5 — Concorrência na geração: **max+1 + loop limitado apoiado na `UNIQUE`** (sem mecanismo novo)

- **Decisão**: geração por consulta do maior `PROV-` + 1; em caso de colisão (`IntegrityError` da `UNIQUE`), rollback e regeneração (loop com limite pequeno); persistindo, erro padrão sem registro parcial.
- **Rationale**: compatível com MariaDB (produção) e SQLite (testes) sem criar mecanismo novo; a `UNIQUE` é a garantia final (nenhum duplicado pode ser gravado); a janela de colisão é ínfima (cadastros simultâneos de colaboradores são raros) e o retentativa a resolve.
- **Alternativas rejeitadas**: `SELECT ... FOR UPDATE` na tabela inteira (serializa cadastros de colaboradores — overkill e diferente entre SQLite/MariaDB); coluna de sequência dedicada (DDL); fila de geração (arquitetura nova).

## R6 — Marcação visual: **badge do padrão Bootstrap existente** + helper no service

- **Decisão**: onde a matrícula viva é exibida (lista/detalhes/form de colaboradores, seleção em movimentação, detalhe/lista de bens, termo), colaborador provisório recebe marcação textual "provisória" com o padrão visual atual (badge, como usados nas telas).
- **Evidência**: templates usam badges Bootstrap em vários contextos (ex.: status de bens/inventário); a regra de exibição vem do helper `is_provisional` (R2), sem lógica em template.
- **Alternativas rejeitadas**: mudar o formato exibido (ex.: mascara `PROV-000123` como "—" — esconde informação que o operador precisa); popup/toast (não persiste na leitura do documento — o termo precisa da marcação no papel).

## Verificações pontuais (fatos, não decisões)

| Fato | Evidência |
|---|---|
| `registration_code` é `String(50) unique not null index` | `app/models/custodian.py` L13 |
| Criação exige matrícula hoje (web, API, CSV) | `schemas/custodian.py` L7; `routes.py` L897; `custodian_import_service.py` L4–5 ("matricula (obrigatório)") |
| Edição web não aceita matrícula; API aceita com unicidade | `routes.py` L956–972 (POST de edição sem o campo; docstring do GET); `custodians_api.py` L105–132 |
| Movimentação: FK por id + snapshot textual | `app/models/movement.py` L26–35; `movement_service.py` L44/L59 |
| Termo exibe matrícula viva | `movements/term.html` L55–56 |
| Inventário usa só snapshot de nome | `app/models/inventario.py` L94 |
| AD casa matrícula == username | `app/services/ad_service.py` L213 |
| Auditoria já existe nos caminhos de criação/alteração | `custodians_api.py` L62/L97/L125; `routes.py` L918 (create web) |
| Precedente de geração sequencial | `inventario_service.py` L32–43 |
| Baseline da suíte | 281 passed / 1 failed (lockout defasado) — sessões de 2026-09-16/17 |
