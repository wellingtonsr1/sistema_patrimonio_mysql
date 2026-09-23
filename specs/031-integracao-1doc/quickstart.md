# Quickstart: Validação da Integração 1Doc (feature 031)

Protocolo de validação de ponta a ponta. Executar após o `/speckit-implement`.

> **Pré-requisito de produção (Fase 1)**: a integração só é ligada em produção (`ONEDOC_ENABLED=true`) com **credenciais reais + contrato da API confirmado (C-1..C-4)** junto ao fornecedor 1Doc. Os cenários abaixo rodam **sem API real** (fakes/testes) — o §5 cobre a validação real pós-fornecedor.

## 1. Pré-requisitos

- Ambiente ativo (Python 3.10+; dependências instaladas).
- Baseline executada antes da edição: **617 passed / 1 failed** (falha pré-existente ambiental `test_backup_config`, subprocesso sem dotenv).
- Banco via `DATABASE_URL` (MariaDB) com usuário com permissões `movimentacao.criar` e (pós-concessão) `integracao1doc.reprocessar`.

## 2. Suíte automatizada

```bash
python -m pytest tests/ -q --tb=no | tail -3
# esperado: (617+novos) passed / 1 failed pré-existente
python -m pytest tests/test_onedoc.py -q
# esperado: todos verdes — US1/US2/US3 com fakes
```

Cenários cobertos (spec §4): comunicação gerada (tabela fiel), processo obrigatório, processo inexistente (bloqueio/tolerante), desativada = byte-idêntico, falha externa não reverte, timeout, idempotência (0 duplicatas), reprocessamento (RBAC + auditoria), credenciais fora de logs, lote CSV intocado.

## 3. Validação manual — integração DESATIVADA (default; não-regressão)

1. `.env` **sem** `ONEDOC_ENABLED` (ou `=false`); reiniciar servidor (`python run.py`).
2. Concluir cautela/transferência pela tela → **sem** campo "Processo 1Doc" (Q5), movimentação concluída, nenhum registro em `onedoc_integrations`, nenhum evento `INTEGRACAO_1DOC_*`, e-mail da 030 chegando normalmente.
3. Comportamento **byte-idêntico** ao anterior (Constitution I).

## 4. Validação manual — integração ATIVADA com fake/provider de teste

1. `ONEDOC_ENABLED=true` + provider fake (ou homologação do fornecedor, se já disponível); reiniciar.
2. **Cautela**: campo "Processo 1Doc" visível; concluir **sem** preencher → erro "Informe o número do processo 1Doc", movimentação **não gravada** (FR-002).
3. Informar processo existente → movimentação gravada; registro `SENT` com `message_id` (ou `SENT` com id vazio — Q3); auditoria `INTEGRACAO_1DOC_SOLICITADA` + `_ENVIADA` (`user=None`).
4. **Transferência**: mesmo comportamento. **Devolução**: sem campo, sem integração (Q1/Q5).
5. **Falha externa** (fake indisponível): movimentação **gravada e válida**; registro `FAILED` com erro sanitizado (sem token); auditoria `_FALHOU`; e-mail 030 não afetado (FR-015).
6. **Idempotência**: repetir requisição/reprocessar integração `SENT` → **nenhuma** segunda comunicação (SC-003).
7. **Reprocessamento**: usuário **sem** `integracao1doc.reprocessar` → 403; com permissão (concedida explicitamente — Q4) → `FAILED`→`SENT`, auditoria `_REPROCESSADA` com usuário real.
8. **Lote CSV**: importação com movimentações elegíveis → nenhum registro 1Doc, nenhuma exigência de processo (onedoc_enforce=False).

## 5. Validação REAL (bloqueada até Fase 1 — fornecedor 1Doc)

Requisitos: credenciais + URL reais no `.env`; ambiente de homologação (C-8); processo real criado pelo setor.

1. `ONEDOC_ENABLED=true` com credenciais reais; reiniciar.
2. Concluir uma cautela de teste informando processo real.
3. Verificar no 1Doc: comunicação incluída no processo, saudação + tabela exatamente no modelo do setor (SC-008 — validação visual do setor).
4. Confirmar `message_id` registrado; responsável assina pelo fluxo próprio do 1Doc.
5. Provocar falha (token inválido) → `FAILED` sanitizado; corrigir → reprocessar → `SENT`.

## 6. Escopo final (Constitution XII)

```bash
git status --porcelain
# esperado: apenas os arquivos do plan.md (schema, movement_service, novos services/model,
# rotas web/admin, template novo + new.html + base.html, permission_service, audit_service,
# import_service, config.py, .env.example, tests/test_onedoc.py, docs)
git diff --stat | tail -3
```

**Intocados**: `notification_service`, `email_provider`, `email_config_service`, regras VAL-*, tipos, RBAC existente, inventário, backup.
