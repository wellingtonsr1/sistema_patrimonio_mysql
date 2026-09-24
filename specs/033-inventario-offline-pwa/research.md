# Research: Conferência de Inventário Offline — feature 033

**Data**: 2026-09-24 · **Spec**: [spec.md](spec.md) · **Plan**: [plan.md](plan.md)

Este documento resolve as incógnitas técnicas do plan (Fase 0) — todas as decisões respeitam
a Constitution (stack intocável, mudança mínima) e as decisões de spec (C-1..C-5, P-1..P-3).

## D1 — Leitura de QR Code (incógnita nº 1 da spec)

**Decisão**: **BarcodeDetector API nativa** do navegador como mecanismo primário, com **digitação
manual do tombamento/URL como fallback permanente** (FR-010). Fallback de biblioteca
(`zxing-wasm`, carregado sob demanda somente quando há rede) registrado como **limitação
documentada e melhoria futura** — fora do escopo da primeira entrega.

**Rationale**:
- O projeto já carrega o QRCode.js para *geração*; *leitura* é capacidade nova. A BarcodeDetector
  é nativa no Chrome Android (83+), plataforma-alvo declarada (tablets de campo Chrome/Edge
  Android), sem adicionar dependência ao bundle offline. (Fontes: MDN BarcodeDetector;
  caniuse.com/mdn-api_barcodedetector — Safari/Firefox sem suporte geral.)
- Suporte limitado (Safari 17 atrás de flag, Firefox sem suporte) **não bloqueia** o fluxo: o
  fallback manual (FR-010, edge case "câmera indisponível") garante a coleta em qualquer navegador.
- `zxing-wasm` sob demanda online não engrossa o cache do SW e não viola "nada de build step".

**Alternatives considered**:
- *zxing-wasm/pdf417 desde o início*: robustez maior, mas adiciona peso ao cache offline e uma
  dependência a versionar; desnecessário se o alvo real é Chrome Android.
- *Biblioteca de UI completa (html5-qrcode)*: acopla UI ao projeto (violação de mudança mínima)
  e duplica o Bootstrap já existente.

## D2 — Conteúdo do QR das etiquetas (incógnita nº 2 da spec)

**Decisão**: **reutilizar o formato atual sem alteração**: o QR da etiqueta codifica URL absoluta
`{origin}/assets/{asset_id}` (gerado em `assets/detail.html` e `assets/labels.html` via QRCode.js).
O leitor offline extrai o `asset_id` por regex da URL (e aceita o tombamento digitado).

**Rationale**: a spec proíbe inventar novo formato ("a leitura reutiliza o padrão de conteúdo
atual das etiquetas"). A URL absoluta contém o identificador interno `asset_id`; o pacote offline
já inclui `asset_id` por item, então a identificação offline é direta:
`asset_id → item do snapshot → conferência`.

**Alternatives considered**:
- *Migrar para payload estruturado* (`sispat:{tombamento}`): quebraria as etiquetas impressas em
  campo; proibido pela spec/Constitution (Princípio I).
- *Validar tombamento no leitor offline*: desnecessário — a validação de existência contra o
  snapshot local é feita na coleta (bem fora do snapshot → "bem não previsto").

## D3 — Armazenamento local e schema do IndexedDB

**Decisão**: **IndexedDB nativo** (sem wrapper/biblioteca), banco `sispatrimonio_offline`,
**version 1** com 4 object stores:

| Store | keyPath | Conteúdo |
|---|---|---|
| `packages` | `inventory_id` | 1 registro por pacote (snapshot mínimo + versão + estado) |
| `coletas` | `client_operation_id` | Cada coleta registrada em campo |
| `sync_queue` | `client_operation_id` | Fila de sincronização (estado + tentativas) |
| `device_info` | `key` | device_id persistente e metadados locais |

`localStorage` fica restrito ao device_id (persistente), nunca dados de coleta (FR-006).

**Rationale**: nativo = zero dependência e controle total da migração versionada (`onupgradeneeded`
preserva coletas pendentes — FR-038/SC-009).

**Alternatives considered**:
- *Dexie.js*: ergonomia melhor, mas nova dependência versionada no cache offline; desnecessária
  para 4 stores simples.
- *localStorage como base*: proibido pela spec (FR-006).

## D4 — Estratégia do Service Worker (precache allowlist)

**Decisão**: **Service Worker próprio** (`/static/js/sw.js`), **precache por allowlist** (lista
explícita de URLs da área de coleta offline: shell HTML + JS + CSS + manifest + ícones),
estratégia **cache-first para os recursos da allowlist** e **network-only para todo o resto**
(incluindo `/api/v1/*` e páginas sensíveis — FR-036). `CACHE_VERSION = "inventario-offline-v1"`
acoplado à versão do schema do IndexedDB; ativação remove caches antigos; `skipWaiting` +
`clients.claim()` controlados. Verificação de servidor real (FR-042) via
`GET /api/v1/inventarios/{id}/offline/ping`.

**Navegação**: apenas a **rota de coleta offline** (`/inventarios/{id}/offline`) é servida
cache-first; toda outra navegação → rede; offline fora da allowlist → fallback estático que
orienta reconectar (nada sensível).

**Rationale**: allowlist satisfaz FR-035/036/037 literalmente; versão do cache e do schema IDB
na mesma constante evita misturas incompatíveis (edge case "SW desatualizado").

**Alternatives considered**:
- *Workbox*: padroniza, mas adiciona build/dependência; o allowlist é pequeno (~6 URLs) —
  desnecessário.
- *Cache-first geral com exclusões*: perigoso (risco de vazar resposta sensível em cache);
  rejeitado por FR-036.

## D5 — Sincronização: transporte, idempotência e conflitos

**Decisão**: um único endpoint em lote `POST /api/v1/inventarios/{inventory_id}/offline/sync`
(recebe até 1.000 operações por requisição), com:

- **Idempotência**: tabela `inventario_offline_coletas` com UNIQUE `(inventory_id, client_operation_id)`;
  reenvio → resposta `duplicated` sem regravar; resultado **igual** ao estado atual do item →
  `duplicated` (já processado, C-5); resultado **diferente** → grava **conflito** (linha com
  `status = CONFLICT` preservando o payload das coletas) — nunca sobrescreve o item conferido (C-5).
- **Resposta estruturada** por operação: `accepted` / `duplicated` / `conflicts` / `rejected`
  (com motivo), conforme FR-024.

**Rationale**: um endpoint em lote minimiza round-trips em campo (SC-005); UNIQUE no banco dá
garantia real de idempotência (padrão usado pelas features 031/032); servidor é a autoridade
(FR-025) — o cliente nunca resolve conflito, apenas registra e preserva.

**Alternatives considered**:
- *Um endpoint por operação*: mais simples, mas 1.000 round-trips inviabilizam o SC-005; rejeitado.

## D6 — Auditoria e datas

**Decisão**: eventos `INVENTARIO_OFFLINE_PREPARADO`, `INVENTARIO_OFFLINE_SYNC`,
`INVENTARIO_OFFLINE_CONFLITO`, `INVENTARIO_OFFLINE_REJEITADO` e `INVENTARIO_OFFLINE_RECONCILED`
no `audit_service` existente, com contexto não sensível (inventário, dispositivo, contagens,
motivos) — nunca credenciais (FR-044). Datas: a coleta preserva `collected_at` declarado pelo
cliente e o servidor grava `received_at` (`now_utc`, padrão do sistema) como referência oficial
(FR-045).

**Alternatives considered**:
- *Tabela de auditoria própria da feature*: proibido (Princípio IX).
- *Confiar no relógio do cliente para eventos oficiais*: rejeitado por FR-045 (edge case
  "relógio do dispositivo incorreto").

## D7 — HTTPS e produção

**Decisão**: Service Worker exige contexto seguro ou localhost. Produção: HTTPS no edge (Nginx),
HTTP interno Nginx→Uvicorn conforme arquitetura atual; a aplicação não gere certificados (FR-033).
Em dev (HTTP localhost) o SW registra normalmente. Pré-requisito de deploy documentado na
implementação (README/quickstart).

**Alternatives considered**:
- *Certificado autoassinado no FastAPI*: proibido (FR-033).
- *HTTP puro em produção*: impossibilita SW/PWA; registrado como pré-requisito de deploy (docs).

## D8 — Expiração do pacote (P-2) e reconciliação de conflitos

**Decisão**: pacote expira por **estado do inventário**: coleta/sync só ocorrem com inventário
PLANNED/IN_PROGRESS; CLOSED bloqueia ambos (C-2, P-2). Reconciliação de conflitos: usuário com
`inventario.conferir` decide na área "Conflitos offline" da tela do inventário entre:

- **"Manter registrado"** — mantém o estado atual do item; coleta `CONFLICT` → `RECONCILED`; ou
- **"Aplicar coleta offline"** — grava via `record_check` (inventário ainda aberto) e marca a
  coleta como `RECONCILED`.

Ambas as ações gravam auditoria do evento `INVENTARIO_OFFLINE_RECONCILED` com a ação escolhida.

**Alternatives considered**:
- *Prazo em dias configurável*: rejeitado na spec (P-2).
- *Reconciliação restrita a admin*: `inventario.conferir` é a permissão que já rege conferência;
  nada de permissão nova (P-1).

## D9 — Pacote: geração e limite de volume

**Decisão**: geração **on-demand** a partir do snapshot `inventario_itens` (sem tabela de pacotes
no servidor que duplique o snapshot); o servidor calcula a **versão do pacote** (hash determinístico
do conjunto de itens — ex.: SHA-256 dos `asset_id` + versão do schema) na hora da preparação. O
registro oficial de sync no servidor é a tabela `inventario_offline_coletas` (2ª tabela nova).
O pacote entregue contém os campos mínimos (FR-003) e a versão (FR-004); limite de 1.000
itens/pacote validado no servidor.

**Rationale**: sem tabela de pacotes, menos duplicação de dados; a versão é determinística do
snapshot (`inventario_itens` é imutável durante inventário aberto — Princípio V).

**Alternatives considered**:
- *Tabela de pacotes com cópia dos itens*: duplica dados já existentes; rejeitado.
- *Sem limite de itens*: sem proteção contra pacote gigante; rejeitado (SC-001 assume 1.000).

## D10 — UI offline (shell + fila)

**Decisão**: shell único `inventarios/offline.html` + `inventario_offline.js` (vanilla, sem build)
com telas embutidas (lista/pesquisa, conferência, fila, conflitos locais, indicador online/offline
com ping real — FR-042), todas renderizadas pelo JS a partir do IndexedDB. Tema claro/escuro via
classes Bootstrap e variáveis CSS existentes (FR-043).

**Alternatives considered**:
- *SPA framework*: proibido (stack da Constitution); rejeitado.
- *Páginas separadas por tela*: mais URLs no allowlist do SW; shell único minimiza allowlist e
  risco de mistura de versões.

## D11 — Permissões (P-1)

**Decisão**: reutilizar `inventario.visualizar` (detalhe/conflitos/fila no servidor) e
`inventario.conferir` (preparar pacote, coletar, sync, reconciliar). Nenhuma permissão nova (P-1);
menu/botões via `can()` são apenas apresentação (Princípio VI).

**Alternatives considered**: permissão dedicada — rejeitada na spec (P-1).

---
*Incógnitas da spec (seção "Dependências externas / informações pendentes"): itens 1 e 2
resolvidos aqui (D1/D2). Item 3 (HTTPS produção) tratado em D7 (pré-requisito de deploy
documentado).*
