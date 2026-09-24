# Contract de UI: Shell de Conferência Offline (035)

Contrato de apresentação da shell `GET /inventarios/{inventario_id}/offline` — define o que a mudança de layout **não pode quebrar**. Nenhum contrato de API/dados muda nesta feature (ver contracts da 033).

## §1 Contrato DOM (JS ↔ template — IDs, names e classes funcionais intocados)

O `inventario_offline.js` (externo) e os scripts inline do template selecionam elementos por identificador. **Nenhum deles pode ser removido, renomeado ou perder a função.**

**IDs obrigatórios** (consumidos por `getElementById`):

| ID | Origem | Função |
|---|---|---|
| `buscaItem` | JS inline (`renderItens`/filtro) | Campo de pesquisa da lista |
| `btnLerQR` | JS inline | Abre leitor de QR |
| `itensBody` | JS inline | `<tbody>` renderizado por `renderItens` |
| `avisoPacote` | JS inline | Alerta de erro do pacote |
| `semPacoteDica` | JS inline | Dica "Preparar coleta offline" |
| `btnSincronizar` / `btnLimpar` | JS inline | Ações do card de sincronização |
| `pendenciasBadge` / `syncStatusLinha` | JS inline | Painel de pendências |
| `cntConferidas` / `cntRestantes` / `cntDivergencias` / `cntNaoPrevistos` | JS inline | Contadores do painel |
| `offlineModeIndicator` | JS inline | Indicador de conexão (st-ok/st-off/st-wait) |
| `darkToggle` / `darkIcon` | JS inline | Alternância de tema |
| `modalColetaOffline`, `formColetaOffline`, `mTag`, `mLocalEsperado`, `mLocalWrap`, `mFoundLocationName`, `mObservacao` | JS inline | Modal de conferência |
| `qrVideo` | `qr_reader.js` | Vídeo do leitor de QR |

**Atributos `name` obrigatórios**: `m_result` (radios do modal, via `querySelector('input[name="m_result"]:checked')`).

**Classes funcionais consumidas pelo JS/CSS** (não podem sumir dos elementos): `offbar-status` + `st-ok`/`st-off`/`st-wait`, `dot`, `st-label`, `badge-soft-primary`, `badge-soft-gray`, `tag-badge`, `result-option`, `btn-ghost`, `btn-outline-primary`, `btn-primary`, `form-control`, `painel-item`.

## §2 Contrato de comportamento do layout (novo — verificação da 035)

1. Marca empilhada: logo (32px) acima, "SisPatrimônio Pro" abaixo, centralizados entre si — espelhando `.navbar-brand` do `style.css` (D1).
2. Container: ≥768px → `container-fluid` + `max-width: 90%` + padding `px-lg-5` (igual `base.html`); ≤767px → 100% + padding `.75rem` (C-1).
3. Linha pesquisa + "Ler QR" (contorno, C-2) e tabela ocupam a mesma largura do card; cabeçalhos alinhados às colunas.
4. Rolagem horizontal restrita à tabela (`table-responsive`); página sem transbordo (`overflow-x: hidden` preservado).
5. ≤767px: código + indicador de conexão na 2ª linha do cabeçalho (C-3); "Ler QR" nunca cortado.
6. Tema claro/escuro funcional via variáveis existentes (`--color-primary`, `--c-text`, etc.).

## §3 O que NÃO muda (vedações)

- Rota, autenticação/permissões, respostas HTTP da shell (200/401/403/404).
- Payload do pacote, coleta, IndexedDB (`sispatrimonio_offline`), fila e reconciliação.
- `PRECACHE_URLS` e handlers do SW — apenas `CACHE_VERSION` v24 → v25.
- Textos/labels funcionais ("Ler QR", "Sincronizar agora", estados, badges).
- `tests/test_inventario_offline.py` — nenhum assert alterado.

## §4 Critério de conformidade

A implementação está conforme este contrato quando: (a) todos os IDs/names/classes do §1 existem com a mesma função; (b) §2 é verificado no quickstart (V1–V4); (c) suíte pytest 100% verde; (d) `git status` mostra apenas template da shell + `sw.js` (versão de cache) + artefatos da spec.
