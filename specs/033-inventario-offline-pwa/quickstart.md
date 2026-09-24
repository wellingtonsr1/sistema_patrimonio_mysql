# Quickstart: Conferência de Inventário Offline (feature 033)

Guia de validação ponta a ponta. Referências: [contract](contracts/inventario-offline-contract.md) · [data-model](data-model.md) · [spec](spec.md)

## Pré-requisitos

- Ambiente de dev rodando (`.venv/bin/python run.py`); login com usuário que tenha
  `inventario.visualizar` + `inventario.conferir` (decisão P-1 — nada de permissão nova).
- **Navegador Chrome/Edge** (leitura de QR via BarcodeDetector é nativa no Chrome Android;
  em desktop Chrome a câmera funciona via `getUserMedia`). Firefox/Safari: usar digitação
  manual (fallback permanente — FR-010/D1).
- Service Worker exige contexto seguro: em dev funciona por ser `localhost`; em produção,
  HTTPS no edge (D7).
- Suíte de regressão: `.venv/bin/python -m pytest tests/ -q` (deve permanecer 100% verde — SC-010).

## Cenários de validação

### C1 — Preparação do pacote (US1 · Testes de origem 1 e 2)

1. **Inventários** → abrir um inventário PLANNED ou IN_PROGRESS → **"Preparar coleta offline"**.
2. Esperado: download/ativação do pacote no dispositivo; confirmação "Pronto para uso offline";
   auditoria `INVENTARIO_OFFLINE_PREPARADO`.
3. **Acesso negado**: usuário sem `inventario.conferir` → botão invisível e, chamando
   `POST /api/v1/inventarios/{id}/offline/package` direto, **403** auditado.
4. **Inventário encerrado** → **409** com mensagem clara (C-2/P-2).

### C2 — Coleta sem conexão (US2 · Testes de origem 3–9)

1. Abrir `/inventarios/{id}/offline` (rota cacheada pelo SW) → DevTools → **Network → Offline**.
2. Recarregar a página: deve continuar abrindo (cache-first) com indicador **🔴 OFFLINE** (FR-041).
3. Escanear o QR de uma etiqueta existente (codifica `{origin}/assets/{asset_id}` — D2) ou
   digitar o tombamento → item identificado.
4. Registrar conferência **com local diferente do esperado** → divergência derivada
   (`LOCAL_DIFERENTE`, mesma regra do fluxo online — C-3); painel atualiza contadores (FR-009).
5. Escanear QR de bem **fora** do pacote → ocorrência "bem não previsto" registrada (FR-014).
6. **Fechar o navegador e reabrir** (e, se possível, reiniciar o dispositivo): coletas
   permanecem íntegras, fila `PENDING` preservada (FR-016/SC-003).

### C3 — Sincronização (US3/US4 · Testes de origem 10–15)

1. Voltar a rede para **Online** → fila dispara sincronização (ou botão "Sincronizar agora").
2. Esperado: resultado "Sincronização concluída N/N"; no inventário oficial, itens conferidos
   aparecem com os status corretos; coletas visíveis em
   `GET .../offline/coletas` (rastreio de device/usuário — US4).
3. **Idempotência**: forçar reenvio do mesmo lote → nada duplicado; resultado igual ao estado
   atual do item → `duplicated` (C-5/SC-004).
4. **Conflito**: com dois dispositivos (ou coleta online + coleta offline pendente), sincronizar
   resultado **diferente** para o mesmo item → `conflicts` na resposta; coleta `CONFLICT`
   preservada; seção **"Conflitos offline"** na tela do inventário lista as duas versões (P-3).
5. **Queda no meio do sync**: interromper a rede após algumas operações → aceitas permanecem
   `SYNCED`; pendentes voltam a `PENDING` e reenvio parcial transfere só o restante (SC-005).
6. **Reconciliação**: em "Conflitos offline", testar `KEEP` e `APPLY` (inventário aberto);
   resultado coerente no item e auditoria `INVENTARIO_OFFLINE_RECONCILED` (D8).

### C4 — Ciclo de vida (US5 · Teste de origem 16)

1. Encerrar o inventário no servidor com pacote ainda ativo no dispositivo → tentativa de
   coleta/sync é bloqueada com orientação para reconectar (P-2; sync rejeita com motivo claro — C-2).
2. **Atualização do SW** (simular nova versão do cache): coletas pendentes preservadas após
   ativação da nova versão; nenhum dado local apagado (FR-038/SC-009).
3. **Limpeza local**: com tudo sincronizado, "Encerrar coleta neste dispositivo" informa o que
   será removido e, confirmado, apaga os dados locais; com pendências, a ação é impedida (FR-040).

### C5 — Segurança e não-regressão (Testes de origem 17–19)

1. **Inspecionar o armazenamento** (DevTools → Application → IndexedDB/Cache Storage): o pacote
   contém apenas os campos do FR-003; **nenhum** dado de usuários/permissões/administração;
   nenhum segredo (SC-008).
2. **Service Worker**: confirmar que apenas as URLs da allowlist da coleta offline estão em
   cache; `/api/*` e páginas administrativas **não** são cacheadas (FR-036).
3. **Cadastro inalterado**: comparar o cadastro de um bem antes/depois de coletas com
   divergências → zero alteração automática (FR-013/SC-007).
4. **Regressão**: suíte completa verde; fluxo online de conferência (`/inventarios/{id}`)
   funcionando como antes (FR-046).

## Automação (pytest — backend)

`.venv/bin/python -m pytest tests/test_inventario_offline.py -q` cobre os 19 cenários de origem
no lado servidor (RBAC 401/403, package/sync/reconcile via TestClient, idempotência via UNIQUE,
conflitos C-5, rejeições com motivo, auditoria sem credenciais, datas received_at/collected_at).
Comportamento exclusivamente do navegador (fila IndexedDB, persistência local, SW cache) é
validado pelos cenários manuais C2/C4 acima — registrado como limitação de automação.
