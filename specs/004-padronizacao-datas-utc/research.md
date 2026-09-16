# Research: Padronização de Data e Hora (UTC na persistência, America/Recife na apresentação)

**Feature**: 004-padronizacao-datas-utc | **Date**: 2026-09-15
**Base**: análise do código-fonte existente + `docs/ANALISE_DATAS_HORARIOS.md` (69 ocorrências,
28 colunas `DATETIME`). Cada decisão abaixo foi **re-verificada no código atual** nesta sessão —
linhas citadas confirmadas.

---

## R1 — Como implementar a geração centralizada de UTC (FR-001/FR-002)

**Decision**: módulo novo `app/utils/time_utils.py` com `now_utc() -> datetime` (naive, UTC), que
passa a ser o único mecanismo de "agora persistível". Os pontos que gravavam hora local migram para
ele; os defaults dos models (`default=datetime.utcnow`) permanecem como estão — já produzem UTC e
tocá-los é alteração sem ganho.

**Rationale**:
- O relatório irmão mapeou exatamente os pontos em hora local: `movement_service.py:116,130`,
  `asset_service.py:147,178,224`, `import_service.py:490,506` — todos confirmados nesta sessão.
- Models: todos os 19 defaults já usam `datetime.utcnow` (ex.: `app/models/movement.py:22,47` —
  verificado), exceto o fallback de `asset_service.py:147`/`import_service.py:490`, que alimenta
  `purchase_date` (data de negócio — ver R6).
- `zoneinfo.ZoneInfo("America/Recife")` está disponível (stdlib + `tzdata` no ambiente, testado OK
  conforme seção F do relatório irmão).
- A `spec` exige mecanismo único e proíbe `datetime.now()`/`datetime.utcnow()` espalhados em
  caminhos novos/modificados (FR-002, SC-009): um helper central com varredura verificável atende.

**Alternativas consideradas**:
- *Trocar os defaults dos models para o helper* — rejeitada: mesmo resultado (UTC naive), maior diff,
  risco de regressão em 19 pontos sem ganho de convenção (o contrato de valor persistido não muda).
- *Usar `datetime.now(timezone.utc)` (aware)* — rejeitado: colunas `DATETIME` sem fuso truncam/
  ignoram `tzinfo` de forma diferente por dialect (PyMySQL/SQLite), criando risco silencioso;
  a convenção do projeto (FR-018) é naive-UTC.
- *Confiar só nos defaults do model e remover os overrides* — rejeitada: `Movement.timestamp` é
  `nullable=False` com default, mas os services passam valor explícito; remover o override alteraria
  o instante de criação (flush vs. call) e espalharia a decisão pelos models.

## R2 — Como converter UTC → America/Recife na apresentação (FR-003/FR-004/FR-005)

**Decision**: no mesmo módulo, `utc_to_recife(dt) -> datetime`: recebe naive (ou aware) e o trata
como UTC por convenção (FR-018), anexa `ZoneInfo("UTC")` e converte para
`ZoneInfo("America/Recife")` com `astimezone`; `None` → `None` (template mantém o "—" / "Nunca"
atual). Registro do filtro Jinja em `app/web/routes.py`, junto dos globals existentes (linhas
120–125 confirmadas): `templates.env.filters["localtime"] = ...` e alias global
`templates.env.globals["localtime"]`.

**Rationale**:
- Ponto central único de registro (Jinja2Templates já é instanciado em `routes.py:112–116`); nenhuma
  lógica de fuso duplicada por tela (FR-006).
- Fuso nomeado (não −3h fixo) — exigência da spec (edge case + SC-008) e do relatório irmão.
- `None`-safe: 100% dos pontos de template atuais já fazem guard (`{% if ... %}` ou
  `if ... else`) — confirmado nos 12 pontos mapeados; o filtro só precisa não quebrar com `None`.
- Sem dupla conversão: contrato do filtro (ver `contracts/presentation-contract.md`) — entrada é
  sempre o valor bruto do banco; nenhum ponto converte e depois passa pelo filtro de novo.

**Alternativas consideradas**:
- *Filtro que também formata (`localtime(value, fmt)`)* — adotada variante mínima: o filtro retorna
  o `datetime` convertido e o template mantém o `.strftime(...)` atual, preservando exatamente o
  formato visual (premissa da spec). Um segundo helper de formatação ficaria disponível para os
  exports do `report_service`, que formatam em Python.
- *Context processor injetando helper global* — rejeitada: filtro é o mecanismo idiomático Jinja
  para transformar valores; globals são para constantes/funções puras.
- *Converter no browser via JS* — proibida pela spec (scope protection).

## R3 — Quais templates mudam e quais ficam intocados

**Decision**: converter **somente** os pontos cuja origem é (ou passa a ser) UTC:

- **Origem UTC hoje (exibem +3h — o sintoma da US1)**: `admin/audit/list.html:85`
  (`log.timestamp`, HH:MM:SS — segundos preservados); `inventarios/detail.html:14,192,239,275,277,280,307`;
  `inventarios/list.html:72`; `inventarios/conferir.html:65`; `admin/users/list.html:101`;
  `admin/users/edit.html:23,100,116`; `maintenances/list.html:39` (`m.start_date` — ver R5).
- **Origem passará a ser UTC (US2)**: `movements/list.html:69`, `dashboard.html:258`,
  `reports/movements_report.html:48`, `assets/detail.html:216,249` (todos `m.timestamp`).
- **Não tocam** (data de negócio): `assets/detail.html:130,136`, `reports/inventory.html:57`
  (`purchase_date`); rodapé `current_year`.

**Rationale**: mapa do relatório irmão (seção E) conferido ponto a ponto nesta sessão via busca
`.strftime` nos templates (19 ocorrências); nenhuma exibição de timestamp ficou de fora da lista
acima. `admin_routes.py:229` (`now` para comparar `locked_until > now` no template) permanece
intocado — é comparação interna UTC×UTC, não exibição (FR-013).

## R4 — Movimentações/Importação: o que muda na gravação (FR-007/FR-008)

**Decision**:
- `movement_service.py:130` (`Movement.timestamp`) e `:116` (`asset.updated_at`) → `now_utc()`.
- `asset_service.py:178,224` (`Movement.timestamp` de entrada inicial e edições) → `now_utc()`.
- `import_service.py:506` (`Movement.timestamp` da entrada CSV) → `now_utc()`.
- `movement_service.py:302` (`term.date` do Termo de Responsabilidade, `strftime` sobre
  `movement.timestamp`) → converte via mecanismo de apresentação (agora imprime Recife).
- Anos de `term_code` (`now().year`/`now().year`-equivalentes em `:124`, `asset_service.py:191`,
  `import_service.py:517`) e `INV-YYYY` (`inventario_service.py:34`): **intocados** (spec: fora do
  escopo).

**Rationale**: elimina a divergência intra-linha (`movements.timestamp` local ×
`movements.created_at` UTC — problema 2 do relatório irmão) e o `assets.updated_at` misto
(problema 3). Após a mudança, ambas as colunas da mesma linha representam o mesmo instante UTC
(SC-003). A apresentação dos carimbos de movimentação muda de "correto por acidente (local)" para
"correto por convenção (UTC→Recife)" — resultado visível idêntico para o usuário.

## R5 — Manutenções: `start_date`/`end_date` são timestamps (classificação da spec confirmada)

**Decision**: tratar `Maintenance.start_date`, `end_date`, `created_at` como **timestamps**
(conforme classificação da spec): gravados em UTC (já são — `maintenance_service.py:41,77` usa
`utcnow`, verificado) e a exibição de `maintenances/list.html:39` (que mostra só a data) passa pelo
filtro de conversão, resolvendo o problema 5 do relatório irmão (OS aberta após 21h local mostra dia
seguinte). O formulário `maintenances/new.html` não tem campo de data (verificado — a data é
gerada pelo sistema), então não há entrada de usuário a preservar neste módulo.

**Rationale**: a spec lista explicitamente essas colunas como "Timestamps (instante)" e exige
validação da classificação contra o código. Verificado: origem do valor é sempre gerada pelo sistema
(`data.start_date or datetime.utcnow()`; o schema `MaintenanceCreate.start_date` é `Optional`), e a
rota web não recebe data (formulário sem campo de data, confirmado). Divergência nenhuma a registrar.

## R6 — Datas de negócio permanecem intocadas (FR-014 / US3)

**Decision**: `purchase_date` e `warranty_expiry` não recebem conversão alguma; os filtros de
compra (strptime `%Y-%m-%d` em `routes.py:321–322,634–635,1480–1481` e `api/reports_api.py:52–53,
96–97,140–141`) permanecem comparando datas puras, como hoje (FR-010, 2ª parte).

**Rationale**: comparadores de data pura são imunes a fuso; tocar neles seria violar o scope
protection. Fallbacks `datetime.now()` para `purchase_date` (`asset_service.py:147`,
`import_service.py:490`) ficam como estão: são data de negócio (fallback "hoje"), não instante
sistêmico; alterá-los os deslocaria um dia perto da meia-noite (UTC) sem ganho semântico.

## R7 — Filtros de período sobre timestamps (FR-010 / US5)

**Decision**: na API de movimentações (`movements_api.py:20–21` + `movement_service.py:272–275`),
`start_date`/`end_date` informados em horário local são convertidos local→UTC antes da comparação
com `Movement.timestamp` (agora UTC). Quando o cliente informar datetime com offset explícito
(ISO-8601 com `Z`/±hh:mm), o valor é respeitado (já é absoluto) e não recebe conversão adicional.
Filtros de data pura (compra) não mudam (R6).

**Rationale**: hoje o filtro "funciona por coincidência" (local informado × local gravado — seção
G.7 do relatório irmão). Com a gravação migrando para UTC, o filtro sem conversão deslocaria −3h o
resultado. A conversão usa o mesmo fuso nomeado (`America/Recife`), sem offset fixo. O endpoint de
API recebe `datetime` (FastAPI/Pydantic fazem o parsing; offsets explícitos produzem valores aware).

**Alternativas consideradas**:
- *Converter no cliente (JS)* — proibida (scope protection).
- *Mudar o schema Pydantic para aceitar string e converter no service* — rejeitada: mudança de
  contrato da API sem necessidade; a conversão é aplicada no limite de uso (service), preservando o
  schema.

## R8 — Testes existentes e não-regressão (FR-015/FR-016)

**Decision**: suíte intacta, com dois ajustes cirúrgicos obrigatórios em
`tests/test_inventario_reconferencia_ui.py:133` e `:245` — as asserções
`item.checked_at.strftime("%d/%m/%Y %H:%M") in html` passam a comparar o valor **convertido para
Recife** (`utc_to_recife(item.checked_at).strftime(...)`), pois a página agora exibe o horário local.
Os demais testes que usam `utcnow` (`test_auth.py:175`, `test_cli_reset_password.py:120,127,184,431`,
`test_assets.py:10`) continuam válidos: comparam origem com origem em UTC e nenhum deles valida
apresentação. `test_inventario.py:109,221` só checa `is not None` — intacto.

**Rationale**: FR-016 permite atualizar apenas testes diretamente dependentes do padrão antigo,
sem enfraquecer cobertura — as duas asserções continuam pegando regressão de exibição (agora da
conversão). Alinhado ao Princípio VIII da Constitution.

## R9 — Dados históricos (FR-012 / edge case "dados antigos em transição")

**Decision**: nenhuma migração, nenhum `UPDATE`. Registros antigos de `movements.timestamp`
(gravados em local) passarão a ser exibidos com −3h até serem descartados — consequência aceita pela
spec (dados de teste).

**Rationale**: FR-012 proíbe migração e manda interromper/registar caso exista base de produção não
descartável; premissa da spec (confirmada na descrição do requisito 9) é ambiente de
desenvolvimento/teste com dados descartáveis.
