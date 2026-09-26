# Research: Destino Externo para Backups (045)

Incógnitas resolvidas com fatos do repositório e as clarificações da spec (PRE_RESTAURACAO copiado; tabelas novas aditivas zero-ALTER; retry imediato limitado; sem retenção externa). Nenhum NEEDS CLARIFICATION restante.

## R1 — Onde engatar a cópia: gancho único em `generate_backup` (C-1)

**Decision**: a cópia externa é invocada **dentro de `BackupService.generate_backup`**, imediatamente após `_record_backup_success(...)` (L804) e antes do `return`, em `try/except` que **nunca propaga** exceção; o `return` ganha a chave `"external"` (status/motivo) para a tela.

**Rationale**: ponto único onde o arquivo já é final, validado (gzip legível) e possui SHA-256 — cobre manual, automático (scheduler chama o mesmo método) e pré-restauração (clarificação) **sem alterar nenhum chamador**; impossível copiar arquivo temporário/inválido (C-2 por construção); `dump_executor`/`_allow_during_restore` intocados.

**Alternatives considered**: *chamar nos dois chamadores (rota + scheduler)*: rejeitado — dois pontos para esquecer/quebrar; *hook no scheduler apenas*: rejeitado — não cobriria manual.

## R2 — Modelos: 2 tabelas novas aditivas (clarificações; §39; Constitution VII)

**Decision**: `BackupExternalConfig` (singleton id=1: `enabled` Bool default False, `dest_type` String(20) default "PASTA_REDE", `dest_path` String(255) nullable, `updated_at`, `updated_by`) e `BackupExternalRecord` (`filename` String(120) **UNIQUE** indexado, `backup_type` String(20), `status` SUCCESS|FAILURE, `copied_at` DateTime default now_utc, `size_bytes` Int nullable, `sha256` String(64) nullable, `error_description` String(255) controlado). Nenhuma coluna nova em tabelas existentes (`create_all` não faz ALTER — registros/config externos não podem viver em `backup_records`/`backup_config`).

**Rationale**: mesmo mecanismo da 020 (`create_all` idempotente em `init_db()`); funciona no MariaDB de produção sem migração manual; `filename` UNIQUE materializa "resultado final único por backup" (C-16); sem segredos (pasta montada não precisa credencial — C-4).

## R3 — Cópia atômica + validação (C-7/§12/§13/§33)

**Decision**: fluxo `copy_backup_to_external(filename, sha256_local, size_local, dest_path)`:
1. caminho validado (absoluto, não vazio; sem caracteres de controle; sem execução de shell);
2. verificação de espaço quando tecnicamente possível (`shutil.disk_usage(dest).free >= size`) — insuficiente → falha com motivo (§31);
3. destino inexistente → falha "destino indisponível" (nunca `mkdir` automático do NAS — a pasta montada é infraestrutura);
4. cópia streaming para `<dest>/.<filename>.tmp` (prefixo ponto — não parece backup válido; flush + `fsync`);
5. validação do temporário: tamanho == size_local **e** SHA-256 streaming == sha256_local;
6. idempotência: se o nome final já existe no destino, comparar hash — igual → sucesso (sem duplicar), diferente → falha (arquivo divergente);
7. `os.replace(tmp, final)` (atômico no mesmo filesystem);
8. qualquer divergência/erro → remover temporário, nunca deixar nome final com aparência de válido.

**Alternatives considered**: *copiar direto para o nome final*: rejeitado (§12 proíbe parcial visível); *validar depois do rename*: rejeitado — janela de arquivo inválido com nome definitivo.

## R4 — Retry imediato limitado + timeout (clarificação C-16; §34/§35)

**Decision**: `EXTERNAL_COPY_ATTEMPTS = 3`, `EXTERNAL_RETRY_WAIT_SECONDS = 2`, `EXTERNAL_COPY_BUDGET_SECONDS = 120` (por tentativa + orçamento total; constantes de módulo, **monkeypatcháveis nos testes**). Orçamento verificado por chunk durante a cópia (`time.monotonic`) — excedido → falha "tempo limite da cópia"; entre tentativas, espera curta; **resultado único final**: um `BackupExternalRecord` por `filename` (escrito uma única vez, ao final) + um evento de auditoria final. Após esgotar, re-tentativa só no próximo ciclo de backup (sem job de recuperação — contraria C-1).

**Rationale**: robustez para falha de rede transitória (opção B escolhida pelo solicitante) sem loops infinitos, sem bloquear além do orçamento total e sem duplicar registro por tentativa.

## R5 — Falha externa nunca afeta o local (C-8; FR-009)

**Decision**: `process_backup_after_success(result, backup_type)` encapsula tudo em try/except: lê config (desabilitado → `None`/no-op sem I/O externo); habilitado → retry/cópia/registro/auditoria; **qualquer exceção vira falha externa registrada**; `generate_backup` continua retornando o dict local de sucesso; a mensagem do local nunca é reescrita pela falha externa.

**Rationale**: Teste E/F exigem local preservado + aplicação íntegra; padrão já usado no serviço ("erro de metadados nunca invalida o arquivo físico").

## R6 — Cópia síncrona com orçamento (tradeoff documentado)

**Decision**: cópia síncrona no fluxo do chamador (rota web para manual; thread do scheduler para automático) com o orçamento total de R4 limitando o bloqueio.

**Rationale**: feedback imediato na tela ("Backup local: SUCESSO / Backup externo: ...", §15) sem polling novo; no automático o bloqueio é da thread do scheduler (protegida por lock — a cópia conta como parte do ciclo, mantendo a exclusão mútua correta); NAS local típico copia em segundos. Alternativa *thread separada*: rejeiada — exigiria consulta/refresh para status e uma segunda fonte de concorrência (§29).

## R7 — Auditoria e segredos (C-14/§26/§27/§28)

**Decision**: 4 constantes em `audit_service.py` seguindo o padrão literal existente: `ACTION_BACKUP_DESTINO_EXTERNO_CONFIGURADO = "BACKUP_DESTINO_EXTERNO_CONFIGURADO"`, `ACTION_BACKUP_DESTINO_EXTERNO_TESTADO = "BACKUP_DESTINO_EXTERNO_TESTADO"`, `ACTION_BACKUP_EXTERNO_SUCESSO = "BACKUP_EXTERNO_SUCESSO"`, `ACTION_BACKUP_EXTERNO_FALHA = "BACKUP_EXTERNO_FALHA"` (+ labels no dicionário). `new_data` contém: arquivo, backup_type, destino como **caminho configurado** (não é segredo), tamanho/sha256 em sucesso, motivo controlado em falha. Nenhum argv/shell: cópia 100% stdlib; teste de destino usa pathlib.

**Rationale**: nomes exatamente como o §26 sugeriu; `_sanitize_stderr`/`_dump_env` existentes ficam intocados (nada novo introduz segredo).

## R8 — Teste de destino (§24)

**Decision**: `test_destination(path)`: (1) configurado/não vazio; (2) existe e é diretório; (3) criação de arquivo temporário com prefixo ponto; (4) escrita + leitura de volta; (5) remoção; retorna (ok, mensagem controlada). **Sem backup completo**. Auditado como `BACKUP_DESTINO_EXTERNO_TESTADO` com resultado.

## R9 — Tela e rotas (C-5/§22/§23/§25)

**Decision**: `admin/backups.html` estendido: (a) fieldset "Backup externo" dentro do formulário existente de configurações (checkbox Ativado; tipo fixo "Pasta de rede/NAS" informativo; input `dest_path`; botão "Testar destino" em formulário próprio `POST /admin/backups/externo/testar`); (b) histórico: coluna "Externo" (✓ / ✗ com motivo no `title` / — para sem cópia), preservando tudo que existe; (c) card de status "Destino externo" (habilitado?, última cópia/tentativa e resultado — derivados do último `BackupExternalRecord`), sem confundir destino indisponível com backup local inválido. Rotas: POST `/configuracoes` também persiste o singleton externo (audita CONFIGURADO quando alterado) e POST `/externo/testar` (ambos gate `backup.gerenciar`); POST `/gerar` compõe o flash com local+externo. Sem tela nova, sem permissão nova.

## R10 — Restauração, pré-restauração e retenção intocados (C-10/C-11/C-12)

**Decision**: nenhuma alteração em `restore_backup`/pré-restauração — o backup pré-restore, por passar pelo mesmo `generate_backup`, **é copiado** (clarificação) sem mudar sua finalidade nem sua retenção local (`keep_pre_restore` local intocado). **Nenhuma retenção externa**: o destino nunca é varrido/excluído pelo sistema (limpeza operacional/manual); a retenção local continua preenchendo `removed_at` apenas local e nunca apaga a única cópia externa (não há código tocando o destino além do serviço de cópia).

## R11 — Concorrência e restore em andamento (§29/§30)

**Decision**: nenhuma trava nova: a cópia herda as proteções existentes (lock `_AUTO_LOCK` do ciclo automático; manual rejeitado durante automático — teste existente; geração rejeitada durante restore, exceto o pré-restore interno, cujo arquivo já está fechado e validado quando a cópia inicia). Sem corrida geração/cópia/retenção: cópia ocorre dentro do fluxo, **antes** de `_apply_retention_after_cycle` (que roda depois no scheduler).

## R12 — Testes (C-17/§36/§37)

**Decision**: `tests/test_backup_externo.py` cobrindo A–L: destino = `tmp_path` (pytest); retry/espera/orçamento encurtados via monkeypatch das constantes de módulo; falha de rede simulada por destino inexistente/permissão (`chmod 0o500` — Teste F) e hash adulterado injetando bytes divergentes (Teste G via monkeypatch do helper de hash/cópia no nível do serviço, sem tocar o arquivo local); duplicidade (Teste H) chamando o processamento duas vezes com o mesmo filename; reinicialização (Teste K) reabrindo sessão e confirmando persistência do singleton; desativação (Teste L) confirmando zero I/O no destino (contagem de entradas). RBAC: 403 sem `backup.gerenciar` em configurar/testar. Segredos: nenhuma operação introduz segredo (assert de ausência é estrutural — não há campo para segredo). Suíte existente permanece verde (regressão de manual/auto/config/records/restore/retenção).
