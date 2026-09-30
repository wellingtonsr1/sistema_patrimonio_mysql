# Registro de Validação — Feature 056 (Constituição XII)

**Data**: 2026-09-29 · **Feature**: HTTPS nativo (uvicorn SSL) para o PWA na rede via IP
**Método**: TDD estrutural (4 testes escritos e vistos falhar) + prova real de TLS (instância na 8443, curl + PowerShell/schannel) + validação de cert via openssl + réguas de suíte.

## Alteração aplicada (diff confinado)

| Arquivo | Mudança |
|---|---|
| `app/config.py` | +14: `APP_SSL_CERTFILE`/`APP_SSL_KEYFILE` (somente ambiente; None = HTTP atual) |
| `run.py` | Passagem condicional de `ssl_certfile`/`ssl_keyfile` ao uvicorn + prints com esquema dinâmico |
| `scripts/gera_cert_dev.py` | **Novo** — CA local + cert do servidor com SAN (`IP:<lan>`, `localhost`, hostname, `sispatrimoniopro.local`); idempotente (`--force`); openssl CLI, zero dependência nova |
| `.gitignore` | `data/ssl/` — chave privada nunca versionada (FR-004) |
| `docs/HTTPS_LOCAL.md` | Seção "Windows nativo (uvicorn SSL)" no topo das opções |
| `tests/test_https_config_056.py` | **Novo** — 4 testes estruturais (TDD red→green) |

**Zero alteração** em rotas/services/models/templates; `requirements.txt` intocado.

## V1 — TDD (SC de estrutura) ✅

RED: 4/4 failed (config sem envs, run.py sem SSL, script inexistente, gitignore sem data/ssl). GREEN: 4/4 após implementação — incluindo recarga de `app.config` com monkeypatch delenv provando defaults `None` (suíte inalterada, FR-006).

## V2 — Certificado real com SAN do IP (SC-003) ✅

`python scripts/gera_cert_dev.py` → detectou LAN `10.39.0.16` (hostname PMJP661745) e gerou em `data/ssl/`. `openssl verify -CAfile ca.crt server.crt` → **OK**. SAN: `IP:10.39.0.16, DNS:localhost, DNS:PMJP661745, DNS:sispatrimoniopro.local`. Regeneração idempotente validada (bloqueia sem `--force`).

## V3 — HTTPS ponta a ponta com HTTP intocado (SC-001) ✅

Instância com `APP_PORT=8443` + `APP_SSL_*`: uvicorn loga `running on https://0.0.0.0:8443`; `curl -sk https://localhost:8443/health` → JSON healthy; **`https://10.39.0.16:8443/health` → 200 via IP**. Paralelamente, a instância HTTP original na 8000 respondeu 200 intocada — o opt-in não afeta o modo atual.

## V4 — Confiança da CA no trust store do Windows (SC-002, prova decisiva) ✅

Após `certutil -user -addstore Root data/ssl/ca.crt`:
`Invoke-WebRequest https://localhost:8443/health` e `https://10.39.0.16:8443/health` → **200 SEM bypass de certificado** (schannel valida cadeia + SAN do IP). Esse é o mesmo trust store dos Chrome/Edge reais — em navegador comum o cadeado fica válido.

**Limitação registrada**: o Chromium **embutido do Freebuff** aborta o handshake contra a CA nova (cache de erro pré-instalação, sem página de aviso navegável) — limitação do tool de prova, não do sistema; a validação schannel cobre o critério (SW registra em qualquer navegador real sobre HTTPS, pois `serviceWorker` passa a existir em secure context — mecanismo provado na 053: em IP+HTTP ele é `undefined`).

**Remoção da CA de teste do store deste usuário**: `certutil -user -delstore Root "SisPatrimonio Pro - CA local (dev)"` (documentado na doc; a CA gerada vale por ~10 anos).

## V5 — Segurança e réguas (SC-004/SC-005/FR-004) ✅

- `git status` com certificados gerados: **nenhum arquivo de `data/ssl/` aparece** (gitignore efetivo; `git archive` do deploy nunca leva chaves).
- Suíte completa: **893 passed / 0 failed** (63,5s) = 889 + 4 novos. Nada que passava passou a falhar.
- Cert DER legado `sispatrimoniopro.cert`: verificado NÃO conter chave privada (grep = 0) — é cert público autoassinado (CN `sispatrimoniopro.local`, vence 2029). Dívida de higiene registrada no plan (remover do repo em feature futura); inútil para este objetivo (sem chave, sem SAN de IP). **RESOLVIDA (2026-09-29)**: removido do repo via `git rm`; `.gitignore` agora bloqueia `*.cert`/`*.crt`/`*.pem`/`*.key` soltos (material TLS só em `data/ssl/`, ignorado).

## V6 — Decisões

- **D1**: openssl CLI em vez de `cryptography` (evita dependência nova; 3.5.6 disponível).
- **D2**: CA válida 10 anos, server 825 dias (limite prudente p/ CA privada).
- **D3**: sem redirect HTTP→HTTPS nesta feature (decisão do operador; doc registra como restringir HTTP).
- **D4**: `--force` + validação de IP não-loopback/link-local no gerador.

## V7 — Ativação PERMANENTE no servidor real (2026-09-29) ✅

- **`.env` do servidor** ganhou `APP_SSL_CERTFILE=data\ssl\server.crt` e `APP_SSL_KEYFILE=data\ssl\server.key` (permanente; sobrevive a reinícios/reboot).
- **App reiniciado na porta 8000 padrão**: log `Uvicorn running on https://0.0.0.0:8000`; health por localhost e por IP → 200; **schannel sem bypass → 200** (cadeia confiável no SO); HTTP simples → recusado (000; TLS-only).
- **Prova de navegador REAL (Chromium embutido, agora sem bloqueio)**: `https://localhost:8000` renderiza o login com `window.isSecureContext === true` e **`"serviceWorker" in navigator === true`** (o objeto que NÃO existia em `http://10.39.0.16:8000` — achado origem desta feature). Após login: visita a `/inventarios/1` → **SW registrado e ATIVADO** (scope `https://localhost:8000/`), cache `inventario-offline-v32` com as 14 entradas precacheadas; screenshot mostra a tela do inventário com o botão "Preparar coleta offline" (viewport 375px).
- **Usuário temporário da prova** (`fieldtest_tmp`): reativado só para o login da prova e **desativado ao final**; backup do `.env` removido.
- **Nota operacional**: o bloqueio anterior do Chromium embutido (validação V4, porta 8443 de teste) não se repetiu na porta 8000 com o app real — a CA instalada no store do usuário foi suficiente; qualquer Chrome/Edge comum segue o mesmo caminho.
- **Checklist para cada celular da rede** (única pendência de campo, depende de aparelho físico):
  1. Copiar `data/ssl/ca.crt` ao aparelho e importar como CA (Android: Configurações → Segurança → Instalar certificado → CA; iPhone: perfil + confiança total).
  2. Acessar `https://10.39.0.16:8000` → cadeado válido.
  3. Login → Inventários → "Preparar coleta offline" → instalar PWA ("Adicionar à tela inicial") → "Ler QR" com câmera.

## V8 — Documentação de produção (follow-up da revisão) ✅

`docs/DEPLOY_PRODUCAO.md` ganhou a **§5.1 HTTPS nativo**: passos no servidor de produção (gerar CA+cert com `--ip <IP-DO-SERVIDOR>`, apontar `.env`, reiniciar serviço, confiar na `ca.crt` nos aparelhos), com as regras de segurança (`data/ssl/` por máquina — chave NUNCA copiada/versionada; alternativa via CA corporativa AD CS), nota de TLS-only na 8000 e renovação. Modelo do `.env` (Seção 4) atualizado com as duas variáveis comentadas.

## V9 — Cookie de sessão Secure ativado (follow-up da análise de 2026-09-30, achado M-N2) ✅

**Data**: 2026-09-30 · **Mudança**: linha `AUTH_COOKIE_SECURE=true` no `.env` do servidor (commit `26ea8ec` já wireava o flag em `session_service.py:98`; faltava ativar no ambiente).

Provas executadas (servidor real, porta 8000, TLS):

1. **Header `Set-Cookie` do login real** (curl sobre HTTPS, usuário temporário `cookietest_2120`): `session=…; HttpOnly; Max-Age=28800; Path=/; SameSite=lax; **Secure**` — o flag é emitido pelo runtime (prova empírica de que o processo carregou a variável).
2. **Login em navegador real (Chromium)**: `https://localhost:8000` → credenciais submetidas → redireção ao dashboard (`200`, `isSecureContext: true`); cookie `HttpOnly` invisível ao JS (comportamento correto) e devolvido nas requisições seguintes.
3. **Persistência da sessão em rota autenticada**: navegação a `/inventarios/1` renderiza a página completa do inventário (INV-2026-0001, 45 bens, botão "Preparar coleta offline") — sessão válida em requisições subsequentes.
4. **Rede**: todas as respostas 200; console limpo.
5. **Usuário temporário desativado** ao final (rastro de auditoria preservado).

Nota operacional (herdada do `.env.example`): se um dia o HTTPS for desativado (remover `APP_SSL_*`), remover também `AUTH_COOKIE_SECURE=true`, sob pena de o login parar (navegadores não enviam cookie Secure por HTTP).

## Resultado

**V1–V9: PASS** — SC-001..005 satisfeitos; HTTPS permanente ativo na porta 8000, PWA com SW ativado (prova real de navegador), cookie de sessão com flag Secure em produção; documentação de produção completa; pendência restante é apenas o passo físico por aparelho (checklist V7).
