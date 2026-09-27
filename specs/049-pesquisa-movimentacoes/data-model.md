# Phase 1 — Data Model: 049-pesquisa-movimentacoes

**Feature**: Campo de Pesquisa no Fluxo Global de Movimentações  
**Date**: 2026-09-27  

Esta funcionalidade é puramente aditiva e de **leitura (read-only)**. Nenhuma nova tabela ou coluna de banco de dados é criada, e nenhuma estrutura existente é modificada.

---

## 1. Schema Extensions (Camada de Aplicação / Pydantic)

### `MovementFilter` (`app/schemas/movement.py`)

O schema de filtros de movimentação recebe um campo opcional adicional:

```python
class MovementFilter(BaseModel):
    asset_id: Optional[int] = None
    movement_type: Optional[MovementType] = None
    custodian_id: Optional[int] = None
    location_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    search: Optional[str] = None  # Novo campo: termo de pesquisa textual livre
```

- **Validação**: String opcional. Espaços antes/depois são sanitizados na camada web (`strip()`).
- **Compatibilidade**: Padrão default `None` assegura 100% de compatibilidade com chamadas existentes.

---

## 2. Entidades do Banco Envolvidas na Pesquisa (Somente Leitura)

A query de busca atua sobre as seguintes colunas e relacionamentos já existentes:

| Entidade | Tabela | Campo / Relacionamento | Tipo / Origem | Finalidade na Busca |
|---|---|---|---|---|
| `Movement` | `movements` | `operator_name` | String(100) | Nome do usuário/operador que registrou o fluxo |
| `Movement` | `movements` | `term_code` | String(50) | Identificador do Termo de Responsabilidade |
| `Movement` | `movements` | `movement_type` | Enum(MovementType) | Tipo da operação (busca por valor ou label) |
| `Movement` | `movements` | `origin_location_name` | String(150) | Snapshot do nome do local de origem |
| `Movement` | `movements` | `destination_location_name` | String(150) | Snapshot do nome do local de destino |
| `Movement` | `movements` | `origin_custodian_name` | String(150) | Snapshot do nome do colaborador de origem |
| `Movement` | `movements` | `destination_custodian_name` | String(150) | Snapshot do nome do colaborador de destino |
| `Asset` | `assets` | `tag` | String(50) | Número de tombamento / plaqueta do equipamento |
| `Asset` | `assets` | `name` | String(150) | Nome e descrição do equipamento |
| `Custodian` | `custodians` | `registration_code` | String(50) | Matrícula funcional do colaborador (origem/destino) |
| `Custodian` | `custodians` | `name` | String(150) | Nome do colaborador no cadastro (origem/destino) |
| `Location` | `locations` | `name` | String(100) | Nome do local no cadastro (origem/destino) |

---

## 3. Integridade e Regras de Dados

1. **Imutabilidade**: Nenhum registro na tabela `movements` é alterado pela pesquisa. A tabela continua servindo como trilha histórica e auditável imutável.
2. **Ausência de Novas Tabelas**: Não há tabelas intermediárias, de índice textual ou de cache persistido. A consulta é resolvida diretamente via SQLAlchemy.
3. **Sem Migrações de Banco**: Nenhuma alteração estrutural no MariaDB/MySQL. O script `_ensure_schema_migrations` não requer alterações.
