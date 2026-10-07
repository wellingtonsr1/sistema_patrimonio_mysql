# Research — Feature 064: Padronização Origem/Destino no Fluxo Global de Movimentações

**Data**: 2026-10-07 · **Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)

Fase 0 do `/speckit-plan`. Cada item segue o formato Decision / Rationale / Alternatives. Todas as afirmações foram verificadas no código (HEAD `41287b8`); nenhuma permanece como NEEDS CLARIFICATION.

## R1 — De onde vêm os dados das colunas Origem/Destino

**Decision**: usar as relações `m.origin_location` / `m.destination_location` (objetos `Location` com `name`, `branch`, `department`) quando existirem; cair para os snapshots `m.origin_location_name` / `m.destination_location_name` quando não existirem.

**Rationale**: `get_all_movements` (`movement_service.py` L477–485) já carrega as 5 relações por `joinedload` — inclusive `Movement.asset` — e `list_movements_view` (`movements.py` L38–60) passa os objetos `Movement` inteiros ao template. O template hoje (L128–137) exibe apenas os snapshots de texto, ignorando as relações já disponíveis. Usar a relação não adiciona consulta nenhuma (R5).

**Alternatives considered**: (a) repassar uma lista pré-formatada do router — rejeitado: criaria lógica de apresentação no backend (Constitution II) e alteraria o contrato do router; (b) manter apenas snapshots — rejeitado: é exatamente a redundância que a feature corrige.

## R2 — Origem do texto redundante `branch - department (name)`

**Decision**: não alterar o formato gravado; a correção é 100% na camada de apresentação.

**Rationale**: o snapshot é gravado em `create_movement` (`movement_service.py` L136/L148) como `f"{branch} - {department} ({name})"`. Como o `name` do local normalmente já contém unidade+setor (`Sede - Assessoria de Gabinete`), a exibição repete o dado 2×. Reformatar a gravação (a) violaria a imutabilidade da trilha (Constitution IV), (b) quebraria a busca que casa contra o texto do snapshot (`get_all_movements` L533–534: `Movement.origin_location_name.ilike`), (c) exigiria backfill de registros antigos — tudo fora de escopo (spec §16).

**Alternatives considered**: (a) regravar snapshots históricos no novo formato — rejeitado: destrói a auditoria (Constitution IV/VII); (b) mudar apenas o formato para novas gravações — rejeitado: criaria dois formatos convivendo na mesma tabela sem resolver a redundância das células antigas.

## R3 — Regra de apresentação (herdada e reafirmada da 063)

**Decision**: quando a relação existe: linha principal = `department` (cadastro atual, Clarifications 2026-10-07); linha secundária `.mov-sec` = `local_curto • branch`, deduplicado (nunca `Clube • Clube`); colaborador inalterado na linha seguinte. Quando a relação não existe: snapshot cru byte-a-byte.

**Rationale**: é o padrão já aprovado e validado na trilha (commit `0b3a329`, `test_presentacao_trilha_063.py` = 4 passed). A macro `_local_curto(name, department)` remove o sufixo ` - {department}` do `name` quando presente (`endswith`/`rsplit`, métodos nativos Jinja2 — precedentes 062/063 na mesma versão). Deduplicação por verificação de pertença à lista `partes` antes do append.

**Alternatives considered**: (a) contexto `branch • department` (ordem invertida) — rejeitado: diverge da referência "Custódia & Localização Atual" (`branch • department`? — verificado em `assets/detail.html` L109–114: é `{{ asset.location.branch }} • {{ asset.location.department }}`; a 063 escolheu `local_curto • branch` para a trilha e esta feature replica a 063, não a Custódia); (b) tooltip com o snapshot cru — rejeitado como regra (opção C da clarificação não escolhida), mas registrado como possível melhoria futura.

## R4 — Replicar a macro vs extrair macro compartilhada

**Decision**: replicar a macro `_local_curto` dentro de `movements/list.html` (Alternativa A da spec §11); extração de macro compartilhada fica registrada como dívida/refatoração futura.

**Rationale**: Jinja2 não compartilha macros entre templates sem `{% import %}` de arquivo externo — o que exigiria tocar `assets/detail.html` (template recém-validado na 063) ou criar `templates/macros/local.html` (novo arquivo de produção). Ambos expandem o raio de alteração além do mínimo (Constitution I). A duplicação é de ~10 linhas, deterministicamente idêntica, e os testes das duas features (063 e 064) travam o comportamento nas duas telas — regressão futura na extração ficaria protegida.

**Alternatives considered**: (a) macro compartilhada em `templates/macros/local.html` importada pelos dois templates — registrada como Alternativa B da spec (refatoração futura); (b) context processor/filtro global Jinja2 registrado no app — rejeitado: toca backend/camada de configuração (spec §11 Alternativa C, descartada).

## R5 — Performance e consultas

**Decision**: nenhuma consulta nova; formatação in-template.

**Rationale**: as relações já chegam carregadas no `get_all_movements` (joinedload, mesma query atual — verificado L479–485). A formatação é computação de string por célula, desprezível mesmo no limite atual de 200 registros por página (não há paginação — spec §22 incerteza (b)). O card equivalente da 063 usa o mesmo mecanismo na trilha sem custo mensurável.

**Alternatives considered**: pré-calcular strings formatadas no service — rejeitado (violaria II/III e duplicaria a lógica de apresentação no backend).

## R6 — Guarda do CSV byte-a-byte (Clarifications 2026-10-07)

**Decision**: teste novo compara a string completa do CSV gerado antes e depois da mudança de template sobre o mesmo banco de teste.

**Rationale**: `ReportService.generate_movements_csv` (`report_service.py` L485–520) formata a partir dos snapshots brutos — nada no caminho do CSV toca o template. O teste byte-a-byte (gerar CSV antes da mudança de template, gerar depois, comparar) é a prova inequívoca do AC11 e detectaria qualquer vazamento acidental de escopo para o backend. O CSV usa `csv.writer` com `delimiter=";"` e `QUOTE_MINIMAL`; as colunas "Origem (Local)"/"Destino (Local)" recebem `m.origin_location_name or "-"` / `m.destination_location_name or "-"` (L508–512).

**Alternatives considered**: (a) teste de presença de substrings — mais frágil ao contrário: aceitaria mutações silenciosas em outras colunas; (b) sem teste novo — rejeitado (Constitution VIII; decisão da clarificação).

## R7 — Telas/consumidores fora de escopo (verificados)

**Decision**: dashboard, relatório `/reports/movements`, termo de cautela e dropdown 062 não são tocados; a suíte existente é a sentinela.

**Rationale**: todos consomem os snapshots brutos com formatação própria aprovada e continuam byte-a-byte: `dashboard.html` L287 (`m.destination_location_name or 'Estoque'`), `reports/movements_report.html` L92/96 (ellipsis + tooltip), termo (`get_term_details` L613: `movement.destination_location_name or "Almoxarifado / Estoque"`), dropdown (`movements/new.html` L103–112, Feature 062). O botão "Exportar CSV" da listagem aponta para `/reports/movements` (página HTML) — mantido como está (spec §22 incerteza (a)). A suíte `test_departamento_destino_062.py` + `test_presentacao_trilha_063.py` protege as features irmãs na régua final.

**Alternatives considered**: padronizar todas as telas de uma vez — rejeitado: expansão de escopo sem previsão (Constitution I); cada tela tem formatação aprovada própria.
