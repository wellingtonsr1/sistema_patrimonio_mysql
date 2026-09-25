# Quickstart: Ajuste Responsivo da Tabela "Inventário Patrimonial" (037)

Guia de validação ponta a ponta. Referências: [contract](contracts/ui-contract-tabela-listagem.md) · [data-model](data-model.md) · [spec](spec.md)

## Pré-requisitos

- Ambiente de dev rodando (`python run.py` — Windows: `python.exe .\run.py`); usuário autenticado.
- Pelo menos 2–3 inventários em estados variados (Planejado, Em andamento, Encerrado), idealmente com: nome longo, escopo descritivo extenso, progresso com múltiplos badges (incluindo "+N não previstos") e um criado por outro usuário.
- Suíte de regressão: `python -m pytest tests/ -q` (100% verde antes e depois — SC-006).

## Como abrir a tela

**Inventários** no menu (ou `/inventarios`) — a tabela está no card central da página.

## Cenários de validação

### V0 — Baseline "antes" (seção 25 do pedido)

1. Antes da alteração: screenshot desktop + medição das larguras das 6 colunas (DevTools) registrada para comparação.

### V1 — Aproveitamento horizontal (US1/AC-01/SC-001/SC-002)

1. Desktop grande (≥1400px): tabela ocupa praticamente toda a largura útil do card (medição ≥95%), sem grandes áreas vazias.
2. Inventário e Escopo dominam visivelmente o espaço (juntas mais da metade — medição); Código, Progresso e Status dimensionados ao conteúdo; Ações mínima.
3. Comparação antes/depois registrada (não é "aumentar tudo" — é redistribuir).

### V2 — Conteúdos íntegros (FR-003/004/005/006/AC-10)

1. Código `INV-YYYY-NNNN` exibido integralmente, sem quebra (nowrap do badge) e sem coluna excessiva.
2. Nome de inventário longo: legível, quebra graciosa quando necessário; linha "Criado em … por …" íntegra.
3. Escopo extenso: texto completo (sem truncamento), quebrando dentro da coluna.
4. Progresso com todos os badges: badges e "X/Y conferidos" legíveis, quebrando/empilhando dentro da coluna sem transbordar.
5. Status "Em andamento" (rótulo mais longo): badge íntegro.

### V3 — Alinhamento e funcionalidade (FR-009/AC-08/AC-11/contract §1–§2)

1. Cada valor sob seu cabeçalho; Ações alinhada à direita (header e botões).
2. Clicar no nome → abre o inventário; clicar no botão-ícone → idem; tooltip "Abrir" presente.
3. Filtros (busca + status) continuam funcionando; estado vazio inalterado (se testável).

### V4 — Responsividade (US2/FR-010/AC-09/contract §3)

1. Desktop médio (768–1399px) e notebook (1024–1399px): proporções mantidas; sem sobreposição de cabeçalhos; ações acessíveis.
2. Tablet (576–767px): adaptação correta; rolagem horizontal (se inevitável) confinada ao contêiner da tabela; controles utilizáveis.
3. Celular (<576px): sem conteúdo cortado indevidamente; sem botão inacessível; sem cabeçalho sobreposto.
4. **Zoom 80% → 200%** (Chrome/Edge): mesmos critérios em toda a faixa (decisão da clarificação).
5. Tema claro e escuro: nenhuma diferença de contraste decorrente da alteração.

### V5 — Não-vazamento de escopo (FR-011/FR-014/contract §4–§5)

1. Outras tabelas/telas visualmente idênticas ao estado anterior (ex.: tela de detalhe do inventário — tabela da 036 —, equipamentos).
2. Container da tela (page header, filtros, card) inalterado.
3. `git diff` contendo **apenas** `app/web/templates/inventarios/list.html` (nenhum asset estático, nenhum `style.css`, nenhum `sw.js`).

## Registro

- Resultado de cada cenário registrado em `specs/037-inventarios-larguras-colunas/validacao.md` (SC-007), incluindo: baseline "antes", tabelas de larguras adotadas (e ajustes com motivo), observações preexistentes fora de escopo e decisões finas — mesmo formato da `validacao.md` da 036.
