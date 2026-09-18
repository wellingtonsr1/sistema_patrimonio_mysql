# Contract — UI de Restauração (feature 017)

**Feature**: 017-restauracao-segura-backup | **Data**: 2026-09-17

Estende `app/web/templates/admin/backups.html` (nenhum template novo; nenhum item de menu novo — o restore vive dentro de Administração → Backups). Padrões visuais existentes preservados: Bootstrap 5, tema claro/escuro, ícones `bi-*`, `can()` para exibição condicionada.

---

## 1. Listagem (linha de cada backup)

- Nova coluna/ação **Restaurar** (botão `btn-outline-danger btn-sm`, ícone `bi-arrow-counterclockwise`) por linha, **apenas** renderizada se `can('backup.restaurar')`.
- Link: `GET /admin/backups/{{ b.filename }}/restaurar` (tela de informações — não executa).
- Restrição de exibição: ação visível para qualquer linha listada (a validação de integridade/estado ocorre no backend; linha `CORROMPIDO` pode ser clicada e receberá recusa informada — evita lógica de estado duplicada no template).
- Colunas/ordem/estilos da 016: inalterados.

## 2. Tela de informações (GET `/admin/backups/{filename}/restaurar`)

Cartão dentro do layout existente, sem execução de nada:

```text
Restaurar backup
Arquivo:        backup_20260917_203000_123456.sql.gz
Data/Hora (UTC): 17/09/2026 20:30:00
Tamanho:        30.0 KB
Integridade:    OK

ATENÇÃO (alert-danger):
• A restauração substituirá TODOS os dados atuais pelos dados deste backup.
• Antes da restauração, o sistema criará automaticamente um backup de segurança
  do estado atual, que permanecerá disponível.
• Sessões: após restaurar um backup, sessões abertas após a data deste backup
  deixam de ser válidas; sessões existentes na data do backup voltam a valer.

[ Cancelar ] (link para /admin/backups)   [ Continuar para confirmação ] (btn-danger)
```

- Se o backup estiver `CORROMPIDO`: banner de erro informando que a restauração não pode continuar e botão Continuar desabilitado (informação derivada da listagem; backend revalida de qualquer forma).
- Nunca inicia a restauração nesta etapa (FR-05).

## 3. Confirmação explícita (mesma tela, formulário POST)

- Formulário `method="post" action="/admin/backups/{filename}/restaurar"` com botão de envio:
  **"SIM, RESTAURAR BACKUP"** (`btn-danger`) + `onclick="return confirm('ATENÇÃO: esta ação substituirá todos os dados atuais. Um backup de segurança será criado antes. Confirmar a restauração?');"`.
- `confirm()` recusado → nada é enviado (cancelamento — Teste C).
- Estado de processamento: ao enviar, botão desabilitado (`disabled`) com texto "Restaurando…", evitando duplo clique (complementa o bloqueio backend FR-16).
- Botão **nunca** em formulário GET; envio só por POST (FR-08).

## 4. Mensagens pós-operação (flash redirect, padrão da 015)

| Resultado | Alerta | Conteúdo |
|---|---|---|
| Sucesso | `alert-success` | "Restauração concluída com sucesso." + backup restaurado + data/hora + **backup de segurança criado** (nome do arquivo) |
| Falha (validação do backup) | `alert-danger` | "Restauração não iniciada." + motivo seguro |
| Falha (backup de segurança) | `alert-danger` | "Restauração não iniciada: não foi possível criar o backup de segurança." |
| Falha (import/pós-restore) | `alert-danger` | "Restauração não concluída." + motivo seguro + orientação: "O backup de segurança do estado anterior permanece disponível na listagem para restauração manual." |
| Concorrência | `alert-warning` | "Já existe uma restauração em andamento. Aguarde a conclusão." |
| Sem permissão | (padrão 403 existente) | Nenhuma tela de restore é renderizada |

## 5. O que NÃO muda

- Tela/card de geração, listagem (colunas da 016), download, menu, navegação: intocados (exceto a coluna/ação Restaurar).
- Nenhum botão de exclusão de backups; nenhuma política de retenção; nenhum campo editável pelo usuário (arquivo vem da listagem; sem input de caminho).
