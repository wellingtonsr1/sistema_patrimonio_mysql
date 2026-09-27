---
description: "Task list for feature implementation"
---

# Tasks: Importação Inteligente — Evolução dos Importadores CSV (048)

**Input**: Design documents from `/specs/048-importacao-inteligente/`

**Prerequisites**: plan.md (required), spec.md (required), research.md (R1–R9), data-model.md, contracts/contrato-importacao-inteligente.md, quickstart.md

**Tests**: Testes automatizados SIM (pedido §37–40 exige Testes A–Q; Constitution VIII): novo arquivo `tests/test_importacao_inteligente.py` com testes ESCRITOS PRIMEIRO e falhando antes da implementação de cada story. Regressão R9: os testes existentes dos importadores devem passar **sem alteração**.

**Organization**: Tasks agrupadas por story (US1 mapeamento → US2 classificação/preview → US3 confirmação/relatório), sobre os 3 importadores existentes (Equipamentos/Colaboradores/Locais).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência pendente)
- **[Story]**: US1 / US2 / US3 da spec

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Fatos de integração confirmados e baseline da suíte

- [X] T001 Confirmar fatos de integração no código atual (assinaturas de `parse_csv`/`preview_import`/`execute_import` em `app/services/import_service.py`, `execute_custodian_import` em `app/services/custodian_import_service.py`, `execute_locations_import` em `app/services/location_import_service.py`, `COLUMN_ALIASES` dos 3, transporte `csv_rows|tojson` nos templates de confirm) e rodar baseline: `.venv/bin/python -m pytest tests/ -q` → **775 passed** (registro no tasks.md)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Camada compartilhada de análise consumida pelas 3 stories (R2)

**⚠️ CRITICAL**: Nenhuma story começa antes desta fase

- [X] T002 [P] Escrever testes TDD de `analyze_columns` (falhando primeiro) em `tests/test_importacao_inteligente.py`: coluna canônica → `auto` (`tombamento`/`TOMBAMENTO`/`nº tombamento`/`patrimonio` → Tombamento); coluna ambígua (colisão de 2+ campos canônicos do mesmo kind na reversão dos aliases) → `ambigua` com `candidates` (FR-003); coluna `cor` → `desconhecida` (FR-005); contagem de registros e delimitador `,`/`;` detectados; zero escrita no banco durante a análise (SC-001)
- [X] T003 Criar `app/services/import_intelligence.py` com `analyze_columns(content, kind)` (R1): união dos `COLUMN_ALIASES` dos 3 services sem duplicar, `_detect_delimiter`/`csv` existentes, guardas R6 iniciais (vazio/só BOM/sem registros → `parse_errors`), `ColumnSuggestion` com `confidence` auto/ambigua/desconhecida conforme data-model §2.1 — sugestões a partir dos aliases do kind selecionado, `ambigua` só por colisão dentro do kind (A1) — implementar até T002 passar

**Checkpoint**: Camada de análise pronta — stories podem começar

---

## Phase 3: User Story 1 — Análise e mapeamento de colunas antes da gravação (Priority: P1) 🎯 MVP

**Goal**: Upload do CSV → passo intermediário dedicado de mapeamento (confirmar/alterar/ignorar colunas) → nada gravado

**Independent Test**: CSVs de cabeçalhos variados (canônico, variações/acentos, colunas desconhecidas, ambíguas) apresentam o mapeamento correto; banco inalterado (quickstart H/I/J/K + US1.1–4)

### Tests for User Story 1 ⚠️ (escritos primeiro, falhando)

- [X] T004 [P] [US1] Escrever testes TDD do passo de mapeamento em `tests/test_importacao_inteligente.py`: `POST /assets/import` (e equivalentes `/custodians/import`, `/locations/import`) com `file` responde o passo de mapeamento com sugestões pré-selecionadas (`auto`), ambíguas sem seleção e desconhecidas como "não utilizada" (contrato §3); Teste I — mapeamento manual alterado e aplicado na fase seguinte; Testes J/K — arquivo vazio, CSV corrompido, encoding inválido, extensão não-CSV e tamanho acima do limite vigente → mensagem compreensível sem traceback (R6/FR-021); guardas capturam `UnicodeDecodeError`/`csv.Error`; Teste L — CSV com BOM/ponto e vírgula/acentuação → dados lidos e preservados (FR-019/FR-020)

### Implementation for User Story 1

- [X] T005 [US1] Implementar a fase de mapeamento nas 3 rotas de import em `app/web/routes.py` (R5): `POST import` com `file` → renderiza `step=map`; `POST import` com `step=analyze` + `mapping` + arquivo oculto → (por enquanto) reexecuta análise e prepara classificação; análise reexecutada server-side a cada fase (data-model §4); permissões existentes inalteradas
- [X] T006 [US1] Criar template parcial do passo de mapeamento (contrato §3) e incluir nos 3 templates de import (`app/web/templates/assets/import.html`, `custodians/import.html`, `locations/import.html`): tabela coluna → campo com `select` (campo sugerido/outros campos/"não utilizada"), arquivo original em campo oculto JSON (padrão `csv_rows|tojson` vigente), destaque para ambíguas/desconhecidas, avançar exige obrigatórios mapeados; zero CSS global novo
- [X] T007 [US1] Completar guardas R6 na apresentação (mensagens amigáveis por caso: vazio, sem registros, sem cabeçalho, corrompido, encoding) e rodar os testes da US1 + comprovar SC-001/SC-003 (zero escrita entre upload e preview; zero coluna silenciada)

**Checkpoint**: US1 funcional e testável isoladamente — upload → mapeamento → sem gravação

---

## Phase 4: User Story 2 — Classificação por registro e pré-visualização sem gravação (Priority: P1)

**Goal**: Cada registro classificado individualmente (VÁLIDO/AVISO/DUPLICADO/ERRO/NÃO ENCONTRADO/IGNORADO) com preview filtrável e resolução interativa — banco inalterado

**Independent Test**: CSV misto (válidos, incompletos, duplicados no banco e no arquivo, responsável inexistente) → classificação correta por linha; contagens do banco idênticas antes/depois (quickstart A/B/C/D/E/F/G/M)

### Tests for User Story 2 ⚠️ (escritos primeiro, falhando)

- [X] T008 [P] [US2] Escrever testes TDD de `classify_rows` (falhando primeiro) em `tests/test_importacao_inteligente.py`: Teste A — CSV válido → todos VALIDO; Teste B — parciais (sem responsável/sem local) → VALIDO com AVISO informacional "Responsável não informado"/"Local não informado" (F3), sem valor fabricado (SC-004); Teste C — misto → classificação por linha (SC-002); Teste D — tombamento existente no banco → DUPLICADO; Teste E — duplicado dentro do próprio arquivo → DUPLICADO com `internal_dup_of`; Teste F — responsável inexistente → NAO_ENCONTRADO sem atribuição automática; Teste G — local inexistente (equipamentos) → regra atual preservada; linhas em branco → IGNORADO

### Implementation for User Story 2

- [X] T009 [US2] Implementar `classify_rows(rows, db, kind, mapping, overrides)` em `app/services/import_intelligence.py` (R3): casca sobre `_validate_row` de cada service (obrigatórios reais F3), duplicidade interna por chave natural (data-model §3: tombamento/matrícula+email/nome normalizado), verificações de duplicata existentes (tag/serial, matrícula/email, nome do local), relacionamentos pelos mecanismos atuais (`_resolver_custodiante`, `LocationService.get_by_name`); normalização só para comparação, valor original preservado (R7)
- [X] T010 [US2] Implementar a estrutura de resolução interativa (R4) em `import_intelligence.py` + rotas: `PreviewSmart.needs_resolution` (linhas NAO_ENCONTRADO), candidatos de colaborador para `assign` (pesquisa existente), `resolutions` = `{row_num: skip|sem_custodia|assign:<id>}` coletadas na preview e validadas server-side na fase seguinte (data-model §2.4)
- [X] T011 [US2] Renderizar a pré-visualização classificada nos 3 templates de import (contrato §4): resumo (total/válidos/avisos/duplicados/erros/não encontrados/ignorados), tabela por linha (linha, identificadores, situação, problema), badges existentes (P-2: `bg-success`/`bg-warning text-dark`/`bg-secondary`/`bg-danger`/`bg-info text-dark`/`bg-light text-dark border`), filtros Todos/Válidos/Avisos/Erros/Duplicados/Ignorados, campos de resolução por linha NÃO ENCONTRADO, link Cancelar (Teste M — nenhum efeito no banco; teste `test_cancelar_antes_gravacao_nao_altera_banco`)
- [X] T012 [US2] Rodar os testes da US2 + comprovar SC-001/SC-002/SC-004/SC-005 (zero escrita na preview; zero rejeição em bloco; zero valor fabricado; 100% das duplicidades identificadas)

**Checkpoint**: US1 + US2 funcionais — upload → mapeamento → preview classificada, banco inalterado

---

## Phase 5: User Story 3 — Confirmação, gravação segura e relatório (Priority: P1)

**Goal**: Confirmação com resumo e `skip_duplicates` explicitado; gravação pelos `execute_*` existentes; relatório por linha; reprocessamento sem duplicar

**Independent Test**: CSV misto confirmado grava somente permitidos, audita pelo padrão atual, produz relatório por linha; reenvio do mesmo arquivo classifica os já importados como DUPLICADO (quickstart N/O/Q + US3.1–5)

### Tests for User Story 3 ⚠️ (escritos primeiro, falhando)

- [X] T013 [P] [US3] Escrever testes TDD de confirmação/relatório (falhando primeiro) em `tests/test_importacao_inteligente.py`: US3.1 — confirm grava válidos (+avisos conforme comportamento atual), nunca ERRO (SC-006), duplicados conforme `skip_duplicates` (marcado → pulados; desmarcado → reimportação atualiza, regra 029); resoluções R4 aplicadas (`skip` remove a linha, `sem_custodia` grava sem custodiante, `assign:<id>` grava com o colaborador escolhido); Teste N — erro na gravação → rollback da linha documentado da 029, demais linhas preservadas, mensagem clara; Teste O — auditoria `write_audit` com quantidades por classificação, sem segredos (SC-008); Teste P — usuário sem permissão bloqueado nas fases de import/confirm das 3 rotas (FR-023); US3.4 — reenvio do mesmo arquivo → já importados como DUPLICADO (FR-018)

### Implementation for User Story 3

- [X] T014 [US3] Aplicar resoluções antes da gravação (R4) nas 3 rotas de confirm em `app/web/routes.py`: lote montado com linhas resolvidas/filtradas (sem ERRO, sem skip) e passado aos `execute_*` existentes — **nenhuma mudança de assinatura/semântica em `execute_import`/`execute_custodian_import`/`execute_locations_import`**; `movement_service` intocado (FR-015/FR-016)
- [X] T015 [US3] Adicionar `row_results` (retorno aditivo — R8) aos 3 `execute_*` em `app/services/import_service.py`, `custodian_import_service.py`, `location_import_service.py` (linha, status, identificadores, motivo) e estender a description do `write_audit` com quantidades por classificação (sem segredos); consumidores atuais dos contadores continuam funcionando (testes 029/014 provam)
- [X] T016 [US3] Implementar tela de confirmação com resumo + `skip_duplicates` explicitado e o relatório final por linha (contrato §5–6) nos 3 templates: resumo (Total analisado/Importados/Avisos/Duplicados/Erros/Ignorados) e tabela por linha construída de `row_results`; rodar os testes da US3 + comprovar SC-006/SC-008/SC-009

**Checkpoint**: Ciclo completo — upload → mapeamento → preview → confirmação → gravação segura → relatório

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T017 [P] Atualizar documentação/ajuda dos importadores (Princípio XI): novo fluxo em 3 fases, classificação, resolução interativa, `skip_duplicates` explicitado — `docs/` + artigo de ajuda existente de importação (mesmo padrão das features anteriores)
- [X] T018 Rodar a suíte completa `.venv/bin/python -m pytest tests/ -q` (≥ **775 passed** + novos) e verificar R9/SC-007: testes existentes dos importadores (`test_import_asset_*`, `test_custodian_import*`) verdes **sem alteração**; diff confinado aos arquivos previstos (`*_import_service.py`, `import_intelligence.py`, `routes.py` — rotas de import, 3 templates + parcial, testes, docs) — `movement_service`, modelos, permissões, backup, AD, e-mail, 1Doc, GLPI intocados
- [X] T019 Criar/atualizar `specs/048-importacao-inteligente/validacao.md` com os resultados (testes A–Q do quickstart, comprovações SC-001…009, limitações) e marcar tasks concluídas neste tasks.md
- [ ] T020 Commit da feature (padrão "Feature 048: ..." sem acentos + footer Codebuff) excluindo arquivos pessoais não relacionados, e produzir o Relatório Final obrigatório (§44 do pedido: arquivos alterados/porquê, reutilizações, novo fluxo, duplicidades, opcionais, ausentes/inexistentes, fluxo patrimonial, auditoria, permissões, testes executados/resultados, limitações, partes não alteradas)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (T001)**: imediato
- **Foundational (T002–T003)**: bloqueia todas as stories (camada compartilhada)
- **US1 (T004–T007)**: após Foundational — fases de upload/mapeamento nas rotas
- **US2 (T008–T012)**: após US1 (consome análise + mapeamento confirmado)
- **US3 (T013–T016)**: após US2 (consome classificação + resoluções)
- **Polish (T017–T020)**: após todas as stories

### Within Each User Story

- Testes escritos e FALHANDO antes da implementação (T002→T003, T004→T005–T007, T008→T009–T012, T013→T014–T016)
- Service antes de rota; rota antes de template
- Checkpoint de cada story validado antes da próxima

### Parallel Opportunities

- T002 (testes da camada) é independente e pode ser escrito em paralelo com T001
- T004/T008/T013 (lotes de testes por story) marcados [P]
- T017 (docs) paralelizável com T018
- Os 3 importadores seguem o MESMO padrão por fase — implementar um e replicar nos demais (mesmos arquivos de rota/template, por isso sem [P] entre entidades)

---

## Implementation Strategy

### MVP First (US1 Only)

1. T001 → T002–T003 (fundação) → T004–T007 (mapeamento)
2. **STOP and VALIDATE**: upload → passo de mapeamento com sugestões — banco inalterado

### Incremental Delivery

- +US2 → preview classificada com resolução interativa (valor central de segurança)
- +US3 → ciclo fechado com gravação segura e relatório

### Compatibilidade (R9 — contrato de regressão)

- Com o mapeamento aceito como sugerido, o resultado é idêntico ao fluxo atual; os testes existentes passam sem alteração — qualquer divergência é bug da feature.

---

## Notes

- Baseline da suíte: **775 passed** (pós-047) — reconfirmado em 2026-09-26 (T001)
- Zero URL nova, zero permissão nova, zero migração, zero CSS global novo, zero dependência nova
- Fontes gravadas intocadas: `MovementService`, modelos, `permission_service`, auditoria (mecanismo), backup/AD/e-mail/1Doc/GLPI/inventário
