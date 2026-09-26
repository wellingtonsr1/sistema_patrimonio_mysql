# Validação: Destino Externo para Backups (045)

**Data**: 2026-09-26 · **Suíte**: `python -m pytest tests/ -q` → **748 passed** (baseline 728 + 20 novos de `tests/test_backup_externo.py`; duas rodadas completas consecutivas verdes)

Testes automatizados (C-17): destino externo de teste = diretório temporário (`tmp_path`); constantes de retry/espera/orçamento monkeypatchadas (R4); dump sempre FAKE (SQLite não roda mysqldump — padrão 015–020).

## Cenários A–L (quickstart §36)

| Cenário | Teste | Resultado | Verificação essencial |
|---|---|---|---|
| A — manual sem externo | `test_externo_desabilitado_manual_somente_local` | ✅ PASS | `external` = None; ZERO I/O no destino; zero registros/eventos externos |
| B — automático sem externo | `test_externo_desabilitado_automatico_somente_local` | ✅ PASS | idem no ciclo do scheduler (`_run_scheduled_backup`) |
| C — manual com externo | `test_manual_com_externo_copia_validada` | ✅ PASS | mesmo nome; sha256 idêntico; `BackupExternalRecord` único (MANUAL/SUCCESS, size+sha); auditoria `BACKUP_EXTERNO_SUCESSO` |
| D — automático com externo | `test_automatico_com_externo_copia_validada` | ✅ PASS | cópia no ciclo automático; registro com `backup_type=AUTOMATICO`; hash igual ao local |
| E — externo indisponível | `test_destino_indisponivel_local_preservado` | ✅ PASS | local SUCCESS íntegro no disco; falha registrada ("destino indisponível") + auditada (`BACKUP_EXTERNO_FALHA`); app responde |
| F — sem permissão de escrita | `test_destino_sem_permissao` | ✅ PASS | `chmod r-x` no destino → FALHA "sem permissão de escrita"; local preservado |
| G — integridade | `test_hash_divergente_copia_invalida` | ✅ PASS | hash divergente → FALHA "falha de integridade (sha256 divergente)"; nada publicado no destino |
| H — duplicidade | `test_sem_duplicidade_de_registro_e_copia` | ✅ PASS | reprocesso com mesmo filename → hash igual = sucesso idempotente; 1 registro (filename UNIQUE), 1 cópia |
| I — restauração | `test_restore_e_pre_restauracao_intactos` | ✅ PASS | ciclo 017/019 completo ok; pré-restauração COPIADO pelo gancho (clarificação); arquivo restaurado não gera cópia |
| J — retenção | `test_retencao_nao_toca_destino` | ✅ PASS | 2 ciclos com `_apply_retention_after_cycle` → destino recebe apenas as novas cópias; nada removido/varrido (C-12) |
| K — reinicialização | `test_config_persiste_apos_reinicializacao` | ✅ PASS | sessão nova reabre singleton id=1 (enabled/dest_path); `scheduler_status` íntegro |
| L — desativado novamente | `test_desativado_volta_somente_local` | ✅ PASS | após desativar, novo backup não é copiado; destino permanece com o estado anterior |

## Extras

| Verificação | Teste | Resultado |
|---|---|---|
| Atomicidade (C-7): tmp oculto nunca permanece; nome final só validado | `test_atomicidade_tmp_oculto_nao_permanece` | ✅ PASS |
| RBAC: 403 sem `backup.gerenciar` em configurar/testar (C-13) | `test_rbac_403_sem_backup_gerenciar` | ✅ PASS |
| "Testar destino" (§24): válido → success flash; inválido → error flash; auditado `BACKUP_DESTINO_EXTERNO_TESTADO` | `test_testar_destino_valido_e_invalido` | ✅ PASS |
| Persistência do singleton: salvar → recarregar página reflete (fieldset+card) | `test_config_salva_persiste_e_tela_reflete` | ✅ PASS |
| Flash composto local+externo em sucesso (§15) | `test_flash_gerar_composto_local_e_externo` | ✅ PASS |
| Flash composto com falha externa (local segue SUCESSO) | `test_flash_gerar_composto_com_falha_externa` | ✅ PASS |
| Coluna "Externo" no histórico (✓ / ✗ motivo no title / —) | `test_coluna_externo_no_historico` | ✅ PASS |
| Zero segredos em logs/auditoria nos cenários E/F/G (SC-007) | `test_zero_segredos_em_logs` | ✅ PASS |

## Verificação de auditoria (4 eventos novos)

- `BACKUP_DESTINO_EXTERNO_CONFIGURADO` — gravado ao salvar config com alteração (`test_config_salva_persiste_e_tela_reflete`).
- `BACKUP_DESTINO_EXTERNO_TESTADO` — gravado no teste de destino, SUCCESS e FAILURE (`test_testar_destino_valido_e_invalido`).
- `BACKUP_EXTERNO_SUCESSO` — gravado na cópia validada (cenários C/D; new_data: arquivo, backup_type, destino).
- `BACKUP_EXTERNO_FALHA` — gravado na falha final com motivo controlado (cenários E/F/G).
- Zero segredos: `test_zero_segredos_em_logs` varre `caplog` (DEBUG) e todas as descrições/new_data da auditoria contra padrões `senha/password/token/secret/credential` — nenhum vazamento.

## Suíte final

- `tests/test_backup_externo.py`: **20 passed**.
- Suíte completa: **748 passed** (728 pré-existentes 100% verdes — regressão manual/auto/config/records/restore/retenção + todas as demais; §37/SC-008).
- `git diff` revisado: nenhum ALTER em tabela existente; nenhum asset estático (`style.css`/`sw.js`) tocado; scheduler/restore/retenção sem alteração de lógica.

## Relatório final obrigatório (§43 do pedido)

**Arquivos novos**
- `app/models/backup_external_config.py` — singleton `backup_external_config` (id=1: `enabled` default False, `dest_type` "PASTA_REDE", `dest_path`, rastreio).
- `app/models/backup_external_record.py` — `backup_external_records` (resultado FINAL por `filename` UNIQUE; status/size/sha/motivo controlado).
- `app/services/external_backup_service.py` — `get_external_config`, `save_external_config`, `test_destination`, `copy_backup_to_external` (tmp oculto + fsync + sha256 + `os.replace`), `process_backup_after_success` (retry 3×/2s/orçamento 120s, registro único, auditoria, try/except total).
- `tests/test_backup_externo.py` — cenários A–L + RBAC + teste de destino + zero segredos.

**Arquivos alterados**
- `app/models/__init__.py` — imports dos 2 models novos (registro no `create_all`; zero ALTER).
- `app/services/audit_service.py` — 4 constantes `ACTION_BACKUP_*` + labels PT.
- `app/services/backup_service.py` — gancho ÚNICO em `generate_backup` imediatamente após `_record_backup_success`; chave aditiva `"external"` no retorno; try/except local nunca-propagante.
- `app/web/admin_routes.py` — POST `/configuracoes` persiste o singleton externo (campos `externo_enabled`/`externo_dest_path`); nova POST `/admin/backups/externo/testar` (gate `backup.gerenciar`, auditada); POST `/gerar` compõe o flash local+externo; GET `/admin/backups` fornece registros externos, último resultado e config do destino (leituras sem efeito colateral).
- `app/web/templates/admin/backups.html` — fieldset "Backup externo" no modal de configurações (checkbox Ativado desmarcado por padrão; tipo fixo "Pasta de rede/NAS"; input destino; botão Testar em form próprio), coluna "Externo" no histórico, card "Destino externo" com última cópia/tentativa e último resultado (estado vazio quando nunca houve).
- `tests/test_backup_manual.py` — 2 asserts de conjunto de chaves atualizados para incluir a chave `"external"` (contrato aditivo do plan T006).
- `specs/045-backup-destino-externo/tasks.md` — marcação de progresso.

**Configuração** — Singleton `backup_external_config` criado sob demanda por `create_all` (MariaDB de produção sem migração manual); default **DESABILITADO** (SC-001: comportamento atual byte-a-byte preservado); administrado na tela existente (RBAC `backup.gerenciar`, nenhuma permissão nova).

**Fluxo manual/automático** — Ambos passam pelo único gancho em `generate_backup` (R1): dump único (C-9), cópia síncrona com orçamento total (R4/R6), resultado externo apenas no flash/registros/auditoria; scheduler/lock/catch-up/proteção de restore intocados (FR-010).

**Integridade** — Cópia validada por existência + tamanho + SHA-256 idêntico ao local; idempotência por hash quando o nome final já existe; temporário oculto (`.filename.tmp`) removido em qualquer erro; nome definitivo só existe com cópia completa validada (C-7).

**Falhas** — Motivos controlados: "destino indisponível", "sem permissão de escrita", "espaço insuficiente no destino", "falha de integridade (sha256 divergente)", "tempo limite da cópia"; nenhuma exceção externa propaga (C-8 — comprovado pelos cenários E/F/G com app íntegra e local SUCCESS); nenhuma credencial existe no fluxo (C-4 — pasta montada; zero `shell=True`).

**Auditoria** — 4 eventos novos no padrão literal PT + labels; ator sistema (None) nas cópias pós-fluxo; `updated_by`/username preservado nas configurações/testes; zero segredos verificado por teste automatizado.

**Testes** — 20 novos (A–L, RBAC, teste de destino, persistência, atomicidade, flash composto, coluna Externo, zero segredos); suíte completa 748 passed, duas rodadas consecutivas.

**Limitações reais**
1. NAS real não existe em dev: validação com diretório local (`tmp_path`), comportamento idêntico a pasta montada (C-4); aceite final em produção com o NAS montado.
2. Segredos são estruturalmente ausentes (nenhum campo/fluxo os introduz); a evidência automatizada cobre logs/auditoria nos cenários de falha.
3. Re-tentativa após esgotar o orçamento ocorre apenas no próximo ciclo de backup (sem job de recuperação — C-1/clarificação).
4. Nenhuma retenção externa: limpeza do destino é operacional/manual (C-12) — a tela não gerencia o conteúdo do NAS.
