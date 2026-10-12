# Data Model: Legibilidade dos Eventos de Alteração Cadastral na Trilha (Feature 070)

**Natureza**: transformação de **leitura para apresentação** — **ZERO** entidade nova, **ZERO** coluna nova, **ZERO** DDL (Constitution VII; spec FR-008/AC17).

---

## 1. Entidades existentes consumidas (intocadas)

### `AuditLog` (`audit_logs`) — fonte única dos eventos

Campos usados na apresentação (não são alterados):

| Campo | Uso no cartão |
|---|---|
| `timestamp` | Data/hora do evento (filtro `localtime` — fuso America/Recife, Feature 004) |
| `username` | Snapshot do responsável → "Registrado por" (`None` → "Sistema") |
| `action` | Badge com rótulo via `action_label` (global Jinja existente) |
| `module` | Badge do módulo ("Patrimônio") |
| `resource_ref` | Tag/tombamento do bem (badge) |
| `description` | Linha "Descrição" — exibida **apenas** nos caminhos sem resumo (R5/R6) |
| `previous_data` / `new_data` | JSON em TEXT → desserializados em `prev_data`/`new_data` pelo service |

### Item da timeline (dict produzido por `MovementService.get_timeline_for_asset`, L441–466)

```python
{
    'type': 'audit',
    'timestamp': datetime,          # UTC
    'data': AuditLog,               # objeto SQLAlchemy completo
    'prev_data': dict | None,       # JSON desserializado (tolerância a inválido → None)
    'new_data': dict | None,
}
```

> **Congelado**: esta estrutura e o payload de `GET /api/v1/assets/{asset_id}/timeline` (`app/api/assets_api.py` L78–130) **não mudam** (contratos M1–M6 em `contracts/preserved-contracts.md`).

## 2. Estrutura derivada (nova, só de apresentação)

O helper de `AssetService` (R1) produz, para cada item `type == 'audit'`, uma chave derivada **adicionada ao dict do item apenas no contexto do template** (a rota aplica; a API não passa por aqui):

```python
item['audit_summary'] = {
    'titulo': str | None,     # "Alteração cadastral — Nome do bem" | "Alteração cadastral — Dados do equipamento" | None (sem diff)
    'mudancas': [             # SOMENTE campos efetivamente alterados, ordenados por rótulo (padrão 067)
        {
            'field':  str,    # chave técnica do snapshot ("name")
            'label':  str,    # _ASSET_FIELD_LABELS.get(field, field) — desconhecido → nome técnico
            'before': Any,    # valor do prev_data (None → '—' na renderização)
            'after':  Any,    # valor do new_data  (None → '—' na renderização)
        },
        ...
    ],
    'detalhes': bool,         # True se prev_data ou new_data é dict → renderiza <details>
}
```

**Regras de derivação** (R6/R7):

| Condição (por item de auditoria) | `titulo`/`mudancas` | `detalhes` | Cartão resultante |
|---|---|---|---|
| `prev_data` e `new_data` são `dict`, diff ≠ vazio | título + lista do diff | `True` | Resumo (novo) + `<details>` |
| `prev_data` e `new_data` são `dict`, diff vazio | `titulo=None`, `mudancas=[]` | `True` | Fallback: descrição atual + `<details>` (estados exibidos) |
| Exatamente um dos dois é `dict` | sem resumo | `True` | Fallback: descrição atual + `<details>` com o estado disponível rotulado |
| Nenhum é `dict` (None por JSON inválido/ausente) | item **sem** `audit_summary` | — | Cartão **idêntico ao atual** (badges + descrição + "Registrado por") |

- Diff = `changed_fields(prev_data, new_data)` (`audit_service.py` L317–330) — união das chaves; `None` (nulo ou ausente) aparece como `None` e renderiza `—` (PD-4/FR-006; ausente × nulo indistinguíveis por design, distinção no JSON original).
- `label` nunca inventa vocabulário: fonte única `_ASSET_FIELD_LABELS` (17 entradas); campo futuro/desconhecido cai no nome técnico (FR-003).

## 3. Exemplo end-to-end (cenário do spec §2)

Evento `ALTERACAO` (`name`: `"Scaners Fujitsu mod. 6140Z"` → `"6140z"`), demais 6 chaves iguais:

```python
item['audit_summary'] = {
    'titulo': 'Alteração cadastral — Nome do bem',
    'mudancas': [{'field': 'name', 'label': 'Nome do bem',
                  'before': 'Scaners Fujitsu mod. 6140Z',
                  'after':  'Scaners Fujitsu mod. 6140z'}],
    'detalhes': True,
}
```

Render (padrão do painel, R5): `Nome do bem: ~~Scaners Fujitsu mod. 6140Z~~ → **Scaners Fujitsu mod. 6140z**`, com "Ver detalhes técnicos" recolhido contendo o JSON original dos dois estados.

## 4. Transições de estado / escritas

**Nenhuma.** A feature não grava, edita nem exclui nada: não há transição de estado, não há nova `write_audit`, não há migração. `changed_fields` e `_ASSET_FIELD_LABELS` são apenas importados/reutilizados (sem alteração de comportamento).

## 5. Volume e limites

- Teto já aplicado pelo service: **50 eventos de auditoria** por bem (sem alteração).
- Snapshot típico: 14–17 chaves (web × API, §1.7 da spec); diff por evento ≤ 17 linhas.
- Custo: transformação em memória, O(eventos × campos) — desprezível (R10).
