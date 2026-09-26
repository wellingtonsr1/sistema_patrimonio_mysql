# Contract: Destino Externo para Backups (045)

Contrato funcional da extensão — define interfaces internas (serviço/rotas/auditoria/tela) e o que a implementação **não pode quebrar**. Nenhum contrato público de API HTTP muda; tudo permanece atrás do RBAC existente.

## §1 Contract do serviço de cópia (`app/services/external_backup_service.py`)

```text
get_external_config(db) -> BackupExternalConfig            # singleton id=1 criado sob demanda (enabled=False)
save_external_config(db, *, enabled, dest_path, updated_by) -> BackupExternalConfig
test_destination(path: str) -> tuple[bool, str]            # §24: acesso+escrita+leitura+remoção de temporário; SEM backup
process_backup_after_success(result: dict, backup_type: str) -> Optional[dict]
    # Gancho ÚNICO chamado pós-_record_backup_success em generate_backup:
    #   - config desabilitada ou sem dest_path -> None (no-op, zero I/O externo)
    #   - habilitada -> cópia atômica com retry (R4) + BackupExternalRecord final + auditoria
    #   - NUNCA propaga exceção (C-8); retorno {"external_status": "SUCCESS"|"FAILURE",
    #     "external_reason": str|None} para composição do flash da tela
copy_backup_to_external(filename, sha256_local, size_local, dest_path) -> dict
    # R3: validar caminho -> espaço (quando verificável) -> tmp oculto + fsync ->
    #      validar tamanho+sha256 -> idempotência (nome existente igual=ok) ->
    #      os.replace -> limpar tmp em qualquer erro
```

**Invariantes**:
1. `process_backup_after_success` nunca levanta; nunca altera o resultado local.
2. Nenhum arquivo com nome definitivo aparece no destino sem cópia completa validada (C-7).
3. Um único `BackupExternalRecord` por `filename` (resultado final — retry não duplica).
4. Timeout por tentativa + orçamento total (constantes de módulo monkeypatcháveis).
5. Zero `shell=True`; zero segredos em qualquer operação (não há campo para segredo).

## §2 Contract de rotas (RBAC existente — nenhuma permissão nova)

| Rota | Método | Gate | Comportamento |
|---|---|---|---|
| `/admin/backups/configuracoes` | POST | `backup.gerenciar` | Também persiste o singleton externo (enabled/dest_path) quando presente no formulário; audita `BACKUP_DESTINO_EXTERNO_CONFIGURADO` quando a configuração é alterada; redirect com flash |
| `/admin/backups/externo/testar` | POST | `backup.gerenciar` | Testa `dest_path` submetido (§24 — sem backup); audita `BACKUP_DESTINO_EXTERNO_TESTADO`; redirect com flash de resultado |
| `/admin/backups/gerar` | POST | `backup.gerenciar` | Flash compõe **local + externo** (§15): "Backup local: SUCESSO / Backup externo: SUCESSO|FALHA (motivo)" |
| `/admin/backups` | GET | `backup.gerenciar` | Histórico com coluna "Externo" (✓/✗ motivo/—) + card de status do destino (§23) |

Rotas existentes de restaurar/download/status polling: **intocadas**.

## §3 Contract de auditoria (módulo existente; padrão literal PT)

| Evento | Quando | new_data (seguro) |
|---|---|---|
| `BACKUP_DESTINO_EXTERNO_CONFIGURADO` | config salva com alteração | enabled, dest_path, updated_by |
| `BACKUP_DESTINO_EXTERNO_TESTADO` | teste executado | dest_path, resultado, motivo |
| `BACKUP_EXTERNO_SUCESSO` | cópia validada | arquivo, backup_type, tamanho, sha256, destino |
| `BACKUP_EXTERNO_FALHA` | cópia falhou (resultado final) | arquivo, backup_type, motivo controlado, destino |

Labels PT no dicionário existente. **Nunca**: senha/credencial/token/segredo (não existe fluxo que os manipule — C-4).

## §4 Contract de tela (`admin/backups.html` — única; C-5)

1. **Configurações**: fieldset "Backup externo" no formulário existente — checkbox "Ativado" (default desmarcado), campo "Destino" (`dest_path`), tipo fixo informativo "Pasta de rede/NAS", botão "Testar destino" (form próprio para `/externo/testar`).
2. **Histórico**: nova coluna "Externo" — ✓ (sucesso), ✗ com motivo no `title` (falha), — (sem cópia/registro); todas as informações atuais preservadas (nome, data, tipo, status, integridade, tamanho, ações).
3. **Status**: card "Destino externo" — habilitado/desabilitado, última cópia/tentativa (`copied_at` do registro mais recente) e último resultado (SUCESSO/FALHA + motivo); **não confunde** destino indisponível com backup local inválido.
4. Estado vazio do card quando nunca houve cópia/tentativa.

## §5 Contratos de preservação (o que NÃO pode mudar)

1. Com externo **desabilitado**: zero I/O no destino, zero eventos externos, comportamento byte-a-byte igual ao atual (Testes A/B/L).
2. Dump único por execução (C-9); scheduler/lock/catch-up/proteção de restore intocados (FR-010).
3. Falha externa nunca: apaga/invalida o local, altera banco, propaga exceção, derruba scheduler/app (C-8).
4. Retenção local intocada; nenhuma rotina varre/apaga o destino (C-12).
5. `BackupRecord`/`BackupConfig` e demais tabelas: **zero ALTER**; dados existentes intocados.
6. RBAC: `backup.gerenciar` para configurar/testar; nenhuma permissão nova (C-13).
7. Nome do arquivo externo = nome do local (C-15).

## §6 Critérios de violação

1. Alguma exceção de cópia externa chegar ao usuário como erro do backup local ou derrubar o ciclo automático.
2. Arquivo com nome definitivo no destino sem cópia completa validada (parcial visível).
3. Dois registros externos para o mesmo `filename` (retry duplicando).
4. Cópia executada com externo desabilitado ou de arquivo inválido/temporário.
5. ALTER em tabela existente, dado existente alterado/apagado, ou novo scheduler/sistema de retenção.
6. Segredo em log/auditoria/argv (ou qualquer campo/fluxo que os introduza).
7. Rota nova sem gate `backup.gerenciar` (ou permissão nova criada).
8. Tela atual quebrada (histórico/config sem as informações existentes) ou segunda tela criada.
9. Suíte pytest existente vermelha; cenários A–L não executáveis.
10. Nome do arquivo externo divergente do local sem vínculo claro.
