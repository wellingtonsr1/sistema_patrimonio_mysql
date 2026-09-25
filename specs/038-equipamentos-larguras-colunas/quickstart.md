# Quickstart: Ajuste Responsivo da Tabela "Equipamentos" (038)

Guia de validação ponta a ponta. Referências: [contract](contracts/ui-contract-tabela-equipamentos.md) · [data-model](data-model.md) · [spec](spec.md)

## Pré-requisitos

- Ambiente de dev rodando (`python run.py` — Windows: `python.exe .\run.py`); usuário **admin** (tem `movimentacao.criar` — valida o caso de 2 botões) e, se possível, um usuário sem essa permissão (valida 1 botão).
- Dados ideais: equipamentos com nome longo, marca/modelo e S/N; responsável com nome completo + matrícula; local institucional extenso; status variados (incluindo "Em Manutenção"); valor alto (R$ 120.000,00); e um equipamento sem responsável/local (fallbacks "Estoque Livre"/"Estoque Central").
- Suíte de regressão: `python -m pytest tests/ -q` (100% verde antes e depois — SC-006).

## Como abrir a tela

**Equipamentos** no menu (ou `/assets`) — a tabela está no card central (aplicar filtros se necessário para ver os dados ideais).

## Cenários de validação

### V0 — Baseline "antes" (seção 27 do pedido)

1. Antes da alteração: screenshot desktop + medição das larguras das 8 colunas (DevTools) registrada para comparação.

### V1 — Aproveitamento horizontal (US1/AC-01/SC-001/SC-002)

1. Desktop grande (≥1400px): tabela ocupa praticamente toda a largura útil do card (medição ≥95%).
2. Equipamento/Modelo + Responsável + Localização dominam (juntas mais da metade — medição); Tombamento/Categoria proporcionais; Status/Valor/Ações compactas.
3. Comparação antes/depois registrada (redistribuição, não "aumentar tudo").

### V2 — Conteúdos íntegros (FR-003..010/AC-12)

1. Tombamento completo, sem quebra/truncamento.
2. Nome de equipamento longo + linha "marca modelo • S/N: XXX" legíveis.
3. Categoria badge íntegro; Status "Em Manutenção"/"Em Transferência" em 1 linha, com a bolinha (::before) alinhada.
4. Responsável com nome completo + matrícula íntegros; fallback "Estoque Livre" correto.
5. Localização institucional longa completa; fallback "Estoque Central" correto.
6. Valor "R$ 120.000,00" sem quebra (nowrap funcional).
7. 2 botões de Ação (admin) lado a lado sem aperto; com usuário sem `movimentacao.criar`, 1 botão e a coluna estável.

### V3 — Alinhamento e funcionalidade (AC-10/AC-13/contract §1–§2)

1. Cada valor sob seu cabeçalho; Ações à direita (header e botões).
2. Links: tombamento → ficha; nome → ficha; responsável → colaborador. Botões: Ver Detalhes; Movimentar (leva a `/movements/new?asset_id=`).
3. Filtros, contagem "Mostrando X de Y" e estado vazio intocados.

### V4 — Responsividade e temas (US2/AC-11/contract §3)

1. Desktop médio (768–1399px) e notebook (1024–1399px): proporções mantidas; sem sobreposição; sem quebras inadequadas.
2. Tablet (576–767px): adaptação; rolagem horizontal (se inevitável) confinada ao `table-responsive`; controles utilizáveis.
3. Celular (<576px): rolagem confinada (tabela larga de 8 colunas); sem conteúdo cortado indevidamente; ações acessíveis.
4. **Zoom 80% → 200%** (Chrome/Edge): mesmos critérios em toda a faixa (precedentes 036/037).
5. Tema claro e escuro: nenhuma diferença de contraste decorrente da alteração.

### V5 — Não-vazamento de escopo (FR-011/FR-015/contract §4–§5)

1. Tabelas da 036 (tela do inventário) e 037 (listagem de inventários) visualmente idênticas ao estado anterior; demais telas inalteradas.
2. Container da tela (page header, filtros, card, contagem) inalterado.
3. `git diff` contendo **apenas** `app/web/templates/assets/list.html` (nenhum asset estático, nenhum `style.css`, nenhum `sw.js`).

## Registro

- Resultado de cada cenário registrado em `specs/038-equipamentos-larguras-colunas/validacao.md` (SC-007) no formato das 036/037: baseline "antes", tabelas de larguras finais (com ajustes/motivos), resultado por cenário com medições e zoom, temas, observações preexistentes fora de escopo e decisões finas (ex.: tratamento do status-pill).
