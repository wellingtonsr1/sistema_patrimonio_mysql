# Implementation Plan: Integração 1Doc — Comunicação Automática de Movimentações

**Branch**: `031-integracao-1doc` | **Date**: 2026-09-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/031-integracao-1doc/spec.md`

## Summary

Após a conclusão e persistência de uma movimentação elegível (cautela ou transferência de local — Q1), o SisPatrimônio inclui automaticamente uma **comunicação no processo 1Doc existente** informado pelo operador no ato da movimentação, com a tabela do modelo do setor (Descrição do Material / Tombamento / Origem / Destino) gerada dos dados oficiais. A integração é **pós-commit, best-effort e idempotente** (mesmo padrão da 030): falha do 1Doc jamais afeta a movimentação. Estado próprio por movimentação (`onedoc_integrations`), reprocessamento manual com permissão dedicada, auditoria `INTEGRACAO_1DOC_*`, configuração `ONEDOC_*` por ambiente. **A API 1Doc é pendência externa documentada** (Fase 1): o cliente HTTP real é isolado atrás de um provider com interface estável; os endpoints são conectados quando o contrato do fornecedor chegar — até lá a integração nasce **desativada** (`ONEDOC_ENABLED=false`).

## Technical Context

**Language/Version**: Python 3.10+ (existente)

**Primary Dependencies**: FastAPI + SQLAlchemy 2 + Pydantic v2 + Jinja2 (existente); **`requests` já está em `requirements.txt`** — **zero dependências novas**

**Storage**: MariaDB/MySQL (produção) via `DATABASE_URL`; SQLite apenas na suíte de testes — **1 tabela nova** (`onedoc_integrations`) criada por `create_all` (precedentes `backup_records`/020 e `notifications`/030); zero DDL destrutivo

**Testing**: pytest (existente; baseline 617 passed / 1 failed pré-existente ambiental) — fakes de provider, nunca API real

**Target Platform**: Windows e Linux (servidor do órgão)

**Project Type**: Web application (FastAPI monolito em camadas — Constitution II)

**Performance Goals**: chamada externa nunca ultrapassa o timeout configurado (default 10 s); resposta da movimentação ao usuário não é atrasada além disso (SC-004)

**Constraints**: integração **desativada por padrão**; movimentação imune a falha do 1Doc (SC-002: 0 reversões); idempotência estrutural (SC-003: 0 duplicatas); credenciais somente em `.env` (SC-005)

**Scale/Scope**: 1 comunicação por movimentação elegível; volume esperado de movimentações do órgão (dezenas/dia) — sem necessidade de fila/worker nesta versão

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Princípio | Avaliação | Status |
|---|---|---|---|
| I | Preservação do sistema existente | Tudo aditivo: 1 tabela nova, 1 campo opcional no schema, hook pós-commit estendido; com `ONEDOC_ENABLED=false` (default) o comportamento é **byte-idêntico** ao atual; e-mail 030 intocado (FR-015) | PASS |
| II | Arquitetura em camadas | Orquestração em `onedoc_service.py`, HTTP isolado em `onedoc_client.py`, conteúdo puro em `onedoc_message.py`; rotas apenas coletam o campo e delegam | PASS |
| III | Regras de negócio nos services | Validação de processo obrigatório (FR-002) e regras de elegibilidade (Q1) em `movement_service`/`onedoc_service`, não nas rotas | PASS |
| IV | Integridade patrimonial | Nenhuma regra de movimentação alterada; validação nova só ativa com integração habilitada; movimentação nunca revertida (FR-007) | PASS |
| V | Integridade do inventário | Não aplicável (sem interação com inventário) | PASS |
| VI | Segurança (auth, RBAC, AD) | Credenciais `ONEDOC_*` só em ambiente; token sanitizado em erros (precedente 030); permissão nova `integracao1doc.reprocessar` **sem concessão default** (Q4); rotas novas com `require_permission` | PASS |
| VII | Banco MariaDB | Tabela nova via `create_all` idempotente; nenhum ALTER/drop em estruturas existentes | PASS |
| VIII | Testes como não regressão | Novos testes com fakes; suíte existente deve permanecer verde; lote CSV continua sem interação externa | PASS |
| IX | Auditoria | 4 eventos `ACTION_INTEGRACAO_1DOC_*` no padrão `write_audit`, `user=None` nos automáticos (precedente 020/030), sem segredos | PASS |
| X | Interface consistente | Campo do processo só nos formulários elegíveis (Q5); tela admin mínima segue padrão 021/030; menu via `can()` | PASS |
| XI | Documentação fiel | README, ARQUITETURA_E_MANUTENCAO e artigo na `/ajuda` atualizados na mesma tarefa | PASS |
| XII | Spec-driven + validação | Fluxo Spec Kit seguido; validação final com suíte + escopo + quickstart | PASS |

**GATE: 12/12 PASS (pré-design). Reavaliado após Phase 1: 12/12 PASS.**

## Project Structure

### Documentation (this feature)

```text
specs/031-integracao-1doc/
├── plan.md              # This file
├── research.md          # Phase 0 output — decisões + PENDÊNCIA EXTERNA (API 1Doc)
├── data-model.md        # Phase 1 output — entidade OneDocIntegration
├── quickstart.md        # Phase 1 output — validação ponta a ponta
├── contracts/
│   └── onedoc-contract.md  # Phase 1 output — contratos dos caminhos afetados
└── tasks.md             # Phase 2 output (/speckit-tasks) — NÃO criado aqui
```

### Source Code (repository root)

```text
app/
├── config.py                        # +ONEDOC_* (padrão SMTP_*; ENABLED=false default)
├── models/
│   ├── __init__.py                  # +import do model novo (registro no create_all)
│   └── onedoc_integration.py        # NOVO: OneDocIntegration (UNIQUE movement_id)
├── schemas/
│   └── movement.py                  # +onedoc_process_number: Optional[str] (aditivo)
├── services/
│   ├── movement_service.py          # +validação FR-002 (condicional), +hook 1Doc pós-commit
│   ├── onedoc_message.py            # NOVO: saudação (P-2) + tabela 4 colunas (funções puras)
│   ├── onedoc_client.py             # NOVO: protocolo OneDocProvider + OneDocHttpClient (requests)
│   ├── onedoc_service.py            # NOVO: orquestração, idempotência, auditoria, reprocessamento
│   ├── import_service.py            # +onedoc_enforce=False no lote CSV (precedente notify=False)
│   ├── permission_service.py        # +integracao1doc.reprocessar (sem concessão default)
│   └── audit_service.py             # +4 ACTION_INTEGRACAO_1DOC_* + rótulos
├── web/
│   ├── routes.py                    # +campo no form GET/POST de /movements/new (tipos elegíveis)
│   ├── admin_routes.py              # +rotas mínimas /admin/integracao-1doc (listar/reprocessar)
│   ├── api (movements_api.py)       # pass-through do campo do schema (aditivo)
│   └── templates/
│       ├── movements/new.html       # +campo condicional (só cautela/transferência — Q5)
│       ├── admin/onedoc.html        # NOVO: lista de integrações + botão reprocessar (padrão 021/030)
│       └── base.html                # +item de menu com can()
tests/
└── test_onedoc.py                   # NOVO: cenários US1/US2/US3 com fakes
```

**Arquivos intocados**: e-mail 030 (`notification_service`, `email_provider`, `email_config_service`), regras VAL-*, tipos de movimentação, RBAC existente, inventário, backup.

## Decisões (D1–D12)

| # | Decisão | Justificativa | Alternativas rejeitadas |
|---|---|---|---|
| D1 | Tabela nova `onedoc_integrations` com `movement_id` **UNIQUE** | Idempotência estrutural (SC-003) e vínculo movimentação↔processo↔mensagem sem alterar `Movement` | Coluna nova em `movements` (contaminaria o modelo patrimonial com dado de integração) |
| D2 | Campos do processo no **registro de integração**, não na movimentação | `Movement` permanece fonte patrimonial pura; integração tem estado próprio (FR-008) | Migrar `movements` ( viola "alterar o mínimo") |
| D3 | Config **100% ambiente**: `ONEDOC_ENABLED` (default **false**), `ONEDOC_API_URL`, `ONEDOC_API_TOKEN`, `ONEDOC_CONNECT_TIMEOUT` (3 s), `ONEDOC_READ_TIMEOUT` (10 s), `ONEDOC_MAX_ATTEMPTS` (3) | P-4 confirmado; padrão `SMTP_*`; segredo nunca em banco | Singleton em banco (021/030) — avaliado, adiado: sem credenciais ainda, tela seria inútil |
| D4 | Provider: protocolo `OneDocProvider` (`find_process`, `send_communication`) + `OneDocHttpClient` (requests) | Isola a API externa atrás de ponto único (spec §8); testes com fake; contratos C-1..C-4 conectados só no client | Espalhar chamadas HTTP pelo service |
| D5 | **PENDÊNCIA EXTERNA documentada**: endpoints reais só no client quando fornecedor confirmar C-1..C-4; até lá `ONEDOC_ENABLED=false` e o plano segue com fakes | Fase 1 bloqueante da spec — nada inventado (regra do input) | Presumir endpoints de exemplos de terceiros (proibido) |
| D6 | `MovementCreate.onedoc_process_number: Optional[str] = None`; `create_movement(..., onedoc_process_number=None, onedoc_enforce=True)` | Aditivo; validação FR-002 condicional (integração ativa + tipo elegível + enforce); import CSV passa `onedoc_enforce=False` (precedente `notify=False`) | Validação na rota (Constitution III) |
| D7 | Validação de existência (Q2): `find_process()` → `False` = inexistente (ValueError antes de gravar); `None` = API não suporta (modo tolerante) | Implementa decisão Q2 sem presumir C-3 | Sempre tolerante / sempre bloqueante |
| D8 | Hook 1Doc **após** o hook de e-mail, no mesmo bloco pós-commit com `try/except` total | Ordem do fluxo da spec §6; RN: falha de 1Doc jamais propaga (FR-007) | Chamada dentro da transação (proibido pela spec §6) |
| D9 | Execução **single-shot pós-commit** + reprocessamento manual; retry automático efetivo (worker) fica como evolução | P-5 default; volume baixo; estados da tabela já viabilizam worker futuro sem redesenho | Fila/Celular/worker agora (complexidade desnecessária) |
| D10 | Tela admin **mínima** `/admin/integracao-1doc`: lista integrações (estado/processo/tentativas/erro) + botão "Reprocessar" | FR-011 exige forma operável de reprocessar; FR-018 veda *painel de monitoramento* — a lista mínima é o meio de execução do FR-011 (interpretação registrada) | Reprocessar sem visibilidade (inoperante) ou painel completo (fora de escopo) |
| D11 | 4 eventos: `INTEGRACAO_1DOC_SOLICITADA`, `_ENVIADA`, `_FALHOU`, `_REPROCESSADA` (padrão `ACTION_*`, `user=None` nos automáticos) | Simetria com 030 e spec §11 | Só 3 eventos (perde rastreio da solicitação) |
| D12 | Conteúdo (saudação por horário + tabela 4 colunas) em `onedoc_message.py` **puro**, formatos text/HTML decididos pelo client conforme C-4 | Testável sem API; fiel ao modelo do setor (P-1/P-2 defaults) | Construir conteúdo no client (mistura responsabilidades) |

## Fase 1 — Pendência Externa (bloqueio de produção, não de desenvolvimento)

> **A API 1Doc NÃO é presumida.** O contrato real (C-1..C-8 da spec §8) deve ser obtido do fornecedor. Impacto no plano:
>
> 1. **Pode implementar agora** (com fakes): model, services, message builder, validações, tela, permissão, auditoria, testes — toda a mecânica interna;
> 2. **Fica com wiring pendente**: `OneDocHttpClient` (URLs/payloads reais) — implementado contra a interface do protocolo, com marcação `[PENDING C-1..C-4]` nos pontos exatos a conectar;
> 3. **Integração nasce desativada** (`ONEDOC_ENABLED=false`) — produção só liga com credenciais + contrato confirmados + validação em homologação (quickstart §5).
>
> Solicitação ao fornecedor (checklist): autenticação (C-1), consulta/validação de processo (C-2/C-3), inclusão de comunicação e formatos aceitos (C-4), assinatura (C-5), idempotência nativa (C-6), erros/limites (C-7), ambiente de homologação (C-8).

## Constraints

- Com `ONEDOC_ENABLED=false` (default): nenhuma validação nova, nenhum campo obrigatório, nenhuma chamada externa — comportamento **byte-idêntico** ao atual (Constitution I);
- Lote da importação CSV: `onedoc_enforce=False` — nunca exige processo nem gera comunicação (F6/Q2 da 030);
- Falha do 1Doc: nunca revert, nunca bloqueia, nunca atrasa além do timeout (FR-007/FR-013);
- Zero dependências novas; zero DDL destrutivo; e-mail 030 intocado;
- Suíte deve permanecer verde (exceto a falha pré-existente ambiental do baseline).
