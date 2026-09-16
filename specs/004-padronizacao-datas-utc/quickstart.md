# Quickstart: Padronização de Data e Hora (feature 004)

**Feature**: 004-padronizacao-datas-utc | **Date**: 2026-09-15
Protocolo de validação executável, ponta a ponta, da convenção **UTC persistido →
`America/Recife` exibido**. Executar após a implementação (`/speckit-tasks` → `/speckit-implement`).

---

## Pré-requisitos

- Ambiente de desenvolvimento com dependências instaladas (`pip install -r requirements.txt`).
- Banco de teste/desenvolvimento descartável (dados atuais são de teste — FR-012; não migrar nada).
- O fuso do **servidor é irrelevante** para a validação — a convenção usa UTC na geração e fuso
  nomeado na apresentação. Para validar a conversão com valores fixos, preferir os testes
  automatizados (seção 1), que fixam instantes independentes do relógio da máquina.

## 1. Suíte automatizada (validação primária)

```bash
# Suíte completa (deve permanecer verde — FR-016/SC-006)
pytest

# Novos testes da convenção
pytest tests/test_datetime_convention.py -v   # mecanismo central + edge cases
pytest tests/test_datetime_flows.py -v        # gravação, filtros, apresentação
```

`test_datetime_convention.py` cobre (FR-015): conversão UTC→Recife; **virada de dia** (UTC
16/09 02:30 → Recife 15/09 23:30); preservação de segundos; valor ausente (`None` → sem erro);
idempotência de uso (não há dupla conversão no caminho); `local_to_utc` (filtro local→UTC);
proibição de offset fixo (valores válidos antes/após mudanças de regra do fuso nomeado).

`test_datetime_flows.py` cobre: gravação de `Movement.timestamp`/`assets.updated_at` em UTC via
movimentação e importação; consistência intra-linha (`timestamp` × `created_at` da mesma
movimentação); filtros de período local→UTC; apresentação convertida em Inventário e Auditoria.

## 2. Gravação em UTC (US2 — teste independente)

1. Registrar uma movimentação (ex.: alocação de bem) em um horário local conhecido
   (ex.: 19:30 locais de Recife).
2. Verificar no banco (ou via ORM em teste):

```sql
SELECT timestamp, created_at FROM movements ORDER BY id DESC LIMIT 1;
```

- **Esperado**: ambas as colunas ≡ UTC do momento (19:30 local ≡ 22:30 UTC), com tolerância de
  segundos de execução (SC-002). Antes da feature, `timestamp` mostrava 19:30 (local) e
  `created_at` 22:30 (UTC) na mesma linha (SC-003).
3. Verificar também `assets.updated_at` do bem movimentado ≡ UTC (era misto antes).

## 3. Apresentação correta nas telas (US1 — SC-001, inspeção por tela)

Com um registro criado às 19:30 locais (22:30 UTC):

| Tela | Onde olhar | Esperado |
|---|---|---|
| Trilha de auditoria | `/admin/audit` | `15/09/2026 19:30:xx` (com segundos) |
| Inventário — detalhe | `/inventarios/{id}` | conferência às `19:30` (não 22:30) |
| Inventário — lista | `/inventarios` | `Criado em 15/09/2026 19:30` |
| Inventário — conferir | `/inventarios/{id}/conferir/{asset_id}` | alerta "em 15/09/2026 19:30" |
| Usuários — lista | `/admin/users` | último acesso `15/09/2026 19:30` (ou "Nunca") |
| Usuários — edição | `/admin/users/{id}/edit` | bloqueio temporário mostra `20:00` para bloqueio até 20:00 locais |
| Manutenções — lista | `/maintenances` | OS aberta às 21:30 locais de 15/09 mostra **15/09** (dia local) |
| Movimentações — lista | `/movements` | `15/09/2026 19:30` |
| Dashboard | `/` | últimas movimentações `15/09/2026 19:30` |
| Bem — detalhe | `/assets/{id}` | histórico de movimentações `19:30`; compra `15/09/2026` **sem deslocamento** |

## 4. Documentos exportáveis (US4)

1. Com inventário conferido às 19:30 locais, exportar CSV e PDF da ata
   (`/inventarios/{id}/export/csv`, `/inventarios/{id}/export/pdf`).
   - **Esperado**: "Conferido em"/"Encerrado em" ≡ 19:30.
2. Exportar CSV de movimentações do relatório.
   - **Esperado**: carimbo da movimentação ≡ 19:30.
3. Carimbo "Gerado em" dos PDFs/Excel: horário **local** do momento da geração (comportamento
   atual preservado).

## 5. Filtros de período (US5)

1. Criar uma movimentação às 19:00 locais de 15/09 (≡ 22:00 UTC).
2. Consultar a API com o intervalo local do dia:

```bash
# 15/09/2026 00:00–23:59 em America/Recife ≡ 15/09 03:00 → 16/09 02:59 UTC
curl "http://localhost:8000/api/v1/movements?start_date=2026-09-15T00:00:00&end_date=2026-09-15T23:59:00" \
  -H "Cookie: <sessão válida>"
```

- **Esperado**: a movimentação das 19:00 locais é retornada (SC-005). Alternativa com offset
  explícito (`2026-09-15T03:00:00-03:00` → `2026-09-16T02:59:00-03:00`): mesmo resultado.
3. Criar um registro às 23:50 locais e repetir o filtro do dia: incluído; filtro do dia anterior:
  não incluído.

## 6. Datas de negócio preservadas (US3 — SC-004)

1. Cadastrar um bem com compra `15/09/2026` e garantia `15/09/2028` → detalhe exibe as datas
   informadas, sem deslocamento.
2. Importar CSV com compra `15/09/2026` → armazenado e exibido como `15/09/2026`.
3. Filtrar relatório de bens por compra `2026-09-01` a `2026-09-15` → resultado igual ao
   comportamento atual (comparação por data de negócio).

## 7. Verificação de conformidade (SC-008/SC-009)

```bash
# Nenhum deslocamento fixo no código entregue
grep -rn "timedelta(hours=3)\|hours=-3\|- 3 \* 3600" app/ || echo "OK"

# Caminhos novos/modificados não geram "agora" fora do mecanismo central
grep -rn "datetime.now()\|datetime.utcnow()" app/ --include="*.py" | grep -v time_utils
# Esperado: apenas os pontos fora do escopo listados em data-model.md §4
# (term_codes/anos, depreciação, "Gerado em", admin_routes:229, ad_ldap helper, seed_demo)

# Zero DDL/migração na feature
git diff --stat   # nenhuma alteração em app/models/, app/database.py
```

## 8. Critérios de sucesso

| Critério | Como foi verificado |
|---|---|
| SC-001 | Tabela da seção 3 — inspeção em cada tela |
| SC-002/SC-003 | Seção 2 — valores no banco ≡ UTC e consistentes intra-linha |
| SC-004 | Seção 6 — datas de negócio idênticas |
| SC-005 | Seção 5 — filtros retornam exatamente o intervalo local |
| SC-006 | Seção 1 — suíte verde + novos testes passando |
| SC-007 | Seção 7 — nenhum DDL, nenhuma migração |
| SC-008/SC-009 | Seção 7 — varreduras sem ocorrências fora do escopo |
