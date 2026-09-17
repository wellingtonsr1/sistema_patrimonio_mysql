# Phase 0 Research: Contraste das Opções de Resultado da Conferência

**Feature**: 011-contraste-conferencia | **Date**: 2026-09-17

Todas as decisões abaixo foram verificadas no código real (análise somente leitura). Nenhum [NEEDS CLARIFICATION] permanece.

## Tabela de fatos verificados

| # | Fato | Evidência |
|---|---|---|
| F1 | O campo "Resultado da conferência" é renderizado em 2 templates | `inventarios/conferir.html` L71 (página dedicada) e `inventarios/detail.html` L316 (modal) |
| F2 | Cada opção é `<label class="d-block border rounded p-2" style="cursor:pointer;">` | Idêntico nos 2 templates, 4 opções cada (8 elementos) |
| F3 | Os emojis/textos/valores são idênticos nos 2 templates (🟢 🟡 🔴 ⚠️; `ENCONTRADO`, `LOCAL_DIFERENTE`, `NAO_ENCONTRADO`, `SEM_IDENTIFICACAO`) | blocos comparados |
| F4 | A borda vem da utilitária `.border` do **Bootstrap 5.3.3** (CDN em `base.html` L24) | classe `border` não definida no CSS do projeto |
| F5 | O projeto NÃO sobrescreve `--bs-border-color` (nem `--bs-border-*`) | grep em `style.css`: 0 ocorrências |
| F6 | `base.html` sincroniza `data-theme` e `data-bs-theme` no `<html>` (L2/L13) | tema escuro ativa o ajuste nativo do Bootstrap 5.3 — por isso o escuro funciona |
| F7 | O tema da aplicação é controlado por `data-theme` no raiz; `[data-theme="dark"]` em `style.css` L1023 | mecanismo de troca existente |
| F8 | Tokens próprios de borda já existem e alternam por tema: `--c-border: var(--color-border)` (`#C8C2C0` claro, L31) → `var(--dark-border)` (`#3A3335` escuro, L1074); mapeados em L63 e L1076-1077 | grep `--c-border` |
| F9 | Classes de componente próprias convivem com utilitários Bootstrap como padrão do projeto (`.badge-soft-primary`, `.tag-badge`, `.badge-soft-gray` usados nos mesmos templates) | `style.css` L498-508; templates |
| F10 | A utilitária `.border` do Bootstrap define `border: var(--bs-border-width) var(--bs-border-style) var(--bs-border-color)!important` | comportamento conhecido do Bootstrap 5.3 (regra `!important` das utilitárias) |
| F11 | `style.css` é carregado DEPOIS de `bootstrap.min.css` em `base.html` | ordem de estilos favorece o CSS do projeto em empate |
| F12 | Seletores modernos (`:has()`) já são usados no `style.css` (L1585-1596) | padrão atual do projeto |
| F13 | Nenhuma outra tela usa `<label class="d-block border rounded` | grep em `app/web/templates/`: somente os 2 templates do inventário |
| F14 | Não existem testes visuais automatizados; `tests/test_inventario.py` cobre regras de conferência | ls tests/; grep |

## Decisões

### R1 — Onde corrigir: classe própria do componente (`.result-option`) no `style.css`

- **Decision**: criar `.result-option { border: 1px solid var(--c-border) !important; }` e acrescentar a classe aos 8 `<label>`.
- **Rationale**: resolve o problema no único arquivo de estilo (F11: carregado depois do Bootstrap), sem tocar na utilitária global `.border` (FR-009/US3) e reutilizando o token de borda que já alterna por tema (F8 → FR-003/FR-004). Segue o padrão estabelecido de classes de componente próprias (F9).
- **Alternatives considered**:
  - *Sobrescrever `--bs-border-color` globalmente* — rejeitada: mudaria TODAS as bordas Bootstrap do sistema (cards, tabelas, formulários) com risco de regressão visual generalizada (violaria US3/SC-004).
  - *Estilo inline em cada `<label>` (`style="border-color:var(--c-border)"`)* — rejeitada: `border-color` inline perde para a utilitária `!important` do Bootstrap (F10) sem duplicar `!important` inline (feio e frágil); espalha estilo por 8 elementos em vez de centralizar.
  - *Remover `.border` e estilizar tudo na classe nova* — rejeitada: alteração maior no markup sem ganho; `.border` mantém a largura/estilo padrão.

### R2 — Cor da borda: token existente `--c-border`

- **Decision**: usar `var(--c-border)` sem criar nenhuma variável nova.
- **Rationale**: é o token de borda padrão dos componentes do projeto (cards, tabelas — L498), com valor apropriado nos dois temas (F8). Atende FR-003 (reutilizar antes de criar) e FR-004 (cor acompanha o tema).
- **Alternatives considered**:
  - *`--c-border-light`* — rejeitada: é ainda mais clara que `--c-border` no tema claro (é o problema atual).
  - *Nova variável `--c-border-strong`* — rejeitada nesta feature: nenhuma evidência de que `--c-border` seja insuficiente; criar token novo sem necessidade expande o sistema de design sem justificativa (poderá ser reavaliado na validação visual — se o contraste ainda for insuficiente, é um ajuste de 1 linha registrado como pendência).

### R3 — Aplicação nos templates: só acrescentar a classe

- **Decision**: `class="d-block border rounded p-2 result-option"` nos 8 `<label>`; nenhum outro toque no markup.
- **Rationale**: mantém estrutura, ordem, atributos e conteúdo byte-idênticos (FR-006/FR-007); `.border` continua presente (largura/estilo), só a cor passa a ser governada pela classe do componente.
- **Alternatives considered**: *substituir as classes utilitárias pela classe nova* — rejeitada: maior difusão de risco, sem benefício.

### R4 — Testes: guarda leve de renderização, validação de contraste manual

- **Decision**: 1 teste pytest (TestClient, padrão da suíte) verificando que a página de conferência renderiza as 4 opções com `result-option` e os 4 valores inalterados, **e** o mesmo para o modal de `detail.html` (prova simétrica do FR-008 — ajuste C1 do analyze); contraste real validado visualmente no quickstart.
- **Rationale**: sem navegador na suíte, cor de borda não é assertável; o teste ancora a feature no ciclo de regressão (Constitution VIII) sem criar infraestrutura de teste visual nova.
- **Alternatives considered**: *teste de CSS com parsing* — rejeitado: frágil e fora do padrão do projeto.

### R5 — Documentação: sem atualização necessária

- **Decision**: não atualizar README/ajuda/docs nesta feature.
- **Rationale**: nenhum comportamento documentado muda (fluxo de conferência, valores, permissões, endpoints intocados); a documentação não descreve estilos de borda (Constitution XI — documentação fiel, não documentação de cosmética).
- **Alternatives considered**: *menção na ajuda* — rejeitada: a ajuda descreve como conferir, não como as bordas aparecem; incluir seria ruído.

## Impacto nos princípios (reavaliação pós-design)

Nenhuma violação: a abordagem é aditiva (1 classe CSS, atributo de classe em 8 elementos), reutiliza o sistema de temas, não toca Python/banco/RBAC/rotas e preserva todos os estados existentes. Plan reavaliado: **12/12 PASS**.
