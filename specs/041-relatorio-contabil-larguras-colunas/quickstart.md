# Quickstart: Ajuste Responsivo da Tabela "Relatório Contábil-Físico do Patrimônio" (041)

Guia de validação ponta a ponta. Referências: [contract](contracts/ui-contract-tabela-relatorio-contabil.md) · [data-model](data-model.md) · [spec](spec.md)

## Pré-requisitos

- Ambiente de dev rodando (`python run.py` — Windows: `python.exe .\run.py`); usuário **admin** (tem `relatorios.exportar` — valida o header completo) e, se possível, um usuário sem essa permissão (valida o header sem o controle de exportação).
- Dados ideais: bens com **descrição longa** e com/sem `serial_number` (linha S/N condicional); localizações institucionais longas; responsáveis com nomes completos extensos; bens **sem** localização/responsável/data (fallbacks "Estoque Geral"/"Livre"/"-"); valores monetários variados (baixos, médios, altos — ex.: `R$ 1.250,00` e `R$ 120.000,00`); percentuais de depreciação diferentes; status e categorias variados.
- Suíte de regressão: `python -m pytest tests/ -q` (100% verde antes e depois — SC-006).

## Como abrir a tela

**Relatórios → Relatório Contábil-Físico** no menu (ou `/reports/inventory`) — a tabela está no card central.

## Cenários de validação

### V0 — Baseline "antes" (seção 34 do pedido)

1. Antes da alteração: screenshot desktop + medição das larguras das 10 colunas (DevTools ou script local padrão 039 — research R11) registrada para comparação.

### V1 — Aproveitamento horizontal (US1/AC-01/SC-001/SC-002)

1. Desktop grande (≥1400px): tabela ocupa praticamente toda a largura útil do card (medição ≥95%).
2. Descrição + Localização + Responsável dominam o espaço (juntas mais da metade do espaço variável — medição); Tombamento/Categoria proporcionais; Status/Data Compra/monetárias compactas.
3. Comparação antes/depois registrada (redistribuição, não "aumentar tudo").

### V2 — Conteúdos íntegros (FR-003..010/AC-02..AC-11)

1. Tombamento completo sem quebra do código (fonte mono/negrito preservadas).
2. Descrição legível — **texto completo, sem corte** — com nome em `<strong>` e linha `S/N` condicional íntegra, sem sobreposição.
3. Categoria (badge) e Status (pill) íntegros, com comportamento visual atual.
4. Localização longa — **texto completo**; fallback "Estoque Geral" quando sem local.
5. Responsável com nome completo — **texto completo**; fallback "Livre" quando sem responsável.
6. Data Compra `dd/mm/YYYY` sem quebra; fallback "-" quando sem data.
7. Monetárias: `R$ X.XXX,XX` íntegros sem quebra, alinhamento à direita consistente nas 3; Depreciação `-XX%` em vermelho; Valor Atual em verde, negrito.

### V3 — Alinhamento e estabilidade (AC-12/AC-14/contract §1–§2)

1. Cada valor sob seu cabeçalho (10/10); thead e tbody com a mesma estrutura (sem deslocamento).
2. Distribuição estável com massas diferentes (filtros variados) — as larguras não mudam por conteúdo da linha.
3. Tabela com uma única linha: distribuição por coluna mantida.

### V4 — Responsividade e temas (US2/AC-13/contract §3)

1. Desktop médio (768–1399px) e notebook (1024–1399px): proporções mantidas; sem sobreposição; sem quebras inadequadas.
2. Tablet (576–767px): adaptação; rolagem horizontal (se inevitável) confinada ao `table-responsive`; 10 colunas acessíveis.
3. Celular (<576px): rolagem confinada; sem conteúdo cortado indevidamente; sem sacrificar legibilidade para eliminar a rolagem.
4. **Zoom 80% → 200%** (Chrome/Edge): mesmos critérios em toda a faixa (precedentes 036–040).
5. Tema claro e escuro: nenhuma diferença de contraste decorrente da alteração.

### V5 — Não-vazamento de escopo (FR-011/FR-016/contract §5)

1. Tabelas da 036 (conferência), 037 (inventários), 038 (equipamentos), 039 (movimentações) e 040 (custodiantes) visualmente idênticas ao estado anterior; demais telas inalteradas.
2. Os outros 2 relatórios (`/reports/movements`, `/reports/custodians`) visualmente idênticos em tela e no papel.
3. Container da tela (page header, cabeçalho interno do relatório, card) inalterado.
4. `git diff` contendo **apenas** `app/web/templates/reports/inventory.html` (nenhum asset estático, nenhum `style.css`, nenhum `sw.js`).

### V6 — Impressão inalterada (US3/SC-007/contract §4 — obrigatório na 041)

1. Pré-visualização de impressão de `/reports/inventory` (Ctrl+P) **antes** da alteração: salvar PDF de referência.
2. Pré-visualização **depois** da alteração: comparar com a referência — mesmas páginas, sem primeira página em branco, cabeçalho das colunas repetido em todas as páginas, linhas indivisíveis, valores íntegros, escala compacta atual.
3. Repetir em orientação retrato e paisagem (o C1 mantém a escolha no diálogo de impressão).
4. Exportações CSV (gate `relatorios.exportar`) com conteúdo/nome de arquivo idênticos antes/depois (Excel/PDF idem, se exercitados).
5. `test_report_print_smoke.py` verde (âncora `report-print` preservada).

## Registro

- Resultado de cada cenário registrado em `specs/041-relatorio-contabil-larguras-colunas/validacao.md` (SC-008) no formato das 036–040: baseline "antes", tabelas de larguras finais (com ajustes/motivos), resultado por cenário com medições e zoom, temas, **verificação de impressão (V6)**, observações preexistentes fora de escopo e decisões finas.
