# Feature Specification: Acessibilidade U3/U4 — Login e Inventário

**Feature Branch**: `069-acessibilidade-login-inventario`

**Created**: 2026-10-11

**Status**: **Implementação concluída** — planejamento (Fases 1–4) com evidência real em
`research.md` (rev. 2), modelo em `data-model.md`, checklist em `checklists/requirements.md`
e contrato em `contracts/acessibilidade-login-inventario-contract.md`; decisões **P1/P2/P3
aprovadas** (2026-10-12) e **Fase 5 implementada e verificada** (T018–T027, evidência em
`validacao.md`: suíte estática 17 passed, suíte completa 1051 passed / 3 skipped, guardas
de escopo por git diff OK).

**Input**: User description: criar a spec para implementar o item de acessibilidade da análise
de 2026-10-10: “8. Acessibilidade: `label[for]`, `aria-live`, axe no fluxo de login e inventário
(U3/U4)”, com os ajustes de escopo e refinamento obrigatório do prompt complementar.

**Prerequisites**: `docs/ANALISE_SEG_PERF_UX_2026-10-10.md` (origem do item); uso do Spec Kit
para planejamento e geração de tasks; nenhuma implementação nesta etapa.

**Organization**: spec de acessibilidade de interface, focada em dois fluxos e em regras de
documentação, critérios automatizáveis e inventário dos problemas reais.

---

## 1. Contexto e origem

### 1.1 O que motivou

A análise técnica de 2026-10-10 (`docs/ANALISE_SEG_PERF_UX_2026-10-10.md`) apontou um
achado de acessibilidade resumido como:

- **U3 — Acessibilidade fraca**: presença limitada de `aria-*` nos templates;
  ausência nos templates `dashboard.html`, `login.html`, `403.html`, `404.html`;
  recomendação de rodar axe/Lighthouse, associar `label[for]` nos inputs e usar
  `aria-live` em mensagens de erro, `aria-label` em botões só-ícone, e revisar contraste.

- **U4**: foco/teclado no campo de trabalho.

O item 8 da análise resume isso como:

> 8. Acessibilidade: `label[for]`, `aria-live`, axe no fluxo de login e inventário (U3/U4).

### 1.2 O que esta spec vai fazer

Esta spec **não é** uma proposta de refatoração geral do sistema. Ela define:

1. Qual é o escopo inicial: fluxos de login e inventário como alvos principais.
2. Quais dados reais a serem coletados antes de transformar o item em requisitos.
3. Como as melhorias serão especificadas, priorizadas e testadas.
4. O que deve ser preservado: comportamento visual, autenticação, permissões, validações
   e funcionalidades existentes.

### 1.3 O que não está resolvido ainda

- Os identificadores **U3** e **U4** precisam ser confirmados no contexto do projeto antes de
  serem tratados como requisitos rígidos.
- A analise apontou “159 inputs” e “29 ocorrências de `aria-*` em 53 templates”, mas essa
  spec não assume que os números são definitivos nem que o problema todo esteja apenas nesses
  dois fluxos.

---

## 2. Escopo inicial

### 2.1 Inclui

- **Login**: formulário de login e de primeira acesso, pois é o acesso principal ao sistema e
  pelas menções da análise.
- **Inventário**: fluxos de inventário mencionados na análise, inclusive o aspecto de foco/teclado
  no campo de trabalho, quando aplicável aos templates envolvidos.
- **Regras de acessibilidade documentadas**: associação de labels a inputs, uso controlado de
  `aria-live`/`role="alert"`/`aria-describedby`, `aria-label` em botões só-ícone quando
  semanticamente apropriado, e verificação de contraste e foco.
- **Integração com a infraestrutura de testes existente**: planejar a inclusão de verificação
  automatizada com axe-core no ecossistema de testes atual, sem introduzir dependências
  automaticamente.
- **Análise antes de implementação**: inspecionar formulários, mensagens dinâmicas e fluxos
  antes de definir quais ajustes são realmente necessários.

### 2.2 Não inclui nesta spec

- Refatoração visual ou de layout.
- Mudanças de permissões, autenticação, fluxos de negócio ou comportamento funcional.
- Expansão automática para todos os 53 templates ou para os 159 inputs sem análise.
- Instalação automática de dependências novas.
- Implementação da melhoria. Esta spec documenta a necessidade, escopo, dados e critérios;
  a execução é tarefa separada.

---

## 3. Problema e motivação

### 3.1 Problema

Pequenos problemas de acessibilidade podem dificultar o uso do sistema por pessoas que
dependem de leitores de tela, navegação por teclado ou que dependem de feedback claro em
mensagens dinâmicas. Para um sistema de gestão patrimonial usado por vários perfis, isso é
um risco de usabilidade e de conformidade, mesmo que não seja uma falha funcional.

### 3.2 Por que focar em login e inventário primeiro

- Login é a entrada do sistema e é sensível: se o formulário for difícil de operar por teclado
  ou por leitor de tela, o acesso ao sistema é prejudicado desde o início.
- Inventário é um fluxo de trabalho onde o foco e o teclado são importantes (leitura de campo,
  confirmação, erro, navegação entre itens), e a análise mencionou explicitamente esse tipo de
  concern.

---

## 4. Refinamento obrigatório — Acessibilidade U3/U4

Antes de definir requisitos, a execução deve inspecionar testes e especificações existentes para
identificar exatamente os fluxos U3 e U4. Não presumir sua finalidade.

### 4.1 Análise de formulários

1. Avaliar os formulários e identificar campos sem rótulos acessíveis ou com associações
   incorretas. Priorizar `label[for]` e IDs únicos, respeitando os componentes existentes.
2. Não criar labels desnecessários, nem alterar estrutura já correta.

### 4.2 Mensagens dinâmicas

3. Identificar mensagens dinâmicas de erro, sucesso, validação e processamento.
   Especificar `aria-live`, `role="alert"` e `aria-describedby` somente quando forem
   semanticamente apropriados, evitando anúncios duplicados.

### 4.3 Infraestrutura de testes

4. Verificar se já existe infraestrutura de testes de interface. Planejar a integração do
   axe-core com a ferramenta atual, sem introduzir dependências desnecessárias.

### 4.4 Critérios automatizáveis

5. Definir critérios de aceitação para ausência de violações críticas e graves detectáveis
   pelo axe-core nos fluxos e estados efetivamente testados. Documentar eventuais exceções
   justificadas.

### 4.5 Complementos manuais

6. Incluir verificações complementares de navegação por teclado, foco visível e identificação
   dos campos, reconhecendo que testes automatizados não comprovam acessibilidade completa.

### 4.6 Escopo e expansão futura

7. Priorizar os fluxos U3/U4 e identificar oportunidades de expansão futura sem ampliar
   indevidamente o escopo inicial.

### 4.7 Preservação

8. Preservar o comportamento visual, as regras de autenticação, as permissões e as
   funcionalidades existentes.

---

## 5. Entradas e dados iniciais

Esta spec não assume números ou listas prontas. A execução deve reunir:

- Templates envolvidos nos dois fluxos e seus formulários reais.
- Campos sem `label` associado, com `label` incorreto, placeholders usados como único rótulo,
  ou botões só-ícone sem descrição textual alternativa.
- Mensagens dinâmicas existentes: onde aparecem, quando são atualizadas e se já possuem
  mecanismo de anúncio acessível.
- Eventuais padrões de foco/teclado já presentes e onde estão faltando.

---

## 5.1 Entradas e dados iniciais

Esta spec não assume números ou listas prontas. A execução deve reunir:

- Templates envolvidos nos dois fluxos e seus formulários reais.
- Campos sem `label` associado, com `label` incorreto, placeholders usados como único rótulo,
  ou botões só-ícone sem descrição textual alternativa.
- Mensagens dinâmicas existentes: onde aparecem, quando são atualizadas e se já possuem
  mecanismo de anúncio acessível.
- Eventuais padrões de foco/teclado já presentes e onde estão faltando.

---

## 6. Usuários envolvidos

| Usuário | Por que importa |
|---|---|
| Usuário com leitor de tela | Precisa que labels e mensagens sejam anunciadas corretamente |
| Usuário que navega por teclado | Precisa de foco visível, ordem lógica e confirmação sem mouse |
| Usuário com necessidades de contraste/legibilidade | Precisa que estados e mensagens sejam distinguíveis |
| Qualquer usuário autenticado | Acessibilidade também é usabilidade geral |

---

## 7. Funcionalidades a preservar

Implementações futuras devem preservar, no mínimo:

- Autenticação e sessão conforme o sistema existente.
- Regras de permissão e negação por padrão.
- Validações existentes de login, formulários e fluxos de inventário.
- Comportamento visual e de layout já aprovado, exceto onde a mudança for estritamente de
  acessibilidade e documentada.

---

## 8. Requisitos

### 8.1 Requisitos de análise

| ID | Descrição |
|---|---|
| AR-01 | Antes de propostas de mudança, inspecionar os templates e formulários dos fluxos login e inventário, registrando os campos com associação de label ausente ou incorreta |
| AR-02 | Antes de proposições de `aria-live`, identificar quais mensagens são dinâmicas e relevantes para anúncio, evitando anúncios duplicados |
| AR-03 | Verificar se existe infraestrutura de teste de interface e como o axe-core se encaixa nela, sem introduzir dependências automaticamente |

### 8.2 Requisitos de acessibilidade documentados

| ID | Descrição |
|---|---|
| FR-A1 | Campos de formulário que merecem rótulo devem ter associação acessível clicável/touchável e compatível com leitores de tela |
| FR-A2 | Mensagens dinâmicas relevantes devem ser perceptíveis para leitores de tela quando apropriado, usando os mecanismos mais adequados ao contexto, sem duplicidade desnecessária |
| FR-A3 | Botões só-ícone devem ter descrição textual alternativa quando essa descrição for semanticamente necessária |
| FR-A4 | Foco visível e navegação por teclado devem ser preservados e, quando necessário, melhorados nos fluxos selecionados |
| FR-A5 | Contraste e legibilidade dos estados relevantes devem ser considerados nos ajustes definidos pela análise |

### 8.3 Requisitos de execução e Integração

| ID | Descrição |
|---|---|
| OR-1 | As melhorias devem ser planejadas de forma incremental, limitadas ao necessary e documentadas |
| OR-2 | A integração do axe-core deve ser planejada em conjunto com a infraestrutura existente, sem introduzir dependências sem avaliação prévia |
| OR-3 | As mudanças devem preservar comportamento visual, autenticação, permissões e funcionalidades existentes |

---

## 9. Critérios de sucesso

### 9.1 Critérios de sucesso (medibles, quando possível)

| Código | Descrição |
|---|---|
| SC-A1 | Registro de campos identificados nos fluxos login e inventário, com classificação do que está correto, do que está ausente e do que está incorreto |
| SC-A2 | Lista de mensagens dinâmicas identificadas e gravação da decisão sobre `aria-live`/`role="alert"`/`aria-describedby` para cada uma delas |
| SC-A3 | Critérios automatizados definidos com base no que é possível validar no ecossistema atual, com exceções documentadas quando necessário |
| SC-A4 | Escopo inicial limitado e justificado, sem expansão automática para todo o sistema |

### 9.2 Critérios de preservação

| Código | Descrição |
|---|---|
| SC-P1 | Nenhuma mudança de escopo pode quebrar autenticação, permissões, validações ou comportamento funcional existente |
| SC-P2 | Mudanças visuais, quando houver, devem ser consequência de necessidade de acessibilidade e documentadas |

---

## 10. Critérios de aceitação

| ID | Condição de aceitação |
|---|---|
| AC-A1 | A spec registra fluxos, campos e mensagens inspecionados antes de qualquer proposta de implementação |
| AC-A2 | As regras de `label[for]`, `aria-live`, `aria-label` e `aria-describedby` são definidas com base no contexto real, não por regra genérica sem exceções |
| AC-A3 | O plano inclui como o axe-core será usado, em quais fluxos e com quais limites, sem supor instalação automática de dependência nova |
| AC-A4 | O plano considera navegação por teclado e foco visível, especialmente no fluxo de inventário, mas reconhece os limites da validação automatizada |
| AC-A5 | Autenticação, permissões, validações e comportamento funcional permanecem preservados conforme documento |

---

## 11. Riscos e medidas de mitigação

| Risco | Impacto | Mitigação |
|---|---|---|
| Expandir escopo para todos os templates sem necessidade | Médio | Manter login e inventário como foco inicial; expansão futura por análise |
| Adicionar dependência nova por impulso | Médio | Planejar integração com a infraestrutura atual antes de qualquer decisão técnica |
| Aplicar `aria-live` indiscriminadamente | Baixo/Médio | Definir uso por mensagem real e evitar anúncios duplicados |
| Quebrar comportamento existente enquanto “melhora” acessibilidade | Alto | Manter preservação explícita de autenticação, validações e fluxo; testar impacto antes de mudar |

---

## 12. Notas de planejamento

- Esta é uma **spec de acessibilidade**, não uma spec de funcionalidade nova.
- O objetivo é que qualquer tarefa futura seja feita com base em análise real, não em suposições.
- A análise de 2026-10-10 é o ponto de partida, mas não a verdade final sobre os fluxos U3/U4
  sem confirmação no projeto.
- A execução futura deve incluir evidência de teste e/ou validação adequada, especialmente para
  o que a automação não cobre.

---

## 13. Próximo passo

O planejamento está concluído — ver artefatos:

| Artefato | Conteúdo |
|---|---|
| `research.md` | R1–R9: confirmação de U3/U4, inventário dos 7 templates, decisões campo a campo, delimitação do axe (estático, sem dependência nova) |
| `data-model.md` | "modelo" de atributos de acessibilidade + invariantes I1–I7 e o que não entra |
| `contracts/acessibilidade-login-inventario-contract.md` | regras RN-1–RN-8 e matriz de validação da suíte estática |
| `checklists/requirements.md` | qualidade da spec + decisões pendentes P1/P2 |
| `tasks.md` | Fases 1–4 ✅; Fase 5 (T018–T027) ✅ — implementação concluída e verificada |
