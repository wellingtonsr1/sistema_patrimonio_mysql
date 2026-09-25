/**
 * Service Worker da coleta offline de inventário (feature 033; D4).
 *
 * - Precache por ALLOWLIST explícita (shell + JS + CSS + manifest + ícones) — FR-035;
 * - cache-first APENAS na allowlist e navegação cache-first APENAS em
 *   `/inventarios/{id}/offline`; todo o resto (incluindo `/api/*`) é
 *   NETWORK-ONLY — nenhuma resposta sensível é cacheada (FR-036);
 * - CACHE_VERSION acoplado ao schema do IndexedDB (D4); ativação remove
 *   caches antigos (FR-037); coletas locais nunca são afetadas (FR-038/SC-009).
 */
"use strict";

var CACHE_VERSION = "inventario-offline-v31"; // v31: contador de conflitos sincroniza com reconciliações do servidor (C-8) · v30: fallback offline do atalho · v29: tombamento no fallback manual · v28: Ler QR vira FAB · v27: .dark-toggle padrão · v26: sticky do header · v25: layout 035 · ↔ DB_VERSION=1 do IndexedDB (D3/D4)
var OFFLINE_NAV_RE = /^\/inventarios\/\d+\/offline$/;

// Allowlist explícita (FR-035) — nada além disso entra em cache
var PRECACHE_URLS = [
  "/static/css/style.css?v=20260924",
  "/static/vendor/css/bootstrap.min.css",
  "/static/vendor/css/bootstrap-icons.css",
  "/static/vendor/css/fonts/bootstrap-icons.woff2",
  "/static/vendor/css/fonts/bootstrap-icons.woff",
  "/static/vendor/js/bootstrap.bundle.min.js",
  "/static/js/inventario_offline.js",
  "/static/js/qr_reader.js",
  "/static/offline-start.html",  // fallback offline do atalho do PWA (navegação sem rede)
  "/static/manifest.webmanifest",
  "/static/icons/pwa-icon-192.png",
  "/static/icons/pwa-icon-512.png",
  "/static/img/Logo_IPMjp_2.png",
  "/static/img/favicon.ico",
];

self.addEventListener("install", function (event) {
  event.waitUntil(
    caches.open(CACHE_VERSION).then(function (cache) {
      return cache.addAll(PRECACHE_URLS);
    }).then(function () {
      // Ativação controlada: não assume controle abrupto de páginas abertas
      return self.skipWaiting();
    })
  );
});

self.addEventListener("activate", function (event) {
  event.waitUntil(
    caches.keys().then(function (keys) {
      // Remove APENAS caches desta feature (FR-037 — remoção segura)
      return Promise.all(
        keys
          .filter(function (k) { return k.startsWith("inventario-offline-") && k !== CACHE_VERSION; })
          .map(function (k) { return caches.delete(k); })
      );
    }).then(function () {
      return self.clients.claim();
    })
  );
});

self.addEventListener("fetch", function (event) {
  var url = new URL(event.request.url);
  if (url.origin !== self.location.origin) return; // CDNs: rede

  var path = url.pathname;

  // FR-036: rede SEMPRE — nenhuma resposta de API é cacheada
  if (path.startsWith("/api/")) return;

  // Navegação: cache-first somente na rota da coleta offline (D4)
  if (event.request.mode === "navigate") {
    if (OFFLINE_NAV_RE.test(path)) {
      event.respondWith(
        caches.match(event.request).then(function (cached) {
          var fetchPromise = fetch(event.request).then(function (response) {
            if (response && response.ok) {
              var clone = response.clone();
              caches.open(CACHE_VERSION).then(function (c) { c.put(event.request, clone); });
            }
            return response;
          }).catch(function () {
            return cached || caches.match(event.request);
          });
          return cached || fetchPromise;
        })
      );
    }
    // Demais navegações: rede; se falhar (sem rede ao abrir o atalho do PWA,
    // ex.: start_url /inventarios), serve o fallback offline-start em vez da
    // página morta do navegador (a coleta em si já funciona offline)
    event.respondWith(
      fetch(event.request).catch(function () {
        return caches.match("/static/offline-start.html").then(function (fallback) {
          return fallback || Response.error();
        });
      })
    );
  }

  // Estáticos: cache-first apenas para URLs da allowlist
  if (PRECACHE_URLS.indexOf(path + (url.search || "")) >= 0 || PRECACHE_URLS.indexOf(path) >= 0) {
    event.respondWith(
      caches.match(event.request).then(function (cached) {
        return cached || fetch(event.request).then(function (response) {
          if (response && response.ok) {
            var clone = response.clone();
            caches.open(CACHE_VERSION).then(function (c) { c.put(event.request, clone); });
          }
          return response;
        });
      })
    );
  }
  // Todo o resto: rede (sem interceptação)
});
