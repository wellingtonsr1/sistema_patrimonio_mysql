/**
 * Leitor de QR Code da coleta offline (feature 033; D1/D2 — sem dependências).
 *
 * - BarcodeDetector nativa como mecanismo primário (Chrome/Edge, Android);
 * - fallback PERMANENTE de digitação manual do tombamento/URL (FR-010);
 * - o QR existente codifica a URL {origin}/assets/{asset_id} (D2) — o
 *   asset_id é extraído por regex, sem inventar novo formato (FR-011).
 *   O conteúdo do QR nunca contém credenciais/dados pessoais (FR-011).
 */
(function () {
  "use strict";

  var QR_URL_RE = /\/assets\/(\d+)/; // padrão atual das etiquetas (D2)

  function extractFromUrl(text) {
    var m = String(text || "").match(QR_URL_RE);
    return m ? parseInt(m[1], 10) : null;
  }

  function extractAssetId(text) {
    if (!text) return null;
    var fromUrl = extractFromUrl(text);
    if (fromUrl) return fromUrl;
    // Tolerância: usuário digitou só o número do asset
    if (/^\d+$/.test(String(text).trim())) return parseInt(String(text).trim(), 10);
    return null;
  }

  function detectWithBarcodeDetector(video, onDetected, onError) {
    if (!("BarcodeDetector" in window)) {
      onError(new Error("BarcodeDetector indisponível"));
      return;
    }
    var detector;
    try {
      detector = new window.BarcodeDetector();
    } catch (e) {
      onError(e);
      return;
    }
    var stopped = false;
    function loop() {
      if (stopped) return;
      detector
        .detect(video)
        .then(function (codes) {
          if (stopped) return;
          if (codes && codes.length) {
            var assetId = extractAssetId(codes[0].rawValue);
            if (assetId) {
              stopped = true;
              onDetected(assetId);
              return;
            }
          }
          requestAnimationFrame(loop);
        })
        .catch(function () {
          if (!stopped) requestAnimationFrame(loop);
        });
    }
    requestAnimationFrame(loop);
    return function stop() { stopped = true; };
  }

  function start(onDetected, options) {
    var video = document.getElementById("qrVideo");
    // resolveTag (opcional): tombamento → asset_id (a shell resolve pelo pacote
    // em memória — FR-010 promete aceitar tombamento digitado; sem rede não há
    // outra fonte de resolução)
    var resolveTag = options && typeof options.resolveTag === "function" ? options.resolveTag : null;
    var manualFallback = function () {
      var text = window.prompt(
        "Câmera indisponível neste navegador.\nDigite a URL do QR, o número do bem ou o tombamento (ex.: TMB-2026-1141):"
      );
      if (!text) return;
      var value = String(text).trim();
      if (!value) return;

      // 1) URL do QR — inequívoca
      var urlId = extractFromUrl(value);
      if (urlId) {
        onDetected(urlId);
        return;
      }
      // 2) Tombamento (inclui etiquetas numéricas tipo "000123" — deve casar
      //    pelo pacote ANTES de tratar dígitos como asset_id)
      if (resolveTag) {
        Promise.resolve(resolveTag(value))
          .then(function (id) {
            if (id) {
              onDetected(id);
              return;
            }
            // 3) Dígitos puros sem casar por tag: tolera asset_id digitado
            if (/^\d+$/.test(value)) {
              onDetected(parseInt(value, 10));
              return;
            }
            window.alert(
              'Tombamento "' + value + '" não está na lista deste dispositivo.\n' +
              "Conecte-se e verifique o pacote preparado para este inventário."
            );
          })
          .catch(function () {
            window.alert("Não foi possível localizar o valor informado.");
          });
        return;
      }
      // Sem resolveTag: comportamento antigo (URL ou número)
      var assetId = extractAssetId(value);
      if (assetId) onDetected(assetId);
      else window.alert("Valor não reconhecido como QR de etiqueta ou tombamento.");
    };

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      manualFallback();
      return;
    }
    navigator.mediaDevices
      .getUserMedia({ video: { facingMode: "environment" } })
      .then(function (stream) {
        video.style.display = "";
        video.srcObject = stream;
        video.setAttribute("autoplay", "");
        return video.play();
      })
      .then(function () {
        var stop = detectWithBarcodeDetector(
          video,
          function (assetId) {
            stopStream(video);
            if (stop) stop();
            video.style.display = "none";
            onDetected(assetId);
          },
          function () {
            stopStream(video);
            video.style.display = "none";
            manualFallback();
          }
        );
        if (!stop) {
          // BarcodeDetector ausente: para a câmera e cai para o manual
          stopStream(video);
          video.style.display = "none";
          manualFallback();
        }
      })
      .catch(function () {
        video.style.display = "none";
        manualFallback(); // permissão negada / sem câmera (edge case da spec)
      });
  }

  function stopStream(video) {
    var s = video.srcObject;
    if (s && s.getTracks) s.getTracks().forEach(function (t) { t.stop(); });
    video.srcObject = null;
  }

  window.QRReader = { start: start, extractAssetId: extractAssetId };
})();
