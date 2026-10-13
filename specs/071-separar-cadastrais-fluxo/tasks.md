# Tasks: 071-separar-cadastrais-fluxo

**Input**: Documentos de design de `/specs/071-separar-cadastrais-fluxo/`

**Pré-requisitos**: plan.md (presente), spec.md (presente), sem research/data-model/contracts para esta feature.

**Testes**: As tasks abaixo incluem tasks de teste. Testes são OPCIONAIS — incluídos aqui porque a spec 071 o exige explicitamente (FR-010).

**Organização**: Tasks agrupadas por user story para permitir implementação e teste independentes de cada story.

## Formato: `[ID] [P?] [Story] Descrição`

- **[P]**: Pode executar em paralelo (arquivos diferentes, sem dependência)
- **[Story]**: Qual user story a task pertence (ex.: US1, US2, US3)
- Incluir caminhos exatos de arquivo nas descrições

## Convenções de caminho

- **Projeto web único**: caminhos na raiz do repositório (`app/web/...`, `tests/...`).

## Fase 1: Setup (Infraestrutura compartilhada)

**Propósito**: Nada externo é necessário. Estado da dependência: a 070 **já está commitada** (`5b3f71f "Implementação da spec 070"`) — spec §6 satisfeita; o commit da 071 vem depois dele.

- [x] T001 Verificar que a implementação 070 e seus testes existem na árvore de trabalho (`app/web/routers/assets.py`, `app/web/templates/assets/detail.html`, `tests/test_legibilidade_trilha_070.py`) e que HEAD contém o commit `5b3f71f`; snapshot do baseline (1059 passed, 3 skipped, 3 failures = infraestrutura de migrações `alembic`, fora do escopo da 071).
- [x] T002 Identificar o predicado exato de alteração cadastral: registros `AuditLog` com `resource='Asset'`, `resource_id` do bem e `action == "ALTERACAO"` (mesmo filtro de `AssetService.get_cadastral_history`); confirmar que nenhuma outra ação de auditoria chega ao ramo de auditoria da trilha hoje (análise da spec §1.6: apenas ALTERACAO).
- [x] T003 Confirmar que `MovementService.get_timeline_for_asset`, `GET /api/v1/assets/{id}/timeline` e o caminho de gravação de auditoria não serão tocados: sem mudança na chamada do service de timeline, sem mudança em `write_audit`/`write_change_audit`, sem migração.

## Fase 2: Foundational (Pré-requisitos bloqueantes)

**Propósito**: Evidências de baseline e guardas que bloqueiam a implementação.

- [x] T004 Executar a suíte completa e registrar o baseline (escopo 070 + 071) com status de saída explícito: esperado 1059 passed, 3 skipped, 3 failures (`alembic` ausente — infraestrutura). Não ocultar o status.
- [x] T005 Executar `tests/test_legibilidade_trilha_070.py` isolado e confirmar 11 passed como baseline da guarda 070 (nenhum arquivo de teste modificado ainda).
- [x] T006 Escrever o novo arquivo `tests/test_separacao_cadastral_fluxo_071.py` com três grupos independentes mapeados às seções da spec (limpar sujeiras de iteração anterior: helper `_gravar_evento` no-op, criação duplicada de local — usar `LocationService.create` e `AuditLog` direto):
  - US1: editar um bem + movimentá-lo; provar que o HTML renderizado contém os itens do painel `cadastral_history` e **zero** itens `audit` com `action == "ALTERACAO"` na trilha; provar que a movimentação permanece.
  - US2: mais de 50 edições num bem; provar painel 50 + aviso `truncado`; provar que o banco e o payload da API não mudam (snapshot de `audit_logs` e contrato de chaves da API).
  - US3: fallback — item `audit` atípico não cadastral (ação diferente de ALTERACAO/MOVIMENTACAO/MANUTENCAO/CRIACAO) continua renderizado na trilha; `ALTERACAO` nunca aparece na trilha.
- [x] T007 Executar o novo arquivo e confirmar o grupo US1/US2/US3 em RED antes da implementação (gate TDD) — os testes falham contra a árvore atual porque os cartões `ALTERACAO` ainda são renderizados na trilha.

## Fase 3: User Story 1 - Trilha de Fluxo sem alterações cadastrais duplicadas (Priority: P1) 🎯 MVP

**Goal**: Em `GET /assets/{asset_id}`, a seção "Trilha de Fluxo & Movimentações" deixa de renderizar registros de `AuditLog` com `action == "ALTERACAO"`; permanecem apenas os itens não cadastrais (movimentações e o fallback US3). O painel `#historico-cadastral` (fonte `cadastral_history`) permanece intocado.

**Teste independente**: Abrir `/assets/{id}` após editar o nome e movimentar o bem: item `ALTERACAO` ausente da trilha, movimentação presente; painel inalterado.

- [x] T008 Setup: em `view_asset_detail` (`app/web/routers/assets.py`, GET `/assets/{asset_id}`), construir a timeline filtrada de apresentação antes do `TemplateResponse`, com dicts Python: manter o item se `item.get("type") != "audit"` OU `(item.get("data") or {}).get("action") != "ALTERACAO"` (predicado equivalente com guardas explícitas); a variável `timeline` entregue ao template passa a ser a filtrada. Sem mudança em `MovementService.get_timeline_for_asset`.
- [x] T009 Implementar o filtro com guardas defensivas para itens malformados (sem `type` ou sem `data`/`action`): itens que **não podem ser classificados com segurança PERMANECEM na trilha** (fallback R-C2/FR-006/US3) — nenhum item é descartado ou ocultado por não classificabilidade; verificar que o conjunto renderizado corresponde ao teste independente da US1 (0 itens `audit` `ALTERACAO` na trilha, todas as movimentações preservadas).
- [x] T010 [P] Adicionar o predicado companheiro em `app/services/asset_service.py` (helper opcional, ex. `is_cadastral_audit(item)`), usado pela rota e testável em unidade; sem mudar assinatura ou comportamento de `get_cadastral_history`.
- [x] T011 Commit único da 071: confirmar que HEAD já contém `5b3f71f` (implementação da 070, dependência §6 da spec satisfeita) e commitar a 071 com apenas as mudanças de apresentação + novo arquivo de teste (dois commits distintos e auditáveis já garantidos pelo histórico).

## Fase 4: User Story 2 - Acessibilidade do histórico cadastral garantida (Priority: P1)

**Goal**: O painel continua exibindo as 50 edições mais recentes com o aviso `truncado`; `/admin/audit` e a API permanecem como caminhos de acesso completo; nenhum evento fica órfão.

**Teste independente**: >50 edições: painel = 50 + `truncado`; eventos antigos acessíveis via `/admin/audit` e API; `audit_logs` byte-a-byte idêntico.

- [x] T012 Re-executar `tests/test_legibilidade_trilha_070.py` após o ajuste documentado e mínimo dos asserts diretamente ligados ao novo comportamento — ENUMERAR explicitamente os testes ajustados (US1: `test_campo_unico_titulo_rrotulo_antes_depois`, `test_varios_campos_todos_listados_inalterados_ausentes`, `test_campo_desconhecido_e_fallbacks`; US2: `test_details_recolhido_por_padrao_com_json_completo`, `test_wrap_sem_overflow_e_estilos`, `test_payload_hostil_exibido_como_dado`, `test_um_estado_solo_fallback` — asserts de presença de `ALTERACAO` na trilha) e confirmar que a guarda `TestUS3Preservacao` (4 testes) fica verde **sem qualquer edição** (FR-009/FR-010; Constitution VIII).
- [x] T013 Confirmar (na execução final T016) que apenas os asserts documentados em T012 mudaram nos testes 070; nada mais enfraquecido, removido ou pulado.
- [x] T014 Evidenciar a preservação (SC-003/FR-004/FR-008): diff vazio em `app/services/movement_service.py`, `app/api/*`, `audit_service.py`, models e migrações; snapshot antes/depois das linhas de `audit_logs` (dump direto) e payload da API de timeline idêntico; sem mudanças em `/admin/audit`, dashboard, relatórios/exportações/termos.
- [x] T021 [P] Gerar o smoke antes/depois (captura de HTML da trilha com edições cadastrais, antes e depois do filtro, em `specs/071-separar-cadastrais-fluxo/smoke/`) para evidenciar SC-007 — redução de rolagem com cartões duplicados eliminados.

## Fase 5: User Story 3 - Fallback para eventos não cadastrais atípicos (Priority: P2)

**Goal**: Eventos de auditoria não cadastrais continuam sendo renderizados com o comportamento da 070 (resumo quando há diff de estado, descrição caso contrário); `ALTERACAO` é exclusivo do painel.

**Teste independente**: injetar manualmente um registro de auditoria atípico não cadastral; ele aparece na trilha; nenhum `ALTERACAO` aparece lá.

- [x] T015 Adicionar teste de regressão em `test_separacao_cadastral_fluxo_071.py` provando o fallback US3: registro de auditoria não cadastral plantado renderiza com resumo/descrição da 070; TODOS os `ALTERACAO` ficam apenas no painel.

## Fase N: Polish & Preocupações transversais

**Propósito**: Documentação, rastreabilidade e handoff seguro.

- [x] T016 Executar a suíte completa uma última vez com o código 071 no lugar e registrar a contagem final com status de saída explícito (esperado: 1059 passed + os novos testes 071 verdes, 3 skipped, 3 failures identificadas como infraestrutura `alembic` — independente da 071).
- [x] T017 Atualizar `specs/071-separar-cadastrais-fluxo/spec.md` §14 para registrar o caminho de implementação executado: predicado escolhido na rota (`view_asset_detail`), template intocado, fronteiras de service preservadas, novo arquivo de teste presente, testes 070 ajustados apenas nos asserts diretamente afetados (lista de T012).
- [x] T018 Atualizar `specs/071-separar-cadastrais-fluxo/checklists/requirements.md` se necessário, marcando o deliverable como implementado e anotando a redação do ajuste de testes de FR-010.
- [x] T019 Registrar a nota de lição/design: a separação de eventos por ação deve permanecer na camada de apresentação (rota/controller), porque `MovementService.get_timeline_for_asset` e o contrato da API (C1/C2) intencionalmente mantêm os registros de auditoria (incl. ALTERACAO) para semântica de API/CLI.
- [x] T020 Verificação final: suíte com status explícito, `git diff`/`git status` mostrando apenas `app/web/routers/assets.py`, `app/services/asset_service.py` (helper opcional), `tests/test_separacao_cadastral_fluxo_071.py`, os asserts 070 ajustados de `tests/test_legibilidade_trilha_070.py` e os artefatos de spec/smoke; commit 071 com a mensagem apropriada.

## Dependências & Ordem de Execução

### Dependências de fase

- **Setup (Fase 1)**: sem dependências — inicia imediatamente.
- **Foundational (Fase 2)**: depende do Setup; BLOQUEIA todas as user stories.
- **User Stories (Fases 3–5)**: dependem do Foundational; US1 (MVP) → US2 → US3 na ordem de prioridade.
- **Polish (Fase N)**: depende das stories desejadas estarem completas.

### Dentro de cada story

- Testes escritos e em RED antes da implementação (gate T007).
- Predicado/helper antes da rota (T010 pode ser paralelo a T008 por arquivo).
- Verificação de preservação depois de cada mudança de código.

## Notas

- Tasks [P] = arquivos diferentes, sem dependência.
- Rótulo [US#] mapeia a task à story para rastreabilidade (spec §9 AC01–AC15).
- Cada story é independente e testável; parar em qualquer checkpoint para validar.
- Commits: um commit auditável da 071 (a 070 já está em `5b3f71f` — histórico preserva a ordem §6).
