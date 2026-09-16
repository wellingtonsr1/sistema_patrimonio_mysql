# Contract: Mecanismo Central de Tempo (`app/utils/time_utils.py`)

**Feature**: 004-padronizacao-datas-utc | **Date**: 2026-09-15
**Escopo**: contrato funcional do módulo utilitário central exigido por FR-001/FR-002/FR-003/FR-004/
FR-005/FR-018. Assinaturas são orientativas (nomes estáveis); o contrato vinculante é o
**comportamento**.

---

## 1. `now_utc() -> datetime`

Gerador único de "agora persistível".

| Aspecto | Contrato |
|---|---|
| Retorno | `datetime` **naive** (`tzinfo is None`) representando o instante atual em **UTC** |
| Implementação | `datetime.now(timezone.utc).replace(tzinfo=None)` — correto mesmo se o processo tiver TZ local ≠ UTC (diferente de `datetime.utcnow()`, que é equivalente, mas mantém a mesma forma naive dos usos atuais) |
| Consumo | Todo timestamp de "agora" gerado pelo sistema e persistido (FR-001). Nenhum caminho novo/modificado usa `datetime.now()`, `datetime.utcnow()`, `func.now()` ou `CURRENT_TIMESTAMP` para persistir "agora" (FR-002, SC-009) |
| Não escopo | Anos de códigos sequenciais (`INV-YYYY`, `TR-YYYY`), depreciação, carimbo "Gerado em" dos relatórios (permanece `now()` local, US4) |

## 2. `utc_to_recife(value: datetime | None) -> datetime | None`

Conversor único de apresentação (UTC → `America/Recife`).

| Aspecto | Contrato |
|---|---|
| Entrada `None` | Retorna `None` — templates mantêm os guards atuais ("—", "Nunca", condicional) sem erro (FR-004) |
| Entrada naive | Tratada como **UTC** por convenção (FR-018): anexa `ZoneInfo("UTC")` e converte com `astimezone(ZoneInfo("America/Recife"))` |
| Entrada aware | Convertida diretamente com `astimezone` (respeita o offset que o valor já carrega) |
| Fuso | `zoneinfo.ZoneInfo("America/Recife")` nomeado — **proibido** offset fixo de −3h (FR-005, SC-008) |
| Perda de precisão | Nenhuma — minutos/segundos preservados (edge case "segundos") |
| Idempotência de uso | Deve ser aplicado **uma única vez** por fluxo de apresentação. Entrada esperada é sempre o valor bruto do banco; nenhum ponto converte um valor já convertido (edge case "dupla conversão") |
| Valor de retorno | `datetime` aware no fuso `America/Recife`; o chamador aplica o `strftime`/formatação existente |

## 3. `local_to_utc(value: datetime) -> datetime`

Conversor de filtros de período (entrada do usuário local → UTC comparável).

| Aspecto | Contrato |
|---|---|
| Entrada naive | Interpretada como horário de `America/Recife`; anexa `ZoneInfo("America/Recife")` e converte para UTC, retornando **naive** (para comparar com colunas naive sem warning do SQLAlchemy) |
| Entrada aware | Respeitada como instante absoluto (o cliente informou offset explícito); convertida para UTC e retornada naive |
| Fuso | `America/Recife` nomeado — sem offset fixo |
| Consumo | Filtros `start_date`/`end_date` da API de movimentações (`MovementFilter`) antes de comparar com `Movement.timestamp` (FR-010). **Não** se aplica a filtros de data pura de compra (R6) |

## 4. `format_local(value: datetime | None, fmt: str = "%d/%m/%Y %H:%M") -> str`

Helper de formatação para **exports em Python** (report_service), onde não há filtro Jinja.

| Aspecto | Contrato |
|---|---|
| Composição | `utc_to_recife(value)` + `.strftime(fmt)` |
| Entrada `None` | Retorna `""` (convenção dos exports, que usam `if ... else ""/"-"` nos chamadores) |
| Formato | O chamador mantém os formatos atuais (`%d/%m/%Y %H:%M`, `%H:%M:%S` etc.) — a feature muda o fuso do valor, não o formato (premissa da spec) |

## 5. Registro Jinja (`app/web/routes.py`)

| Aspecto | Contrato |
|---|---|
| Filtro | `templates.env.filters["localtime"] = utc_to_recife` |
| Uso em template | `{{ ts | localtime | strftime('%d/%m/%Y %H:%M') }}` — o `strftime` atual permanece, apenas o valor passa pelo filtro |
| Não uso | Nenhum template converte "por fora" (cálculo manual de horas) — toda conversão passa pelo filtro (FR-006) |

## 6. Regras transversais (vinculantes)

1. **Persistência**: coluna `DATETIME` + valor naive-UTC. Nenhuma mudança de schema (FR-011).
2. **Leitura**: naive lido de coluna-timestamp = UTC (FR-018).
3. **Apresentação**: uma conversão única por fluxo, sempre via mecanismo central (FR-003/005).
4. **Proibições**: offset fixo (−3h), dupla conversão, conversão de data de negócio (FR-014),
   alteração da lógica auth/sessão/AD (FR-013).
5. **Divergência de classificação**: interromper e registrar, não assumir (edge case da spec).
