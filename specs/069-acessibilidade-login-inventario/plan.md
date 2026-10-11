# Plan: Acessibilidade U3/U4 — Login e Inventário

**Feature**: `069-acessibilidade-login-inventario`
**Estrita para a spec**: `specs/069-acessibilidade-login-inventario/spec.md`
**Status do Spec**: Draft — baseado em `docs/ANALISE_SEG_PERF_UX_2026-10-10.md` (item 8, U3/U4)

---

## 1. Método

Este plano é gerado a partir da spec, sem inventar implementação. Ele:
1. reúne o que deve ser verificado antes de propor mudanças;
2. divide o trabalho em análise/documentação e melhorias;
3. define critérios automatizáveis e os limites deles;
4. preserva autenticação, permissões, validações e comportamento existente.

**Regra de escopo**: login e inventário são o foco inicial. Qualquer expansão para outros
templates ou para toda a aplicação deve ser resulto de análise específica, não de regra genérica.

---

## 2. Pré-requisitos

- Ler e entender `specs/069-acessibilidade-login-inventario/spec.md`.
- Conhecer os fluxos reais de login e inventário no projeto, inclusive templates, formulários
  e mensagens dinâmicas.
- Saber como a suíte de testes atual funciona para não introduzir intervenções desnecessárias.
- Decisão futura sobre dependências: não instalar nada nova por padrão; se algo novo for
  necessário, documentar retorno e justificativa.

---

## 3. Organização do trabalho

### Fase 1 — Inventário e confirmação dos fluxos U3/U4

**Propósito**: confirmar o que U3 e U4 significam no projeto antes de qualquer proposta.

Entregas:
- Lista dos templates e formulários envolvidos nos fluxos login e inventário.
- Campo a campo: quais inputs têm `label` associado, quais têm `label` incorreto, quais usam
  apenas `placeholder` como rótulo, quais são campos de texto, selects, botões só-ícone, etc.
- Mensagens dinâmicas identificadas: erro, sucesso, validação, processamento; onde aparecem e como
  são atualizadas.
- Padrões já existentes de foco visível, tabindex, order e `aria-*` no contexto desses fluxos.

### Fase 2 — Análise e decisões de acessibilidade

**Propósito**: transformar o inventário em decisões documentadas.

Entregas:
- Decisão por campo: se precisa de `label[for]`, se o atual está correto ou incorreto, se há
  exceções justificadas.
- Decisão por mensagem dinâmica: se merece `aria-live`, `role="alert"`, `aria-describedby`,
  ou nenhum destes, evitando anúncios duplicados.
- Decisão por botão só-ícone: se precisa de `aria-label` ou outro rótulo alternativo.
- Decisão sobre contraste/legibilidade relevante apenas onde houver problema identificado.

### Fase 3 — Planejamento de verificação automatizada

**Propósito**: encaixar o axe-core na infraestrutura existente sem pressupor instalação nova.

Entregas:
- Como o axe será executado: em qual ferramenta, em quais fluxos e estados, quais páginas/states
  são testáveis de forma automatizada.
- O que ele pode comprovar e o que não comprova.
- Critérios de aceitação: ausência de violações críticas/graves detectáveis nos fluxos
  efetivamente testados, com exceções documentadas quando necessário.

### Fase 4 — Critérios de preservação e regressão

**Propósito**: garantir que nada dos fluxos e regras essenciais seja alterado sem necessidade.

Entregas:
- Lista de coisas que devem permanecer intactas: autenticação, sessão, validações, permissões,
  comportamento dos formulários e mensagens funcionais.
- Critérios de regressão: qualquer mudança de acessibilidade deve ser verificada contra o
  comportamento funcional, não apenas contra o visual.
- Regra de mudança incremental: cada alteração deve ser portuação limitada e documentada.

---

## 4. Operações futuras não inclusas aqui

Estoas ações não são obrigatórias nesta etapa:

- Implementar mudanças nos templates/JS/CSS.
- Introduzir dependências novas sem análise.
- Expandir a cobertura para todos os templates do sistema sem análise nova.
- Declarar conformidade total com base apenas em teste automatizado.

---

## 5. Critérios de término do plano

O plano está pronto quando:

- os fluxos login e inventário estiverem identificados com evidência de leitura;
- o que é correto, o que está ausente e o que está incorreto tiver sido registrado;
- as regras para `label[for]`, `aria-live`, `aria-label` e `aria-describedby` tiverem sido
  definidas com base no contexto real, não em regra genérica sem exceções;
- o plano de uso do axe-core estiver definido sem supor instalação automática;
- os critérios de regressão e preservação estiverem explícitos.

---

## 6. Próximo passo

Gerar as tasks específicas a partir deste plano e da spec. Se desejar, a próxima etapa é
executar a Fase 1 e F2 antes de qualquer decisão de implementação.
