# Tasks: Acessibilidade U3/U4 — Login e Inventário

**Feature**: `069-acessibilidade-login-inventario`
**Base**: `specs/069-acessibilidade-login-inventario/spec.md` e `specs/069-acessibilidade-login-inventario/plan.md`
**Origem do item**: `docs/ANALISE_SEG_PERF_UX_2026-10-10.md`, item 8 (U3/U4)
**Nota**: Esta lista é de planejamento e execução controlada. Ela não pressupõe instalação automática
de dependência nova e não expande o escopo para todos os templates sem análise adicional.

---

## Format

- `[ID] [P?] [Fase] Descrição`
- `[P]` = pode rodar em paralelo com outra tarefa, desde que não dependa dela
- Prioridade e escopo seguem o que foi definido na spec e no plano
- Nenhuma tarefa aqui deve alterar autenticação, permissões, validações ou comportamento funcional
  sem análise prévia e registro do impacto

---

## Fase 1 — Inventário e confirmação dos fluxos U3/U4 — ✅ concluída (evidência em `research.md`, 2026-10-12)

**Propósito**: reunir evidência real dos fluxos login e inventário antes de propor qualquer mudança.

- [x] **T001** [Fase 1] Mapear os templates envolvidos nos fluxos login e inventário mencionados na análise
  e registrar qual página/fluxo cada um pertence. → `research.md` R1/R2 (7 templates mapeados; U3/U4 confirmados com correções de contexto).
- [x] **T002** [Fase 1] Identificar os formulários existentes nesses fluxos e listar campos por tipo
  (input, select, botão só-ícone, etc.). → `research.md` R2 (tabela por arquivo).
- [x] **T003** [Fase 1] Verificar associação de `label[for]` campo a campo: quais têm label associado
  corretamente, quais têm label incorreto, quais usam apenas `placeholder` ou outro padrão como
  único rótulo. → `research.md` R2/R7: login/setup ✅ corretos; gaps reais nos fluxos de inventário.
- [x] **T004** [Fase 1] Identificar mensagens dinâmicas nos fluxos: erros, sucesso, validação e
  processamento; registrar onde aparecem e quando são atualizadas. → `research.md` R3.
- [x] **T005** [Fase 1] Registrar padrões já existentes de foco visível, ordem de tabulação e uso de
  `aria-*` nos fluxos login e inventário, sem presumir que tudo está errado. → `research.md` R1/R6/R8.

**Checkpoint da Fase 1**: ✅ inventário documentado com evidência de leitura dos templates/fluxos
principais. Nenhuma mudança de código nesta fase (Constitution: somente leitura).

---

## Fase 2 — Análise e decisões de acessibilidade — ✅ concluída (decisões em `research.md` R3/R7/R8 + `data-model.md` §2.4)

**Propósito**: transformar o inventário em decisões documentadas antes de qualquer implementação.

- [x] **T006** [Fase 2] Decidir campo a campo se o `label[for]` atual está correto, ausente ou incorreto,
  e registrar exceções justificadas. → `research.md` R7 (tabela campo a campo).
- [x] **T007** [Fase 2] Decidir mensagem a mensagem se merece `aria-live`, `role="alert"`,
  `aria-describedby`, ou nenhum destes, evitando anúncios duplicados. → `research.md` R3: `role="alert"` onde falta; **sem `aria-live`** hoje (nada é atualizado via JS).
- [x] **T008** [Fase 2] Decidir botão a botão só-ícone se precisa de `aria-label` ou outro rótulo
  alternativo quando o contexto exigir. → `research.md` R2/R7 (toggle de senha, bi-funnel, limpar filtros).
- [x] **T009** [Fase 2] Verificar se há questões de contraste/legibilidade relevantes identificadas
  nos fluxos selecionados e registrar apenas as que tiverem base concreta. → `research.md` R4: contraste fica condicionado a medição (varredura axe futura); nenhuma alteração preventiva de CSS.
- [x] **T010** [Fase 2] Confirmar o escopo inicial: login e inventário como alvos principais, deixando
  expansão para outros fluxos como decisão futura com base em análise nova. → `data-model.md` §4.

**Checkpoint da Fase 2**: ✅ as regras de `label[for]`, `aria-live`, `aria-label` e `aria-describedby`
são definidas com base no contexto real, não por regra genérica sem exceções.
**Pendências de decisão do responsável antes da Fase 5** (rev. 2 do `research.md`): **P1**
(`aria-label` vs label `visually-hidden` nos controles compactos — recomendação: `aria-label`),
**P2** (skip-link em `base.html` — recomendação: incluir; `<main>` já existe, risco baixo) e
**P3** (indicador de foco dos `.result-option` — recomendação: incluir; única lacuna concreta de
foco). Ver `checklists/requirements.md` Notes.

> **✅ APROVADAS em 2026-10-12**: P1 (`aria-label`), P2 (incluir skip-link) e P3 (incluir
> indicador de foco) — Fase 5 liberada; T024a e T024b entram no escopo.

---

## Fase 3 — Planejamento de verificação automatizada — ✅ concluída (`research.md` R5/R9 + `contracts/acessibilidade-login-inventario-contract.md` §3)

**Propósito**: encaixar a verificação automatizada na infraestrutura existente sem introduzir
dependências automaticamente.

- [x] **T011** [Fase 3] Verificar se já existe infraestrutura de teste de interface no projeto e,
  caso exista, como ela pode ser reutilizada para varredura de acessibilidade.
  → `research.md` R5: não existe teste com navegador (pytest + TestClient, sem JS). Precedentes 013/035 rejeitaram player de browser.
- [x] **T012** [Fase 3] Definir como o axe-core seria usado: qual ferramenta, quais fluxos e estados,
  quais páginas/states são testáveis de forma automatizada.
  → `research.md` R5: nesta feature, verificação **estática** com parser `html.parser` (stdlib, zero dependência nova); axe com browser = evolução futura no backlog (`docs/Melhorias_SisPatrimonio_Pro.md`).
- [x] **T013** [Fase 3] Definir critérios de aceitação automatizados: ausência de violações críticas
  e graves detectáveis nos fluxos efetivamente testados, com exceções documentadas quando necessário.
  → `contract.md` §3 (0 controles sem nome acessível, 0 ids duplicados, `fieldset` nos rádios, `role=alert` nos erros; subconjunto declarado, ver `research.md` R5).
- [x] **T014** [Fase 3] Documentar o que a automação comprova e o que ela não comprova, deixando
  claro que navegação por teclado, foco visível e usabilidade real precisam de verificação complementar.
  → `research.md` R6/R9 + `quickstart.md` §4–§5 (já previa).

**Checkpoint da Fase 3**: ✅ o plano de uso do axe-core está definido sem supor instalação automática
de dependência nova.

---

## Fase 4 — Critérios de preservação e regressão — ✅ concluída (`data-model.md` §3 invariantes + `contract.md` §2 RN-8/§5)

**Propósito**: garantir que a evolução de acessibilidade não altere comportamento funcional.

- [x] **T015** [Fase 4] Registrar o que deve permanecer intacto: autenticação, sessão, validações,
  permissões e comportamento funcional dos formulários envolvidos. → invariante I3/I4.
- [x] **T016** [Fase 4] Definir verificações de regressão para cada mudança de acessibilidade:
  comportamento funcional, não apenas visual. → `research.md` R9 (lista de suítes de regressão).
- [x] **T017** [Fase 4] Estabelecer regra de mudança incremental: cada alteração deve ser limitada,
  documentada e verificada contra impacto nos fluxos login e inventário. → invariante I5/I6; Fase 5 estruturada por entrega pequena.

**Checkpoint da Fase 4**: ✅ qualquer mudança posterior tem critérios claros de preservação e
regressão antes de ser executada.

---

## Fase 5 — Implementação (liberada apenas com P1/P2 resolvidas e aprovação do responsável)

**Propósito**: aplicar o contrato (`contracts/acessibilidade-login-inventario-contract.md`) com TDD
estático, em entregas pequenas e independentes de comportamento.

- [x] **T018** [Fase 5] Criar `tests/test_acessibilidade_estatica_069.py` (parser `html.parser`, stdlib)
  com as verificações do `contract.md` §3, escrito **primeiro contra os templates atuais** (RED —
  contabiliza os controles sem nome acessível de hoje). *depends: —* [P]
- [x] **T019** [Fase 5] `inventarios/new.html`: `for`/`id` nos 4 campos (labels visíveis já existentes).
  *depends: T018* — GREEN parcial.
- [x] **T020** [Fase 5] "Local onde foi encontrado" e "Observação": `for`/`id` em `conferir.html`,
  `detail.html` (com sufixo `{{ item.id }}` nos ids do modal) e `offline.html`. *depends: T018* [P].
- [x] **T021** [Fase 5] `fieldset`/`legend` no grupo "Resultado da conferência" nos 3 templates
  (reset visual inline, zero mudança de layout). *depends: T018* [P].
- [x] **T022** [Fase 5] `aria-label` nos controles compactos: busca/status de `list.html`, filtro de
  itens e campo de tombamento de `detail.html`, botão `bi-funnel`, link limpar-filtros.
  *depends: T018 + P1 aprovada* [P].
- [x] **T023** [Fase 5] `togglePassword`/`toggleConfirmPassword`: `aria-label` que alterna
  Mostrar/Ocultar senha + `aria-pressed` sincronizado com o ícone. *depends: T018* [P].
- [x] **T024** [Fase 5] `role="alert"` no alerta de erro de `conferir.html` (único dos fluxos-alvo
  sem o atributo — `research.md` R3 rev. 2). *depends: T018* [P].
- [x] **T024a** [Fase 5] *(só com P2 aprovada)* Skip-link no `base.html`: 1 `<a>` invisível que
  foca o topo do `<main>` existente (nenhum template filho tocado). *depends: P2*.
- [x] **T024b** [Fase 5] *(só com P3 aprovada)* Indicador de foco dos `.result-option` em
  `style.css` (~3 linhas; nenhuma mudança de layout — o outline só aparece no foco).
  *depends: P3* [P].
- [x] **T025** [Fase 5] Suíte estática 100 % GREEN + régua de regressão: `test_inventario.py`,
  `test_inventario_offline.py`, `test_rbac.py`, `test_route_inventory.py` (manifesto intacto),
  `test_help.py` e suíte completa. *depends: T019–T024 (e T024a/T024b quando aprovadas)*.
- [x] **T026** [Fase 5] Documentação: `docs/ARQUITETURA_E_MANUTENCAO.md` (seção de acessibilidade,
  padrão 068 §12.8) + artigo da central de ajuda (`app/services/help_service.py`). *depends: T025*.
- [x] **T027** [Fase 5] Fechamento: verificar por `git diff` os guardas I2/I4/I5 (`route_manifest.json`,
  `requirements.txt`, `migrations/`, `app/models/`, nenhum teste existente editado); registro final em
  `validacao.md` (padrão 067/068), **sem commit** (apenas sob pedido explícito). *depends: T026*.

**Checkpoint da Fase 5**: ✅ contrato atendido com 0 dependência nova, 0 rota nova, 0 teste existente
editado; limite do que a automação comprova declarado (`research.md` R5); contraste e leitor de
tela permanecem verificação manual (quickstart §4). Escopo de diff: templates dos
fluxos-alvo; `base.html` (P2); `style.css` (P3). Evidência completa em `validacao.md`.

---

## Critérios de término

A lista está pronta para execução quando:
- o inventário dos fluxos login e inventário estiver registrado; ✅ (`research.md`)
- as decisões para `label[for]`, `aria-live`, `aria-label` e `aria-describedby` estiverem documentadas
  com base no contexto real; ✅ (`research.md` R3/R7 + `data-model.md` §2.4)
- o plano de uso do axe-core e os critérios automatizados estiverem definidos; ✅ (`research.md` R5 + contrato §3)
- as regras de preservação e regressão estiverem explícitas. ✅ (`data-model.md` §3)

**Estado atual**: ✅ **todas as fases concluídas** (Fases 1–4 na etapa de planejamento; Fase
5 implementada e verificada em 2026-10-12 com P1/P2/P3 aprovadas). Evidência: `validacao.md`
(1051 passed / 3 skipped, guardas por git diff OK, sem commit).

---

## Próximo passo

Feature implementada e validada (`validacao.md`). Pendências restantes: verificação manual
com leitor de tela/360 px (quickstart §4) e commit, apenas sob pedido explícito.
