# Melhorias do SisPatrimônio Pro (backlog)

Registro de problemas/melhorias identificados durante o desenvolvimento, pendentes
de especificação própria. Não constituem obrigações automáticas (Constitution v1.0.0,
seção "Restrições de Tecnologia e Dados"): cada item vira feature pelo fluxo Spec Kit.

---

## M-001 — Flakiness: `test_ata_csv_exibe_horario_local` (tests/test_datetime_flows.py)

**Status**: aberto (2026-09-24) · **Prioridade**: baixa (falha esporádica, sem impacto em produção)

### Sintoma observado

Na primeira execução da suíte completa após a implementação da feature 032
(2026-09-24 ~00:56 UTC ≈ 21:56 Recife), o teste falhou 1×:

```
FAILED tests/test_datetime_flows.py::TestUS4Exports::test_ata_csv_exibe_horario_local
1 failed, 678 passed
```

Nas re-execuções seguintes (isolada ×5, arquivo completo e suíte completa 2×),
o teste passou **sempre** — inclusive com o mesmo código (o stash/re-pop da 032
confirmou que a falha não depende das mudanças da 032).

### O que o teste faz

- Fixa `checked_at = 2026-09-15 22:30 UTC` (`FIXED_UTC`) e afirma que o CSV da ata
  exibe `19:30` (Recife) e **não contém** `22:30` (`tests/test_datetime_flows.py:292`).

### Causa provável (a confirmar na próxima ocorrência)

1. **Janela de carimbo real**: além do `checked_at` fixo, o CSV inclui
   `Criado em: format_local(inventario.created_at)` com `created_at = now_utc()` REAL.
   O assert negativo (`"22:30" not in body`) varre o CSV inteiro — se a suíte rodar
   exatamente quando o horário em Recife for **22:30** (janela de ~1 min/dia),
   o carimbo real contém "22:30" e o assert quebra.
2. **Não bate com o horário observado** (21:56 Recife na falha registrada) —
   hipóteses alternativas a investigar quando reproduzir com traceback completo:
   - contaminação de estado entre testes via `StaticPool` (SQLite em memória
     compartilhado) + `expire_all` do fixture;
   - variação de `tzdata` do SO na conversão `ZoneInfo` (descartado em verificação
     pontual: `22:30 UTC → 19:30 Recife` estável na máquina atual).

### Evidência de não-relação com a feature 032

- `git stash` (removendo todas as mudanças da 032) → teste passou isolado;
- suíte completa reexecutada 2× com a 032 aplicada → **680 passed** nas duas;
- nenhum arquivo tocado pela 032 interfere em `report_service`, `time_utils` ou
  no fluxo de exportação de atas.

### Ação recomendada (quando especificado)

Tornar o teste determinístico (feature pequena, mudança apenas de teste):

- capturar o traceback completo na próxima falha (rodar com `-x --tb=long`);
- isolar o carimbo real: `monkeypatch` em `now_utc`/`datetime` usado pelo
  `InventarioService` na criação, OU restringir o assert negativo às linhas do
  item conferido (em vez do corpo inteiro do CSV);
- alternativa mais simples: trocar o assert negativo para validar apenas a linha
  do item fixo (`pandas`/parse do CSV) — elimina a dependência do "agora".

**Regra vigente enquanto aberto**: a falha esporádica NÃO bloqueia entregas;
reexecutar a suíte para confirmar (o teste passa isolado e em re-execuções).
Registro aqui cumpre o Princípio I da Constitution (problemas encontrados no
caminho são registrados e tratados em tarefa própria).
