# Quickstart: Ajuste Responsivo da Tabela "Trilha de Auditoria & Fluxo" (042)

Guia de validação ponta a ponta. Referências: [contract](contracts/ui-contract-tabela-trilha-auditoria.md) · [data-model](data-model.md) · [spec](spec.md)

## Pré-requisitos

- Ambiente de dev rodando (`python run.py` — Windows: `python.exe .\run.py`); usuário **admin** (tem `relatorios.exportar` — valida o header completo) e, se possível, um usuário sem essa permissão (valida o header sem o controle de exportação).
- Dados ideais (massa com movimentações variadas): motivo **longo** (excedendo a largura da coluna); origem/destino institucionais longos **com e sem custodião** (estrutura de 2 linhas condicional); equipamento com nome extenso; tipo com label longo ("Entrada por Aquisição", "Envio para Manutenção"); operador com nome completo extenso; status variados (incluído "Em Manutenção"); termo **presente e ausente** (link vs "-"); data/hora variadas.
- Suíte de regressão: `python -m pytest tests/ -q` (100% verde antes e depois — SC-006).

## Como abrir a tela

**Relatórios → Trilha de Auditoria** no menu lateral (ou `/reports/movements`) — a tabela está no card central.

## Cenários de validação

### V0 — Baseline "antes" (seção 36 do pedido)

1. Antes da alteração: screenshot desktop + medição das larguras das 10 colunas (DevTools ou script local padrão 039/041 — research R11) registrada para comparação; **contar as quebras de linha por célula** nas primeiras linhas (a métrica central desta spec é a linha única).

### V1 — Aproveitamento horizontal e linha única (US1/AC-01..AC-11/SC-001/SC-002)

1. Desktop grande (≥1400px): tabela ocupa praticamente toda a largura útil do card (medição ≥95%).
2. Equipamento + Origem + Destino + Motivo dominam o espaço (maior bloco — medição); Operador intermediária; Data/Hora, Tombamento, Tipo, Status e Termo compactas.
3. **Linha única**: Data/Hora, Tombamento, Tipo, Status e Termo sem nenhuma quebra; Equipamento, Motivo e Operador em 1 linha (com ellipsis quando excedem); Origem/Destino com 2 linhas informativas (local + custodião), cada uma em linha única.
4. Comparação antes/depois registrada (redução de quebras + redistribuição).

### V2 — Conteúdos íntegros e tooltips (FR-003..012/AC-02..AC-11/C-7)

1. **Tooltip Bootstrap** em cada valor truncado (Equipamento, Motivo, Operador, segmentos de Origem/Destino): hover exibe o texto **completo**, com leitura confortável; tooltip não aparece em valores não truncados (sem tooltip desnecessário, se a implementação condicionar).
2. Motivo: sem `truncate-2`/`max-width:200px` antigos; valor completo no tooltip.
3. Tombamento sem quebra; Data/Hora completa; badge de Tipo íntegro; pill de Status íntegro; link do Termo íntegro e funcional (abre em nova aba); fallbacks "-" onde não há dado; estrutura local + custodião preservada.
4. Cores semânticas preservadas (Destino/Termo em `var(--c-primary-text)`, Operador `text-muted`).

### V3 — Alinhamento e estabilidade (AC-12/seção 23/contract §1–§2)

1. Cada valor sob seu cabeçalho (10/10); thead e tbody com a mesma estrutura.
2. Distribuição estável com massas diferentes (filtrar por período/tipo, se aplicável) — larguras não mudam por conteúdo.
3. Altura das linhas uniforme (linha garantida ⇒ linhas de 1–2 linhas informativas, sem "escadinha" de quebras).

### V4 — Responsividade e temas (US2/AC-13/contract §3)

1. Desktop médio (768–1399px) e notebook (1024–1399px): linha única mantida com corte controlado; sem sobreposição.
2. Tablet (576–767px): rolagem horizontal (quando necessária) confinada ao `table-responsive`; 10 colunas acessíveis.
3. Celular (<576px): rolagem confinada funcional; todas as colunas acessíveis; sem fonte minúscula; sem sobreposição.
4. **Zoom 80% → 200%** (Chrome/Edge): mesmos critérios em toda a faixa.
5. Tema claro e escuro: nenhuma diferença de contraste decorrente da alteração.

### V5 — Não-vazamento de escopo (FR-014/FR-019/contract §5)

1. Tabelas da 036 (conferência), 037 (inventários), 038 (equipamentos), **039 (listagem de Movimentações — `movements/list.html`)**, 040 (custodiantes) e 041 (Relatório Contábil-Físico) visualmente idênticas; demais telas inalteradas.
2. Os outros 2 relatórios (`/reports/inventory`, `/reports/custodians`) idênticos em tela e no papel.
3. Container da tela (page header, cabeçalho interno do relatório, card) inalterado.
4. `git diff` contendo **apenas** `app/web/templates/reports/movements_report.html` (nenhum asset estático, nenhum `style.css`, nenhum `sw.js`).

### V6 — Impressão e exportação inalteradas (US3/SC-007/contract §4 — obrigatório na 042)

1. Pré-visualização de impressão de `/reports/movements` (Ctrl+P) **antes** da alteração: salvar PDF de referência.
2. Pré-visualização **depois**: comparar — mesmas páginas, sem página em branco, cabeçalho repetido, linhas indivisíveis, textos **impressos por completo** (sem ellipsis no papel — spans neutralizados), escala compacta atual.
3. Repetir em retrato e paisagem (C1 mantém a escolha no diálogo).
4. Exportação CSV com conteúdo/nome de arquivo idênticos (gate `relatorios.exportar`).
5. `test_report_print_smoke.py` verde (âncora `report-print` preservada).

## Registro

- Resultado de cada cenário registrado em `specs/042-trilha-auditoria-larguras-colunas/validacao.md` (SC-008) no formato das 036–041: baseline "antes" (com contagem de quebras), tabelas de larguras finais (com ajustes/motivos), resultado por cenário V1–V6 (com medições, zoom e **verificação de tooltips e de impressão**), temas, observações preexistentes fora de escopo e decisões finas.
