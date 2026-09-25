# Quickstart: Ajuste Responsivo da Tabela "Fluxo Global de Movimentações" (039)

Guia de validação ponta a ponta. Referências: [contract](contracts/ui-contract-tabela-movimentacoes.md) · [data-model](data-model.md) · [spec](spec.md)

## Pré-requisitos

- Ambiente de dev rodando (`python run.py` — Windows: `python.exe .\run.py`); usuário **admin** (tem `movimentacao.visualizar` — acesso à tela; permissões não mudam nesta feature).
- Dados ideais: movimentações de tipos variados (incluindo "Envio para Manutenção"/"Atualização de Estado" — rótulos longos); locais institucionais extensos e custodiantes com nome completo em Origem/Destino; motivo descritivo longo (excede 2 linhas); movimentação **com** termo (`term_code` — 2 botões) e **sem** termo (1 botão); ao menos 1 registro com fallback `-` em origem/destino (ex.: ENTRADA_AQUISICAO sem origem).
- Suíte de regressão: `python -m pytest tests/ -q` (100% verde antes e depois — SC-006).

## Como abrir a tela

**Movimentações / Fluxo Global de Movimentações** no menu (ou `/movements`) — a tabela está no card central (usar o filtro de tipo se necessário para ver os dados ideais).

## Cenários de validação

### V0 — Baseline "antes" (seção 27 do pedido)

1. Antes da alteração: screenshot desktop + medição das larguras das 9 colunas (DevTools) registrada para comparação.

### V1 — Aproveitamento horizontal (US1/AC-01/SC-001/SC-002)

1. Desktop grande (≥1400px): tabela ocupa praticamente toda a largura útil do card (medição ≥95%).
2. Equipamento + Origem + Destino + Motivo + Operador dominam (juntas mais da metade — medição); Data / Hora, Tombamento e Tipo proporcionais; Ações compacta.
3. Comparação antes/depois registrada (redistribuição, não "aumentar tudo").

### V2 — Conteúdos íntegros (FR-003..010/AC-12)

1. Data / Hora `dd/mm/AAAA HH:MM` completa, em 1 linha, sem quebra entre data e hora.
2. Tombamento completo, sem quebra/truncamento (badge `tag-badge` íntegro).
3. Nome de equipamento longo legível.
4. Badge do Tipo íntegro — "Envio para Manutenção" e "Atualização de Estado" sem quebra inadequada.
5. Origem e Destino: local + custodiante nas 2 linhas empilhadas, com ícones; fallbacks `-` corretos; nomes longos sem truncamento.
6. **Motivo**: ocupa a largura da coluna sem o cap de 220px; corte em 2 linhas funcionando (texto além de 2 linhas oculto, como no restante do sistema); nada truncado em 1 linha.
7. Operador com nome completo íntegro.
8. 2 botões de Ação ("Imprimir Termo" + "Ver Bem") lado a lado sem aperto; registro sem termo exibe 1 botão e a coluna permanece estável.

### V3 — Alinhamento e funcionalidade (AC-11/AC-14/contract §1–§2)

1. Cada valor sob seu cabeçalho (9/9); Ações à direita (header e botões).
2. Links: tombamento → ficha do bem; nome → ficha do bem. Botões: Imprimir Termo (abre `/movements/{id}/term`) e Ver Bem → ficha.
3. Filtro de tipo, botões "Exportar CSV"/"Nova Movimentação", contagem "Mostrando N registros de fluxo" e estado vazio intocados.

### V4 — Responsividade e temas (US2/AC-12/contract §3)

1. Desktop médio (768–1399px) e notebook (1024–1399px): proporções mantidas; sem sobreposição; sem quebras inadequadas.
2. Tablet (576–767px): adaptação; rolagem horizontal (se inevitável) confinada ao `table-responsive`; controles utilizáveis.
3. Celular (<576px): rolagem confinada (tabela larga de 9 colunas); sem conteúdo cortado indevidamente; ações acessíveis.
4. **Zoom 80% → 200%** (Chrome/Edge): mesmos critérios em toda a faixa (precedentes 036/037/038).
5. Tema claro e escuro: nenhuma diferença de contraste decorrente da alteração.

### V5 — Não-vazamento de escopo (FR-011/FR-015/contract §4–§5)

1. Tabelas da 036 (tela do inventário), 037 (listagem de inventários) e 038 (equipamentos) visualmente idênticas ao estado anterior; demais telas inalteradas.
2. Container da tela (page header, botões, filtro, card, contagem) inalterado.
3. `git diff` contendo **apenas** `app/web/templates/movements/list.html` (nenhum asset estático, nenhum `style.css`, nenhum `sw.js`).

## Registro

- Resultado de cada cenário registrado em `specs/039-movimentacoes-larguras-colunas/validacao.md` (SC-007) no formato das 036/037/038: baseline "antes", tabelas de larguras finais (com ajustes/motivos), resultado por cenário com medições e zoom, temas, observações preexistentes fora de escopo e decisões finas (ex.: quebra do badge de Tipo, se a medição exigir).
