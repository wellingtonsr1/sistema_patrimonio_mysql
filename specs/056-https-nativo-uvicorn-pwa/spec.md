# Feature Specification: HTTPS nativo (uvicorn SSL) para o PWA na rede (056)

**Feature Branch**: `056-https-nativo-uvicorn-pwa`

**Created**: 2026-09-29

**Status**: Implemented (2026-09-29 — validacao.md V1–V6 PASS; TLS provado via schannel em localhost e IP)

**Input**: Achado da prova de campo da 053 (validacao.md V6): em origin de IP puro (`http://10.39.0.16:8000`) o `navigator.serviceWorker` é `undefined` — origin sem HTTPS não é *secure context*, logo o PWA/coleta offline (033) não funciona nos dispositivos da rede via IP. A doc `docs/HTTPS_LOCAL.md` cobre Linux/Caddy; esta máquina é Windows/XAMPP. Solução: SSL **nativo no uvicorn** (sem proxy novo), com gerador de CA+certificado local (SAN com o IP da LAN) e variáveis de ambiente opcionais — comportamento atual intocado quando desativado.

---

## 1. Contexto (fonte: código real, 2026-09-29)

- `run.py` chama `uvicorn.run(...)` sem parâmetros SSL; `app/config.py` não tem variáveis de TLS.
- `sispatrimoniopro.cert` (commitado) é certificado DER autoassinado para CN `sispatrimoniopro.local`, SEM chave privada no repositório — não servível e sem SAN de IP (inútil para o objetivo; tratado no §Riscos).
- `openssl` CLI disponível (3.5.6). `cryptography` NÃO está no venv (evitar dependência nova).
- O cenário já mapeado na doc (proxy_headers/forwarded_allow_ips para `qr_url`) vale quando o TLS é terminado no próprio uvicorn: sem proxy, as URLs saem `https` nativamente.

## 2. Requisitos

### Functional Requirements

- **FR-001**: `app/config.py` MUST expor `APP_SSL_CERTFILE` e `APP_SSL_KEYFILE` (somente ambiente — padrão SMTP_*/AD_*; sem fallback em banco; default `None`).
- **FR-002**: `run.py` MUST passar `ssl_certfile`/`ssl_keyfile` ao `uvicorn.run` quando AMBOS definidos (imprimindo URL `https://`); quando ausentes, comportamento byte-a-byte atual (HTTP, URL `http://`).
- **FR-003**: `scripts/gera_cert_dev.py` (novo) MUST gerar CA local + certificado de servidor (RSA) com SAN completo — `IP:<ip-lan>`, `DNS:localhost`, `DNS:sispatrimoniopro.local` (+ extras por arg) — em `data/ssl/` via `openssl` CLI; idempotente (não sobrescreve sem `--force`); valida sanidade do IP detectado.
- **FR-004**: `.gitignore` MUST cobrir `data/ssl/` — **chave privada NUNCA vai ao git** (nem ao snapshot PRO via `git archive`).
- **FR-005**: `docs/HTTPS_LOCAL.md` MUST ganhar a seção "Windows nativo (uvicorn SSL)": gerar cert, apontar env vars, reiniciar, instalar `ca.crt` nos aparelhos — mantendo o roteiro Caddy/Linux como alternativa.
- **FR-006**: A suíte NÃO PODE ter comportamento alterado (envs ausentes por default; testes novos são estruturais).
- **FR-007**: Nenhuma dependência nova em `requirements.txt` (openssl CLI já disponível).

### Não-requisitos

- Não HSTS/redirect forçado de HTTP→HTTPS (decisão do operador; documentado).
- Não alterar `app/main.py` (confiança de proxy permanece a atual — sem proxy no cenário nativo).
- Não mexer no cert DER legado (`sispatrimoniopro.cert`) — registrada como dívida de segurança a tratar (§Riscos do plan).

## 3. Critérios de sucesso

| # | Critério |
|---|---|
| SC-001 | Instância na porta 8443 com `APP_SSL_*` responde `https://localhost:8443/health` 200 (curl -k); sem envs, porta 8000 segue HTTP idêntica |
| SC-002 | Em `https://localhost:8443`, `navigator.serviceWorker` É definido e o SW da 033 registra com sucesso (prova real do objetivo) |
| SC-003 | Certificado gerado tem SAN com o IP da LAN (`openssl x509 -text`) e cadeia valida contra a CA gerada |
| SC-004 | Suíte completa 889 passed / 0 failed (nada muda sem envs) |
| SC-005 | `git status` limpo após gerar cert em `data/ssl/` (gitignore efetivo) |

## 4. Assumptions

- Acesso por IP com TLS de CA própria exige importar `ca.crt` nos aparelhos (uma vez) — procedimento já documentado na doc para Android/iPhone.
- Produção (instalador Linux 027) pode adotar o mesmo mecanismo via env vars; o roteiro Caddy/Let's Encrypt permanece recomendado para domínio público.
