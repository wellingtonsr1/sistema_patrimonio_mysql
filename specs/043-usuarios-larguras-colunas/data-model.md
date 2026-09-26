# Data Model: Ajuste Responsivo da Tabela "Usuários do Sistema" (043)

**Sem entidades de dados novas ou alteradas.** Feature exclusivamente de apresentação: nenhum model, tabela, coluna, rota, permissão ou payload muda (FR-013/FR-014). Os dados exibidos (`User`: username, full_name, email, auth_provider, role_names, is_admin, is_active, last_login) e a rota `/admin/users` (`admin_routes.py:136`) permanecem intocados.

## Modelo de apresentação (única superfície afetada)

### Template `app/web/templates/admin/users/list.html` — tabela de usuários (7 colunas)

Larguras de partida (C-1; soma ≈ 1330px, coerente com 041/042; a medir/refinar). Textuais = **linha garantida** (ellipsis + tooltip Bootstrap — clarificações); rígidas = nowrap com pisos de fonte real.

| Col | Coluna | Conteúdo atual | Largura de partida | Regras de layout previstas |
|---|---|---|---|---|
| c1 | Usuário | username `fw-semibold` + ícone + badge condicional "ADMIN"; 2ª linha condicional `full_name` (`.text-muted`, .74rem) | ~150px | textual (FR-003): **ambas as linhas com linha garantida** — ellipsis + tooltip Bootstrap cada; ícone e badge ADMIN fora dos spans cortáveis |
| c2 | E-mail | `td.small.text-muted` — `u.email` ou "-" | ~200px | textual (FR-004): **linha garantida** — ellipsis + tooltip; maior coluna |
| c3 | Origem | badge "Active Directory" + ícone (`badge-soft-primary`) OU "Local" (`badge-soft-gray`) | ~120px | compacta (FR-005): badge íntegro; quebra apenas entre palavras se a coluna ficar estreita (lição 042 — `.badge` é nowrap por padrão) |
| c4 | Perfis | `div.d-flex.flex-wrap.gap-1` de badges `badge-soft-gray` por papel OU "Sem perfil" (`badge-soft-red`) | ~150px | (FR-006/C-6): **badges sem ellipsis** (dado funcional); organização entre badges via flex-wrap preservada; cada badge quebra só entre palavras se necessário |
| c5 | Status | badge "Ativo" (`bg-success-subtle`) OU "Bloqueado" (`badge-soft-red`) | ~90px | compacta (FR-007): badge íntegro em linha única |
| c6 | Último Acesso | `td.small.text-muted.text-nowrap` — `dd/mm/YYYY HH:MM` ou "Nunca" | ~150px | compacta/intermediária (FR-008): nowrap existente preservado; sem truncamento necessário |
| c7 | Ações | `td.text-end.text-nowrap` — "Editar Usuário" `btn-icon` condicional a `usuarios.editar` | ~70px | mínima (FR-009): 1 botão-icon; condições e alinhamentos preservados |

Textuais (Usuário+E-mail+Perfis) ≈ 500px de partida (maior bloco — SC-002); rígidas com folga ×1,25–1,30 (Plus Jakarta Sans; padding `.5rem .5rem` = 16px/coluna).

### Estrutura técnica prevista (mecanismo reusado das 036–042 + adaptações da 043)

- `<style>` embutido no topo do `{% block content %}` com comentário "Feature 043" (sem citar controles do header — lição `b75ba99`) e classe de escopo própria (ex.: `.usr-lista-table`).
- `table-layout: fixed; width: 100%; min-width: ~1330px` (único conjunto, sem media query de colunas — lição da 041) + `<colgroup>` com `<col class="cN">`.
- **Classe auxiliar de ellipsis** (ex.: `.usr-ellip`): `display:inline-block; max-width:100%; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; vertical-align:bottom` + `data-bs-toggle="tooltip" data-bs-placement="top"` — aplicada no username, no full_name e no e-mail.
- `white-space: normal` escopado para os badges desta tabela (`.usr-lista-table .badge`) — lição direta da 042 (o nowrap embutido do Bootstrap transborda células fixas com labels longos como "Active Directory"); os badges de Perfis permanecem sem ellipsis (C-6).
- `text-nowrap` existentes (Último Acesso, Ações) preservados.
- **Sem bloco de impressão** (R10 — tela não-relatório; nenhum `@media print` criado ou alterado).
- `table-responsive`, card, filtro e estado vazio preservados (FR-010).

### O que NÃO é tocado (fronteira da superfície)

| Elemento da mesma página | Motivo |
|---|---|
| `page-header` com "Novo Usuário" (condicional a `usuarios.criar`) | FR-010/FR-013: fora do escopo (comentários novos não citam esses nomes — lição `b75ba99`) |
| Card de busca/filtro (search + status_filter + Filtrar/Limpar) e contador "Mostrando N usuário(s)" | FR-010: fora do escopo |
| Estado vazio "Nenhum usuário encontrado" + CTA condicional | FR-010: intocado |
| Container global `base.html` (`container-fluid`, `max-width:90%`) | FR-010: não alterado |
| Condições Jinja dos dados (`is_admin`, `full_name`, `auth_provider`, `role_names`, `is_active`, `last_login`, `can('usuarios.editar')`) | FR-013/FR-014: lógica de dados intocada |
| `style.css`, `sw.js`, qualquer asset estático | Sem bump de cache global |
| Tabelas das specs 036 (conferência), 037 (inventários), 038 (equipamentos), 039 (movimentações), 040 (custodiantes), 041 (Relatório Contábil-Físico), 042 (Trilha de Auditoria) e demais telas | FR-015 |
