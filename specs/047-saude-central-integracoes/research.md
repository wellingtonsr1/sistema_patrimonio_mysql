# Research: 047 — Saúde da Central de Integrações

**Data**: 2026-09-26 · **Feature**: `047-saude-central-integracoes` · **Spec**: [spec.md](spec.md)

Todas as decisões abaixo partem de fatos verificados no código (leitura somente, 2026-09-26). Formato: Decisão → Racional → Alternativas consideradas.

---

## R1 — Vocabulário de status: nova constante `STATUS_ATENCAO`

**Decisão**: adicionar 1 constante aditiva `STATUS_ATENCAO = "ATENCAO"` (label "Atenção") ao vocabulário existente da Central, usada pelos novos componentes de saúde (Armazenamento com pouca espaço; Backup Local atrasado com agendador ativo). Badges: `bg-warning text-dark` — mesmo amarelo já usado por `INDISPONIVEL` no template.

**Racional**: a spec (§7) prevê ATENÇÃO/DEGRADADO no vocabulário amarelo, mas a 032 não definiu constante equivalente (só INDISPONIVEL para rede). Criar a constante evita sobrecarregar INDISPONIVEL (que tem semântica de rede/serviço inalcançável) e mantém a precedência de derivação limpa. Aditivo: nenhum status existente muda.

**Alternativas consideradas**: (a) reutilizar `STATUS_INDISPONIVEL` — rejeitada: mistura "sem espaço em disco"/"backup atrasado" com "serviço inalcançável", confundindo diagnóstico; (b) reutilizar `STATUS_COM_ERRO` — rejeitada: ATENÇÃO é estado intermediário, não falha; alarme falso.

---

## R2 — Rótulos específicos por componente (`label_by_status`)

**Decisão**: entrada opcional `label_by_status: dict` no catálogo declarativo. O `get_panel` resolve o rótulo como `label_by_status.get(status) or STATUS_LABELS.get(status)`. Exemplos: `app`: `{ATIVA: "Operacional"}`; `database`: `{ATIVA: "Conectado", COM_ERRO: "Falha"}`; `storage`: `{ATIVA: "OK", ATENCAO: "Espaço limitado", COM_ERRO: "Falha"}`; `backup_local`: `{ATIVA: "OK", ATENCAO: "Sem backup recente", COM_ERRO: "Falha"}`; `backup_externo`: `{ATIVA: "OK", DESABILITADA: "Desabilitado", NAO_CONFIGURADA: "Não configurado", COM_ERRO: "Falha"}`; `scheduler`: `{ATIVA: "Ativo", DESABILITADA: "Desabilitado", COM_ERRO: "Falha"}`.

**Racional**: o pedido (§3) pede vocabulário operacional por componente ("Operacional", "Conectado", "OK", "Ativo") sem quebrar o modelo padronizado da 032. A extensão declarativa mantém o contrato (status interno imutável) e atende FR-002 (sem alteração estrutural).

**Alternativas consideradas**: (a) mudar `STATUS_LABELS` global — rejeitada: quebraria os cards existentes (email/1doc/AD) que já usam os rótulos atuais; (b) template com `if key ==` — rejeitada: lógica de negócio em template (Constitution II/III).

---

## R3 — Resumo de uma linha por card (`summary`)

**Decisão**: cada `status_fn` retorna `detail["summary"]` como lista de pares `(rótulo, valor)` (máx. 3). O template lista os pares em uma `div.small` quando presentes; a `dl` existente (Última execução/Último sucesso/Falhas 24h/Pendentes) continua para todas as integrações. Componentes de saúde sem execuções mostram `—` nessas linhas (precedente da 032: ausência não é falha).

**Racional**: FR-003 pede resumo útil por componente (próximo backup, último backup válido, destino externo, espaço livre) que não cabe nos 4 campos fixos atuais; pares rotulados são genéricos e exigem só uma mudança de apresentação no template.

**Alternativas consideradas**: (a) campos fixos novos no card dict — rejeitada: a cada componente novo seria preciso acrescentar campos; pares rotulados escalam pelo catálogo; (b) só description — rejeitada: não atende FR-003.

---

## R4 — Teste do Backup Externo: reuso integral de `test_destination`

**Decisão**: o dispatcher `run_test` (032) ganha o ramo `backup_externo` que chama `external_backup_service.test_destination(config.dest_path)` — a **mesma função já usada pela tela da 045** (arquivo temporário `.backup_externo_teste.tmp` → grava com fsync → lê → valida → remove no `finally`). Registro via `record_execution` (op `OP_CONNECTION_TEST`) + `write_audit` existentes (`ACTION_CENTRAL_TESTE_*`), padrão idêntico aos ramos email/onedoc. Permissão: `integracoes.testar` (já é a guarda da rota POST da Central).

**Racional**: o pedido proíbe segundo mecanismo de teste de destino (§9/§15); a 045 já implementou o teste seguro (sem gerar backup, sem deixar arquivos, mensagens controladas). A Central apenas expõe a ação pelo painel.

**Alternativas consideradas**: (a) link "Testar destino" apontando para a tela da 045 — rejeitada: o pedido lista explicitamente o teste como ação da Central (§15), e o dispatcher da 032 existe exatamente para isso; (b) duplicar a lógica na Central — proibida (Constitution I/III).

---

## R5 — Fontes intocadas (comprobação de reuso)

**Decisão**: nenhum arquivo dos serviços fontes é alterado — as status_fn apenas **importam e consultam**:

| Componente | Fonte consultada (intocada) | O que a status_fn lê |
|---|---|---|
| `app` | — (semântica do `/health` de `app/main.py`) | Renderização da página = aplicação operacional; detail reapresenta o conceito, sem reexecutar verificação |
| `database` | `db` (sessão da request, mesma config `DATABASE_URL`) | `SELECT 1` com try/except — mesmo padrão do `/health` (consulta trivial, não é conexão nova) |
| `storage` | `BACKUP_DIR` (config/`backup_config`), `BackupExternalConfig` | `Path.exists()` + `shutil.disk_usage()` |
| `backup_local` | `BackupRecord`, `backup_scheduler.retention_monitoring_summary` | último backup, último válido, válidos, última falha |
| `backup_externo` | `BackupExternalConfig`, `BackupExternalRecord` | enabled/destino/última cópia/última falha |
| `scheduler` | `backup_scheduler.scheduler_status()` | enabled/agendamento/próximo run/último resultado/running |
| `ad`/`email`/`glpi`/`onedoc` | catálogo da 032 (já existente) | sem mudança de comportamento |

**Racional**: regra máxima do pedido (nenhum segundo mecanismo) + Constitution I. A única linha nova de código toca `integration_center_service.py` (catálogo/status_fn/dispatcher), `list.html` (apresentação), `help_article_032.py`/docs e `tests/`.

**Alternativas consideradas**: um service novo `system_health_service` — rejeitada: a Central já é a camada de observabilidade prevista (032 §2); service paralelo violaria o espírito do pedido.

---

## R6 — Isolamento por componente (painel à prova de falha)

**Decisão**: cada `status_fn` é escrita com try/except total; em exceção retorna `{"status": STATUS_COM_ERRO, "detail": {"summary": [("Erro", "Não foi possível verificar este componente")]}}`. O `get_panel` também protege a chamada individual (belt and suspenders), de modo que uma falha de um componente nunca impede a renderização dos demais (SC-007).

**Racional**: edge case da spec (§4) e risco identificado (§13): espaço em disco, disco de rede e consultas podem falhar por causas externas; o painel é de leitura e não pode derrubar a Administração.

**Alternativas consideradas**: deixar propagar e capturar na rota — rejeitada: perderia os cards restantes (página inteira em erro).

---

## R7 — P-2 detalhada: fonte do "tamanho do último backup válido"

**Decisão**: a regra do Armazenamento (clarify 2026-09-26) usa como referência `size_bytes` do **último `BackupRecord` com status SUCCESS e `removed_at IS NULL`** (consulta direta ao modelo — ordenado por `timestamp desc`). Sem backup válido de referência → status `ATIVA` com nota no card ("sem backup de referência para avaliar espaço"). `disk_usage` falhando (OSError/diretório ausente) → `COM_ERRO`. Espaço livre < referência → `ATENCAO`.

**Racional**: `retention_monitoring_summary` não expõe tamanho (só nome/momento); a consulta direta ao modelo é trivial e não cria duplicação de verdade (mesma tabela fonte). "Não cabe mais um backup" é a métrica operacional decidida no clarify.

**Alternativas consideradas**: somar tamanho dos backups do diretório via filesystem — rejeitada: I/O desnecessário e duplicaria informação já persistida (`size_bytes`); percentual fixo — rejeitada no clarify.

---

## R8 — Grid, ordem e atualização (P-3 + FR-023/FR-025)

**Decisão**:
- **Ordem do catálogo** (= ordem dos cards): `app`, `database`, `storage`, `ad`, `email`, `glpi`, `backup_local`, `backup_externo`, `scheduler`, `onedoc` — reflete o mock do pedido (3×3 de saúde + 1Doc fechando).
- **Grid**: mudar as classes de coluna de `col-12 col-md-6 col-xl-6` para `col-12 col-md-6 col-xl-4` (3 colunas ≥1200px; 2 em ≥768px; 1 no celular) — classes Bootstrap existentes, zero CSS novo.
- **"Atualizar"**: nenhum endpoint novo — a página é a própria consulta (GET); links/botões existentes preservados. Sem JS novo.
- **Rodapé**: manter os atalhos existentes (AD/1Doc/Notificações/Backups) e atualizar a nota do GLPI.

**Racional**: FR-023 pede 3 colunas em telas grandes na ordem do pedido; `col-xl-4` é o mecanismo Bootstrap padrão já vigente no projeto; "Atualizar" como recarregamento evita endpoint/meio de verificação em massa (§14 do pedido).

**Alternativas consideradas**: auto-refresh JS — rejeitada: JS novo sem necessidade e contraria "Atualizar = recarregar"; grid de 2 colunas — rejeitada: não reproduz o mock do pedido.

---

## Pendências resolvidas da spec

- **P-1** → R2/R8: keys `app`, `database`, `storage`, `backup_local`, `backup_externo`, `scheduler`.
- **P-2** → R7: fonte da referência de tamanho e comportamento sem backup válido.
- **P-3** → R8: ordem exata e classes de grid.
