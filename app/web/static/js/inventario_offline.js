/**
 * Inventário Offline — núcleo client (feature 033; sem build step, vanilla ES2020+).
 *
 * Armazenamento local (FR-006/D3): IndexedDB `sispatrimonio_offline` (version 1)
 * com stores packages/coletas/sync_queue/device_info. `localStorage` fica
 * restrito a `sp_device_id` (FR-028) e preferências de UI — NUNCA dados de
 * coleta nem credenciais (FR-031).
 *
 * Migração versionada (FR-038/SC-009): `onupgradeneeded` apenas CRIA stores/
 * índices; nenhum store ou registro é apagado em atualizações.
 *
 * API exposta: window.InventarioOffline
 *   .getDeviceId()                 → UUID persistente do dispositivo
 *   .savePackage(package)          → guarda/ativa o pacote no dispositivo
 *   .getPackage(inventoryId)       → lê o pacote armazenado
 *   .prepareFromDetail(button)     → fluxo da tela do inventário (US1)
 */
(function () {
  "use strict";

  var DB_NAME = "sispatrimonio_offline";
  var DB_VERSION = 1; // acoplado ao CACHE_VERSION do Service Worker (D4)

  // ---------------------------------------------------------------------------
  // device_id persistente (FR-028) — UUID local, sem dados pessoais
  // ---------------------------------------------------------------------------
  function uuid4() {
    if (window.crypto && window.crypto.randomUUID) return window.crypto.randomUUID();
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
      var r = (Math.random() * 16) | 0;
      var v = c === "x" ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }

  function getDeviceId() {
    var id = null;
    try {
      id = window.localStorage.getItem("sp_device_id"); // ÚNICO uso de localStorage (FR-006)
    } catch (e) { /* modo privado: cai para device_info */ }
    if (id) return id;
    id = uuid4();
    try {
      window.localStorage.setItem("sp_device_id", id);
    } catch (e) { /* persistido apenas no IndexedDB abaixo */ }
    return id;
  }

  // ---------------------------------------------------------------------------
  // IndexedDB — helpers promise
  // ---------------------------------------------------------------------------
  var dbPromise = null;

  function openDb() {
    if (dbPromise) return dbPromise;
    dbPromise = new Promise(function (resolve, reject) {
      var req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onupgradeneeded = function (event) {
        var db = event.target.result;
        var tx = event.target.transaction;
        // Migração aditiva (FR-038): cria o que falta, NUNCA apaga.
        if (!db.objectStoreNames.contains("packages")) {
          tx.db.createObjectStore("packages", { keyPath: "inventory_id" });
        }
        if (!db.objectStoreNames.contains("coletas")) {
          tx.db.createObjectStore("coletas", { keyPath: "client_operation_id" });
        }
        if (!db.objectStoreNames.contains("sync_queue")) {
          tx.db.createObjectStore("sync_queue", { keyPath: "client_operation_id" });
        }
        if (!db.objectStoreNames.contains("device_info")) {
          tx.db.createObjectStore("device_info", { keyPath: "key" });
        }
      };
      req.onsuccess = function () {
        var db = req.result;
        db.onversionchange = function () { db.close(); }; // não bloqueia migração
        resolve(db);
      };
      req.onerror = function () { reject(req.error); };
    });
    return dbPromise;
  }

  function tx(store, mode, fn) {
    return openDb().then(function (db) {
      return new Promise(function (resolve, reject) {
        var t = db.transaction(store, mode);
        var s = t.objectStore(store);
        var out;
        try {
          out = fn(s);
        } catch (e) {
          reject(e);
          return;
        }
        // Resolve SEMPRE com o resultado real da request: `undefined` quando o
        // registro não existe (get sem match) — nunca o objeto da request.
        t.oncomplete = function () { resolve(out ? out.result : undefined); };
        t.onerror = function () { reject(t.error); };
        t.onabort = function () { reject(t.error); };
      });
    });
  }

  function idbPut(store, value) {
    return tx(store, "readwrite", function (s) { return s.put(value); });
  }
  function idbGet(store, key) {
    return tx(store, "readonly", function (s) { return s.get(key); });
  }
  function idbGetAll(store) {
    return tx(store, "readonly", function (s) { return s.getAll(); });
  }

  // ---------------------------------------------------------------------------
  // Pacote offline (US1)
  // ---------------------------------------------------------------------------
  function savePackage(pkg) {
    pkg.status = "READY"; // READY | EXPIRED (P-2: expira por estado do inventário)
    pkg.saved_at = new Date().toISOString();
    pkg.device_id = getDeviceId();
    return idbPut("packages", pkg).then(function () {
      return idbPut("device_info", {
        key: "device_id",
        value: pkg.device_id,
        created_at: pkg.saved_at,
      });
    });
  }

  function getPackage(inventoryId) {
    return idbGet("packages", Number(inventoryId));
  }

  // ---------------------------------------------------------------------------
  // Fila de sincronização (US3; FR-018..FR-023) — o servidor é a autoridade
  // ---------------------------------------------------------------------------
  var MAX_ATTEMPTS = 5; // retry com limite (FR-023) — sem bloquear o usuário

  function sincronizar(inventoryId, onProgress, onDone) {
    return openDb().then(function (db) {
      return new Promise(function (resolve) {
        db.transaction("sync_queue", "readonly").objectStore("sync_queue").getAll().onsuccess = function (e) {
          var pendentes = (e.target.result || []).filter(function (r) {
            return r.state === "PENDING" || r.state === "FAILED";
          });
          resolve(pendentes);
        };
      });
    }).then(function (pendentes) {
      if (!pendentes.length) {
        if (onDone) onDone();
        return Promise.resolve();
      }
      // marca SYNCING (FR-018)
      return Promise.all(pendentes.map(function (p) {
        p.state = "SYNCING";
        return idbPut("sync_queue", p);
      })).then(function () {
        return Promise.all([
          idbGet("packages", Number(inventoryId)),
          Promise.all(pendentes.map(function (p) {
            return idbGet("coletas", p.client_operation_id);
          })),
        ]);
      }).then(function (arr) {
        var pkg = arr[0];
        var coletas = arr[1].filter(Boolean);
        if (!pkg) throw new Error("Pacote não encontrado no dispositivo.");
        var ops = coletas.map(function (c) {
          return {
            client_operation_id: c.client_operation_id,
            operation: c.operation,
            asset_id: c.asset_id,
            item_id: c.item_id || null,
            result: c.result || null,
            found_location_id: c.found_location_id || null,
            found_location_name: c.found_location_name || null,
            found_custodian_id: c.found_custodian_id || null,
            found_custodian_name: c.found_custodian_name || null,
            observation: c.observation || null,
            collected_at: c.collected_at,
          };
        });
        return fetch("/api/v1/inventarios/" + inventoryId + "/offline/sync", {
          method: "POST",
          credentials: "same-origin", // sessão web existente (C-1)
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            device_id: getDeviceId(),
            snapshot_version: pkg.snapshot_version,
            operations: ops,
          }),
        }).then(function (resp) {
          if (resp.status === 401) throw new Error("Sessão expirada: faça login novamente para sincronizar (coletas preservadas).");
          if (!resp.ok) throw new Error("Falha na sincronização (" + resp.status + ").");
          return resp.json();
        }).then(function (out) {
          var okIds = {};
          (out.accepted || []).concat(out.duplicated || []).forEach(function (x) { okIds[x.client_operation_id] = true; });
          var conflIds = {};
          (out.conflicts || []).forEach(function (x) { conflIds[x.client_operation_id] = true; });
          // Confirmação INEQUÍVOCA antes de alterar estado local (FR-019)
          return Promise.all(pendentes.map(function (p) {
            if (okIds[p.client_operation_id]) {
              p.state = "SYNCED"; // coleta local retida até limpeza (FR-040)
            } else if (conflIds[p.client_operation_id]) {
              p.state = "CONFLICT";
            } else {
              p.state = p.attempts + 1 >= MAX_ATTEMPTS ? "FAILED" : "PENDING";
              p.attempts += 1;
            }
            p.last_attempt_at = new Date().toISOString();
            return idbPut("sync_queue", p);
          })).then(function () {
            var total = (out.accepted || []).length + (out.duplicated || []).length;
            var msg = "Sincronização concluída " + total + "/" + ops.length;
            if (onProgress) onProgress(msg);
            if (onDone) onDone();
            // FAILED → PENDING para permitir nova tentativa manual (FR-023)
            return openDb().then(function (db2) {
              db2.transaction("sync_queue", "readonly").objectStore("sync_queue").getAll().onsuccess = function (e2) {
                (e2.target.result || []).filter(function (r) { return r.state === "FAILED" && r.attempts < MAX_ATTEMPTS; })
                  .forEach(function (r) { r.state = "PENDING"; idbPut("sync_queue", r); });
              };
            });
          });
        });
      }).catch(function (err) {
        // Queda de rede no meio: devolve tudo a PENDING preservando payload (FR-019/FR-023)
        return Promise.all(pendentes.map(function (p) {
          if (p.state === "SYNCING") {
            p.state = "PENDING";
            p.attempts += 1;
            p.last_error = String(err && err.message || err);
            p.last_attempt_at = new Date().toISOString();
            return idbPut("sync_queue", p);
          }
          return Promise.resolve();
        })).then(function () {
          if (onProgress) onProgress(err.message || "Falha de rede; coletas preservadas.");
          if (onDone) onDone();
        });
      });
    });
  }

  // ---------------------------------------------------------------------------
  // Ciclo de vida (US5; P-2/FR-039/FR-040)
  // ---------------------------------------------------------------------------

  /** Consulta o servidor; offline → considera bloqueável apenas por dados locais. */
  function checkServerState(inventoryId) {
    return fetch("/api/v1/inventarios/" + inventoryId + "/offline/ping", {
      credentials: "same-origin", cache: "no-store",
    }).then(function (r) { return r.ok ? r.json() : null; })
      .catch(function () { return null; });
  }

  /** Bloqueia a coleta com pacote expirado (encerrado/re-preparado — P-2). */
  function aplicarBloqueioExpiracao(pkg, motivo) {
    pkg.status = "EXPIRED";
    pkg.expired_reason = motivo;
    return idbPut("packages", pkg);
  }

  /** Limpeza local segura (FR-040): só após sync completo confirmado; informa
   *  exatamente o que será removido; impede perda de pendências. */
  function limparDispositivo(inventoryId) {
    return openDb().then(function (db) {
      return new Promise(function (resolve) {
        db.transaction("sync_queue", "readonly").objectStore("sync_queue").getAll().onsuccess = function (e) {
          resolve(e.target.result || []);
        };
      });
    }).then(function (rows) {
      var pendentes = rows.filter(function (r) { return r.state !== "SYNCED"; }).length;
      if (pendentes > 0) {
        window.alert(
          "Não é possível encerrar a coleta: existem " + pendentes +
          " coleta(s) ainda não confirmada(s) pelo servidor. Sincronize primeiro — " +
          "nenhum dado pendente será apagado (proteção FR-040)."
        );
        return false;
      }
      var msg = "Isto removerá DESTE DISPOSITIVO:\n" +
        "• o pacote offline do inventário " + inventoryId + ";\n" +
        "• " + rows.length + " coleta(s) já sincronizada(s);\n" +
        "• a fila local de sincronização.\n\n" +
        "Os dados oficiais permanecem no servidor. Confirmar?";
      if (!window.confirm(msg)) return false;
      return openDb().then(function (db) {
        return Promise.all([
          new Promise(function (res) {
            var t = db.transaction(["packages", "coletas", "sync_queue"], "readwrite");
            t.objectStore("packages").delete(Number(inventoryId));
            t.objectStore("coletas").clear();
            t.objectStore("sync_queue").clear();
            t.oncomplete = res;
          }),
        ]).then(function () { return true; });
      });
    });
  }

  // ---------------------------------------------------------------------------
  // Fluxo da tela do inventário (botão "Preparar coleta offline")
  // ---------------------------------------------------------------------------
  function prepareFromDetail(btn) {
    var inventoryId = btn.getAttribute("data-inventory-id");
    var original = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Preparando…';

    fetch("/api/v1/inventarios/" + inventoryId + "/offline/package", {
      method: "POST",
      credentials: "same-origin", // sessão web existente (C-1) — nada armazenado (FR-031)
      headers: { "Accept": "application/json" },
    })
      .then(function (resp) {
        if (resp.status === 403) throw new Error("Você não tem permissão para preparar a coleta offline.");
        if (resp.status === 409) throw new Error("Este inventário está encerrado; não pode ser preparado para coleta offline.");
        if (resp.status === 422) throw new Error("Inventário não pode ser preparado (sem itens ou acima do limite de 1.000).");
        if (!resp.ok) throw new Error("Falha ao gerar o pacote offline (" + resp.status + ").");
        return resp.json();
      })
      .then(function (pkg) { return savePackage(pkg); })
      .then(function () {
        // Estado PERSISTENTE de sucesso (o pacote ficou salvo no dispositivo):
        // o botão não volta ao estado anterior.
        marcarPreparado(btn, inventoryId);
      })
      .catch(function (err) {
        btn.disabled = false;
        btn.innerHTML = original;
        window.alert(err.message || "Falha ao preparar a coleta offline.");
      });
  }

  /** Marca o botão como pacote pronto (persistente) e oferece o acesso à
   *  área de coleta offline. Também aplicado ao carregar a página quando o
   *  pacote já existe no dispositivo. */
  function marcarPreparado(btn, inventoryId) {
    btn.setAttribute("data-ready", "1");
    btn.classList.remove("btn-outline-primary");
    btn.classList.add("btn-success");
    btn.disabled = false;
    btn.innerHTML = '<i class="bi bi-check-circle me-1"></i> Pronto para uso offline';
    btn.title = "Pacote salvo neste dispositivo. Clique para preparar novamente (a nova versão substitui a anterior; coletas pendentes permanecem).";
    if (!document.getElementById("linkAbrirOffline")) {
      var link = document.createElement("a");
      link.id = "linkAbrirOffline";
      link.className = "btn btn-ghost";
      link.href = "/inventarios/" + inventoryId + "/offline";
      link.innerHTML = '<i class="bi bi-box-arrow-in-right me-1"></i> Abrir coleta offline';
      btn.parentNode.insertBefore(link, btn.nextSibling);
    }
  }

  // ---------------------------------------------------------------------------
  // Boot
  // ---------------------------------------------------------------------------
  document.addEventListener("DOMContentLoaded", function () {
    // Garante o device_id já na primeira visita à área do inventário
    getDeviceId();
    var btn = document.getElementById("btnPrepararOffline");
    if (btn) {
      var inventoryId = btn.getAttribute("data-inventory-id");
      btn.addEventListener("click", function () {
        if (btn.getAttribute("data-ready") === "1") {
          // Re-preparo controlado (edge case da spec): nova versão substitui
          // a anterior; coletas pendentes ficam na store `coletas`, intactas.
          if (window.confirm("Já existe um pacote preparado neste dispositivo. Preparar novamente? A nova versão substitui a anterior (as coletas pendentes são preservadas).")) {
            prepareFromDetail(btn);
          }
          return;
        }
        prepareFromDetail(btn);
      });
      // Estado persistente: se o pacote já está no dispositivo, reflete ao carregar
      getPackage(inventoryId).then(function (pkg) {
        if (pkg) marcarPreparado(btn, inventoryId);
      });
    }
  });

  // API pública
  window.InventarioOffline = {
    getDeviceId: getDeviceId,
    savePackage: savePackage,
    getPackage: getPackage,
    getAllPackages: function () { return idbGetAll("packages"); },
    sincronizar: sincronizar,
    checkServerState: checkServerState,
    aplicarBloqueioExpiracao: aplicarBloqueioExpiracao,
    limparDispositivo: limparDispositivo,
    _idb: { put: idbPut, get: idbGet, getAll: idbGetAll },
  };
})();
