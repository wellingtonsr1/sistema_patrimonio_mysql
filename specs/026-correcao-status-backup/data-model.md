# Data Model: Correção da Atualização Imediata do Status do Backup Automático

**Feature**: 026 | **Data**: 2026-09-19
**Natureza**: nenhuma entidade de produção é criada ou alterada (model/tabela `backup_config` intocados). O "modelo" aqui descreve o **fluxo de dados do card** antes/depois e os campos de contexto do template.

---

## 1. Fluxo de dados do card "Backup Automático" — ANTES (problema)

| Campo exibido | Fonte atual | Problema |
|---|---|---|
| Badge Ativado/Desativado | `auto_status.enabled` ← `scheduler_status()` ← `_eff()` (snapshot do scheduler) | defasado até 30 s pós-salvamento |
| Frequência (`daily`/`weekly`) | `auto_status.schedule` ← snapshot | idem |
| Horário (`time_local`) | `auto_status.time_local` ← snapshot | idem |
| Running / próximo disparo / último resultado | `auto_status.running`/`next_run_local`/`last_result` | correto (dados de execução) |

## 2. Fluxo de dados — DEPOIS (correção)

| Campo exibido | Fonte corrigida | Por quê |
|---|---|---|
| Badge Ativado/Desativado | `config_form.auto_enabled` (efetiva por request) | mesma fonte do checkbox; reflete o commit imediatamente |
| Frequência | `config_form.schedule` | configuração, não execução |
| Horário | `config_form.time` (string "HH:MM" America/Recife — mesmo formato de `time_local`) | configuração; sem conversão nova |
| Running / próximo disparo / último resultado | `auto_status.*` (MANTIDO — `scheduler_status()`) | dados de execução pertencem ao agendador |

**Invariantes**:
- `config_form` = `get_effective_config(db, create=False)` — leitura por request, sem efeito colateral (022); já presente nos 2 GETs (`admin_routes.py:840` e `:894`) — nenhuma chamada nova necessária.
- Checkbox do modal continua `config_form.auto_enabled` → **mesma fonte do badge** (FR-002).
- Nenhum campo novo de contexto; nenhuma função nova; nenhum cache.

## 3. Contraste: estado exibido × estado interno (preservado)

```text
config_form (efetiva por request)          _current_effective (snapshot do scheduler)
        ↓                                          ↓
Interface (badge + checkbox + form)        Execução (loop, catch-up, retenção, scheduler_status)
```

A separação é intencional (spec US2): **exibição** lê o banco por request; **execução** usa o snapshot renovado por tick (30 s) — mecanismo do scheduler intocado (briefing §6/§20).

## 4. Entidade de entrega: `FinalReport` (briefing §45)

`specs/026-correcao-status-backup/relatorio.md` — 6 itens: (1) causa confirmada com evidência; (2) arquivos alterados; (3) por que cada alteração; (4) fluxo corrigido (POST → persistência → redirect → GET → efetiva → template → indicador); (5) testes executados (somente os reais, com resultado); (6) limitações.

## 5. Novos testes (entidade `FlowTest`)

| Teste | Fluxo | Assert |
|---|---|---|
| Ativação | config off → POST `auto_enabled=true` → follow redirect | HTML contém badge "Ativado" |
| Desativação | config on → POST `false` | "Desativado" |
| Repetição | off→on→off→on→off (5 POSTs) | cada resposta reflete o novo estado |
| Com outros campos | toggle + horário; desativar + retenção | indicador coerente com o toggle |
| Idempotência F5 | GET consecutivo após o fluxo | mesmo valor do primeiro |
| Reprodução da causa | `_current_effective` desatualizado (monkeypatch) + fluxo | documenta a causa (falha no código antigo; irrelevante no novo) |
