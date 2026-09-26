# Implementation Plan: Destino Externo para Backups (Pasta de Rede/NAS)

**Branch**: `045-backup-destino-externo` | **Date**: 2026-09-26 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/045-backup-destino-externo/spec.md`

## Summary

Adicionar a dimensão **DESTINO (LOCAL | EXTERNO)** ao mecanismo de backup existente: após cada backup local **válido** (MANUAL, AUTOMATICO ou PRE_RESTAURACAO — clarificação), um novo serviço de cópia (chamado no ponto único pós-`_record_backup_success` em `generate_backup`) copia **atomicamente** o arquivo para uma **pasta de rede/NAS** configurável, valida a cópia por **existência + tamanho + SHA-256 idêntico ao local** e registra resultado em **tabelas novas aditivas** (zero ALTER) + **auditoria existente** (4 eventos novos no padrão `BACKUP_*`). Falha externa nunca afeta o local (timeout por tentativa, retry imediato limitado — clarificação, resultado final único). Configuração estende a tela existente de Configurações de Backup (Ativado/Tipo/Destino/"Testar destino"), default **DESABILITADO**, RBAC existente (`backup.gerenciar`), **sem novo scheduler, sem segundo dump, sem retenção externa automática** (clarificação), restauração externa fora de escopo. **Testes automatizados obrigatórios** (cenários A–L do pedido) — padrão distinto das features visuais 036–044.

## Technical Context

**Language/Version**: Python 3.10+ / FastAPI / SQLAlchemy 2 / Jinja2 / Bootstrap 5.3 (nenhuma dependência nova — cópia é stdlib: `shutil`/`gzip`/`hashlib`/`pathlib`)

**Primary Dependencies**: `BackupService.generate_backup` (gancho único pós-validação), `backup_scheduler` (intocado — herda a cópia pelo gancho), `audit_service.write_audit` + eventos literais, `admin_routes` (gates `backup.gerenciar`), `admin/backups.html`

**Storage**: **2 tabelas novas aditivas** (criadas por `Base.metadata.create_all` em `init_db()` — idempotente, **zero ALTER** em tabelas existentes, clarificações): `backup_external_config` (singleton id=1) e `backup_external_records` (resultado final por `filename`). Nenhum dado existente é tocado.

**Testing**: pytest — **novos testes obrigatórios** (`tests/test_backup_externo.py`, cenários A–L do pedido; destino externo = diretório temporário; constantes de retry/timeout injetáveis/monkeypatcháveis) + suíte existente 100% verde (regressão: backup manual/automático/config/records/restore/retenção)

**Target Platform**: servidor institucional com a pasta de rede/NAS **já montada no SO** (sem credenciais na aplicação — C-4); produção MariaDB

**Performance Goals**: cópia local de arquivo `.sql.gz` por rede local; tempo total da cópia limitado (timeout por tentativa + orçamento total); nenhuma alteração na duração do dump (dump único — C-9)

**Constraints**: alteração pequena e localizada (C-18); local obrigatório e anterior (C-2); cópia atômica com nome temporário (C-7); falha externa nunca propaga exceção nem invalida o local (C-8); zero segredos em logs/auditoria/argv (C-4/C-14); sem `shell=True` (cópia via stdlib, caminho validado); scheduler/lock/catch-up/proteção de restore intocados (FR-010); tela única estendida (C-5); nenhuma permissão nova (C-13)

**Scale/Scope**: 1 serviço novo (`external_backup_service.py`), 2 models novos, 1 gancho em `backup_service.generate_backup`, 4 constantes de auditoria, extensões em `admin_routes.py` + `admin/backups.html`, 1 arquivo de testes novo

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação | Status |
|---|---|---|
| I. Preservação do existente / escopo | Extensão por acoplamento no serviço existente; default OFF preserva o comportamento atual exatamente (SC-001); alteração localizada | ✅ PASS |
| II. Arquitetura em camadas | Cópia em serviço próprio (`external_backup_service`), chamado pelo serviço de backup; nenhuma regra em rota/template | ✅ PASS |
| III. Regras nos services | Toda a política (habilitado, retry, validação, atômica) vive no serviço novo | ✅ PASS |
| IV. Integridade patrimonial | Nenhum dado patrimonial alterado; só cópia de arquivo pós-validado | ✅ PASS |
| V. Integridade do inventário | Inventários intocados | ✅ PASS |
| VI. Segurança/RBAC | Gates existentes; nenhuma permissão nova; zero segredos em logs/auditoria/argv; caminho validado, sem shell | ✅ PASS |
| VII. Banco de dados | **Somente tabelas novas aditivas** (create_all idempotente, zero ALTER, sem tocar dados) — clarificações | ✅ PASS |
| VIII. Testes | **Testes novos obrigatórios** (A–L) + suíte existente verde | ✅ PASS |
| IX. Auditoria | Módulo existente reutilizado; 4 eventos novos no padrão literal; nunca segredos | ✅ PASS |
| X. Interface consistente | Tela existente estendida (fieldset + coluna Histórico + card de status); nenhuma tela nova | ✅ PASS |
| XI. Documentação fiel | `docs/ARQUITETURA_E_MANUTENCAO.md` descreve rotas/backup — atualizar endpoints/comportamento na implementação (task dedicada) | ✅ PASS |
| XII. Validação | Quickstart + validação A–L registrada em `validacao.md` + relatório final obrigatório (§43) | ✅ PASS |

**GATE: PASS (12/12)** — reavaliação pós-design ao final deste documento.

## Project Structure

### Documentation (this feature)

```text
specs/045-backup-destino-externo/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── contrato-backup-externo.md
├── checklists/
│   └── requirements.md  # Created by /speckit-specify + clarified by /speckit-clarify
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
app/
├── models/
│   ├── backup_external_config.py    # NOVO: singleton id=1 (enabled, dest_type, dest_path, rastreio)
│   └── backup_external_record.py    # NOVO: resultado externo final por filename (UNIQUE)
├── services/
│   ├── external_backup_service.py   # NOVO: config, test_destination, cópia atômica+validação, retry, registro
│   ├── audit_service.py             # +4 constantes ACTION_BACKUP_DESTINO_EXTERNO_*/BACKUP_EXTERNO_* + labels
│   └── backup_service.py            # +1 gancho pós-_record_backup_success (try/except não-propagante)
├── web/
│   ├── admin_routes.py              # ext. POST /configuracoes + POST /externo/testar; flash local+externo no /gerar
│   └── templates/admin/backups.html # fieldset "Backup externo" + botão Testar + coluna Externo + card status
tests/
└── test_backup_externo.py           # NOVO: cenários A–L + RBAC + segredos
```

**Structure Decision**: Serviço novo seguindo o padrão dos services existentes (sessão própria e curta para registros; auditoria nunca quebra o fluxo; descrições de erro controladas). O gancho único dentro de `generate_backup` garante C-1 (um mecanismo só) e cobre os três tipos de backup sem alterar chamadores; a cópia é **síncrona com tempo total limitado** (feedback imediato na tela, §15; no automático já roda em thread do scheduler) — tradeoff documentado em research R6.

## Complexity Tracking

> Nenhuma violação de Constitution a justificar.

**GATE pós-design: PASS (12/12)** — 2 tabelas aditivas (zero ALTER), 1 serviço novo reutilizando auditoria/RBAC existentes, 1 gancho localizado; scheduler/restore/retenção intocados; segredos fora da aplicação por design (pasta montada).
