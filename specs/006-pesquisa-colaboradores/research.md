# Phase 0 — Research & Decisions: 006-pesquisa-colaboradores

**Feature**: Pesquisa de Colaboradores | **Date**: 2026-09-16

> Toda decisão abaixo foi validada por leitura dos arquivos citados (16/09/2026).
> Não há unknowns de tecnologia — a decisão central (R1) resolve o ponto que a spec
> deixou para o plano (RT-003).

---

## R1 — Onde o filtro executa: servidor ou navegador? (RT-003)

- **Decision**: **Server-side** — o filtro vive em `CustodianService.get_all` (parâmetro
  opcional `search`) e a rota recebe `?search=` por formulário GET.
- **Rationale**:
  1. **Precedente do sistema**: a listagem de bens já pesquisa exatamente assim —
     `GET /assets?search=` → `AssetService.get_all(search=...)` com `or_` + `ilike`
     (`app/services/asset_service.py`), input com `input-group` + ícone `bi-search`
     (`assets/list.html` L47-48). Seguir outro padrão criaria uma divergência de UX/arquitetura
     (Constitution X: consistência).
  2. **Camadas**: a regra de filtragem fica na camada de serviço (Constitution II/III;
     RT-002 proíbe segunda lógica).
  3. **Desempenho (RT-003)**: a tela hoje carrega a lista completa sem paginação (verificado:
     a rota itera todos os colaboradores). Client-side exigiria drenar tudo para o DOM e filtrar
     em JS — volume no navegador **igual ou maior** que o atual. Server-side filtra no banco
     (ILIKE) e renderiza só o resultado; nenhuma consulta adicional (a contagem de bens já é
     calculada por colaborador visível, igual a hoje).
  4. **Sem JavaScript**: formulário GET funciona nos navegadores suportados sem JS novo (RT-005).
- **Alternatives considered**: filtro client-side em JS (rejeitado — segundo padrão de busca no
  sistema, regra em JS, volume de DOM); paginação server-side nova (rejeitada como pré-requisito:
  não existe hoje e introduzi-la é expansão de escopo — a spec veda alterar a estrutura da tela
  sem necessidade técnica comprovada; volume atual não a exige).

## R2 — Como estender `get_all` sem quebrar os chamadores existentes?

- **Decision**: parâmetro opcional **aditivo** `search: Optional[str] = None` em
  `CustodianService.get_all(db, active_only=False, search=None)`; `None`/vazio → consulta atual
  sem filtro (comportamento byte-idêntico ao de hoje).
- **Rationale**: os chamadores existentes continuam compilando e se comportando igual:
  a API REST `/api/v1/custodians` (`custodians_api.py:30`), as rotas de bens (`active_only=True`,
  `routes.py` L337/402/601/752) e importações. Nenhuma assinatura quebra (Constitution I).
- **Verificação**: `custodian_service.py:11-15` (assinatura atual); chamadores listados via grep.
- **Alternatives considered**: método novo `search_custodians` — rejeitado (RT-002: segunda
  lógica de consulta; divergência futura entre listagem e pesquisa).

## R3 — Quais campos entram na pesquisa combinada e como?

- **Decision**: 5 campos exibidos na tabela, todos com `ilike("%termo%")` dentro de `or_`:
  `registration_code` (matrícula), `name`, `role` (cargo), `department`, `email`.
- **Rationale**: espelha exatamente as colunas da tela (FR-001..RF-007) e o padrão do
  `asset_service`. `ilike` resolve o case-insensitive (FR-009) no banco; `%...%` resolve o
  parcial (FR-008). `strip()` no termo (edge case de espaços).
- **Alternatives considered**: normalização de acentos — rejeitada nesta feature (premissa 3
  da spec; melhoria futura); busca por campos não exibidos (CPF, telefone) — fora de escopo.

## R4 — Como o template distingue "sem cadastro" de "busca sem resultado"?

- **Decision**: três estados no template: (1) tabela com resultados; (2) `{% elif search %}` →
  "Nenhum colaborador encontrado." (busca sem correspondência — FR-010); (3) `{% else %}` →
  "Nenhum colaborador cadastrado" (estado atual da tela, preservado).
- **Rationale**: `search` chega ao template como string (`search or ""`); vazia = sem busca
  ativa. Distingue com precisão os dois estados vazios sem mudar o comportamento atual.
- **Verificação**: `custodians/list.html` L64-72 (bloco `empty-state` atual a preservar).

## R5 — Permissão e API REST

- **Decision**: rota mantém `require_permission("colaboradores.visualizar")` intacta; a API
  REST `/api/v1/custodians` **não** recebe o parâmetro nesta feature (escopo = tela web).
- **Rationale**: RN-002/FR-013 — a pesquisa reduz, nunca amplia, o universo visível; não há
  rota nova nem gate novo. A API de listagem segue funcionando sem alteração (R2) e, se o
  responsável quiser `search` na API depois, é extensão trivial do mesmo parâmetro do service
  (candidata a tarefa própria).
- **Alternatives considered**: adicionar `search` à API REST agora — rejeitada (fora do escopo
  da spec; evitar alteração de contrato não exigida).

## R6 — Caracteres especiais (`%`, `_`, aspas) no termo

- **Decision**: comportamento **idêntico ao da pesquisa de bens existente** — o termo segue
  como parâmetro vinculado (sem SQL concatenado; sem erro) e `%`/`_` funcionam como
  wildcards do `LIKE` (comportamento de banco, igual ao precedente).
- **Rationale**: consistência entre as duas telas de busca do sistema (o usuário já convive
  com esse comportamento em bens); escapar `%`/`_` aqui sem escapar lá criaria divergência
  sutil. Segurança mantida: bind parameters impedem injeção (aspas são literais).
- **Verificação**: `asset_service.py` (mesmo padrão `f"%{search.strip()}%"` sem escape).
- **Alternatives considered**: escapar `%`/`_` no custodian_service — rejeitada nesta feature
  (divergiria do precedente; seria melhoria cross-cutting em tarefa própria).

---

## Resumo de resolução de unknowns

| Ponto aberto (spec) | Resolução |
|---|---|
| RT-003 — onde o filtro executa | Server-side no service, via `?search=` (R1) |
| RT-001/RT-002 — reuso sem duplicação | Parâmetro aditivo no `get_all` existente (R2) |
| Campos pesquisáveis e case/parcialidade | 5 campos da tabela, `ilike %termo%` em `or_` (R3) |
| Estados vazios do template | 3 estados distintos; "Nenhum colaborador cadastrado" preservado (R4) |
| RN-002 / API REST | Permissão intacta; API fora do escopo desta feature (R5) |
| Caracteres especiais | Comportamento do precedente de bens (R6) |
