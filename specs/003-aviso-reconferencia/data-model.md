# Data Model: Aviso de sobrescrita na re-conferência de inventário

**Feature**: 003-aviso-reconferencia | **Date**: 2026-09-15

## Visão geral

Esta feature é **somente-leitura sobre os dados existentes**. Nenhuma entidade nova, nenhum campo novo,
nenhuma migração, nenhuma transição de estado nova. O data-model abaixo documenta as entidades que a
interface **lê** para renderizar o aviso — servindo de contrato de qual dado alimenta qual elemento de UI.

## Entidades (somente leitura)

### `InventarioItem` (`inventario_itens`) — fonte dos dados do alerta

Campos consumidos pelos templates (todos pré-existentes, verificados em `app/models/inventario.py`):

| Campo | Tipo / Nulabilidade | Uso na feature | Guard de UI |
|---|---|---|---|
| `status` | `Enum(InventarioItemStatus)`, `NOT NULL`, default `PENDING` | Dispara o alerta quando ≠ `PENDENTE` e exibe o resultado anterior via `item.status.label` | Sempre presente — não exige guard |
| `checked_by_name` | `String(100)`, `NULL` | "por {nome}" no alerta | `nullable=True` + FK `checked_by_id` com `ondelete="SET NULL"` → **guard obrigatório** |
| `checked_at` | `DateTime`, `NULL` | "em {dd/mm/aaaa hh:mm}" no alerta | `nullable=True` → **guard obrigatório**; formato `'%d/%m/%Y %H:%M'` (padrão da listagem) |
| `found_location_name` | `String(150)`, `NULL` | (existente) contexto do resultado anterior no alerta de `conferir.html` | Guard já existente no template |

Vocabulário controlado de `InventarioItemStatus` (`app/models/enums.py:172`):
`PENDENTE`, `ENCONTRADO`, `LOCAL_DIFERENTE`, `NAO_ENCONTRADO`, `SEM_IDENTIFICACAO` — com `label`
legível via `_LabeledEnum`.

### `Inventario` (`inventarios`) — governa a disponibilidade da UI

| Campo | Uso na feature |
|---|---|
| `status` (`PLANNED`/`IN_PROGRESS`/`CLOSED`) | Loop dos modais em `detail.html` só renderiza quando ≠ `ENCERRADO` (condição já existente, intocada). Com `ENCERRADO`, nenhum modal e nenhum formulário — bloqueio atual preservado |

## Validações e regras (existentes, nenhuma alterada)

- A gravação continua exclusivamente via `InventarioService.record_check` — validações de resultado
  (`LOCAL_DIFERENTE` exige local diverso, `ENCONTRADO` assume local esperado, `NAO_ENCONTRADO` limpa
  local) e bloqueio de encerrado (`ValueError`) permanecem a garantia definitiva.
- `confirm()` cancelado = **nenhuma requisição** → nenhum dado é lido nem escrito; a UI apenas não envia.

## Transições de estado

Nenhuma nova. Os fluxos existentes permanecem:

```text
PENDENTE ──(1ª conferência)──▶ ENCONTRADO | LOCAL_DIFERENTE | NAO_ENCONTRADO | SEM_IDENTIFICACAO
   ▲                                     │
   └────────── (não existe) ◀────────────┘
         re-conferência (sobrescreve, enquanto aberto): resultado → resultado'
         [NOVO DA FEATURE: apenas alerta + confirm() antes do POST — nada muda no dado]
```

## Regra de mapeamento dado → UI (anti-invenção, FR-005)

```text
item.status != PENDENTE            → renderiza alerta
item.checked_by_name presente      → "Já conferido por {checked_by_name}"
item.checked_at presente           → "em {checked_at:%d/%m/%Y %H:%M}"
item.checked_by_name ausente       → omite o trecho "por {nome}" (jamais "—", "desconhecido" etc.)
item.checked_at ausente            → omite o trecho "em {data}"
sempre                             → "Resultado anterior: {status.label}"
sempre                             → aviso: novo registro substitui o anterior
```
