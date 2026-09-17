# Quickstart: Validação do Contraste das Opções de Resultado da Conferência (feature 011)

Protocolo de validação de ponta a ponta. Executar após o `/speckit-implement`.

## 1. Pré-requisitos

- Ambiente do projeto ativo (Python 3.10+; dependências instaladas).
- Baseline executada antes da edição: **310 passed / 1 failed** (lockout defasado conhecido).
- Aplicação executável localmente (`python run.py`; banco via `DATABASE_URL`) com usuário contendo as permissões de inventário (`inventario.visualizar` e `inventario.conferir`).
- Um inventário **aberto** (status `EM_ANDAMENTO`) com pelo menos 1 bem pendente de conferência.

## 2. Validação automatizada (não-regressão)

```bash
python -m pytest tests/ -q --tb=no
```

Esperado: **patamar baseline + 1** (novo teste de renderização) — 311 passed / 1 failed conhecida. Nenhum failure novo.

## 3. Validação visual manual (2 temas × 2 telas)

> A cor de borda não é assertável na suíte (sem navegador); esta é a validação principal da feature.

### Cenário 3.1 — Página de conferência no modo claro (US1/AC-01)

1. Login → **Inventários** → abra o inventário em andamento → localize um bem pendente e abra a conferência (página dedicada `/inventarios/{inventario_id}/conferir/{asset_id}` — o parâmetro final é o **id do bem**, não do item; rota `conferir_asset_page`, `routes.py` L1989).
2. Confira o **modo claro** (menu de tema no cabeçalho).
3. **Esperado**: cada uma das 4 opções (🟢 Encontrado, 🟡 Encontrado em local diferente, 🔴 Não encontrado, ⚠️ Sem identificação) apresenta **contorno claramente perceptível** contra o fundo claro — distinção fácil entre a área da opção e o fundo da página.

### Cenário 3.2 — Modal de detalhes no modo claro (US1/FR-008)

1. No detalhe do mesmo inventário, use a ação de conferir do item (abre o modal).
2. **Esperado**: as 4 opções do modal têm o **mesmo tratamento visual** da página dedicada (contornos perceptíveis no claro).

### Cenário 3.3 — Ambas as telas no modo escuro (US1/AC-02)

1. Alterne para o **modo escuro** e repita 3.1 e 3.2.
2. **Esperado**: os contornos continuam claramente perceptíveis sobre o fundo escuro — sem ficar mais fracos que antes da correção (borda escura equivalente à de cards/tabelas do tema).

### Cenário 3.4 — Troca de tema em runtime (edge case)

1. Com a tela de conferência aberta, alterne claro ↔ escuro sem recarregar.
2. **Esperado**: os contornos atualizam imediatamente junto com o tema (cor acompanha o tema ativo — FR-004).

### Cenário 3.5 — Seleção preservada (US2/AC-03)

1. Em cada tema, clique em cada uma das 4 opções.
2. **Esperado**: o rádio marca/desmarca normalmente; a opção selecionada continua identificável (marcação do controle). Nenhum estado "some".

### Cenário 3.6 — Hover preservado (US2)

1. Passe o mouse sobre as opções.
2. **Esperado**: cursor de clique (pointer) em toda a área da opção — inalterado.

### Cenário 3.7 — Foco por teclado (US2)

1. Navegue com **Tab** até o grupo de opções.
2. **Esperado**: o anel/outline de foco do controle aparece normalmente (acessibilidade preservada — FR-011: a borda não é o único indicador).

### Cenário 3.8 — Item já conferido (edge case)

1. Abra a conferência de um item que **já tem resultado** (aviso de re-conferência visível).
2. **Esperado**: o aviso aparece intacto; as opções abaixo mantêm os contornos corrigidos (re-conferência segue funcionando — decisão registrada na DECISAO_RECONFERENCIA).

### Cenário 3.9 — Ausência de efeitos colaterais (US3/AC-08)

1. Percorra as principais telas nos dois temas: Dashboard, Equipamentos (lista/detalhe), Movimentações, Colaboradores, Locais, Manutenções, Relatórios, Administração.
2. **Esperado**: nenhuma diferença visual em cards, tabelas, formulários ou botões (a classe utilitária global não foi alterada).

### Cenário 3.10 — Conteúdo e valores intactos (AC-04/SC-005)

1. Registre uma conferência real em cada tema (1 bem de teste).
2. **Esperado**: o registro grava o resultado escolhido normalmente (nenhuma mudança funcional); textos e emojis das opções idênticos aos atuais.

## 4. Validação alternativa via renderização (sem navegador)

O mesmo caminho da suíte (TestClient) pode confirmar o markup antes da validação visual:

- Página de conferência renderiza as 4 opções com a classe nova e os 4 valores (`ENCONTRADO`, `LOCAL_DIFERENTE`, `NAO_ENCONTRADO`, `SEM_IDENTIFICACAO`) — coberto pelo teste novo.
- O mesmo vale para o HTML do modal em `detail.html` (se incluído no teste).

## 5. Fechamento

- [ ] Suíte no patamar esperado (§2).
- [ ] Cenários 3.1–3.10 executados e registrados em `tasks.md` §Validation Results (com data e resultado).
- [ ] `git status --porcelain` restrito a: `app/web/static/css/style.css`, `app/web/templates/inventarios/conferir.html`, `app/web/templates/inventarios/detail.html`, teste novo, artefatos `specs/011.../`.
- [ ] Constitution checklist (plan) confirmado — 12/12.
