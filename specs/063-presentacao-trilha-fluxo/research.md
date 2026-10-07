# Research — Feature 063: Padronização da Apresentação de Origem e Destino

**Data**: 2026-10-06 · **Spec**: [spec.md](./spec.md) · **Natureza**: resolução das incógnitas do Technical Context + verificação de premissas da spec

## R1 — De onde virão os dados da nova apresentação (sem backend novo)

**Decisão**: usar as relações `item.data.origin_location` / `item.data.destination_location` (objetos `Location` completos: `name`, `branch`, `department`) que o service **já carrega** via joinedload em `get_timeline_for_asset` (`movement_service.py` L417–422) e que o template **hoje ignora** — ele exibe apenas os snapshots de texto (`origin_location_name`/`destination_location_name`).

**Rationale**:
- Zero consulta nova, zero endpoint novo, zero campo novo (FR-002): os objetos já chegam prontos ao template.
- A relação reflete a FK do registro — imune a typos do snapshot e à edição posterior do cadastro (o snapshot cru é preservado para o fallback).
- Precedente de reutilização: o padrão visual de referência ("Custódia & Localização Atual", `assets/detail.html` L109–114) usa exatamente os mesmos campos da mesma relação (`asset.location.name/branch/department`).

**Alternatives considered**:
- Decompor o snapshot com `split(' - ')` — rejeitada: inventa estrutura a partir de texto livre; quebra com nomes que contêm ` - ` (`IPMJP - DAF - Seção de Folha`) e com textos sem estrutura (`Fornecedor / Entrada Inicial`) (FR-010).
- Nova query/endpoint que devolva locais formatados — rejeitada: viola FR-002/FR-007 e o Princípio I.
- Passar os dados já formatados pelo router (`view_asset_detail`) — rejeitada: tocaria backend sem necessidade; a formatação é apresentação (Princípio II/III).

## R2 — Regra de apresentação exata (título + contexto, com deduplicação)

**Decisão**: para cada ponto (Origem/Destino), quando a relação existe:

- **Linha principal**: `location.department` — ex.: `Divisão de Previdência`.
- **Linha de contexto**: `local_curto • branch` — ex.: `Sede • IPMJP - Sede`, onde:
  - `local_curto` = `location.name` **sem o sufixo ` - {department}`** quando o nome termina exatamente com esse sufixo (`name.endswith(' - ' + department)` → `name.rsplit(' - ' + department, 1)[0]`); caso contrário, o próprio `name`;
  - **deduplicação**: se `local_curto == department` (nome igual ao departamento — ex.: `Clube da Pessoa Idosa`), o componente é omitido; se `branch` for igual a `local_curto` ou a `department`, também é omitido (edge cases 3/4 da spec — `Shopping 4400 - Shopping 4400` e repetição de unidade jamais aparecem);
  - se sobrar um único componente, a linha mostra só ele; se não sobrar nenhum, a linha de contexto é omitida.
- **Colaborador**: `origin_custodian_name`/`destination_custodian_name` com os fallbacks atuais (`Nenhum` / `Almoxarifado / Estoque`) — inalterado.

**Rationale**:
- Reproduz **exatamente** o exemplo aprovado pelo usuário: snapshot `IPMJP - Sede - Divisão de Previdência (Sede - Divisão de Previdência)` → título `Divisão de Previdência` + contexto `Sede • IPMJP - Sede` (o `name` de produção é `{local} - {departamento}`; remover o sufixo do departamento deixa o local físico: `Sede`).
- Verificação com dados de importação (CSV da casa, `Nome,Filial,Departamento`): `IPMJP - DAF - Seção de Folha de Beneficios` + dept `Seção de Folha de Beneficios` → título `Seção de Folha de Beneficios` + contexto `IPMJP - DAF • IPMJP` — consistente e sem invenção.
- **Comprovado na versão Jinja2 do projeto**: macro testada em `.venv` (2026-10-06) — `endswith` + `rsplit(...,1)[0]` renderizam `Sede|Clube da Pessoa Idosa|IPMJP - DAF|Sede - A` para os 4 casos de borda.

**Alternatives considered**:
- Contexto = `{building} • {branch}` — rejeitada: `building` é `nullable` e não populado na produção/importação (CSV só tem Nome/Filial/Departamento); geraria contexto vazio.
- Contexto = `{name} • {branch}` integral — rejeitada: reintroduz a duplicação que a feature elimina (o departamento apareceria no título E no nome).
- Contexto = `{branch} • {department}` (espelhando a referência da Custódia) — rejeitada: o departamento já é o título; duplicaria na linha de contexto.

## R3 — Fallback quando a relação não existe (FR-010)

**Decisão**: sem relação carregada (local excluído do cadastro, registro sem FK), o ponto é exibido como **texto único**: o snapshot cru (`origin_location_name`/`destination_location_name`), sem decomposição e sem linha de contexto. Fallbacks existentes preservados: `Estoque Geral` (quando snapshot vazio) para o valor; `Nenhum` / `Almoxarifado / Estoque` para o colaborador.

**Rationale**: impossível distinguir `Unidade - Departamento (Nome)` de texto livre sem inventar estrutura (FR-010); o snapshot é a fonte histórica completa e correta. Exemplo real: ENTRADA_AQUISICAO grava origem literal `Fornecedor / Entrada Inicial` (Feature 029) — deve aparecer como está.

**Alternatives considered**: parsear o snapshot com regex — rejeitada (R1); esconder o ponto sem local — rejeitada: perderia informação histórica.

## R4 — Veículo da implementação: macro local no template (zero Python)

**Decisão**: macro Jinja2 **definida no próprio `assets/detail.html`** (topo do arquivo, após o `extends`), usada para Origem e Destino do card `flow-card`. Nenhum filtro novo registrado em `templates_env.py`, nenhum helper Python novo.

**Rationale**:
- Um único arquivo alterado (FR-007/escopo); fácil de revisar e reverter.
- Princípio II/III: formatação de rótulos é apresentação, não regra de negócio.
- Precedente da 062 (research R1): "o filtro nativo do template engine é o mecanismo idiomático para apresentação"; sem registro global de filtros, o impacto fica contido no template que usa.
- Operações necessárias (`endswith`, `rsplit`, concatenação, comparação) validadas na versão Jinja2 do projeto (R2).

**Alternatives considered**:
- Filtro global Jinja2 em `templates_env.py` — rejeitada: tocaria arquivo de backend/presentação global para uma necessidade de uma única tela (Princípio I — menor alteração); viável em feature futura se outras telas adotarem o padrão.
- Macro em arquivo separado (`macros.html`) com import — rejeitada: criaria arquivo novo para uma macro usada em um template; import adiciona indireção sem benefício.
- Formatar no service/router — rejeitada (R1).

## R5 — Snapshot gravado e busca: intocados (não-mutação)

**Decisão**: nenhum caminho de escrita é alterado. O formato `f"{branch} - {department} ({name})"` gravado em `movement_service.py` L136/L148 (e equivalentes em `asset_service.py`/`import_service.py`) permanece; a busca 049 (`ilike` sobre `origin_location_name`/`destination_location_name`) continua casando termos antigos.

**Rationale**:
- Mudar o formato do snapshot agora criaria dois formatos convivendo na busca — proibido pela spec (FR-003/FR-004; risco 2).
- A não-mutação é **consequência estrutural** (nenhum arquivo de escrita tocado) e é **comprovada por teste** (US2): snapshot byte-a-byte antes/depois + busca por termo.
- Régua existente mantida: `test_import_asset_movements.py` L134/L216 seguem verdes sem edição.

**Alternatives considered**: "modernizar" o snapshot para o novo formato — rejeitada: viola FR-003/FR-004 e o Princípio IV.

## R6 — Telas fora de escopo (proteção de não-escopo)

**Decisão**: NÃO tocar nos demais pontos que exibem os mesmos snapshots — catálogo verificado:

| # | Template | Linha | Papel | Por que fora |
|---|---|---|---|---|
| 1 | `movements/list.html` | L129/133 | colunas Origem/Destino da listagem | formatação própria aprovada (feature 039 de larguras de coluna) |
| 2 | `dashboard.html` | L287 | coluna Destino do painel | ídem |
| 3 | `reports/movements_report.html` | L92/96 | Origem/Destino do relatório impresso | ídem (feature 041) |
| 4 | `movement_service.py` `get_term_details` | L613 | local do termo de responsabilidade | documento oficial; formato atual é o aprovado |
| 5 | `movements/new.html`, `assets/form.html` | selects | Feature 062 | byte-a-byte intocados (FR-005) |

**Rationale**: a spec (§10) limita a mudança à trilha do `assets/detail.html`; padronizar as outras telas é feature própria (risco 3). Os testes da 062 e o subconjunto de movimentação protegem esses pontos.

## R7 — Estratégia de testes (o que prova o quê)

**Decisão**: 1 arquivo novo `tests/test_presentacao_trilha_063.py` com dois grupos:

1. **US1 — renderização** (red→green): locais de produção-like (`Sede - Divisão de Previdência` / `Sede - Setor de Recadastramento` na unidade `IPMJP - Sede`; `Clube da Pessoa Idosa` no `Clube`), entrada + transferência via form web; `GET /assets/{id}` e asserts sobre o HTML:
   - título = departamento (`Divisão de Previdência`, `Setor de Recadastramento`) nos blocos de Destino/Origem;
   - contexto `Sede • IPMJP - Sede` presente;
   - snapshot cru formatado `IPMJP - Sede - Setor de Recadastramento (Sede - Setor de Recadastramento)` **ausente** do HTML da trilha;
   - caso deduplicado: local `Clube da Pessoa Idosa` (name == department) exibe contexto `Clube` sem repetição.
2. **US2 — guarda** (verde-verde, como a US3 da 062): snapshot `destination_location_id` + `destination_location_name` no formato atual após a transferência; ENTRADA_AQUISICAO byte-a-byte idêntica; busca 049 encontra por termos do snapshot; dropdown 062 intacto é garantido pela suíte existente (`test_departamento_destino_062.py`) que corre sem edição na régua final.

**Rationale**: espelha o padrão da casa da 062 (TDD red→green + guarda verde-verde); os asserts de HTML usam os mesmos auxiliares de extração por marcador (`flow-label-origin`/`flow-label-dest` → trecho até o próximo fechamento).

**Alternatives considered**: testar o HTML das outras telas — rejeitado (fora do escopo, R6).
