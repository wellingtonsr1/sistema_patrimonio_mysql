# Feature Specification: Padronização da Apresentação de Origem e Destino no Fluxo Global de Movimentações

**Feature Branch**: `064-origem-destino-fluxo-global`

**Created**: 2026-10-07

**Status**: Draft (aguardando aprovação para FASE DE IMPLEMENTAÇÃO)

**Input**: Padronizar a apresentação das colunas ORIGEM e DESTINO na página "Fluxo Global de Movimentações" (`/movements`), eliminando a redundância do snapshot cru e adotando a mesma hierarquia visual já aprovada na Feature 063 para a trilha do equipamento (`063-presentacao-trilha-fluxo`, commit `0b3a329`). Mudança somente de APRESENTAÇÃO; o snapshot gravado, a busca, o CSV e todo o histórico permanecem intocados, com testes de guarda.

---

## Clarifications

### Session 2026-10-07

- Q: Quando a relação com o cadastro existe, a célula Origem/Destino do Fluxo Global deve mostrar o departamento atual da localização ou o texto congelado no momento da movimentação? → A: Cadastro atual (decisão herdada e reafirmada da 063; snapshot fiel permanece acessível no banco, CSV e termo, com guarda por teste).
- Q: Como o contexto “Sede • IPMJP - Sede” deve aparecer dentro da célula, considerando o layout fixo da tabela (Feature 039)? → A: Duas linhas — linha 1 `department` em destaque, linha 2 contexto em `.mov-sec` (fonte menor), espelhando a trilha 063; larguras de coluna da 039 intocadas.
- Q: Qual nível de garantia os testes devem dar sobre a exportação CSV permanecer idêntica após a mudança visual? → A: Teste byte-a-byte — comparar o CSV gerado antes/depois da mudança de template sobre o mesmo banco (mesmo banco ⇒ mesmo CSV, prova inequívoca do AC11).

---

## 1. Contexto

O sistema possui a página **"Fluxo Global de Movimentações"** (`/movements`), descrita na própria tela como "Registro histórico auditável de todas as transferências, alocações e alterações de custódia". Colunas: Data/Hora, Tombamento, Equipamento, Tipo, Origem, Destino, Motivo, Operador, Ações. A página oferece pesquisa, filtro por tipo e o botão "Exportar CSV".

### Análise do código real (somente leitura, verificada nesta especificação — 2026-10-07, HEAD `41287b8`)

| # | Ponto investigado | Realidade verificada |
|---|---|---|
| 1 | Rota | `GET /movements` → `list_movements_view` (`app/web/routers/movements.py` L38–60), permissão `movimentacao.visualizar`, `MovementService.get_all_movements(db, filters=..., limit=200)`. **Não há paginação** (limite fixo de 200 registros) |
| 2 | Query | `get_all_movements` (`app/services/movement_service.py` L477) carrega por `joinedload` as relações `Movement.asset`, `origin_location`, `destination_location`, `origin_custodian`, `destination_custodian` — **o template JÁ recebe os objetos `Location` completos** (name, branch, department), exatamente como na trilha da 063 |
| 3 | Template | `app/web/templates/movements/list.html` L128–137: Origem exibe `{{ m.origin_location_name or '-' }}` + colaborador `{{ m.origin_custodian_name or '-' }}`; Destino exibe `{{ m.destination_location_name or '-' }}` + `{{ m.destination_custodian_name or '-' }}` — **apenas snapshots de texto** |
| 4 | Origem da redundância | O snapshot `origin_location_name`/`destination_location_name` é gravado em `create_movement` (`movement_service.py` L136/L148) no formato `f"{branch} - {department} ({name})"`. Como o `name` do local já contém unidade+setor (ex.: `Sede - Assessoria de Gabinete`), a exibição repete o dado 2×: `IPMJP - Sede - Assessoria de Gabinete (Sede - Assessoria de Gabinete)` |
| 5 | Literais especiais gravados no snapshot | L307–311: `origin_location_name or "Não definido"`, `origin_custodian_name or "Nenhum / Estoque"`; destino sem FK recebe o snapshot anterior; termo usa fallback `Almoxarifado / Estoque` (L613). Entrada inicial grava o literal `Fornecedor / Entrada Inicial` (Feature 029) |
| 6 | Busca (Feature 004/049) | `get_all_movements` pesquisa por `Movement.origin_location_name.ilike` / `destination_location_name.ilike` (L533–534) — **a busca casa contra o TEXTO do snapshot**; alterar o formato gravado quebraria a busca |
| 7 | Exportação CSV | O botão "Exportar CSV" da listagem aponta para `/reports/movements` (relatório HTML). O download CSV real é `GET /api/reports/movements/csv` (`app/api/reports_api.py` L208–214) → `ReportService.generate_movements_csv` (`app/services/report_service.py` L485–520), que grava **os snapshots brutos** nas colunas "Origem (Local)"/"Destino (Local)" — formatter próprio, sem passar pelo template |
| 8 | Outras telas com o mesmo snapshot | `reports/movements_report.html` L92/96 (com ellipsis+tooltip), `dashboard.html` L287, termo (`get_term_details` L613) — **todas fora do escopo desta spec** |
| 9 | Referência visual aprovada (063) | `app/web/templates/assets/detail.html`: card `flow-card` da trilha exibe `{{ loc.department }}` como linha principal + contexto `local_curto • branch` deduplicado via macro `_local_curto`, com fallback ao snapshot cru quando a relação não existe (commit `0b3a329`; testes `test_presentacao_trilha_063.py` = 4 passed) |
| 10 | Helper compartilhável | **NÃO existe** helper/formatter central de localização: a macro `_local_curto` vive dentro de `assets/detail.html` (escopo de template Jinja) e não é importável sem extrair um arquivo de macros compartilhado (refatoração) |
| 11 | Departamento do colaborador × da localização | `Custodian.department` é coluna distinta, sem FK com `Location.department` (spec 063 §1 item 9) — a apresentação usa **apenas** `Location.department` |
| 12 | CSS da tabela | `<style>` escopado em `list.html` (Feature 039): `table-layout: fixed`, colunas rígidas em px, `.mov-fluxo` (Origem horizontal), `.mov-sec` (linhas secundárias) — qualquer mudança de marcação deve respeitar esse layout validado |

**Consequências da análise**:

- A redundância é **100% de apresentação**: o template recebe as relações completas e escolhe exibir o snapshot cru. A correção cabe no template, sem backend, sem DDL (Princípio I da Constitution).
- O snapshot textual **não pode ser reformatado na gravação** (quebraria a busca L533–534 e violaria a imutabilidade — Princípio IV) e **não será regravado** (teste de guarda).
- Não existe helper compartilhável pronto; extrair um agora tocaria o template recém-validado da 063. A alternativa de menor risco replica o padrão 063 no template do Fluxo Global (ver §11 e §18).

---

## 2. Problema

A célula Origem/Destino do Fluxo Global exibe o snapshot cru, gerando: (1) repetição do mesmo dado 2× (`IPMJP - Sede - Assessoria de Gabinete (Sede - Assessoria de Gabinete)`); (2) unidade administrativa antes do setor, invertendo a prioridade de leitura; (3) excesso de texto por célula em uma tabela de 9 colunas (quebra em 2–3 linhas); (4) inconsistência com a trilha do mesmo conceito, já padronizada pela 063 na tela de detalhes.

## 3. Objetivo

Apresentar Origem e Destino no mesmo padrão visual aprovado na 063, em **duas linhas por ponto** (layout fixo da Feature 039 preservado — nenhuma largura de coluna muda):

```
ORIGEM
Assessoria de Gabinete        ← Departamento/Setor (linha principal, destaque)
Sede • IPMJP - Sede           ← Localização (curta) • Unidade (contexto, .mov-sec)
Aslan Ezequiel do Nascimento (PROV-000012)   ← colaborador (linha seguinte, inalterado)
```

Sem duplicação: no caso `Clube da Pessoa Idosa` (name == department), o contexto exibe apenas `Clube` — **nunca** `Clube • Clube`. Os exemplos visuais são objetivos, não regras: os campos reais de cada posição são os verificados na §1 (department; local_curto; branch).

## 4. Comportamento atual

- Origem/Destino = snapshot de texto cru (`branch - department (name)`) + colaborador (snapshot `Nome (Matrícula)`); fallback do template: `-`.
- Registros sem origem: literal `Não definido` + `Nenhum / Estoque` (gravados no snapshot).
- Entrada inicial: origem literal `Fornecedor / Entrada Inicial`.
- Busca/filtro/CSV/das demais telas: funcionam sobre o snapshot cru.

## 5. Comportamento desejado

- Quando a **relação** `origin_location`/`destination_location` existe: linha principal = `department`; contexto = `local_curto • branch` (deduplicado, cada valor 1×); colaborador inalterado.
- Quando a **relação não existe** (FK nula — local excluído, entrada inicial, `Não definido`): exibe o **snapshot cru como está**, sem inventar estrutura (`Fornecedor / Entrada Inicial`, `Não definido`, `Nenhum / Estoque` continuam byte-a-byte).
- Nada mais muda: busca, filtros, ordenação (timestamp desc), limite 200, botões, termo, CSV, dashboard, relatório, trilha 063, dropdown 062.

## 6. Análise técnica

Resumo da §1: mudança restrita ao corpo das 2 células (`<td class="small mov-fluxo">` e o `<td>` do destino) de `movements/list.html`, respeitando o layout fixo da Feature 039 (classes `mov-fluxo`/`mov-sec` preservadas; nenhuma largura de coluna alterada). O `department` ocupa a linha principal e o contexto a linha secundária `.mov-sec`. O `joinedload` já existente (L479–485) traz as relações sem query nova. Custo por célula: idêntico ao da 063 (sem consulta adicional).

## 7. Modelo de dados envolvido

`Movement` (imutável): `origin_location_id`/`destination_location_id` (FK `locations.id`) **+** snapshots `origin_location_name`/`destination_location_name` (String 150) + `origin_custodian_id`/`destination_custodian_id` + snapshots de colaborador. `Location`: `name`, `branch` (NOT NULL), `department` (NOT NULL), building/floor/room/manager_name (fora de uso aqui). **Zero DDL; nada a migrar.**

## 8. Origem

Snapshot gravado em `create_movement` a partir do estado anterior do bem (`asset.location`); FK `origin_location_id` aponta para a `Location` de origem; literal `Não definido` quando o bem estava em estoque; literal `Fornecedor / Entrada Inicial` na entrada inicial. Template decide qual fonte exibir (relação × snapshot).

## 9. Destino

Mesma estrutura: FK `destination_location_id` + snapshot gravado no momento do POST (formato `branch - department (name)`); quando a transferência preserva o local, grava o snapshot anterior. Exibição segue a mesma regra da §8.

## 10. Formatação atual

- **Tabela (em escopo)**: `{{ m.origin_location_name or '-' }}` — snapshot cru (redundante).
- **CSV (fora do escopo)**: `report_service.py` L508–512 grava `m.origin_location_name or "-"` — snapshot cru, formatter próprio.
- **Dashboard/relatório/termo (fora do escopo)**: snapshot cru com tratamentos próprios aprovados.

## 11. Formatação proposta (alternativas avaliadas)

| Alternativa | Descrição | Complexidade | Risco | Veredito |
|---|---|---|---|---|
| **A — Replica do padrão 063 no template** | Macro `_local_curto` + deduplicação dentro de `movements/list.html` (mesma lógica aprovada na 063) | Mínima (1 template + testes) | Baixo (nada fora do template) | ✅ **ESCOLHIDA** |
| B — Extrair macro compartilhada (`templates/macros/local.html`) importada pela trilha e pelo Fluxo Global | Elimina duplicação futura | Média (toca `assets/detail.html` validado na 063) | Médio (regressão em feature recém-entregue) | Registrada como refatoração futura |
| C — Formatter no backend (`movement_service`/context processor) | Centraliza em Python | Alta | Alto (viola apresentação-only; toca camada de negócio) | Descartada |

Sobre AC14: não existe hoje lógica reutilizável **importável** (§1 item 10); a Alternativa A reutiliza o **padrão** validado (mesma regra, mesmo resultado) e a duplicação de ~10 linhas de macro fica registrada como dívida consciente, resolvível pela Alternativa B em feature futura.

## 12. Casos especiais

| Caso | Comportamento proposto |
|---|---|
| 1. Localização completa | `department` principal + `local_curto • branch` |
| 2. name == department (Clube) | contexto exibe só `branch` (`Clube`) — deduplicação proíbe `Clube • Clube` e `Clube da Pessoa Idosa - Clube da Pessoa Idosa` |
| 3. Department vazio | Impossível no cadastro (`NOT NULL`); se ocorrer em dados antigos, a deduplicação naturalmente exibe o `local_curto` como principal — sem texto artificial |
| 4. Branch vazio | Impossível (`NOT NULL`); mesmo tratamento do caso 3 |
| 5. Localização vazia (FK nula) | Snapshot cru como está (fallback atual preservado; template nunca quebra) |
| 6. Dados antigos/incompletos | Sempre o snapshot cru via fallback — nenhum registro antigo perde significado |
| 7. `Não definido` / `Nenhum / Estoque` | Literais gravados no snapshot; exibidos byte-a-byte como hoje |
| 8. `Fornecedor / Entrada Inicial` | Snapshot literal sem estrutura `branch - department (name)` → exibido como está (linha principal = o próprio snapshot; sem contexto artificial) |

## 13. Histórico e auditoria

A movimentação armazena **FK + snapshot** (Opção C do diagnóstico). Nada é regravado, reformatado ou remigrado: o banco permanece byte-a-byte. Quando a relação existe, a exibição usa o cadastro atual da localização — **decisão confirmada pelo usuário nesta spec (Clarifications 2026-10-07)**, herdada da 063; o valor histórico fiel continua disponível no snapshot (banco), no CSV e no termo, que não mudam. Consequência aceita: se um setor for renomeado após a movimentação, a tabela exibe o nome novo; o nome antigo permanece no snapshot (banco/CSV/termo). **Risco à auditoria: BAIXO** (nenhum dado alterado; apenas a leitura visual da tabela ganha hierarquia).

## 14. CSV

**Decisão: Alternativa A — mudança somente visual na tabela (§11).** O CSV (`generate_movements_csv`) continua exportando os snapshots brutos: (1) é o registro de auditoria fiel ao banco; (2) alterá-lo exigiria tocar `report_service.py` (backend), expandindo escopo e duplicando a formatação em Python; (3) nenhum requisito do usuário pede CSV limpo. A redundância no CSV fica **registrada como observação** para eventual feature futura. O CSV permanece funcional e byte-a-byte idêntico (guarda por teste).

## 15. Escopo (INCLUI)

Padronização visual de Origem e Destino na tabela do Fluxo Global (`movements/list.html`); eliminação de redundâncias com hierarquia `department` → `local_curto • branch` → colaborador; tratamento dos 8 casos especiais via fallback ao snapshot; preservação de busca, filtros, ordenação, limite/paginação (inexistente) e exportação (intocada); testes novos de renderização e guarda.

## 16. Fora do escopo (NÃO INCLUI)

Banco/tabelas/migrações; cadastro de localização ou colaboradores; dropdown "Novo Local / Departamento" (062); lógica/regras de movimentação e custódia (`movement_service.py`); permissões; histórico e IDs; alteração de registros existentes; CSV, termo, dashboard, relatório `/reports/movements`, trilha 063 e demais telas; extração de macro compartilhada (Alternativa B); mudança do conceito de `Custodian.department`.

## 17. Arquivos potencialmente afetados

| Arquivo | Alteração |
|---|---|
| `app/web/templates/movements/list.html` | **ÚNICO arquivo de produção**: macro `_local_curto` no topo + corpo das 2 células Origem/Destino; `<style>` e layout da Feature 039 intocados |
| `tests/test_fluxo_global_064.py` | **Novo**: US1 renderização (red→green) + US2 guarda de não-mutação |

Nenhum outro arquivo de produção é tocado.

## 18. Estratégia de implementação

1. **Baseline**: régua completa (`python -m pytest`) registrada — patamar atual **948 passed / 2 skipped / 4 failed** (4 failures ambientais: `dotenv`/`alembic` ausentes no subprocesso; ver `063/validacao.md` V1).
2. **US1 (red→green)**: teste de renderização em `/movements` com locais de dados conhecidos (incl. caso Clube deduplicado e registro sem FK) → RED contra o template atual → alterar as 2 células + macro → GREEN.
3. **US2 (guarda verde-verde)**: gravação de transferência com snapshot no formato atual; busca 049/Fluxo Global por "Dept B" encontra o registro; conteúdo do CSV endpoint (`/api/reports/movements/csv`) contém o snapshot cru; suítes 062 e 063 verdes sem edição.

## 19. Estratégia de testes (arquivo `tests/test_fluxo_global_064.py`)

| Teste | Protege |
|---|---|
| `test_fluxo_global_titulos_sao_departamento_e_contexto_deduplicado` | AC01–AC04 (department principal; `Sede • IPMJP - Sede`; snapshot cru ausente do HTML) |
| `test_fluxo_global_caso_deduplicado_clube` | AC02/AC04 (sem `Clube • Clube` nem `Clube da Pessoa Idosa - Clube da Pessoa Idosa`) |
| `test_fluxo_global_fallbacks_snapshot_e_literais` | Casos 5–8 (`Não definido`, `Nenhum / Estoque`, `Fornecedor / Entrada Inicial`, FK nula) — AC06/AC07 |
| `test_fluxo_global_nao_muda_gravacao_nem_busca_nem_csv` | AC08–AC11 (snapshot `Unidade B - Dept B (Sala B)`; busca por "Dept B"; **CSV byte-a-byte idêntico** — gera o CSV sobre o mesmo banco antes e depois da mudança de template e compara as strings; colaborador correto) |
| Execução da suíte 062 + 063 na régua final | AC12/AC13 (dropdown e trilha intocados) + AC14/AC15 (escopo/diff `git diff app/` = apenas `list.html`) |

Reuso das fixtures e helpers da casa (`client`/`db_session`, `LocationService`, `AssetService`, `MovementService`), espelhando `test_presentacao_trilha_063.py`. Nenhum teste existente é editado.

## 20. Critérios de aceitação

AC01 Origem sem redundância · AC02 Destino sem redundância · AC03 `department` com destaque principal · AC04 Localização + Unidade como contexto secundário (cada valor 1×) · AC05 Colaborador correto · AC06 `Não definido`/`Nenhum / Estoque`/entrada inicial funcionam · AC07 Histórico exibido · AC08 Nenhum dado histórico alterado · AC09 Pesquisa e filtros OK · AC10 Ordenação e limite 200 OK · AC11 CSV funcional e idêntico · AC12 Dropdown 062 intocado · AC13 Custódia & Localização Atual e trilha 063 intocados · AC14 Sem segunda lógica paralela além da replicação documentada da §11-A (dívida registrada) · AC15 Zero DDL.

## 21. Riscos

| Risco | Nível | Justificativa |
|---|---|---|
| Busca/CSV/termo quebrem | BAIXO | Snapshot não muda (guarda por teste); mudança só no template |
| Exibição refletir cadastro atual quando relação existe | BAIXO/MÉDIO | Decisão já aprovada na 063; snapshot fiel permanece no banco/CSV/termo |
| Regressão visual na tabela 039 | BAIXO | Marcação mínima dentro das `<td>` existentes; classes e layout preservados |
| Duplicação da macro (dívida) | BAIXO | ~10 linhas; Alternativa B registrada como refatoração futura |
| Regressão em 062/063 | BAIXO | Suítes executadas na régua final sem edição |

## 22. Plano de implementação mínimo

1. Baseline da régua (§18.1) → 2. Teste US1 (RED) → 3. Macro + 2 células em `movements/list.html` (GREEN) → 4. Subconjunto de regressão (`test_movements.py + test_movements_search.py + test_import_asset_movements.py + test_departamento_destino_062.py + test_presentacao_trilha_063.py`) → 5. Teste US2 (guarda) → 6. Régua completa + `validacao.md` no padrão da casa → 7. Commit (sob pedido do usuário).

**Incertezas registradas**: (a) o botão "Exportar CSV" aponta para a página `/reports/movements` (HTML), não para o endpoint CSV direto — mantido como está, fora do escopo; (b) não há paginação na listagem (limite fixo 200) — nada a preservar além do comportamento atual; (c) existência de snapshots legados em formato diferente de `branch - department (name)` em produção não foi auditada linha a linha — o fallback ao snapshot cru (caso 6) cobre qualquer formato desconhecido sem quebra.
