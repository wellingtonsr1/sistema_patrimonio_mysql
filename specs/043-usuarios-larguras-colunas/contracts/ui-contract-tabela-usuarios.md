# Contract de UI: Tabela de Usuários do Sistema (043)

Contrato de apresentação da tabela em `app/web/templates/admin/users/list.html` — define o que a mudança de larguras **não pode quebrar**. Nenhum contrato de API/dados muda nesta feature.

## §1 Contrato DOM (Jinja/Bootstrap/template — identificadores e atributos funcionais intocados)

| Identificador | Função |
|---|---|
| `div.fw-semibold` (Usuário, 1ª linha) com `i.bi-person-circle` + badge condicional "ADMIN" (`{% if u.is_admin %}`) | Identidade do usuário; ícone e badge ADMIN preservados (badge fora de qualquer span cortável) |
| `div.text-muted` condicional (`{% if u.full_name %}`, .74rem) | Nome de exibição como 2ª linha informativa (condição e estilo preservados) |
| `td.small.text-muted` (E-mail) com fallback `u.email or '-'` | E-mail (classe/fallback preservados) |
| Badge de Origem: `badge-soft-primary` + `bi-hdd-network` "Active Directory" (`{% if u.auth_provider == 'ad' %}`) OU `badge-soft-gray` "Local" | Condição/ícone/classes preservados |
| `div.d-flex.flex-wrap.gap-1` com loop de badges (`{% for r in u.role_names %}`) OU "Sem perfil" (`badge-soft-red`) | Perfis (estrutura flex e condição preservadas; badges sem ellipsis) |
| Badge de Status: `bg-success-subtle text-success` "Ativo" OU `badge-soft-red` "Bloqueado" (`{% if u.is_active %}`) | Condição/classes preservadas |
| `td.small.text-muted.text-nowrap` (Último Acesso) com `localtime` e fallback "Nunca" | Data/hora em linha única (classe existente preservada) |
| `td.text-end.text-nowrap` (Ações) com "Editar Usuário" `btn-icon` condicional a `{% if can('usuarios.editar') %}` | Ação condicional (condição Jinja e tooltip existente preservados) |
| `.table-responsive` envolvendo a tabela | Contêiner de rolagem (rolagem confinada quando inevitável) |
| page-header ("Novo Usuário" condicional a `usuarios.criar`), card de busca/filtro, contador, estado vazio | Fora do escopo — intocados; **comentários CSS/HTML novos não citam controles** (lição `b75ba99`; `test_rbac.py:213/221` valida strings de link nesta página) |

## §2 Contrato de conteúdo (FR-014 — nada exibido é removido; C-4: nada oculto sem consulta)

Por linha da tabela, TODOS estes elementos permanecem renderizados como hoje:

1. Username com ícone + badge "ADMIN" quando aplicável.
2. `full_name` quando houver.
3. E-mail (ou "-") — **acessível por tooltip** quando visualmente truncado.
4. Badge de origem "Active Directory" (com ícone) ou "Local".
5. Badges de perfis (ou "Sem perfil").
6. Badge de status "Ativo"/"Bloqueado".
7. Último acesso `dd/mm/YYYY HH:MM` ou "Nunca".
8. Botão "Editar Usuário" quando houver permissão.

## §3 Contrato de comportamento responsivo (FR-012/C-4)

| Viewport | Comportamento exigido |
|---|---|
| Desktop grande (≥1400px) | Tabela ocupa praticamente toda a largura útil do card; textuais (Usuário/E-mail/Perfis) dominam; valores predominantemente em linha única (com corte controlado + tooltip quando excedem) |
| Desktop médio (768–1399px) | Mesmas proporções relativas; sem sobreposição; linha garantida mantida com corte controlado |
| Notebook (1024–1399px) | Leitura confortável; e-mails/nomes/datas íntegros ou com tooltip |
| Tablet (576–767px) | Rolagem horizontal (quando necessária) confinada ao `table-responsive`; todas as 7 colunas acessíveis |
| Celular (<576px) | Rolagem confinada (mecanismo do projeto); sem fonte reduzida excessivamente; sem conteúdo cortado sem consulta; ações acessíveis |
| Zoom 80%–200% | Mesmos critérios de legibilidade, linha única e ausência de sobreposição (precedentes 036–042) |

## §4 Contrato de tooltips e badges (específico da 043 — clarificações/C-6)

- Tooltip Bootstrap (`data-bs-toggle="tooltip" data-bs-placement="top" title="..."`) em **username, full_name e e-mail** — sempre com o valor completo; sem JS novo (inicialização existente em `base.html:329–333`/`main.js`).
- **Nenhum badge recebe ellipsis** (Perfis/Origem/Status são dados funcionais): badges podem quebrar apenas entre palavras quando a coluna for estreita (`.usr-lista-table .badge { white-space: normal; }` — lição da 042), permanecendo legíveis.
- Os controles do header e o botão de editar **não são afetados**.

## §5 Contrato de não-vazamento de escopo (FR-010/FR-015)

- CSS novo **escopado** à tabela de usuários (classe dedicada + `<style>` embutido): nenhuma outra tabela/página herda regra nova; nenhuma classe genérica.
- Container da tela (page header, filtro, contador, estado vazio) **inalterado**; nenhum `@media print` criado ou alterado (tela não-relatório — R10).
- `git diff` contendo apenas `app/web/templates/admin/users/list.html` (nenhum asset estático, nenhum `style.css`, nenhum `sw.js`).
- Tabelas das specs 036 (inventarios/detail.html), 037 (inventarios/list.html), 038 (assets/list.html), 039 (movements/list.html), 040 (custodians/list.html), 041 (reports/inventory.html), 042 (reports/movements_report.html) e demais telas intocadas.

## §6 Critérios de violação do contrato

O contrato é violado se, após a alteração:

1. O badge "ADMIN", a linha `full_name`, o ícone de Origem, os badges de Perfis/Status ou o fallback "Nunca" deixarem de renderizar.
2. Username, full_name ou e-mail ficarem truncados **sem tooltip** com o valor completo (C-4).
3. Algum badge (Perfis/Origem/Status) quebrar no meio de uma palavra.
4. A condição do botão "Editar Usuário" deixar de respeitar `usuarios.editar` (ou o botão sumir/quebrar).
5. Cabeçalhos desalinharem do corpo (thead ≠ tbody).
6. Outra tabela/tela mudar de aparência (inclusive 036–042).
7. `style.css` ou `sw.js` forem modificados, ou o container/filtro/estado vazio mudarem.
8. Alguma regra de autenticação/RBAC/AD mudar (FR-013) — a alteração é exclusivamente visual.
9. A página lançar erro de template (suíte pytest detecta via `test_rbac.py`/`test_help.py`/testes do domínio).
10. Um comentário CSS/HTML citar o nome de um controle e um teste RBAC de template falhar (lição `b75ba99`).
