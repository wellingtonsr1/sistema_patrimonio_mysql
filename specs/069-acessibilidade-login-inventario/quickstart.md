# Quickstart: Acessibilidade U3/U4 — Login e Inventário

**Feature**: `069-acessibilidade-login-inventario`
**Data**: 2026-10-11
**Origem**: `docs/ANALISE_SEG_PERF_UX_2026-10-10.md`, item 8 (U3/U4)

Este quickstart não assume que a feature já está implementada. Ele orienta a **coleta de evidência,
verificação manual e planejamento** antes de qualquer mudança. Esta etapa é sobre entender o que
existe e o que deve ser melhorado, não sobre aplicar mudanças genéricas.

---

## 1. Pré-requisitos

- Ambiente do projeto ativo e aplicação executável localmente (para acesso a `/login` e `/inventarios`
  quando necessário).
- Permissão para inspecionar templates, formulários e mensagens do fluxo de login e de inventário.
- Consciência de que algumas verificações de acessibilidade exigem ferramenta/leitor de tela/
  navegação por teclado, e que isso pode estar fora do escopo local de execução.
- Não presumir que todos os 53 templates ou os 159 inputs são o escopo inicial.

---

## 2. O que este quickstart não faz

- Não instala dependências novas automaticamente.
- Não transforma a melhoria de acessibilidade em refatoração geral do sistema.
- Não altera código, templates, JS, CSS, testes ou comportamento funcional nesta etapa.
- Não expande o escopo para toda a aplicação sem análise específica.

---

## 3. O que coletar primeiro

### 3.1 Fluxos e templates envolvidos

- Identifique os templates reais dos fluxos **login** e **inventário** que são o objeto desta feature.
- Registre quais páginas/templates cada um corresponde, e quais formulários aparecem em cada um.

### 3.2 Formulários e campos

- Para cada formulário relevante, liste os campos e anote para cada um:
  - tem `label` associado por `for`/`id`?
  - o `label` está correto e único?
  - há uso de apenas `placeholder` como rótulo?
  - é botão só-ícone?
  - caso seja campo de texto, select, checkbox, radio, botão, etc., o mecanismo atual já é
    semanticamente adequado?

### 3.3 Mensagens dinâmicas

- Identifique onde aparecem mensagens de erro, sucesso, validação e processamento nos dois fluxos.
- Anote:
  - quando essa mensagem aparece;
  - se ela é atualizada dinamicamente;
  - se o usuário seria dependeremte de anúncio acessível para percebê-la.

---

## 4. Verificações manuais recomendadas

Estas são sugestões de observação, não checklist de implementação pronta.

### 4.1 Login

- Abrir `/login` e inspecionar o formulário de login:
  - cada campo tem rótulo associado?
  - botões só-ícone têm descrição alternativa?
  - mensagens de erro são visíveis e claras?
- Navegar pelo formulário usando apenas teclado, quando possível:
  - ordem de tabulação é lógica?
  - foco visível aparece onde esperado?

### 4.2 Inventário

- Abrir a seção relevante de inventário e observar:
  - campos de busca/filtro têm rótulo associado?
  - botões só-ícone ou ícones sem texto alternativo são claros?
  - mensagens dinâmicas de erro/validação são anunciadas ou percebíveis?
- Se o fluxo envolve campo de trabalho/leitura, observar:
  - foco visível;
  - comportamento de confirmação/Enter quando aplicável;
  - se há feedback adequado para o usuário.

---

## 5. Validação complementar

- Se houver infraestrutura de teste de interface no projeto, considerar como ela poderia ser
  reutilizada para varredura de acessibilidade nos fluxos selecionados.
- Planejar o uso do axe-core, se for adotado, de forma integrada ao que já existe, sem instalar
  dependências automaticamente.
- Documentar o que a automação pode comprovar e o que ela não comprova, especialmente:
  - navegação por teclado;
  - foco visível;
  - equivalência semântica percebida;
  - experiência real com leitor de tela.

---

## 6. Critérios de pronto para esta etapa

- inventário dos templates/fluxos login e inventário registrado;
- campos e mensagens dinâmicas mapeados com o que está correto, ausente ou incorreto;
- decisões preliminares para `label[for]`, `aria-live`, `aria-label` e `aria-describedby` registradas
  com base no que foi observado, não por regra genérica sem exceções;
- plano de uso do axe-core definido, se for adotado, sem pressupor instalação nova;
- regras de preservação e regressão deixadas explícitas.

---

## 7. Escopo de arquivos para esta etapa

Se a execução avançar, espera-se que qualquer registro ou decisão seja mantido nos artefatos da
feature (`specs/069-acessibilidade-login-inventario/`). Nesta etapa, **não deve haver alteração de
código funcional, templates, JavaScript, CSS, testes ou dependências**.

---

## Notas finais

- Esta feature começou como item de análise e pode evoluir para tarefas de implementação apenas
  quando houver evidência coletada e decisões documentadas.
- Se houver necessidade de expansão para outros fluxos, ela deve ser resultado de análise, não de
  regra automática.

---

## 8. Resultado da coleta de evidência (2026-10-12) — conclusão do planejamento

A coleta orientada nas §3.1–§3.5 foi executada (somente leitura) e registrada em `research.md`:

- **U3/U4 confirmados com correções**: login e setup **já têm** `label[for]` correto (2/2 e 5/5) e
  `autofocus` no username; o U4 já está parcialmente atendido (tombamento em
detail também tem `autofocus`). Os gaps reais estão nos fluxos de
  inventário: labels soltos sem `for` (`new.html`, "Local/Observação" em conferir/detail/offline),
  controles de busca/filtro sem nome acessível, botões só-ícone sem `aria-label` (toggle de senha,
  `bi-funnel`), rádios de resultado sem `fieldset`/`legend`. Os números "29 aria-*" de
  `dashboard.html`/`login.html` com 0 ocorrências eram históricos/outdated — hoje são 33 ocorrências
  e `role="alert"` já presente no login.
- **Mensagens dinâmicas**: nenhuma é atualizada via JS nos fluxos-alvo — `aria-live` **não** entra;
  `role="alert"` é completado onde falta (contrato RN-6).
- **axe-core**: a suíte não tem player de browser (precedentes 013/035); critério automatizado é
  **estático** (`test_acessibilidade_estatica_069.py`, `html.parser` da stdlib, zero dependência
  nova) — matriz no `contract` §3; axe com browser fica no backlog.
- **Verificações manuais §4 continuam valendo** para leitor de tela, foco visível e contraste
  (não são provadas por automação — `research.md` R6/R9).
- **Implementação**: ✅ concluída — Fase 5 do `tasks.md` (T018–T027) executada com P1/P2/P3
  aprovadas; evidência em `validacao.md`.
- **Rev. 2 do research (2026-10-12)** — correções da revisão crítica:
  `base.html` **já tem** `<main>` (skip-link é só 1 `<a>`, risco baixo); botões
  "Filtrar"/"Localizar"/"Exportar" têm texto visível (não são só-ícone); os verdadeiros
  só-ícone são `togglePassword`, `bi-funnel` e o link limpar-filtros; o alerta de erro de
  `conferir.html` **não tem** `role="alert"` (único dos fluxos-alvo); a página **offline**
  tem atualização dinâmica real → `role="status"` nos contadores; única lacuna concreta de
  foco: `.result-option` sem indicador próprio (nenhum `outline:none` no CSS da casa).
