# Contrato — Extensão `locations` do Pacote Offline (spec 074)

**Data**: 2026-10-18 | **Natureza**: extensão **adição** do contrato §2 da spec 033 (`specs/033-inventario-offline-pwa/contracts/inventario-offline-contract.md`). Contrato de sync (§3) **inalterado**.

## 1. `POST /api/v1/inventarios/{inventory_id}/offline/package` (permissão `inventario.conferir`)

Resposta ganha um campo adicional:

| Campo | Tipo | Semântica |
|---|---|---|
| `locations` | `Array<{ id: int, name: string }>` | Catálogo completo de locais cadastrados, ordem de exibição (`branch, department, name`); `id` = PK estável (`Location.id`); `name` = nome único de apresentação |

- **Aditivo e não quebrante**: clientes antigos ignoram o campo; servidores antigos não o enviam (cliente deve tratar ausência — §3).
- Sem campos além de `id`/`name` (mínimo viável; RF03).
- Subida de versionamento do cache: `sw.js` `CACHE_VERSION = "inventario-offline-v35"` (atualiza shell + JS nos dispositivos).

## 2. Consumo no dispositivo

| Aspecto | Regra |
|---|---|
| Persistência | `savePackage()` grava o payload inteiro (incl. `locations`) na store `packages` — **nenhum store novo, `DB_VERSION` = 1** |
| Recuperação | `getPackage(invId).locations` |
| Estado "indisponível" | `locations` **ausente** (pacote antigo) ou pacote inexistente → UI exibe orientação para reconectar e re-preparar; registro `LOCAL_DIFERENTE` **bloqueado** |
| Estado "vazio" | `locations` presente e `[]` → "nenhum local cadastrado"; registro bloqueado |
| Seleção | opção do dropdown = `id`; nome exibido = `name` |

## 3. Envio na sincronização — `POST .../offline/sync` (§3 — inalterado)

A coleta `LOCAL_DIFERENTE` passa a enviar:

```jsonc
{
  "client_operation_id": "…",
  "operation": "CHECK",
  "asset_id": 101, "item_id": 501,
  "result": "LOCAL_DIFERENTE",
  "found_location_id": 7,          // ← passa a ser preenchido (antes sempre null)
  "found_location_name": "Filial Campinas - Almoxarifado",  // snapshot de apresentação
  "observation": null, "collected_at": "…"
}
```

Validação do servidor (existente, intocada):
- `found_location_id` desconhecido → rejeição estável `local_inexistente` (coleta **preservada**, reprocessável).
- Coletas antigas só com `found_location_name` → resolução por nome exato único (compatibilidade, FR-012).
- Gravação oficial: `InventarioService.record_check` — único caminho; cadastro patrimonial não é alterado.

## 4. Garantias

- 1 requisição a mais **zero** durante a coleta offline (catálogo vem no pacote).
- Falha ao (re)preparar → `savePackage` não executa → pacote anterior permanece íntegro (SC-005).
- Nenhuma mudança de permissão, endpoint, modelo de banco ou rotina de retry.
