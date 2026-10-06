# Research — Feature 062: Seleção de Destino por Departamento/Setor

**Data**: 2026-10-06 · **Spec**: [spec.md](./spec.md) · **Natureza**: resolução das incógnitas do Technical Context + verificação de premissas da spec

## R1 — Como agrupar por Unidade no template (sem tocar backend)

**Decisão**: usar o filtro nativo Jinja2 `groupby('branch')` sobre a lista `locations` já fornecida ao template.

**Rationale**:
- `LocationService.get_all(db)` já ordena por `Location.branch, Location.department, Location.name` (`app/services/location_service.py` L22) — o `groupby` Jinja2 **ordena a sequência pela chave antes de agrupar** (comportamento documentado do filtro, ordenação case-insensitive), então os grupos saem em **ordem alfabética de unidade**, determinística e independente da ordem da fonte; dentro de cada grupo, a ordenação estável preserva a ordem da fonte (departamento → nome).
- Com os dados atuais (`branch` em 36 registros: `IPMJP - Sede` ×34, `Clube` ×1, `Shoping` ×1), os grupos já nascem prontos.
- `{% for branch, locs in locations | groupby('branch') %}` — padrão Jinja2 padrão, zero código novo em rota/service, sem dependência nova (Constitution X).
- Precedente de não-criar helper: o projeto não tem NENHUM uso de `groupby` hoje (verificado por grep em `app/`) — esta feature não cria service/helper; o filtro nativo do template engine é o mecanismo idiomático para apresentação.

**Alternatives considered**:
- Agrupar no backend (router/service montando estrutura `[(branch, [locs])]`) — rejeitado: viola o escopo da spec (FR-009: zero backend) e a camada (Princípio II: agrupamento de exibição não é regra de negócio).
- JS client-side reagrupando `<option>`s — rejeitado: complexidade nova, sem benefício, quebra renderização server-side padrão da casa.
- Novo método `LocationService.get_all_grouped()` — rejeitado: código novo sem necessidade (a lista já vem ordenada); viola Princípio I (mudança mínima).

## R2 — Fonte dos dados: reutilizar a lista existente

**Decisão**: manter `LocationService.get_all(db)` como fonte de `locations` nos dois routers (`form_new_movement`, `form_new_asset`) — nenhum change de rota.

**Rationale**: já é a fonte usada hoje por ambos os formulários (verificado: `app/web/routers/movements.py` ~L65–95 e `app/web/routers/assets.py` L391+); a lista já ordenada é suficiente para o agrupamento (R1). Zero risco de regressão na fonte.

**Alternatives considered**: qualquer mudança de rota/service — rejeitada pelo escopo (spec FR-009) e pelo Princípio I.

## R3 — Os 4 selects fora de escopo (proteção de não-escopo)

**Decisão**: NÃO tocar em nenhum dos outros 4 pontos que iteram sobre `locations` — verificados e catalogados:

| # | Template | Linha | Formato atual | Papel |
|---|---|---|---|---|
| 1 | `assets/list.html` | L76 | `<option ...>{{ loc.name }}</option>` (com `selected` condicional) | filtro da lista de equipamentos |
| 2 | `assets/labels.html` | L69 | idem | filtro da página de etiquetas |
| 3 | `inventarios/new.html` | L40 | `{{ loc.name }}` (option vazia "Todos os locais") | filtro/escopo de novo inventário |
| 4 | `locations/list.html` | L64 | loop de **tabela**, não select | listagem de localizações |

**Rationale**: a spec limita a mudança aos 2 selects de **cadastro/destino** (US1/US2); os outros 4 são filtros/listagem com formato próprio (`loc.name` puro) e comportamento aprovado — alterá-los seria escopo não previsto (Princípio I da Constitution).

**Alternatives considered**: padronizar todos os selects — rejeitada: fora do escopo da spec; evolução candidata a feature futura.

## R4 — Suíte existente: nenhum teste trava o texto das opções

**Decisão**: nenhum teste existente precisa ser editado; a feature adiciona um arquivo novo.

**Rationale** (verificação na elaboração do plan):
- Grep nos testes por `movements/new`: apenas `test_help.py` L99 (verifica link de ajuda, não opções) e `test_movements.py` L401+ (envia `destination_location_id` numérico, não lê textos de option).
- Grep por asserts de texto de opção de local: **nenhum** (os únicos asserts de texto de option são de colaborador — `c.name (matrícula - department)` — não afetados).
- Os asserts de `*_location_name` (`test_import_asset_movements.py` L134: `"Matriz - TI (Sala de TI)"`) travam o **formato do snapshot gravado**, não a UI — permanecem verdes e servem de régua de não-mutação (R5).

**Alternatives considered**: atualizar algum teste existente — desnecessário (nenhum trava o texto da UI).

## R5 — Snapshot do histórico: manter formato (não-mutação)

**Decisão**: o formato do snapshot gravado nas movimentações permanece EXATAMENTE o atual: `f"{branch} - {department} ({name})"` — ex.: `IPMJP - Sede - Divisão de Previdência (Sede - Divisão de Previdência)`.

**Rationale**:
- O formato é gravado no backend (`movement_service.py` L136/L148; `asset_service.py` L167; `import_service.py` L482/L629) — arquivos intocados pela feature; a não-mutação é **consequência estrutural** (nenhum caminho de escrita é alterado).
- O formato já é travado por testes existentes (`test_import_asset_movements.py` L134; `test_import_asset_location.py` L153; `test_import_asset_movements.py` L216 — fallback "Estoque Central").
- Mudar o formato do snapshot **agora** criaria dois formatos convivendo na busca de movimentações (Feature 049 casa os snapshots por `ilike`) — a spec proíbe (FR-006).
- Exemplo concreto (dados reais): snapshot existente `IPMJP - Sede - Setor de Arquivo (Sede - Setor de Arquivo)` — a busca por "Setor de Arquivo" ou "IPMJP - Sede" casa por `ilike` **substrings**; mudanças de formato quebrariam termos antigos.

**Alternatives considered**: aproveitar para "modernizar" o snapshot (`Departamento (Unidade)`) — rejeitada: viola FR-006 e cria dois formatos convivendo (busca/relatórios); queda registrada na spec como risco 6 da análise.

## R6 — UX do optgroup e do rótulo

**Decisão**: rótulo autocontido `Departamento (Unidade)` dentro do grupo da unidade; a opção vazia de cada select permanece FORA de qualquer grupo (primeira opção do `<select>`, como hoje).

**Rationale**:
- Clarificações Q2/Q3 da spec (decisão do usuário em 2026-10-06): optgroups por unidade + rótulo `Departamento (Unidade)` — a unidade aparece no cabeçalho do grupo **e** no contexto da opção (deliberado: rótulo legível mesmo fora do contexto do grupo, ex. leitor de tela/inspeção).
- `<optgroup>` é HTML nativo suportado por todos os navegadores alvo (desktop/mobile) e renderizado pelo Bootstrap sem CSS novo.
- A opção vazia (`-- Manter Local Atual --` / `-- Estoque Central / Almoxarifado --`) deve ficar antes do primeiro `optgroup` — HTML válido e padrão corrente.
- A ordem dos grupos segue a ordenação case-insensitive do `groupby` (alfabética de unidade: `Clube`, `IPMJP - Sede`, `Shoping`) — determinística; a unidade com travessão `IPMJP – Sede` em 1 registro fica em grupo próprio, logo após o principal — higiene de dados é feature própria.

**Alternatives considered**:
- Rótulo sem contexto (`Departamento` puro) — rejeitada na clarificação Q3 (autocontido).
- Rótulo com nome do local (`Departamento — Nome (Unidade)`) — rejeitada na clarificação Q3 (o `name` já contém branch+department hoje; a redundância era a dor original).

## R7 — Escrita dos templates: uma passada, sem regra nova

**Decisão**: cada template alterado mantém estrutura idêntica (`<select name=...>` com sua option vazia), apenas o loop das opções muda de um `for` plano para `for` sobre `groupby`.

**Rationale**: a única mudança é no corpo do loop (2 arquivos); o atributo `name`, os values e a option vazia permanecem byte-a-byte idênticos (FR-003/FR-004). Nenhum atributo `selected` é necessário no select de destino (comportamento atual — o repovoamento em erro usa o redirect com `?error=` e o bem/tipo repovoados, não o local escolhido; verificar no contract UI que isso permanece).

**Alternatives considered**: incluir controle de `selected` no local de destino — rejeitada: não existe hoje (verificado no template atual), adicionar seria mudança de comportamento fora do escopo.

---
