# Implementation Plan: Configurações de Backup em Modal

**Branch**: `022-modal-configuracoes-backup` | **Date**: 2026-09-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/022-modal-configuracoes-backup/spec.md`

## Summary

A feature 021 disponibilizou as configurações operacionais do backup pela interface: hoje o formulário "Configurações de Backup" vive na rota dedicada `/admin/backups/configuracoes` e a página principal `/admin/backups` acessa-o por um botão "Configurar". Este plano altera **somente a apresentação**: o formulário passa a viver dentro de um **Modal Bootstrap** na própria página de Backups, aberto por um **botão somente-ícone (⚙)** no canto superior direito, alinhado ao título "Backup Automático" (wrapper flex no `page-header` — padrão existente). O modal replica a **estrutura do Modal de Conferência do Bem** (`inventarios/detail.html`: `modal fade` → `modal-dialog` → `modal-content` → `modal-header` + `btn-close` → `modal-body` → footer; acionado por `data-bs-toggle`/`data-bs-target` — zero JavaScript novo). O `POST` continua apontando para a **rota existente** `/admin/backups/configuracoes` (validação backend → persistência → auditoria → redirect), que passa a redirecionar de volta para `/admin/backups` com `?success=`/`?error=` (mensagens no alerta do topo, padrão atual). **Achado técnico-chave**: a rota de listagem não pode chamar `get_backup_config(db)` porque ele **cria+commita** a linha singleton (efeito colateral de escrita em um GET que quebrou testes durante a 021). Solução mínima e aditiva: parâmetro `create: bool = True` em `get_backup_config`/`get_effective_config` — a listagem lê a efetiva **sem criar** nada (sem linha persistida → env/default, mesmo valor que uma primeira abertura mostraria). Nenhuma lógica de configuração, retenção, scheduler, RBAC ou auditoria é alterada.

## Technical Context

**Language/Version**: Python 3.10+ (runtime do projeto)

**Primary Dependencies**: FastAPI + Jinja2 + Bootstrap 5 + Bootstrap Icons (stack existente — modais já usados em `inventarios/detail.html` e `maintenances/list.html`; **nenhuma dependência nova**)

**Storage**: N/A — **zero alteração de banco** (a tabela `backup_config` da 021 já existe; nenhuma tabela/coluna/migration nova)

**Testing**: pytest (suíte existente 522 testes; TestClient para estrutura HTML/fluxos; validação visual em navegadores é manual — quickstart)

**Target Platform**: Linux e Windows (paridade herdada; mudança é somente template/service de leitura — sem plataforma nova)

**Project Type**: web-service (sistema existente, processo uvicorn único)

**Performance Goals**: N/A (mesma renderização atual; o modal é HTML server-rendered estático — sem fetch/JS)

**Constraints**: escopo mínimo (briefing §33/§34/§39): somente template + ajuste de leitura; **nenhum JS novo, nenhum CSS novo, nenhuma rota nova, nenhuma dependência nova**; o botão "Gerar backup" e o card "Backup Automático" permanecem na página (§12/§13); Cancelar não persiste (§11/§25); Salvar usa o mecanismo existente (§26); responsividade 320–1920 px e temas claro/escuro (§14/§15)

**Scale/Scope**: 1 template alterado (`backups.html` — seção vira modal + botão ⚙ no header) + 1 ajuste de rota (`admin_routes.py`: redirect do POST de volta para a listagem; contexto da listagem passa a incluir `config_form` **readonly**) + 1 ajuste aditivo e compatível no service (`backup_config_service.py`: parâmetro `create=False` para leitura sem efeito colateral) + testes + docs. Zero alteração em: scheduler, retenção, Restore, RBAC, auditoria, banco, demais telas.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Princípio | Status | Evidência |
|---|---|---|---|
| I | Preservação do sistema existente / evolução incremental | ✅ PASS | Mudança é apresentacional: a seção vira modal; funcionalidade, rota, campos e semântica preservados; nada removido além do botão "Configurar" que é substituído pelo ⚙ (transição da própria 021, prevista na spec) |
| II | Arquitetura em camadas | ✅ PASS | Template apenas apresenta; dados vêm do service; rota delega — nenhum negócio em template |
| III | Regras de negócio nos services | ✅ PASS | Único toque no service é **aditivo** (`create=False`) para leitura sem escrita — reutiliza a resolução de efetiva existente; nenhuma regra movida ou duplicada |
| IV | Integridade patrimonial/movimentações | ✅ PASS (N/A) | Nenhum bem/movimentação tocado |
| V | Integridade do inventário | ✅ PASS (N/A) | Nenhum fluxo de inventário tocado (o modal de Conferência é apenas **referência visual**) |
| VI | Segurança (auth, RBAC, AD, credenciais) | ✅ PASS | Mesma permissão `backup.gerenciar` no guard da página; POST direto continua 403; nenhum campo técnico/credencial exposto (campos são os mesmos da 021) |
| VII | Banco MariaDB e proteção dos dados | ✅ PASS | **Zero DDL**; adicionalmente, a leitura `create=False` **reduz** escritas acidentais em GET |
| VIII | Testes como requisito de não regressão | ✅ PASS | Testes novos para Testes A–H do briefing §28 (abrir/fechar/cancelar/salvar/valores/backup/retenção/auditoria) + estrutura do modal; suíte 522 permanece verde — nada removido/enfraquecido (testes que citam o botão "Configurar" são adaptados legitimamente) |
| IX | Auditoria das operações relevantes | ✅ PASS | Nenhuma mudança: `BACKUP_CONFIGURACAO_ALTERADA` continua gravado pelo fluxo existente (Teste H) |
| X | Interface consistente | ✅ PASS | Modal replica a estrutura dos modais existentes (`modalConferir`); classes Bootstrap + variáveis CSS de tema; **nenhum CSS/JS novo**; alinhamento via `d-flex justify-content-between` (padrão do projeto) |
| XI | Documentação fiel | ✅ PASS | README/help atualizados na mesma tarefa (a tela continua existindo; mudou a forma de acesso) |
| XII | Especificação e validação | ✅ PASS | Fluxo Spec Kit seguido; validação = suíte pytest + Testes A–H + validação visual manual (navegadores, 320–1920 px, claro/escuro) no quickstart |

**Veredito pré-Phase 0: 12/12 PASS**

## Project Structure

### Documentation (this feature)

```text
specs/022-modal-configuracoes-backup/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output — decisões R1–R5 (obtenção do config_form, estrutura do modal, redirect…)
├── data-model.md        # Phase 1 output — NENHUMA mudança de dados; forma do contexto config_form
├── quickstart.md        # Phase 1 output — Testes A–H (§28) + validação visual/responsiva manual
├── contracts/
│   └── service-contract.md  # Contratos: template (estrutura do modal), rotas, service (create=False), testes
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
app/
├── web/
│   ├── admin_routes.py          # Ajustes mínimos de rota (briefing §19 permite o indispensável):
│   │                            #   - POST /admin/backups/configuracoes redireciona para
│   │                            #     /admin/backups?success=|error= (modal vive na página principal)
│   │                            #   - GET /admin/backups passa config_form=get_effective_config(db, create=False)
│   │                            #   - GET /admin/backups/configuracoes MANTIDO (compatibilidade/links antigos)
│   └── templates/admin/
│       └── backups.html         # ÚNICA mudança estrutural:
│                                #   - botão ⚙ (somente ícone, aria-label/title) no page-header (flex)
│                                #   - card "Configurações de Backup" → modal Bootstrap (modalConferir-like)
│                                #   - campos idênticos (mesmos name=), footer Cancelar + Salvar
│                                #   - botão "Configurar" do card Backup Automático removido (substituído)
└── services/
    └── backup_config_service.py # Parâmetro aditivo create: bool = True em get_backup_config e
                                 #   get_effective_config (default True = comportamento atual em TODOS
                                 #   os chamadores); create=False → NUNCA cria/commita (leitura pura)

tests/
└── test_backup_config.py        # Testes novos 022 (estrutura do modal na listagem, ⚙, cancelar
                                 #   via template, POST inalterado, 403) + adaptação mínima dos
                                 #   testes 021 afetados (botão Configurar → engrenagem; valores
                                 #   agora verificados na página principal)

specs/022-modal-configuracoes-backup/
└── (docs da feature — quickstart valida Testes A–H e visual manual)
```

**Não alterados** (verificação explícita do briefing §37): `backup_scheduler.py`, retenção (lógica GFS), `backup_service.py`, `audit_service.py`, `config.py`, models, migrations, `base.html`, demais templates, RBAC/permissões, autenticação/AD, qualquer módulo patrimonial.

## Complexity Tracking

*Nenhuma violação constitucional — tabela vazia.*
