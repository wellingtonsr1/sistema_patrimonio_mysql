# Contract — UI de Backup Manual (feature 015)

**Feature**: 015-backup-manual | **Data**: 2026-09-17

Contrato das rotas web, template e menu. Todas as rotas exigem **autenticação** (global) + **`backup.gerenciar`** (deny-by-default).

---

## 1. Rotas (novas em `admin_routes.py`, precedentes dos padrões existentes)

| Rota | Método | Descrição | Autorização |
|---|---|---|---|
| `/admin/backups` | GET | Tela de backups: listagem + botão de geração | `require_permission("backup.gerenciar")` |
| `/admin/backups/gerar` | POST | Aciona a geração; redirect de volta com confirmação | idem |
| `/admin/backups/{filename}/download` | GET | Serv o arquivo (FileResponse, attachment) | idem |

## 2. Template `admin/backups.html` (novo)

- Padrões visuais de Administração (Bootstrap 5, card de listagem, tooltips existentes).
- **Listagem**: tabela com colunas Arquivo (nome), Data/Hora (formatada, **UTC** — remediação I1; dica/tooltip indicando que o identificador segue UTC), Tamanho (formatado human-readable) — ordenada do mais recente; estado vazio amigável ("Nenhum backup gerado ainda").
- **Ação de geração**: botão "Gerar backup agora" (form POST) com confirmação nativa; estado de processamento simples (o dump é síncrono).
- **Download**: link/botão por linha → rota de download.
- **Mensagens**: sucesso (flash de confirmação com nome do arquivo); erro controlado (mensagem amigável, sem detalhes internos do subprocesso); 404/403 amigáveis existentes.

## 3. Menu (`base.html`)

- Item "Backups" no bloco **Administração**, condicionado a `can('backup.gerenciar')` (padrão dos itens existentes). Nenhum outro item é alterado.

## 4. Fluxos

1. **Geração**: usuário clica "Gerar backup agora" → POST `/admin/backups/gerar` → service cria + audita → redirect para `/admin/backups` com flash de sucesso (lista já contém o novo backup no topo). Falha → flash de erro controlado + auditoria da falha.
2. **Download**: GET com permissão → `FileResponse` (attachment, nome do arquivo) → auditoria do download. Nome fora do padrão ou arquivo ausente → 404 amigável, **sem** evento de auditoria de download (validação precede).

## 5. Navegação/segurança

- `filename` sempre validado pela regex estrita do padrão (path traversal impossível — R8).
- Nenhum dado de outra tela é alterado; nenhuma permissão existente é modificada.
