# Data Model: 047 — Saúde da Central de Integrações

**Data**: 2026-09-26 · **Spec**: [spec.md](spec.md) · **Nenhuma tabela/coluna nova** (spec §10/FR-028)

Este documento descreve as **estruturas em memória** (catálogo + derivados) e a **derivação de status por componente** — tudo sobre dados existentes.

---

## 1. Estruturas existentes consultadas (fontes — nenhuma alterada)

| Estrutura | Arquivo | Campos usados pela 047 |
|---|---|---|
| `BackupRecord` | `app/models/backup_record.py` | `filename`, `backup_type`, `status` (SUCCESS/FAILURE), `timestamp`, `size_bytes`, `error_description`, `removed_at` |
| `BackupExternalConfig` | `app/models/backup_external_config.py` | `enabled`, `dest_type`, `dest_path` |
| `BackupExternalRecord` | `app/models/backup_external_record.py` | `filename`, `status`, `copied_at`, `size_bytes`, `error_description` |
| `BackupConfig` (via `scheduler_status`) | `app/models/backup_config.py` | lido pelo `backup_scheduler` (não diretamente pela 047) |
| `ADSettings` | `app/models/ad_settings.py` | `enabled`, `server`, `base_dn` (status_fn existente) |
| `EmailConfig`, `Notification` | `app/models/notification.py` | estado de e-mail (status_fn existente) |
| `OneDocIntegration` | `app/models/onedoc_integration.py` | PENDING/SENT/FAILED (status_fn existente) |
| `IntegrationExecution` | `app/models/integration_execution.py` | histórico unificado de testes (contadores da 032) |
| `audit_logs` | trilha existente | eventos `ACTION_CENTRAL_TESTE_*` (reutilizados) |
| Config ambiente | `app/config.py` | `AD_SERVER`/`AD_BASE_DN` (AD), `SMTP_HOST` (email), `BACKUP_DIR`/`DATABASE_URL` |

**Nenhuma entidade nova é persistida.** Os "novos" dados abaixo vivem apenas em memória, retornados pelas `status_fn` e consumidos pelo template.

## 2. Extensões em memória (sem persistência)

### 2.1 Vocabulário — 1 constante aditiva (R1)

```text
STATUS_ATENCAO = "ATENCAO"          # label: "Atenção" (badge bg-warning text-dark)
```

Estados existentes reutilizados sem mudança de significado: `NAO_CONFIGURADA`, `PENDENTE`, `DESABILITADA`, `ATIVA`, `COM_ERRO`, `INDISPONIVEL`, `INATIVA`.

### 2.2 Entrada do catálogo — campo opcional (R2/R3)

```text
{ ...campos atuais...,                       # key, name, description, purpose,
                                             # supports_test, supports_reprocess,
                                             # supports_enable_disable,
                                             # config_route, config_permission,
                                             # status_fn
  "label_by_status": {<status>: <label>},    # opcional; fallback STATUS_LABELS
  "test_label": "...",                       # opcional; fallback "Testar conexão"
                                             # (backup_externo → "Testar destino" — R4)
}
```

### 2.3 Derivado por card — campo novo (R3)

```text
status_detail["summary"] = [(rótulo, valor), ...]   # 0–3 pares; template lista quando presente
```

## 3. Catálogo ampliado (ordem = ordem dos cards — P-1/P-3)

| # | key | name | status_fn | supports_test | config_route | label_by_status (diferenças) |
|---|---|---|---|---|---|---|
| 1 | `app` | Aplicação | `_app_status_fn` | não | — | ATIVA→"Operacional" |
| 2 | `database` | Banco de Dados | `_database_status_fn` | não | — | ATIVA→"Conectado", COM_ERRO→"Falha" |
| 3 | `storage` | Armazenamento | `_storage_status_fn` | não | `/admin/backups` | ATIVA→"OK", ATENCAO→"Espaço limitado", COM_ERRO→"Falha" |
| 4 | `ad` | Active Directory | `_ad_status_fn` (existente) | não* | `/admin/ad` | — (mantém) |
| 5 | `email` | E-mail | `_email_status_fn` (existente) | sim | `/admin/notificacoes` | — (mantém) |
| 6 | `glpi` | GLPI | `_glpi_status_fn` (existente) | não | — | — (mantém) |
| 7 | `backup_local` | Backup Local | `_backup_local_status_fn` | não | `/admin/backups` | ATIVA→"OK", ATENCAO→"Sem backup recente", COM_ERRO→"Falha" |
| 8 | `backup_externo` | Backup Externo | `_backup_externo_status_fn` | **sim (R4)** | `/admin/backups` | ATIVA→"OK", COM_ERRO→"Falha" |
| 9 | `scheduler` | Agendador de Backup | `_scheduler_status_fn` | não | `/admin/backups` | ATIVA→"Ativo", DESABILITADA→"Desabilitado", COM_ERRO→"Falha" |
| 10 | `onedoc` | 1Doc | `_onedoc_status_fn` (existente) | sim | `/admin/integracao-1doc` | — (mantém) |

\* AD mantém o teste na tela própria com a guarda vigente (R7 — `run_test(ad)` permanece conduzindo, comportamento da 032).

## 4. Derivação de status por componente (única fonte de verdade: estado real)

### `app` — Aplicação
- **Fonte**: própria renderização da página (a request chegou = aplicação responde). Sem verificação ativa adicional.
- **Status**: `ATIVA` ("Operacional").
- **summary**: [("Estado", "Respondendo"), ("/health", "aplicação verificável via endpoint existente")] *(conceitual — o painel não chama o endpoint)*.

### `database` — Banco de Dados
- **Fonte**: sessão da request (mesma conexão/config do app — nenhuma conexão nova).
- **Método**: `db.execute(text("SELECT 1"))` com try/except (mesmo padrão do `/health` — consulta trivial); **apenas estado** (sem latência — clarify 2026-09-26).
- **Status**: sucesso → `ATIVA` ("Conectado"); exceção → `COM_ERRO` ("Falha").
- **summary**: [("Consulta", "OK") ou ("Erro", mensagem sanitizada curta)].

### `storage` — Armazenamento
- **Fonte**: `BACKUP_DIR`/config de backup +, se `BackupExternalConfig.enabled` e `dest_path`, o destino externo. Mecanismo: `Path.exists()` + `shutil.disk_usage` (padrão da plataforma, já usado pela 045).
- **Referência da regra (P-2/R7)**: `size_bytes` do último `BackupRecord` com `status=SUCCESS` e `removed_at IS NULL` (consulta direta, `timestamp desc`).
- **Status**:
  - nenhum diretório configurado → `NAO_CONFIGURADA`;
  - diretório inexistente ou `disk_usage` falhando (OSError) → `COM_ERRO` ("Falha");
  - espaço livre < referência → `ATENCAO` ("Espaço limitado");
  - sem backup válido de referência → `ATIVA` (summary registra "sem backup de referência");
  - caso geral → `ATIVA` ("OK").
- **summary**: [("Diretório", caminho), ("Livre", "X GB"), ("Último backup", "Y GB" ou "—")]. Nenhum arquivo de teste é gravado ao abrir a página.

### `backup_local` — Backup Local
- **Fonte**: `retention_monitoring_summary()` (`last_auto`, `last_valid`, `last_failure`, `valid_count`) + `scheduler_status()["enabled"]` (para o regime).
- **Status** (clarify 2026-09-26):
  - agendador **ATIVO**: nenhum backup válido → `COM_ERRO`; ciclo esperado passado sem backup novo (folga de 1 ciclo) → `ATENCAO`; caso geral → `ATIVA` ("OK");
  - agendador **DESABILITADO** (regime manual): última falha registrada → `COM_ERRO`; caso geral → `ATIVA` ("OK") — **sem alerta por atualidade**.
- **summary**: [("Último válido", dt + nome), ("Válidos no disco", N), ("Última falha", dt ou "—")].

### `backup_externo` — Backup Externo
- **Fonte**: `BackupExternalConfig` (enabled, dest_path) + `BackupExternalRecord` (última cópia/última falha — `copied_at desc`).
- **Status**: config ausente → `NAO_CONFIGURADA`; `enabled=False` → `DESABILITADA`; última cópia FAILURE (ou destino inacessível registrado) → `COM_ERRO`; cópia SUCCESS recente e nenhuma falha mais recente → `ATIVA` ("OK"); habilitado sem nenhuma cópia ainda → `INATIVA`.
- **Teste** (R4): `run_test(backup_externo)` → `test_destination(dest_path)` (função existente da 045; arquivo temporário gravado/lido/removido — nenhum backup gerado, nada deixado no destino).
- **summary**: [("Habilitado", "Sim/Não"), ("Destino", dest_path mascarado se muito longo), ("Última cópia", dt + status ou "—")].

### `scheduler` — Agendador de Backup
- **Fonte**: `backup_scheduler.scheduler_status()` (leitura direta; nenhum thread novo).
- **Status**: `enabled=False` → `DESABILITADA` ("Desabilitado"); `last_result` com erro → `COM_ERRO`; caso geral → `ATIVA` ("Ativo").
- **summary**: [("Agendamento", "daily/weekly HH:MM"), ("Próximo backup", dt local ou "—"), ("Último resultado", "Sucesso/Falha" ou "—")].

### Componentes existentes (032) — inalterados
`email`, `glpi`, `ad`, `onedoc` mantêm suas `status_fn`, testes e rótulos atuais (R7); apenas recebem as colunas/ordem do novo grid.

## 5. Transições de estado (resumo operacional)

Não há máquina de estados persistida: o status é **recomputado a cada consulta** a partir das fontes. As únicas transições "de verdade" continuam sendo as já existentes nos mecanismos fontes (ex.: novo `BackupRecord` após backup; novo resultado de cópia externa; teste manual registrado em `IntegrationExecution`).

## 6. Integridade e segurança

- Nenhuma credencial transita pelos novos campos: `summary` traz caminhos (com truncamento quando muito longos), contagens e datas — mensagens de erro sempre sanitizadas via `_sanitize_detail` (R6).
- Caminhos de destino no card: exibir o caminho é seguro (não é segredo — já visível na tela da 045 para quem tem permissão); truncar quando > ~40 chars para preservar o layout.
- Todos os horários em UTC armazenados (fontes existentes) e exibidos com `|localtime` (convenção 004).
