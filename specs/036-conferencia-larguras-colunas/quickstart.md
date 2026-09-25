# Quickstart: Ajuste Responsivo das Larguras das Colunas na Tabela de Conferência (036)

Guia de validação ponta a ponta. Referências: [contract](contracts/ui-contract-tabela-conferencia.md) · [data-model](data-model.md) · [spec](spec.md)

## Pré-requisitos

- Ambiente de dev rodando (`python run.py` — Windows: `python.exe .\run.py`); usuário com `inventario.conferir` (o admin serve).
- Um inventário em `PLANEJADO` ou `EM_ANDAMENTO` com bens esperados listados — idealmente com: local institucional longo (ex.: "IPMJP - Fundo Municipal de Previdência"), nome de bem extenso, itens em estados variados (pendente, encontrado, local diferente com observação e conferidor registrados) e pelo menos um item num inventário **encerrado** (para o edge case).
- Suíte de regressão: `python -m pytest tests/ -q` (deve permanecer 100% verde — SC-005).

## Como abrir a tela

1. **Inventários** → abrir o inventário → a tabela "Bens esperados" está no painel principal da página `/inventarios/{id}`.
2. Ter à mão também um inventário **encerrado** (coluna Conferir sem botões).

## Cenários de validação

### V1 — Proporção das colunas em desktop (US1 / SC-001 indicativo)

1. Abrir a tela em desktop (≥1400px): **Bem** e **Local esperado** dominam visivelmente a largura da tabela; **Resultado** e **Conferir** ficam compactas (badge/botão); **Tombamento** proporcional ao conteúdo (C-1).
2. Referência indicativa (não limite rígido — clarificação Q1): Bem+Local ≈ 60–65% da largura; Resultado+Conferir ≈ 20–25%.
3. Larguras NÃO são iguais entre as colunas (C-4).

### V2 — Conteúdos longos legíveis (FR-003/FR-004/SC-002)

1. Local institucional de 35–45 caracteres (ex.: "IPMJP - Superintendência Adjunta") aparece **completo, em linha única**, sem truncamento.
2. Nome de bem extenso permanece legível (linha única em desktop; quebra graciosa ao estreitar).
3. Badge de LOCAL_DIFERENTE com local anexado (ex.: "⚠ Local diferente: Almoxarifado Central") **não alarga** a coluna Resultado — quebra para a linha seguinte dentro da célula, sem sobrepor vizinhos.
4. Observação e metadados ("data • usuário") da célula Resultado permanecem legíveis, quebrando dentro da coluna (FR-005).

### V3 — Alinhamento e integridade (FR-007 / contract §1–§2)

1. Cabeçalho de cada coluna alinhado com seu conteúdo; coluna **Conferir** com header e botões à direita (`text-end` preservado).
2. Clicar num tombamento → navega à ficha do bem (link intacto).
3. Clicar no botão-ícone de conferir → modal abre com o bem correto (modal intacto).
4. Nenhum dado sumiu: badges, observação, "data • usuário" e fallback "Estoque Central" presentes (contract §2).
5. Inventário **encerrado**: sem botão na coluna Conferir, header permanece alinhado, sem espaço vazio desproporcional (edge case).

### V4 — Responsividade (US2 / FR-008 / contract §3)

1. **Desktop médio (768–1399px)**: mesmas proporções relativas; sem sobreposição.
2. **Tablet (576–767px)**: colunas mantêm proporção; se houver rolagem horizontal, ela fica restrita ao contêiner da tabela (`table-responsive`); botão acessível.
3. **Celular (<576px)**: tabela utilizável; conteúdo não cortado sem rolagem; botões acessíveis.
4. Prioridade em telas menores (C-3): Bem > Local esperado > Tombamento > Resultado > Conferir.
5. **Zoom 80% → 200%** (Chrome/Edge): mesmos critérios de legibilidade; sem sobreposição em nenhum nível (decisão Q3).
6. Tema **claro e escuro**: nenhuma diferença de cor/contraste decorrente da alteração.

### V5 — Não-vazamento de escopo (FR-012 / contract §4–§5)

1. Na MESMA página, os cards **"Conflitos offline"** e de **coletas offline** (tabelas vizinhas) estão visualmente **idênticos** ao estado anterior (mesmas larguras/quebras de antes).
2. Abrir outra tela com tabela (ex.: lista de inventários, equipamentos): nada mudou.
3. `git status`/diff mostra alteração **apenas** em `app/web/templates/inventarios/detail.html` (nenhum asset estático, nenhum `style.css`, nenhum `sw.js`).

## Registro

- Resultado de cada cenário registrado em `specs/036-conferencia-larguras-colunas/validacao.md` (SC-007), incluindo data, resoluções testadas e qualquer decisão fina tomada (ex.: truncamento com `title` no badge longo, se aplicável — research R3/R4).
