# Quickstart: Validação — Configuração Administrável do Backup (feature 021)

**Pré-requisitos**: suíte da 020 verde (497 testes); ambiente com `.env` contendo apenas `DATABASE_URL` (estado do projeto).

---

## 1. Suíte automatizada

```bash
python3 -m pytest -q                      # suíte completa: 497 existentes + novos (nenhuma falha)
python3 -m pytest tests/test_backup_config.py -q   # Testes A–R abaixo
```

Mapeamento dos Testes obrigatórios (briefing §33) → casos em `tests/test_backup_config.py`:

| Teste | Cenário | Verificação |
|---|---|---|
| **A** — configuração padrão | Instalação sem linha `backup_config` | Efetiva = defaults 020 (desativado; daily; 02:00; dom; 30/12/12; pré-restauração preservar todos); scheduler nunca indefinido |
| **B** — backup desativado | `auto_enabled=false` | Loop não dispara backup (nenhum BackupRecord AUTOMATICO criado) |
| **C** — ativação | `auto_enabled=true` + horário atingido | Scheduler dispara o ciclo normal da 020 |
| **D** — diário | Próximo disparo com `schedule=daily` | Cálculo correto no fuso Recife (herda regras 020) |
| **E** — semanal | `schedule=weekly` + weekday | Dia/horário corretos (semana iniciando no weekday — 020) |
| **F** — horário inválido | POST com "25:99" / "abc" | Rejeição no backend; nada persiste; mensagem clara |
| **G** — retenção diária | Retenção diária alterada (ex.: 7) | `_apply_retention` usa o novo limite no snapshot |
| **H** — retenção semanal | Semanal alterada (ex.: 4) | Âncoras semanais recalculadas com o novo limite |
| **I** — retenção mensal | Mensal alterada (ex.: 6) | Âncoras mensais idem |
| **J** — pré-restauração | `keep_pre_restore=0` vs `N>0` | Preservação conforme configuração (política 020 intocada) |
| **K** — alteração pela interface | POST 02:00 → 23:00 | Persistência na linha singleton; form exibe 23:00; auditoria com before/after |
| **L** — scheduler usa a config atual | Env com horário X, banco com Y | Todas as leituras (scheduler/status/retenção) usam Y (precedência única) |
| **M** — auditoria | Alteração feita | Evento `BACKUP_CONFIGURACAO_ALTERADA` com usuário, data/hora, antes/depois por campo; sem segredos |
| **N** — RBAC | Usuário sem `backup.gerenciar` | GET e POST (direto) → 403; nada altera |
| **O** — backup manual | Geração manual com nova config vigente | Funciona como antes (registro MANUAL; fluxo 020 intacto) |
| **P** — restauração | Restore com nova config vigente | Ciclo 017/019 intacto; pré-restauração criado e marcado |
| **Q** — retenção | Ciclo de limpeza com nova config | GFS + guardas da 020 intactos; limites novos aplicados |
| **R** — reinicialização | Persistir → reiniciar app | Efetiva recarregada da persistência (create_all idempotente) |

Casos adicionais obrigatórios (spec): **anti-regressão do default** (`BACKUP_AUTO_ENABLED` default `"false"` — FR-009); **env divergente do banco** (Teste L negativo: env nunca vence o salvo); **dois POSTs simultâneos** (última escrita válida + 2 eventos); **falha de persistência** (estado anterior vigente); **valores limítrofes válidos** (00:00, retenção 1, keep 0 aceitos — FR-016); **aplicação dinâmica** (salvar → próximo tick ≤ 30 s usa o novo valor, sem reinício — FR-011).

## 2. Validação manual (navegador)

1. **Configurar**: Login admin → Administração → Backups → seção "Configurações de Backup" → confirmar campos com valores efetivos → alterar horário **02:00 → 23:00**, ativar o backup, salvar → mensagem de sucesso → form exibe 23:00.
2. **Auditoria**: Administração → Auditoria → evento "Configuração de Backup Alterada" com antes/depois.
3. **RBAC**: usuário só com perfil Consulta → tentar acessar `/admin/backups/configuracoes` → 403; POST direto → 403.
4. **Validação**: submeter horário "25:99" e retenção 0 → mensagens de erro; valores anteriores preservados.
5. **Observação de campo técnico**: confirmar que a tela NÃO oferece `MYSQLDUMP_PATH`, `BACKUP_DIR`, `BACKUP_IMPORT_TIMEOUT` nem credenciais.

## 3. Validação de aplicação dinâmica (sem reinício)

1. Com `BACKUP_AUTO_ENABLED=true` salvo pela tela e horário 23:00, observar o log do agendador → próxima execução passa a refletir 23:00 **sem reiniciar** (tick ≤ 30 s);
2. Alterar para semanal/segunda → status do card mostra a nova próxima execução no próximo tick.

## 4. Validação real nos dois SO (manual)

- **Linux**: ciclo completo (configurar → disparo → retenção → reinício) no ambiente de produção/staging atual;
- **Windows (XAMPP/MariaDB)**: mesmos passos — nenhum caminho de código dependente de SO foi alterado (R4 usa apenas leituras de banco + funções de tempo existentes).

## 5. Critérios de aceite (spec §34)

Suíte 100% verde (497 + novos) · Testes A–R passando · tela funcional nos padrões visuais · auditoria com before/after · 403 backend · sem campo técnico na tela · persistência sobrevive a reinício · scheduler sem estado indefinido · documentação (README/arquitetura/ajuda) fiel.
