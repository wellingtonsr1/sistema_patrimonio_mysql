# Quickstart: Ajuste Responsivo da Tabela "Etiquetas de Patrimônio" (044)

Guia de validação ponta a ponta. Referências: [contract](contracts/ui-contract-tabela-etiquetas.md) · [data-model](data-model.md) · [spec](spec.md)

## Pré-requisitos

- Ambiente de dev rodando (`python run.py` — Windows: `python.exe .\run.py`); usuário **admin** (gate `patrimonio.visualizar`).
- Dados ideais: equipamentos com **tombamentos de comprimentos variados** (ex.: `IMPJP1456`, `IMPJP679450`); **nomes longos** de equipamento ("Computador Dell OptiPlex 7090"); **com e sem marca/modelo** (e marca/modelo longa); **setores longos** ("Setor de Contabilidade", "Gabinete da Superintendência"); **localizações longas** ("IPMJP - Fundo Municipal de Previdência", "IPMJP - Setor de Análise de Benefícios"); equipamento **sem local** (fallbacks "—").
- Suíte de regressão: `python -m pytest tests/ -q` (100% verde antes e depois — SC-006).

## Como abrir a tela

**Patrimônio → Etiquetas** (ou `/assets/labels`) — a tabela de seleção está no card "Mostrando N de M" (usar a busca/filtros se necessário para ver os dados ideais). A folha de etiquetas aparece abaixo (pré-visualização) conforme a seleção.

## Cenários de validação

### V0 — Baseline "antes" (seção 29 do pedido)

1. Antes da alteração: screenshot desktop + medição das larguras das 5 colunas (DevTools ou script local padrão 041/042/043 — research R11) + **contagem de quebras de linha por célula** registrada para comparação.

### V1 — Aproveitamento horizontal e linha única (US1/AC-01..AC-09/SC-001/SC-002)

1. Desktop grande (≥1400px): tabela ocupa praticamente toda a largura útil do card (medição ≥95%).
2. Equipamento + Setor + Localização dominam o espaço (maior bloco — medição); Tombamento compacto mas suficiente; checkbox mínima.
3. **Linha única**: tombamento completo sem quebra; nome do equipamento em uma linha (marca/modelo na sua linha própria); setor e localização completos sem quebra; títulos em linha única.
4. Comparação antes/depois registrada (redução de quebras + redistribuição).

### V2 — Conteúdos íntegros e tooltips (FR-003..008/AC-02..AC-08/C-4)

1. **Tooltip Bootstrap** no nome, na marca/modelo, no setor e na localização quando truncados: hover exibe o valor **completo**.
2. Tombamento: badge `.tag-badge` íntegro (código completo nas larguras alvo); sem regra nova sobre o badge.
3. Marca/modelo como 2ª linha informativa preservada; equipamento sem marca/modelo renderiza sem buraco visual.
4. Setor e Localização com fallbacks "—" íntegros (fora dos spans cortáveis).
5. Checkbox funcional: marcar/desmarcar atualiza contagem, folha de etiquetas e estado na URL — **comportamento idêntico ao atual**.

### V3 — Alinhamento e estabilidade (AC-08/contract §1–§2)

1. Cada valor sob seu cabeçalho (5/5, incluindo o cabeçalho vazio do checkbox); thead e tbody com a mesma estrutura.
2. Distribuição estável com massas diferentes (busca/filtro) — larguras não mudam por conteúdo.
3. Altura das linhas uniforme (linha garantida ⇒ 2 linhas estruturais do Equipamento, sem "escadinha" nas demais colunas).

### V4 — Responsividade e temas (US2/AC-09/contract §3)

1. Desktop médio (768–1399px) e notebook (1024–1399px): proporções mantidas; linha garantida com corte controlado; sem sobreposição.
2. Tablet (576–767px): rolagem horizontal (quando necessária) confinada ao `table-responsive`; 5 colunas acessíveis.
3. Celular (<576px): rolagem confinada funcional; checkboxes acessíveis; valores truncados consultáveis; fallback global do `.tag-badge` (≤479.98px) aceitável.
4. **Zoom 80% → 200%** (Chrome/Edge): mesmos critérios em toda a faixa (precedentes 036–043).
5. Tema claro e escuro: nenhuma diferença de contraste decorrente da alteração (contraste dos checkboxes em `style.css` intacto).

### V5 — Não-vazamento de escopo e impressão (FR-010/FR-013/FR-016/contract §5–§6)

1. Tabelas das specs 036 (conferência), 037 (inventários), 038 (equipamentos), 039 (movimentações), 040 (custodiantes), 041 (Relatório Contábil-Físico), 042 (Trilha de Auditoria) e 043 (Usuários) visualmente idênticas; demais telas inalteradas.
2. Container da tela (page header, filtros, toolbar, contador, estado vazio) inalterado.
3. **Impressão de etiquetas idêntica à atual**: selecionar equipamentos, "Imprimir etiquetas" → apenas `#labels-print-area` é impresso, A4 com margens de 8mm, etiquetas íntegras (QR + logo + tombamento), quebra apenas ENTRE etiquetas (domínio da 013 intocado).
4. `git diff` contendo **apenas** `app/web/templates/assets/labels.html` (nenhum asset estático, nenhum `style.css`, nenhum `sw.js`).

## Registro

- Resultado de cada cenário registrado em `specs/044-etiquetas-larguras-colunas/validacao.md` (SC-007) no formato das 036–043: baseline "antes" (com contagem de quebras), tabelas de larguras finais (com ajustes/motivos), resultado por cenário V1–V5 (com medições, zoom, **verificação de tooltips** e **conferência da impressão de etiquetas**), temas, observações preexistentes fora de escopo e decisões finas.
