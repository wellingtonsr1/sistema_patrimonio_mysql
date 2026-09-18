# Contract — UI v2 (feature 016)

**Feature**: 016-backup-manual-completo | **Data**: 2026-09-17

Única alteração de UI: colunas de integridade na listagem existente (`admin/backups.html`). Botões, fluxos, mensagens e componentes da 015: preservados.

---

## 1. Listagem (§18 do briefing)

| Coluna | Conteúdo |
|---|---|
| Arquivo | `backup_....sql.gz` (ou `.sql` antigo) — font-monospace |
| Data/Hora (UTC) | `dd/mm/AAAA HH:MM:SS` do nome |
| Tamanho | human-readable (KB) |
| **Integridade** (nova) | badge **OK** (verde) · **—** (neutro, `.sql` antigos) · **CORROMPIDO** (vermelho — gzip ilegível) |
| **SHA-256** (nova) | primeiros 12 hex + `…`, atributo `title` com o hash completo; "—" quando indisponível |
| Ações | Baixar (inalterado) |

## 2. Integridade (semântica exibida)

- **OK**: arquivo legível + checksum presente + gzip com trailer válido (§16).
- **—**: backup `.sql` anterior à 016 (sem checksum retroativo).
- **CORROMPIDO**: leitura/trailer do gzip falha — o arquivo **não** é removido automaticamente (retenção manual; §28 veda exclusão automática) e o download segue permitido (pode ser útil para diagnóstico), com o status visível.

## 3. Textos

- Subtítulo da página: passa a mencionar comprimidos (`.sql.gz`) e verificação SHA-256.
- Nenhum botão "Restaurar"/"Recuperar" (§29); nenhum agendamento (§30).

## 4. Preservações (015)

Tema claro/escuro, responsividade, page-header, alertas, botão "Gerar backup" com confirmação, mensagens por query param, menu com `can('backup.gerenciar')`.
