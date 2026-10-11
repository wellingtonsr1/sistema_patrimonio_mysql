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

## Fase 1 — Inventário e confirmação dos fluxos U3/U4

**Propósito**: reunir evidência real dos fluxos login e inventário antes de propor qualquer mudança.

- [ ] **T001** [Fase 1] Mapear os templates envolvidos nos fluxos login e inventário mencionados na análise
  e registrar qual página/fluxo cada um pertence.
- [ ] **T002** [Fase 1] Identificar os formulários existentes nesses fluxos e listar campos por tipo
  (input, select, botão só-ícone, etc.).
- [ ] **T003** [Fase 1] Verificar associação de `label[for]` campo a campo: quais têm label associado
  corretamente, quais têm label incorreto, quais usam apenas `placeholder` ou outro padrão como
  único rótulo.
- [ ] **T004** [Fase 1] Identificar mensagens dinâmicas nos fluxos: erros, sucesso, validação e
  processamento; registrar onde aparecem e quando são atualizadas.
- [ ] **T005** [Fase 1] Registrar padrões já existentes de foco visível, ordem de tabulação e uso de
  `aria-*` nos fluxos login e inventário, sem presumir que tudo está errado.

**Checkpoint da Fase 1**: inventário documentado com evidência de leitura dos templates/fluxos
principais. Nenhuma mudança de código nesta fase.

---

## Fase 2 — Análise e decisões de acessibilidade

**Propósito**: transformar o inventário em decisões documentadas antes de qualquer implementação.

- [ ] **T006** [Fase 2] Decidir campo a campo se o `label[for]` atual está correto, ausente ou incorreto,
  e registrar exceções justificadas.
- [ ] **T007** [Fase 2] Decidir mensagem a mensagem se merece `aria-live`, `role="alert"`,
  `aria-describedby`, ou nenhum destes, evitando anúncios duplicados.
- [ ] **T008** [Fase 2] Decidir botão a botão só-ícone se precisa de `aria-label` ou outro rótulo
  alternativo quando o contexto exigir.
- [ ] **T009** [Fase 2] Verificar se há questões de contraste/legibilidade relevantes identificadas
  nos fluxos selecionados e registrar apenas as que tiverem base concreta.
- [ ] **T010** [Fase 2] Confirmar o escopo inicial: login e inventário como alvos principais, deixando
  expansão para outros fluxos como decisão futura com base em análise nova.

**Checkpoint da Fase 2**: as regras de `label[for]`, `aria-live`, `aria-label` e `aria-describedby`
são definidas com base no contexto real, não por regra genérica sem exceções.

---

## Fase 3 — Planejamento de verificação automatizada

**Propósito**: encaixar a verificação automatizada na infraestrutura existente sem introduzir
dependências automaticamente.

- [ ] **T011** [Fase 3] Verificar se já existe infraestrutura de teste de interface no projeto e,
  caso exista, como ela pode ser reutilizada para varredura de acessibilidade.
- [ ] **T012** [Fase 3] Definir como o axe-core seria usado: qual ferramenta, quais fluxos e estados,
  quais páginas/states são testáveis de forma automatizada.
- [ ] **T013** [Fase 3] Definir critérios de aceitação automatizados: ausência de violações críticas
  e graves detectáveis nos fluxos efetivamente testados, com exceções documentadas quando necessário.
- [ ] **T014** [Fase 3] Documentar o que a automação comprova e o que ela não comprova, deixando
  claro que navegação por teclado, foco visível e usabilidade real precisam de verificação complementar.

**Checkpoint da Fase 3**: o plano de uso do axe-core está definido sem supor instalação automática
de dependência nova.

---

## Fase 4 — Critérios de preservação e regressão

**Propósito**: garantir que a evolução de acessibilidade não altere comportamento funcional.

- [ ] **T015** [Fase 4] Registrar o que deve permanecer intacto: autenticação, sessão, validações,
  permissões e comportamento funcional dos formulários envolvidos.
- [ ] **T016** [Fase 4] Definir verificações de regressão para cada mudança de acessibilidade:
  comportamento funcional, não apenas visual.
- [ ] **T017** [Fase 4] Estabelecer regra de mudança incremental: cada alteração deve ser limitada,
 	documentada e verificada contra impacto nos fluxos login e inventário.

**Checkpoint da Fase 4**: qualquer mudança posterior tem critérios claros de preservação e
regressão antes de ser executada.

---

## Critérios de término

A lista está pronta para execução quando:
- o inventário dos fluxos login e inventário estiver registrado;
- as decisões para `label[for]`, `aria-live`, `aria-label` e `aria-describedby` estiverem documentadas
  com base no contexto real;
- o plano de uso do axe-core e os critérios automatizados estiverem definidos;
- as regras de preservação e regressão estiverem explícitas.

---

## Próximo passo

Executar as tarefas das Fases 1 e 2 antes de tomar qualquer decisão de implementação.
