# Quickstart: Ajuste Responsivo da Tabela "Usuários do Sistema" (043)

Guia de validação ponta a ponta. Referências: [contract](contracts/ui-contract-tabela-usuarios.md) · [data-model](data-model.md) · [spec](spec.md)

## Pré-requisitos

- Ambiente de dev rodando (`python run.py` — Windows: `python.exe .\run.py`); usuário **admin** (tem `usuarios.criar`/`usuarios.editar` — valida o header completo e o botão Editar) e, se possível, um usuário sem `usuarios.editar` (valida a coluna Ações estável).
- Dados ideais: usuário admin (badge ADMIN) e não-admin; usuário **com e sem `full_name`** (nomes completos longos); **e-mails longos** (ex.: `wellington.rodrigues@ipmjp.pb.gov.br`); usuário de **Active Directory** e Local; usuário com **múltiplos perfis** e um **sem perfil**; status Ativo e Bloqueado; usuário com **último acesso recente e com "Nunca"**.
- Suíte de regressão: `python -m pytest tests/ -q` (100% verde antes e depois — SC-006).

## Como abrir a tela

**Administração → Usuários do Sistema** (ou `/admin/users`) — a tabela está no card central (usar a busca se necessário para ver os dados ideais).

## Cenários de validação

### V0 — Baseline "antes" (seção 29 do pedido)

1. Antes da alteração: screenshot desktop + medição das larguras das 7 colunas (DevTools ou script local padrão 041/042 — research R11) + **contagem de quebras de linha por célula** registrada para comparação.

### V1 — Aproveitamento horizontal e linha única (US1/AC-01..AC-09/SC-001/SC-002)

1. Desktop grande (≥1400px): tabela ocupa praticamente toda a largura útil do card (medição ≥95%).
2. Usuário + E-mail + Perfis dominam o espaço (maior bloco — medição); Último Acesso intermediária; Origem, Status e Ações compactas.
3. **Linha única**: e-mail completo sem quebra; username e full_name em linhas únicas; badges íntegros; data/hora sem quebra; títulos em linha única.
4. Comparação antes/depois registrada (redução de quebras + redistribuição).

### V2 — Conteúdos íntegros e tooltips (FR-003..009/AC-02..AC-08/C-4)

1. **Tooltip Bootstrap** em username, full_name e e-mail quando truncados: hover exibe o valor **completo**.
2. Usuário: ícone + badge "ADMIN" (quando admin) íntegros ao lado do username; full_name como 2ª linha informativa preservada.
3. Origem: "Active Directory" com ícone íntegro (ou quebra apenas entre palavras se a coluna for estreita) / "Local" compacto.
4. Perfis: badges íntegros (nunca cortados), organizando-se entre si quando necessário; "Sem perfil" preservado.
5. Status "Ativo"/"Bloqueado" íntegros; Último Acesso `dd/mm/YYYY HH:MM` ou "Nunca" sem quebra.
6. Botão "Editar Usuário" funcional com tooltip próprio; usuário sem `usuarios.editar` vê a coluna Ações estável.

### V3 — Alinhamento e estabilidade (AC-10/contract §1–§2)

1. Cada valor sob seu cabeçalho (7/7); thead e tbody com a mesma estrutura.
2. Distribuição estável com massas diferentes (busca/filtro) — larguras não mudam por conteúdo.
3. Altura das linhas uniforme (linha garantida ⇒ 1–2 linhas informativas do Usuário, sem "escadinha").

### V4 — Responsividade e temas (US2/AC-11/contract §3)

1. Desktop médio (768–1399px) e notebook (1024–1399px): proporções mantidas; linha garantida com corte controlado; sem sobreposição.
2. Tablet (576–767px): rolagem horizontal (quando necessária) confinada ao `table-responsive`; 7 colunas acessíveis.
3. Celular (<576px): rolagem confinada funcional; ações acessíveis; valores truncados consultáveis.
4. **Zoom 80% → 200%** (Chrome/Edge): mesmos critérios em toda a faixa (precedentes 036–042).
5. Tema claro e escuro: nenhuma diferença de contraste decorrente da alteração.

### V5 — Não-vazamento de escopo (FR-010/FR-015/contract §5)

1. Tabelas das specs 036 (conferência), 037 (inventários), 038 (equipamentos), 039 (movimentações), 040 (custodiantes), 041 (Relatório Contábil-Físico) e 042 (Trilha de Auditoria) visualmente idênticas; demais telas inalteradas.
2. Container da tela (page header, filtro, contador, estado vazio) inalterado; **nenhuma mudança de impressão** (tela não-relatório).
3. `git diff` contendo **apenas** `app/web/templates/admin/users/list.html` (nenhum asset estático, nenhum `style.css`, nenhum `sw.js`).

## Registro

- Resultado de cada cenário registrado em `specs/043-usuarios-larguras-colunas/validacao.md` (SC-007) no formato das 036–042: baseline "antes" (com contagem de quebras), tabelas de larguras finais (com ajustes/motivos), resultado por cenário V1–V5 (com medições, zoom e **verificação de tooltips**), temas, observações preexistentes fora de escopo e decisões finas.
