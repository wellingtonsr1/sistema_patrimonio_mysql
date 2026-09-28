# Data Model — Feature 050 (apresentação)

**Nenhuma alteração de banco** (FR-016/017 — decisão clarify Q2). Este documento registra o modelo de apresentação/contrato envolvido, para rastreio.

## 1. Entidade existente (intocada)

`Location` (`app/models/location.py`) — colunas `name` (unique), `branch`, `department`, `building`, `floor`, `room`, `manager_name`, `description`. Os três conceitos oficiais já suportados:

| Conceito oficial | Campo canônico | Semântica |
|---|---|---|
| Localização | `name` | local físico de alocação/movimentação patrimonial |
| Unidade Administrativa | `branch` | unidade administrativa à qual o local está vinculado |
| Departamento | `department` | setor associado ao local |

## 2. Contrato CSV (mudança de rótulos, não de estrutura)

### 2.1 Formato oficial (primário)

```csv
Localização;Unidade Administrativa;Departamento[;Prédio;Andar;Sala;Gestor]
```

Campos obrigatórios: os 3 primeiros (regra existente). Colunas adicionais (prédio/andar/sala/gestor/descrição) permanecem opcionais conforme parser atual.

### 2.2 Tabela de aliases (estado alvo)

| Header (chave normalizada) | Campo | Origem |
|---|---|---|
| `localizacao` | name | existente |
| `nome_da_localizacao` | name | **NOVO (050)** |
| `nome`, `name`, `identificacao`, `local`, `descricao_local` | name | existente (legado — manter) |
| `unidade_administrativa` | branch | **NOVO (050)** |
| `filial`, `branch`, `unidade`, `empresa`, `sede` | branch | existente (legado — manter) |
| `departamento`, `department`, `setor`, `area`, `divisao` | department | existente |
| `matriz/filial`, `filial / unidade` | — (não utilizada) | nunca reconhecidos — permanecem (FR-008) |
| `descricao` | **ambígua** (name × description) | existente — exige confirmação (FR-003 da 048) |

## 3. Mensagens de validação (estado alvo)

| Situação | Hoje | 050 |
|---|---|---|
| Localização ausente | `Linha N: nome é obrigatório` | `Linha N: Localização é obrigatória` |
| Unidade Administrativa ausente | `Linha N: filial é obrigatória` | `Linha N: Unidade Administrativa é obrigatória` |
| Departamento ausente | `Linha N: departamento é obrigatório` | (permanece) |

## 4. Rótulos de UI (estado alvo)

| Superfície | Hoje | 050 |
|---|---|---|
| Mapeamento inteligente (`FIELD_LABELS["locations"]`) | "Nome do local" / "Filial" | "Localização" / "Unidade Administrativa" |
| Prévia tradicional (import.html `<th>`) | "Nome / Identificação" / "Filial" | "Localização" / "Unidade Administrativa" |
| Export `locais.csv` (header) | `nome;filial;departamento;predio;andar;sala;gestor` | `Localização;Unidade Administrativa;Departamento;Prédio;Andar;Sala;Gestor` |

## 5. Fronteira explícita (NÃO muda)

- Nomes de campo de banco, de input HTML (`name="branch"`), de schema Pydantic e de API JSON (`name`/`branch`/`department`).
- Duplicidade: por `name` normalizado (`_find_existing_location` / `_natural_key`) — imune a rótulos.
- Auditoria (`write_audit` padrão `IMPORT_*`), permissões (`locais.criar`), rotas/URLs.
