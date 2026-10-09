# Contract — Formulário web de cadastro de localização (`POST /locations/new`)

**Feature**: 066-preenchimento-automatico-localizacao | **Data**: 2026-10-09
**Status**: NOVO comportamento apenas no fluxo web; contratos de API e importação **preservados** (ver §Preservados).

## 1. Entrada (form-urlencoded)

| Campo | Obrigatório | Comportamento |
|---|---|---|
| `branch` | **Sim** | Unidade Administrativa — fonte 1 da composição |
| `department` | **Sim** | Departamento / Setor — fonte 2 da composição |
| `name` | Não (antes: sim) | **Ignorado pelo servidor** — valor recebido é descartado e recomposto (FR-003). O browser o envia porque o campo é `readonly`, não `disabled` |
| `manager_name`, `building`, `floor`, `room`, `description` | Não | Inalterados |

Permissão: `locais.criar` (middleware existente — inalterado).

## 2. Regra do servidor

```
name_persistido = LocationService.compose_name(branch, department)
                = f"{branch.strip()} - {department.strip()}"
```

- Composição vazia (branch ou department em branco) → `422`/bloqueio (campos obrigatórios) — nenhum registro criado.
- `len(name_persistido) > 100` → redirect `303` para `/locations/new?error=<mensagem>` — nenhum registro criado.
- Nome já cadastrado → `ValueError` existente → redirect `303` para `/locations/new?error=Já existe um local cadastrado com este nome` — nenhum registro criado.

## 3. Saída

- Sucesso: `303` → `/locations` (inalterado); auditoria `ACTION_CREATE` com `after={name, branch, department}` (inalterado).
- Erro: `303` → `/locations/new?error=…` (padrão atual).

## 4. Contratos PRESERVADOS (fora desta mudança)

| Contrato | Garantia |
|---|---|
| `POST /api/v1/locations` | Continua aceitando `name` explícito no payload (`LocationCreate`); **sem** imposição da composição (P1 aprovada) |
| `PUT /api/v1/locations/{id}` | Intocada; `exclude_unset` ⇒ atualização parcial não renomeia (AC08) |
| Importação CSV de locais | Coluna "Localização" obrigatória e independente; duplicata por nome; só cria — inalterado |
| Importação CSV de bens / inventário offline | Resolução `get_by_name` inalterada — nomes novos seguem o mesmo padrão dos 37 existentes |
| Snapshots de movimentações, CSV, relatórios, termos | Intocados (nenhum dado regravado) |

## 5. Front-end (comportamento observável, não bindável por teste de contrato)

- Campo `Localização` exibido `readonly`, atualizado a cada tecla em `branch`/`department`, vazio enquanto um dos dois não estiver preenchido.
- Valida a mesma composição que o servidor; servidor permanece a autoridade (spec AC05).
