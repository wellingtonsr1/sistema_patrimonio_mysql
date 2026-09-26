# Contract de UI: Painel de Saúde da Central de Integrações (047)

Contrato de apresentação do painel `/admin/integracoes` (template `admin/integracoes/list.html`) — define o que a ampliação **não pode quebrar**. Nenhum contrato de API/dados muda nesta feature.

## §1 Contrato DOM (identificadores e atributos funcionais intocados)

| Identificador | Função |
|---|---|
| `GET /admin/integracoes` com `require_permission("integracoes.visualizar", web=True)` | Rota existente — **não muda** (o painel já itera o catálogo via `get_panel(db)`) |
| `div.row.g-3` > `div.col-*` por card > `div.card.h-100.shadow-sm` | Estrutura Bootstrap existente; classes de coluna mudam de `col-md-6 col-xl-6` para `col-md-6 col-xl-4` (3 colunas ≥1200px — FR-023) |
| `h2.h5` nome do componente + badge de status | Badge reutilizado: mapeamento atual ampliado com `ATENCAO` → `bg-warning text-dark` (mesma cor vigente do amarelo); demais badges preservados |
| `dl.row` (Última execução / Último sucesso / Falhas 24h / Pendentes) | Mantida para TODOS os cards (032); componentes de saúde exibem `—` onde não se aplica |
| `div` de pares `summary` (novo) | Renderiza `status_detail["summary"]` como `rótulo: valor` — ausente = não renderiza (comportamento padrão Jinja) |
| Botão "Detalhes" (`/admin/integracoes/{{ key }}`) | Preservado para todos os componentes |
| Form `POST /admin/integracoes/{{ key }}/testar` | Preservado; exibido somente quando `supports_test` e `can('integracoes.testar')` — `backup_externo` passa a exibir "Testar destino" (R4), email/onedoc mantêm "Testar conexão" |
| Botão "Configurar" (`card.config_route`) | Preservado; novo para storage/backup_local/backup_externo/scheduler → `/admin/backups` |
| Rodapé de atalhos (Voltar/AD/1Doc/E-mail) | Preservado; nota do GLPI atualizada sem remover conteúdo |

## §2 Contrato de conteúdo (nada exibido é removido; nada inventado)

1. Os 4 componentes existentes (E-mail, 1Doc, AD, GLPI) mantêm nome, descrição, finalidade e campos atuais.
2. Os 6 novos componentes (Aplicação, Banco de Dados, Armazenamento, Backup Local, Backup Externo, Agendador) entram com status derivado **somente** do estado real (data-model §4) — nunca status "decorado".
3. Resumo de uma linha por card (summary) com as informações úteis já disponíveis (próximo backup, último backup válido, espaço livre, destino externo, agendamento).
4. Estados "não configurado"/"desabilitado" claramente distintos de falha (badges cinza/escuro vs. vermelho).
5. Nenhuma credencial, token, senha ou segredo em qualquer card ou detalhe (mascaramento pelos mecanismos da 032).

## §3 Contrato de comportamento (Consulta × Teste)

| Ação | Comportamento exigido |
|---|---|
| Abrir a página (GET) | **Consulta apenas**: leitura de config/registros/`scheduler_status()`/`SELECT 1` trivial — 0 backups gerados, 0 testes SMTP/LDAP/destino, 0 threads (SC-002) |
| "Testar" (POST, ação explícita) | Apenas componentes com mecanismo: `email` (SMTP sem envio), `onedoc` (verificação interna), `backup_externo` (`test_destination` da 045 — sem gerar backup, sem deixar arquivos); `ad` mantém teste na tela própria com guarda vigente; `glpi` sem teste enquanto não configurada (R7) |
| "Atualizar" | Recarregamento da página (GET) — nenhum endpoint novo de verificação em massa (FR-025) |
| Falha de um componente | Card isolado em erro com mensagem sanitizada; demais 9 cards renderizam (R6/SC-007) |

## §4 Contrato responsivo e temas

- **Desktop grande (≥1200px)**: 3 colunas, ordem dos cards = catálogo (app, database, storage, ad, email, glpi, backup_local, backup_externo, scheduler, onedoc — mock do pedido §19).
- **Tablet (768–1199px)**: 2 colunas. **Celular (<768px)**: 1 coluna, empilhamento sem sobreposição.
- **Temas claro/escuro**: badges e cards reutilizados — contraste garantido pelos estilos vigentes; nenhum CSS novo.
- Grid, cards, badges e botões são os componentes existentes do sistema — nenhum segundo design system (FR-022).

## §5 Contrato de não-vazamento de escopo

- Alterações permitidas: `integration_center_service.py` (catálogo/status_fn/dispatcher/vocabulário), `list.html` (grid + summary + badge ATENCAO), `help_article_032.py`/docs, `tests/test_central_saude.py`.
- **Zero linhas alteradas**: `app/main.py` (`/health`), `backup_service.py`, `backup_scheduler.py`, `external_backup_service.py`, `ad_service.py`/`ad_ldap.py`, `email_provider.py`/`notification_service.py`, `onedoc_*`, `permission_service.py`, `admin_routes.py` (rotas já atendem), `detail.html`/`historico.html`/`movimentacao.html` (a menos que o detalhe precise listar summary — decisão da tasks).
- Nenhuma tabela/coluna nova; nenhuma permissão nova; nenhum CSS global novo; nenhum JS novo.
