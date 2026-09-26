# Quickstart: Ajuste Responsivo da Tabela "Visão Geral do Patrimônio" (046)

Guia de validação ponta a ponta. Referências: [contract](contracts/ui-contract-tabela-dashboard.md) · [data-model](data-model.md) · [spec](spec.md)

## Pré-requisitos

- Ambiente de dev (`python run.py`); qualquer usuário autenticado acessa `/` (dashboard).
- Dados mínimos para a tabela ter conteúdo: **pelo menos 1 movimentação registrada** (ideal: movimentações com e sem `term_code` — par de botões vs. botão único; destinos por colaborador E por local/"Estoque"; equipamentos com nomes longos).
- Estado V0: renderizar/medir **ANTES** da alteração (script de medição salva baseline em `validacao_local.out.md`).
- Suíte: `python -m pytest tests/ -q` verde antes e depois (regressão §37).

## Como exercitar

- **Script de medição local** (clarificação 2026-09-26): `python specs/046-dashboard-larguras-colunas/validar_local.py` — mede larguras por coluna, quebras de linha por célula, alinhamento thead/tbody, truncamento sem tooltip e a IDENTIDADE da tabela "Necessitam de atenção" (deve ser idêntica antes/depois), nas larguras de referência (desktop grande/médio, notebook, tablet, celular) e zoom 80%–200%; relatório comparativo V0/V1 em `validacao_local.out.md`.
- **Manual (dev)**: abrir `/` (Visão Geral do Patrimônio) e inspecionar a tabela "Fluxo Recente de Movimentações": largura do card, linha única por valor, tooltips nos valores truncados, par de botões nas linhas com termo.

## Cenários de validação (§28 do pedido) — mapeamento

| Cenário | Verificação essencial | Onde |
|---|---|---|
| Desktop grande | tabela ≥95% do card; 6 colunas de valores em linha única; Ações compacta | `validacao.md` (manual) + script |
| Desktop médio | distribuição proporcional; sem sobreposição; linha garantida com corte controlado | script + manual |
| Notebook | legibilidade; ações acessíveis; largura eficiente | script + manual |
| Tablet | adaptação; conteúdo acessível; controles utilizáveis | script + manual |
| Celular | rolagem confinada ao `table-responsive`; nada inacessível; sem fonte excessivamente reduzida | script + manual |
| Zoom 80%–200% | layout íntegro; sem desalinhamento; sem overflow indevido | script |
| Integridade do escopo | tabela "Necessitam de atenção" e demais cards IDÊNTICOS antes/depois | script (R5) |
| Conteúdo (FR-016) | todos os valores/botões presentes (data, tombamento, equipamento, ação, destino, operador, termo condicional, ver bem) | manual + script |
| Regressão | suíte pytest 100% verde | SC-006 |

## Registro

- Resultado de cada cenário + suíte completa em `specs/046-dashboard-larguras-colunas/validacao.md` (SC-007), incluindo comparação antes/depois do script `validar_local.py` (relatório `validacao_local.out.md` no padrão das 039/042/044).
