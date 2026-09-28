# Feature Specification: Compatibilização da Importação Inteligente de Localizações com a Nova Nomenclatura (048 → 050)

**Feature Branch**: `050-importacao-locais-nomenclatura`

**Created**: 2026-09-28

**Status**: Draft

**Input**: Compatibilizar a funcionalidade de Importação Inteligente de localizações (Spec 048 — `specs/048-importacao-inteligente/`) com as alterações de nomenclatura e semântica já realizadas no sistema (commit `62728fa`): o CSV oficial e o formulário passaram de `Nome;Filial;Departamento` para **`Localização;Unidade Administrativa;Departamento`**. A Spec 048 é requisito/base existente — esta spec NÃO recria a importação inteligente; analisa Spec 048 × implementação atual × nova nomenclatura e ajusta somente o que ficou desatualizado. Regra máxima: **ANALISAR → EVIDÊNCIA → AJUSTE MÍNIMO**.

> **Fatos verificados no código e execução real (2026-09-28)**: a nomenclatura nova foi aplicada **parcialmente** ao sistema — templates (`form.html`, `list.html` e parte de `import.html` de locations) e o CSV de exemplo documentado (`docs/doc_provisorios/docs_para_testes/doc-final/locais.csv`) já usam Localização/Unidade Administrativa/Departamento; porém o **mecanismo de importação não reconhece o cabeçalho oficial novo**: `_normalize_column_name('Unidade Administrativa')` devolve `unidade_administrativa` (não `branch`) — sem alias — e um CSV no formato oficial novo **falha hoje** com `"Linha 2: filial é obrigatória"` (execução real do `parse_locations_csv`). A camada inteligente exibe rótulos legados (`FIELD_LABELS["locations"]`: `"name": "Nome do local"`, `"branch": "Filial"` em `import_intelligence.py`). A tabela de pré-visualização de locais mantém `<th>Filial</th>` e `Nome / Identificação` (`import.html` L183). Este gap é o objeto desta spec.

---

## Clarifications

### Session 2026-09-28

- Q: O cabeçalho `Localização` (oficial novo) e `Nome`/`Nome da Localização` (legados) devem coexistir como aliases do mesmo campo lógico? → A: Sim — aliases controlados, já que `local`/`localização`/`nome` já são aliases de `name` no mecanismo atual; `Nome da Localização` e `Localização` passam a mapear explicitamente para `name`; nenhum alias novo inventado além dos termos legados documentados (decisão 2026-09-28).
- Q: `Unidade Administrativa` deve mapear para o campo `branch` existente (sem mudança de banco)? → A: Sim — o modelo atual já suporta os três conceitos (`Location.name` = local físico, `Location.branch` = unidade à qual está vinculada, `Location.department` = setor); a mudança é de contrato/aliases/rótulos, NÃO de schema; renomeação de coluna de banco está fora de escopo (decisão 2026-09-28).
- Q: Formas legadas como `Matriz/Filial` e `Filial / Unidade` devem continuar reconhecidas? → A: Apenas as que o sistema já reconhece hoje (`filial`, `unidade`, `empresa`, `sede` → `branch`) permanecem por compatibilidade; nenhum alias novo é criado para formas que o parser nunca aceitou (`matriz/filial`, `nome da localização` entram como alias novo apenas pela exigência oficial do pedido — mapeados para o campo canônico correspondente) (decisão 2026-09-28).
- Q: A exportação de locais (`locais.csv`, feature 008) deve ser incluída nesta spec, atualizando os cabeçalhos do CSV exportado para a nomenclatura oficial? → A: **Incluir** — os usuários usam o CSV exportado como modelo para reimportar; o round-trip exportar→importar fica 100% coerente com a nomenclatura oficial; ajuste confinado aos rótulos do export de locais (`report_service.py` hoje exporta `nome;filial;departamento` — evidência L460) e aos seus testes (`test_locations_export.py`) (decisão 2026-09-28).
- Q: O que fazer com os nomes de campos expostos pela API de localizações (`name`/`branch`/`department` nos schemas/endpoints)? → A: **Intocar a API** — a mudança de nomenclatura é de rótulos/mensagens/CSV, nunca de campos serializados; schemas, endpoints e consumidores externos (Central de Integrações, scripts) permanecem exatamente como estão; nenhum alias de schema é criado (decisão 2026-09-28).
- Q: Qual o alcance da varredura de eliminação de termos legados ("Filial", "Nome do local", "Nome / Identificação")? → A: **Domínio de locais** — varredura restrita a import/export/form/list/detail/search/JS de locations + rótulos do importador no código (`FIELD_LABELS` de locations, mensagens do parser); inclui corrigir assertions de testes que referenciam textos legados da tela de locais (ex.: `test_locations_export.py` L157 assertion "Nome / Identificação" — texto já inexistente na listagem oficial); telas de outros domínios ficam fora (decisão 2026-09-28).

## 1. Contexto

A terminologia oficial do SisPatrimônio Pro para localizações passou por alteração de nomenclatura e semântica (realizada após a Spec 048):

| Conceito | ANTES (legado) | AGORA (oficial) |
|---|---|---|
| Campo de identificação do local | Nome / Nome da Localização | **Localização** |
| Unidade à qual o local está vinculado | Filial / Matriz/Filial / Filial / Unidade | **Unidade Administrativa** |
| Setor associado | Departamento / Setor | **Departamento** (mantido) |

CSV oficial: `Localização;Unidade Administrativa;Departamento` (delimitador `;` ilustrativo — o mecanismo detecta `;`/`,`).

A alteração já foi aplicada em parte da interface (formulário de localização, listagem, trechos da tela de importação e CSV de exemplo documentado), mas **não** no mecanismo de importação (aliases do parser, rótulos da camada inteligente, tabela de prévia, testes e docs de referência).

## 2. Problema identificado (com evidência)

1. **O CSV oficial novo não importa**: `parse_locations_csv("Localização;Unidade Administrativa;Departamento\n...")` devolve erro `Linha 2: filial é obrigatória` — `unidade_administrativa` não resolve para `branch` e a validação procura o campo pelo nome legado na mensagem.
2. **Rótulos legados na camada inteligente**: `FIELD_LABELS["locations"]` exibe "Nome do local" e "Filial" no passo de mapeamento de colunas da importação inteligente (tela que a Spec 048 criou) — contradição direta com a nomenclatura oficial na mesma tela que já usa os termos novos na ajuda.
3. **Prévia com cabeçalhos legados**: a tabela de pré-visualização de locais exibe `Nome / Identificação` e `Filial` (import.html L183) — o pedido exige `Localização` e `Unidade Administrativa`.
4. **Mensagens de validação com termo legado**: "filial é obrigatória" deve refletir o termo oficial ("Unidade Administrativa é obrigatória") sem quebrar o reconhecimento de arquivos legados.
5. **Aliases legados soltos**: `local` e `localização` já mapeiam `name` (bom); `nome` também (compatibilidade); formas que nunca foram reconhecidas (`nome da localizacao`, `matriz/filial`) falham silenciosamente como "coluna desconhecida" ou obrigatório ausente.
6. **Testes e CSVs de teste** ainda exercitam primariamente o formato legado (`nome;filial;departamento` em `test_importacao_inteligente.py` L644; `tests/setores.csv` com `Nome,Filial,Departamento`) — legítimo como compatibilidade, mas não cobre o contrato oficial novo.
7. **Documentação**: `docs/ARQUITETURA_E_MANUTENCAO.md` referencia o importador sem a terminologia do CSV; exemplos espalhados podem citar colunas legadas.

## 3. Objetivo

Fazer com que a importação inteligente de localizações (e o fluxo de importação simples dela derivado) **aceite o CSV oficial novo como formato primário**, exiba a nomenclatura oficial em todas as telas/mensagens/relatórios do fluxo, **preservando** a inteligência da Spec 048 (análise, mapeamento com confirmação, classificação por registro, prévia, duplicidades, confirmação, gravação transacional existente, auditoria) e a **compatibilidade controlada** com arquivos legados — sem nenhuma mudança de schema, sem recriar importador, sem tocar regras patrimoniais.

## 4. Análise da Spec 048 (base existente — o que DEVE ser preservado)

- Objetivo e comportamento: análise somente-leitura → mapeamento com passo dedicado → classificação por registro (VÁLIDO/AVISO/DUPLICADO/ERRO/NÃO ENCONTRADO/IGNORADO) → prévia com filtros → confirmação explícita → gravação pelos `execute_*` existentes → relatório por linha (FR-001..FR-025 da 048).
- Guardas: 0 escrita na análise; ambiguidade nunca resolvida em silêncio; coluna desconhecida = "não utilizada"; zero valores fabricados; duplicidades (banco e interno) antes da gravação; auditoria `write_audit` existente; permissões existentes (`locais.criar`); parser existente não alterado sem necessidade.
- A Spec 048 NÃO fixa a lista de aliases de locais (evolui os existentes) e NÃO fixa rótulos de campo — ambos são exatamente os pontos que a mudança de nomenclatura torna obsoletos. **Não há conflito de comportamento entre 048 e a nova nomenclatura; há gap de contrato** (aliases/rótulos/mensagens) que esta spec fecha.

## 5. Análise do sistema atual (fonte: código real, 2026-09-28)

| # | Fato | Arquivo |
|---|---|---|
| A1 | `COLUMN_ALIASES` de locais: `nome`/`name`/`identificacao`/`local`/`localizaçao`/`localização`/`descricao_local`/`descricao` → `name`; `filial`/`branch`/`unidade`/`empresa`/`sede` → `branch`; `departamento`/`department`/`setor`/`area`/`divisao` → `department` | `location_import_service.py` L34–80 |
| A2 | **Sem alias** para `unidade_administrativa`, `nome_da_localizacao`, `matriz/filial` — a forma oficial nova falha | idem + execução real |
| A3 | Modelo `Location`: `name` (unique), `branch`, `department` (obrigatórios) + `building/floor/room/manager_name/description` — os 3 conceitos oficiais já suportados; **nenhuma migração necessária** | `app/models/location.py` |
| A4 | Formulário oficial novo aplicado: labels "Localização", "Unidade Administrativa", "Departamento / Setor" (inputs `name`, `branch`, `department` — nomes de campo inalterados) | `templates/locations/form.html` L28–36 |
| A5 | Tela de importação mista: ajuda já oficial (`Localização;Unidade Administrativa;Departamento`), porém prévia com `<th>Nome / Identificação</th>`, `<th>Filial</th>` | `templates/locations/import.html` L183, L286–357 |
| A6 | `FIELD_LABELS["locations"]`: `"name": "Nome do local"`, `"branch": "Filial"` — consumido por `routes.py` (L631/1580/1638) para o mapeamento inteligente e mensagens | `import_intelligence.py` L78–92 |
| A7 | Validação por linha exige `name`, `branch`, `department` e reporta "filial é obrigatória" (mensagem legada) | `location_import_service.py` `_validate_row` |
| A8 | Duplicidade por `name` normalizado (`_find_existing_location`) — regra real de unicidade; **não depende de rótulo**; nenhuma alteração necessária para evitar duplicidades | idem L163 |
| A9 | Camada inteligente: `analyze_columns` sugere por aliases (colisão `descricao` → ambígua já tratada); `_classify_location_row` classifica; testes usam `nome;filial;departamento` | `import_intelligence.py` L132+, `test_importacao_inteligente.py` L644 |
| A10 | CSV oficial novo já documentado no exemplo da tela e no material de testes (`docs/doc_provisorios/docs_para_testes/doc-final/locais.csv`) | docs |
| A11 | Exportação de locais (`locais.csv`, feature 008) — cabeçalho de exportação deve ser verificado no implement para coerência de rótulos (não bloqueante para importar) | `docs/ARQUITETURA_E_MANUTENCAO.md` L712 |
| A12 | `generate_locations_csv` escreve cabeçalho **legado**: `nome;filial;departamento;predio;andar;sala;gestor` (writer.writerow L460) — o arquivo que os usuários baixam como modelo não segue a nomenclatura oficial | `app/services/report_service.py` L447–470 |

## 6. Matriz de compatibilidade (Spec 048 × sistema atual × alteração necessária)

| Item | Spec 048 | Sistema atual | Alteração necessária |
|---|---|---|---|
| CSV de locais | Evolui aliases existentes (FR-002) | Oficial novo **falha** (sem alias `unidade administrativa` → `branch`) | **SIM** — adicionar aliases oficiais novos (A2) |
| Localização (name) | Rótulo livre | Alias já resolve (`localização` → `name`); `nome da localização` não resolve | **SIM** — alias `nome_da_localizacao` → `name` |
| Unidade Administrativa (branch) | Rótulo livre | Sem alias; rótulo "Filial" na UI | **SIM** — alias + rótulo oficial |
| Departamento (department) | Rótulo livre | Alias resolve; rótulo correto | NÃO (só conferir rótulos) |
| Formulário | fora de escopo da 048 | Já oficial (A4) | NÃO |
| Parser (delimitador/BOM/aspas) | FR-020 preservar | OK (utf-8-sig, `;`/`,`) | NÃO |
| Prévia da importação | Reutiliza componentes | Cabeçalhos legados "Nome / Identificação", "Filial" (A5) | **SIM** — rótulos oficiais |
| Mensagens de validação | Relatório legível (FR-017/FR-009) | "filial é obrigatória" (A7) | **SIM** — "Unidade Administrativa é obrigatória" |
| Mapeamento inteligente (048) | Rótulos da entidade | "Nome do local"/"Filial" (A6) | **SIM** — rótulos oficiais |
| Duplicidades | FR-009 (por nome real) | Por `name` normalizado (A8) — imune a rótulos | NÃO (regredir = proibido) |
| Auditoria | write_audit existente | Padrão `IMPORT_*` sem termo de coluna | NÃO (verificar no implement) |
| Aliases legados (`filial`, `unidade`, `empresa`, `sede`, `nome`) | FR-002 evolui existentes | Ativos | **MANTER** (compatibilidade controlada) |
| Exportação de locais | fora do escopo da 048 | `nome;filial;departamento` (A12) | **SIM** — cabeçalhos oficiais (FR-026, decisão da clarify) |
| Banco/schema | fora de escopo | Já suporta os conceitos (A3) | NÃO — proibido renomear colunas |
| Testes | 048 cobriu com CSV legado | `nome;filial;departamento` (A9) | **SIM** — novo contrato oficial + compatibilidade |
| Docs | XI da 048 | Referências genéricas (A11) | **SIM** — terminologia nos trechos de locais |

## 7. Requisitos

### Functional Requirements

**Contrato oficial (US1 — P1)**

- **FR-001**: O importador de localizações MUST reconhecer o cabeçalho oficial **`Localização`** → campo `name` (incluindo variações de caixa/acento/espaço pelo mecanismo existente).
- **FR-002**: O importador MUST reconhecer **`Unidade Administrativa`** → campo `branch` existente (sem qualquer alteração de modelo/banco).
- **FR-003**: O importador MUST reconhecer **`Departamento`** → campo `department` (já reconhecido — manter).
- **FR-004**: Um CSV com cabeçalho oficial `Localização;Unidade Administrativa;Departamento` MUST ser importado com sucesso (análise, mapeamento sugerido correto, classificação, prévia e gravação) — hoje falha (Problema 1).
- **FR-005**: A ordem das colunas MUST continuar livre (mapeamento por cabeçalho, nunca por posição — inteligência da 048 preservada).

**Compatibilidade controlada (US2 — P1)**

- **FR-006**: Os aliases legados já reconhecidos hoje MUST permanecer funcionando: `nome`/`name`/`identificacao`/`local`/`localização`/`descricao_local` → `name`; `filial`/`branch`/`unidade`/`empresa`/`sede` → `branch`; `departamento`/`department`/`setor`/`area`/`área`/`divisao`/`divisão` → `department` — zero regressão de arquivos antigos.
- **FR-007**: `Nome da Localização` (termo legado do formulário antigo) MUST mapear explicitamente para `name` (hoje vira coluna desconhecida).
- **FR-008**: Nenhum alias MAY ser criado para formas que o sistema nunca reconheceu e que não pertençam às nomenclaturas oficial/legada documentadas (ex.: `matriz/filial` permanece coluna não utilizada — comportamento atual de "desconhecida" da 048, sem invenção).
- **FR-009**: Colisões de aliases (2+ campos canônicos na mesma chave) MUST continuar tratadas como ambíguas com confirmação do usuário (FR-003 da 048) — a adição de aliases novos não pode introduzir colisão silenciosa.

**Nomenclatura oficial na interface e mensagens (US3 — P1)**

- **FR-010**: O passo de mapeamento da importação inteligente MUST exibir os rótulos oficiais: "Localização" (name), "Unidade Administrativa" (branch), "Departamento" (department) — substituindo "Nome do local" e "Filial" em `FIELD_LABELS["locations"]`.
- **FR-010a**: A varredura de termos legados MUST cobrir todo o domínio de locais (templates form/list/detail/search/import, JS do domínio, rótulos de `FIELD_LABELS["locations"]` e mensagens do parser de locais) — não apenas a tela de importação; assertions de testes que referenciem textos legados da tela de locais MUST ser atualizados junto (ex.: "Nome / Identificação" em `test_locations_export.py` — texto já inexistente na listagem, que usa cabeçalhos oficiais). Termos legados em dados de teste (valores como branch="Filial Norte") são conteúdo, não rótulos — permanecem.
- **FR-011**: A tabela de pré-visualização de locais MUST usar cabeçalhos oficiais (`Localização`, `Unidade Administrativa`, `Departamento`) — substituindo "Nome / Identificação" e "Filial".
- **FR-012**: As mensagens de validação MUST usar a terminologia oficial (ex.: "Unidade Administrativa é obrigatória" em vez de "filial é obrigatória") sem alterar os campos avaliados.
- **FR-013**: Situações de prévia e relatório ("nova localização", "já existente", "será criado") MUST usar os termos oficiais quando se referirem aos conceitos alterados.
- **FR-014**: A ajuda/documentação da própria tela de importação MUST permanecer consistente com os rótulos exibidos (hoje a ajuda já está oficial — evitar regressão).

**Semântica e dados (US4 — P1)**

- **FR-015**: Os três conceitos MUST permanecer semanticamente distintos: Localização = local físico (name), Unidade Administrativa = unidade administrativa vinculada (branch), Departamento = setor associado (department) — nunca sinônimos, nunca mesclados.
- **FR-016**: Nenhuma alteração de schema MAY ser feita (nenhuma coluna renomeada, nenhuma tabela nova) — o modelo atual já suporta os conceitos (A3).
- **FR-017**: Dados existentes MUST ser preservados integralmente: nenhuma localização, patrimônio ou movimentação apagada/recriada pela mudança de nomenclatura.
- **FR-018**: A unicidade e a comparação de duplicidade MUST continuar pelos valores reais dos campos (`name` normalizado — A8): a mudança de rótulo NÃO pode gerar duplicidades nem registros novos.

**Preservação da inteligência 048 (US5 — P1)**

- **FR-019**: Todo o comportamento da Spec 048 MUST permanecer: análise somente-leitura, passo de mapeamento dedicado com confirmação, colunas desconhecidas como "não utilizada", classificação por registro, prévia com filtros, confirmação explícita, gravação pelos `execute_locations_import` existentes, relatório por linha, auditoria `write_audit`, permissão `locais.criar`.
- **FR-020**: Rotas/URLs do importador (`/locations/import`, `/locations/import/confirm`) MUST permanecer inalteradas.
- **FR-021**: O motor patrimonial, movimentações, inventário e demais importadores (equipamentos/colaboradores) MUST permanecer intocados (a mudança é restrita ao domínio de locais).

**Exportação coerente (US6 — P2)**

- **FR-026**: O CSV de exportação de locais (`generate_locations_csv`) MUST usar cabeçalhos oficiais: `Localização;Unidade Administrativa;Departamento;Prédio;Andar;Sala;Gestor` (hoje `nome;filial;departamento;predio;andar;sala;gestor` — evidência A12) — alteração apenas dos rótulos do cabeçalho; valores e colunas inalterados.
- **FR-027**: O arquivo exportado com os cabeçalhos oficiais MUST ser reimportável sem ajustes (round-trip exportar→importar coerente) — coberto pelo cenário 1 do FR-022.

### Requisitos de teste

- **FR-022**: A suíte MUST ganhar cobertura do contrato oficial novo: (1) CSV oficial válido importado; (2) ordem de colunas diferente; (3) espaços nos cabeçalhos; (4) caixa/acentuação variada; (5) cabeçalhos legados ainda aceitos (`Nome;Filial;Departamento`); (6) cabeçalho desconhecido marcado "não utilizada"; (7) coluna obrigatória ausente com mensagem oficial; (8) valores vazios → erro por campo com termo oficial; (9) localização existente → DUPLICADO sem novo registro; (10) reanálise do mesmo arquivo → duplicados, nada duplicado; (11) rollback da linha com erro preservado; (12) dados pré-existentes intactos.
- **FR-023**: A suíte existente (`test_importacao_inteligente.py`, `test_import_asset_location.py`, `test_locations_export.py`, `test_locations_search.py` e suíte completa) MUST permanecer 100% verde.

### Requisitos de documentação

- **FR-024**: Trechos de documentação relacionados à importação **e exportação** de localizações MUST usar a terminologia e o CSV oficiais — atualização mínima, sem tocar seções de funcionalidades não relacionadas (Princípio XI).

### Requisitos de segurança/auditoria (preservação)

- **FR-025**: Auditoria e permissões MUST permanecer exatamente como na 048 (eventos `IMPORT_*` existentes; `locais.criar`) — nenhum evento novo, nenhuma concessão, segredos jamais registrados. Se algum texto de auditoria citar rótulos legados, atualizar somente a descrição legível sem alterar tipo/evento/consultas.

## 8. Success Criteria

- **SC-001**: CSV oficial `Localização;Unidade Administrativa;Departamento` importado com sucesso ponta a ponta (análise → mapeamento → prévia → confirmação → gravação → relatório) — comprovado por teste (hoje: falha).
- **SC-002**: 100% dos aliases legados listados em FR-006 continuam funcionando (teste de regressão dedicado).
- **SC-003**: 0 ocorrências dos rótulos legados no **domínio de locais** ("Nome do local", "Filial", "Nome / Identificação" como rótulos de coluna/campo de locais; "filial é obrigatória" como mensagem) — verificado por busca no código (templates/services/JS de locations + `FIELD_LABELS`) + testes; termos legados em **valores de dados** (ex.: branch="Filial Norte" em fixtures) não contam como violação.
- **SC-004**: 0 duplicidades criadas pela mudança de nomenclatura (mesmo arquivo em formato legado e oficial → mesmos registros, sem duplicar).
- **SC-005**: Suíte sem regressão (semântica do baseline medido no plan — R7): os **842 testes que passavam** continuam passando; os **3 failures do domínio de locais** (assertions defasados do `62728fa`) passam a passar; os **2 failures de `test_backup_externo.py`** permanecem como baseline externo documentado (feature 045, fora do escopo — FR-021); todos os novos testes do contrato (FR-022) verdes.
- **SC-006**: 0 alterações fora do domínio de locais/importação (diff confinado a `location_import_service.py`, `import_intelligence.py` (só rótulos de locations), `report_service.py` (só `generate_locations_csv`), `templates/locations/import.html`, testes e docs de locais).
- **SC-007**: 0 alterações de schema/migração (verificado por diff de `models/` e `data/` vazio).

## 9. Estratégia de migração

**Nenhuma migração de dados necessária** — a alteração é de contrato de importação (aliases), rótulos e mensagens. O banco permanece intocado (FR-016/017). Compatibilidade com arquivos legados é preservada por aliases (FR-006/007), sem bandeira/flag nova.

## 10. Arquivos potencialmente afetados

- `app/services/location_import_service.py` — aliases oficiais + mensagem de validação oficial (extensão mínima de `COLUMN_ALIASES` e texto de `_validate_row`).
- `app/services/report_service.py` — **apenas** `generate_locations_csv` (cabeçalhos oficiais do export, FR-026/FR-027).
- `app/services/import_intelligence.py` — **apenas** `FIELD_LABELS["locations"]` (rótulos oficiais).
- `app/web/templates/locations/import.html` — cabeçalhos da prévia (e conferência de consistência dos textos).
- `tests/test_locations_export.py` — ajuste dos assertions do export (FR-026) e do texto legado da listagem ("Nome / Identificação", L157 → texto oficial, FR-010a).
- `tests/test_importacao_inteligente.py` (+ novo/ajustado arquivo de testes do contrato de nomenclatura), fixtures CSV se necessário.
- `docs/ARQUITETURA_E_MANUTENCAO.md` (trecho de locais) e material de ajuda relacionado.
- **Intocáveis**: `models/location.py`, schemas, `routes.py` (URLs/lógica), `execute_locations_import` (gravação), motor de movimentações, inventário, outros importadores, auditoria/permissões, demais telas.

## 11. Riscos e cuidados

| Risco | Cuidado |
|---|---|
| Quebrar arquivos legados ao adicionar aliases | FR-006 com teste de regressão dedicado; nenhum alias removido |
| Introduzir colisão ambígua nova | Verificar reversão alias→campo após adicionar (FR-009; `descricao` permanece a única ambígua conhecida) |
| Mensagem oficial quebrar consumo/teste existente | Mensagens são exibidas ao usuário e testadas por substring nos testes da 048 — atualizar os trechos afetados junto (mesma task) |
| Vazamento do ajuste para outros importadores | Rótulos alterados **somente** na entrada `locations` de `FIELD_LABELS` |
| Confundir rótulo com campo | Campos de banco/`name` de input do formulário permanecem `name`/`branch`/`department` |

## 12. Explicitamente fora de escopo (NÃO alterar)

- Renomear colunas/tabelas do banco; qualquer migração de dados; **renomear campos serializados na API** (schemas/endpoints de localizações intocados — decisão 2026-09-28).
- Recriar/substituir o importador inteligente; novo parser; novas telas/URLs.
- Regras de movimentação, alocação, histórico, inventário, patrimônio.
- Aliases indiscriminados (ex.: `matriz/filial` → branch) além do oficial + legados documentados.
- Outras telas/funcionalidades (equipamentos, colaboradores, relatórios, backup, AD, RBAC, 1Doc, GLPI).
- Auditoria (mecanismo/eventos) e permissões (exceto verificação de consistência de texto).

## 13. Assumptions

- A nomenclatura oficial definida pelo solicitante prevalece sobre textos antigos onde houver divergência puramente terminológica.
- O delimitador e o encoding seguem o mecanismo atual (detecção `;`/`,` e `utf-8-sig`) — o CSV oficial usa `;` nos exemplos, mas ambos são aceitos.
- A exportação de locais (feature 008) pode ter rótulos conferidos no implement por coerência, sem ser objetivo desta spec (ajuste só se trivial e restrito a rótulos de locais).
