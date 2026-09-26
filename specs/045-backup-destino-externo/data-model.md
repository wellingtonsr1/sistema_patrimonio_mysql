# Data Model: Destino Externo para Backups (045)

**Nenhuma entidade existente é alterada.** Duas **tabelas novas aditivas**, criadas por `Base.metadata.create_all` em `init_db()` (idempotente, **zero ALTER** — clarificações; Constitution VII; §39). `BackupRecord`, `BackupConfig`, models de patrimônio, movimentações, inventários e usuários permanecem intocados.

## Entidades novas

### `BackupExternalConfig` — configuração do destino externo (singleton id=1, padrão BackupConfig/ADSettings)

| Campo | Tipo | Restrição | Semântica |
|---|---|---|---|
| `id` | Integer PK | sempre 1 | singleton |
| `enabled` | Boolean | NOT NULL, default **False** (FR-004) | cópia externa ativa |
| `dest_type` | String(20) | NOT NULL, default `"PASTA_REDE"` | único tipo nesta feature (FR-003); vocabulário controlado para extensão futura |
| `dest_path` | String(255) | nullable | caminho montado no SO (ex.: `/mnt/backup-sispatrimonio`); None/"" = não configurado |
| `updated_at` | DateTime | default/onupdate `now_utc()` | UTC naive (política 004) |
| `updated_by` | String(100) | nullable | username do administrador |

**Regras**: nenhum campo contém segredo (C-4 — pasta montada não exige credencial); caminho validado no serviço antes de uso (sem caracteres de controle; absoluta — sem traversal para fora do destino declarado).

### `BackupExternalRecord` — resultado externo FINAL por backup (clarificação C-16)

| Campo | Tipo | Restrição | Semântica |
|---|---|---|---|
| `id` | Integer PK | — | — |
| `filename` | String(120) | **NOT NULL UNIQUE**, indexado | mesmo nome do backup local (C-15); casa `_BACKUP_NAME_RE` |
| `backup_type` | String(20) | NOT NULL | MANUAL \| AUTOMATICO \| PRE_RESTAURACAO (cópia do tipo original) |
| `status` | String(10) | NOT NULL | SUCCESS \| FAILURE (vocabulário de `BackupRecord`) |
| `copied_at` | DateTime | NOT NULL, default `now_utc()`, indexado | momento do resultado final (última cópia/tentativa exibida na tela — §23) |
| `size_bytes` | Integer | nullable | tamanho validado no destino (SUCCESS) |
| `sha256` | String(64) | nullable | hash validado no destino (SUCCESS; igual ao local — FR-008) |
| `error_description` | String(255) | nullable | motivo controlado (FAILURE): "destino indisponível", "sem permissão de escrita", "espaço insuficiente no destino", "falha de integridade (sha256 divergente)", "tempo limite da cópia" — nunca segredos |
| `created_at` | DateTime | default `now_utc()` | rastreio |

**Regras**: **um único registro por `filename`** (resultado final único — retry não duplica; Teste H); a linha é escrita uma única vez ao fim do ciclo de cópia; nenhuma rotina edita/apaga registros (histórico imutável); a tela deriva o status do destino do registro mais recente.

## Relacionamentos e integridade

- Sem FK física — vínculo **lógico por `filename`** com `backup_records.filename` (mesmo padrão de desacoplamento da 020; FAILURE local usa nome projetado, mas **cópia externa só ocorre para SUCCESS local**, então o vínculo sempre existe para registros externos).
- `BackupExternalRecord` **não participa** da retenção local (que só preenche `removed_at` em `BackupRecord`): nenhuma rotina apaga registros externos ou arquivos do destino (C-12).
- Índice composto não necessário: consultas da tela usam `filename` (UNIQUE) e `copied_at` (indexado).

## O que NÃO é tocado (fronteira)

| Elemento | Motivo |
|---|---|
| `BackupRecord` (tabela/service de metadados locais) | zero ALTER (clarificação); fonte da verdade do local |
| `BackupConfig` (singleton 021) | config externa em tabela própria; sem misturar responsabilidades |
| Fluxo de geração (dump/gzip/hash/rename) e `_apply_retention_after_cycle` | apenas 1 gancho pós-sucesso (R1); dump único (C-9) |
| `restore_backup` / slot de restauração / pré-restauração | finalidade intocada (C-10/C-11) |
| Rotinas de retenção (GFS, anchors, `keep_pre_restore`) | intocadas; nunca tocam o destino (C-12) |
| Rotas/permissões existentes (`backup.gerenciar`/`backup.restaurar`) | apenas estendidas; nenhuma permissão nova (C-13) |
| `style.css`, `sw.js`, qualquer asset estático | sem alteração global |
