# Quickstart: Ajuste Responsivo da Tabela "Colaboradores & Custodiantes" (040)

Guia de validação ponta a ponta. Referências: [contract](contracts/ui-contract-tabela-custodiantes.md) · [data-model](data-model.md) · [spec](spec.md)

## Pré-requisitos

- Ambiente de dev rodando (`python run.py` — Windows: `python.exe .\run.py`); usuário **admin** (tem `colaboradores.editar` — valida o caso de 2 botões) e, se possível, um usuário sem essa permissão (valida 1 botão).
- Dados ideais: colaborador com **matrícula provisória** (badge "provisória" visível); nomes completos longos; cargos extensos ("Analista Administrativo", "Diretor Administrativo", "Assessor Técnico"); departamentos institucionais extensos; e-mails longos; contagens de bens variadas (0 e alta).
- Suíte de regressão: `python -m pytest tests/ -q` (100% verde antes e depois — SC-006).

## Como abrir a tela

**Colaboradores & Custodiantes** no menu (ou `/custodians`) — a tabela está no card central (usar a pesquisa se necessário para ver os dados ideais).

## Cenários de validação

### V0 — Baseline "antes" (seção 25 do pedido)

1. Antes da alteração: screenshot desktop + medição das larguras das 7 colunas (DevTools) registrada para comparação.

### V1 — Aproveitamento horizontal (US1/AC-01/SC-001/SC-002)

1. Desktop grande (≥1400px): tabela ocupa praticamente toda a largura útil do card (medição ≥95%).
2. Nome + Cargo + Departamento + E-mail dominam (juntas mais da metade — medição); Matrícula proporcional; Bens e Ações compactas.
3. Comparação antes/depois registrada (redistribuição, não "aumentar tudo").

### V2 — Conteúdos íntegros (FR-003..009/AC-11)

1. Matrícula completa sem quebra (badge `tag-badge` íntegro); badge "provisória" presente nas matrículas provisórias.
2. Nome longo legível (link com ícone) — **texto completo, sem corte**.
3. Cargo longo legível — **texto completo**.
4. Departamento extenso — **badge com texto completo**, sem clamp.
5. E-mail longo — **texto completo**, sem quebra em posição inadequada.
6. Pill de Bens íntegro e centralizado (testar contagem 0 e alta).
7. 2 botões de Ação (admin) sem aperto; usuário sem `colaboradores.editar` vê apenas "Ver Bens" e a coluna permanece estável.

### V3 — Alinhamento e funcionalidade (AC-09/AC-12/contract §1–§2)

1. Cada valor sob seu cabeçalho (7/7); Ações à direita (header e botões); Bens centralizado.
2. Links: nome → ficha do colaborador. Botões: Editar Colaborador → `/custodians/{id}/edit`; Ver Bens → ficha.
3. Pesquisa, botões do header e ambos os estados vazios intocados.

### V4 — Responsividade e temas (US2/AC-10/contract §3)

1. Desktop médio (768–1399px) e notebook (1024–1399px): proporções mantidas; sem sobreposição; sem quebras inadequadas.
2. Tablet (576–767px): adaptação; rolagem horizontal (se inevitável) confinada ao `table-responsive`; controles utilizáveis.
3. Celular (<576px): rolagem confinada; sem conteúdo cortado indevidamente; ações acessíveis.
4. **Zoom 80% → 200%** (Chrome/Edge): mesmos critérios em toda a faixa (precedentes 036–039).
5. Tema claro e escuro: nenhuma diferença de contraste decorrente da alteração.

### V5 — Não-vazamento de escopo (FR-010/FR-014/contract §4–§5)

1. Tabelas da 036 (tela do inventário), 037 (listagem de inventários), 038 (equipamentos) e 039 (movimentações) visualmente idênticas ao estado anterior; demais telas inalteradas.
2. Container da tela (page header, botões, pesquisa, card) inalterado.
3. `git diff` contendo **apenas** `app/web/templates/custodians/list.html` (nenhum asset estático, nenhum `style.css`, nenhum `sw.js`).

## Registro

- Resultado de cada cenário registrado em `specs/040-custodiantes-larguras-colunas/validacao.md` (SC-007) no formato das 036–039: baseline "antes", tabelas de larguras finais (com ajustes/motivos), resultado por cenário com medições e zoom, temas, observações preexistentes fora de escopo e decisões finas.
