# Quickstart: Validação da Correção do Status Imediato (Feature 026)

**Feature**: 026 | **Data**: 2026-09-19
**Natureza**: correção funcional localizada — validação por reprodução da causa + testes automatizados do fluxo real + regressão + inspeção de diff.

---

## Pré-requisitos

- Ambiente de testes do projeto (pytest + TestClient; banco de teste isolado — padrão das fixtures existentes em `tests/`).
- Branch de trabalho com as alterações pendentes de validação.

## Passo 1 — Reproduzir o problema no código ANTES da correção (briefing §45.1)

Com o código antigo (badge alimentado por `auto_status`):

```python
# Conceito: simular snapshot desatualizado + salvar o oposto + seguir redirect
# (implementar como teste-documentação; executar e registrar o resultado)
monkeypatch do snapshot _current_effective com auto_enabled contrário ao POST
POST /admin/backups/configuracoes salvando o toggle oposto (follow_redirects)
assert do badge → DEVE FALHAR mostrando o valor antigo (reproduz a causa)
```

**Registrar**: saída/resultado no relatório (§45.1) — causa confirmada por reprodução, não por hipótese. (Se a reprodução não for viável tecnicamente, registrar como limitação e validar a causa por evidência de código.)

## Passo 2 — Aplicar a correção e rodar os novos testes (SC-001/SC-002)

```bash
pytest tests/test_backup_config.py -q
```

**Esperado**: novos testes do fluxo real verdes — ativação, desativação, repetição (off→on→off→on→off), com outros campos (horário; retenção), idempotência de F5 (GET consecutivo idêntico), e o teste-documentação da causa (agora irrelevante ao resultado).

## Passo 3 — Regressão (FR-010)

```bash
pytest tests/test_backup_config.py tests/test_backup_automatico.py tests/test_backup_retencao.py tests/test_backup_monitoramento.py -q
```

**Esperado**: 100% verde, **sem alteração** nos testes existentes. Se algum teste citar o badge via `auto_status` (esperado: nenhum — varredura prévia só encontrou `scheduler_status()` em teste da 020 sobre o próprio agendador), avaliar adaptação legítima mínima e registrar.

## Passo 4 — Inspeção do diff (SC-004 / briefing §44)

```bash
git status --porcelain
git diff --stat
```

**Esperado**: somente `app/web/admin_routes.py` (se um ajuste de contexto for necessário), `app/web/templates/admin/backups.html` (badge/frequência/horário → `config_form.*`) e `tests/test_backup_config.py`. **Zero** em: `app/services/backup_scheduler.py`, `backup_service.py`, `backup_config_service.py`, `app/models/backup_config.py`, migrations, docs. Qualquer caminho inesperado → investigar/reverter.

## Passo 5 — Contrato de fontes (contracts/status-source-contract.md §1)

Conferir no template: badge/frequência/horário usam `config_form.*`; `running`/`next_run_local`/`last_result` usam `auto_status.*`; checkbox permanece `config_form.auto_enabled`. Nenhum `reload`/JS novo; nenhum objeto/contexto novo.

## Passo 6 — Testes manuais de navegador (quando o ambiente permitir — registrar no relatório só os executados)

1. Abrir `/admin/backups` → ⚙ → Ativar → Salvar → **badge "Ativado" imediato** (sem F5).
2. Desativar → Salvar → badge "Desativado" imediato.
3. F5 após salvar → valor antes = depois (§29).
4. Botão direito → Atualizar → mesmo valor (§30).
5. Reabrir o modal → checkbox condizente com o badge (§31).
6. Reiniciar a aplicação → primeiro GET já correto (§33).
7. Dois navegadores simultâneos → sem estado cruzado (§37).

## Resultado esperado final

| Verificação | Critério |
|---|---|
| Reprodução | causa confirmada (teste-documentação) registrada no relatório |
| Novos testes | fluxo real verdes em todas as variações |
| Regressão | suíte relacionada 100% verde, testes intocados |
| Diff | só rota (se necessário) + template + testes; zero em scheduler/service/model/banco/docs |
| Contrato | fontes corretas por campo; nenhuma segunda fonte; sem reload |
| Relatório | 6 itens do §45 completos (causa confirmada, não hipótese) |

Todos os passos verdes → critérios de aceitação do briefing §43 satisfeitos.
