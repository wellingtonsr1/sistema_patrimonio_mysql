# Implementation Plan: HTTPS nativo (uvicorn SSL) para o PWA na rede (056)

**Branch**: `056-https-nativo-uvicorn-pwa` · **Spec**: [spec.md](spec.md) · **Created**: 2026-09-29

## Summary

TLS terminado no próprio uvicorn via `ssl_certfile`/`ssl_keyfile` (env vars `APP_SSL_CERTFILE`/`APP_SSL_KEYFILE`), com gerador de CA local + certificado de servidor (SAN do IP da LAN) usando o `openssl` CLI já disponível. Zero dependência nova, zero mudança de comportamento sem as envs.

## Constitution Check

| Princípio | Status | Nota |
|---|---|---|
| I. Evolução incremental | PASS | Opt-in por env; default intocado |
| II. Arquitetura em camadas | PASS | Config + entrypoint + script de suporte |
| III. Regras de negócio | PASS | Zero regra tocada |
| IV/V. Integridade patrimonial | PASS | Intocada |
| VI. Segurança RBAC | PASS | Segredos só no ambiente (padrão VI); chave privada fora do git (FR-004) |
| VII. Banco protegido | PASS | Zero DDL |
| VIII. Testes como não-regressão | PASS | Suíte inalterada (FR-006); testes estruturais novos |
| IX. Auditoria | PASS | Intocada |
| XI. Documentação fiel | PASS | HTTPS_LOCAL.md ganha a seção Windows nativa (FR-005) |
| XII. Especificações e validação | PASS | validacao.md com provas SC-001..005 |

**GATE: PASS 10/10**

## Design

### D1 — Config (`app/config.py`, após load_dotenv — guarda da 018)

```python
# HTTPS nativo (feature 056): caminhos do certificado/chave do servidor.
# Somente ambiente (padrão VI); None = HTTP puro (comportamento atual).
APP_SSL_CERTFILE = os.getenv("APP_SSL_CERTFILE") or None
APP_SSL_KEYFILE = os.getenv("APP_SSL_KEYFILE") or None
```

### D2 — `run.py`

```python
from app.config import APP_SSL_CERTFILE, APP_SSL_KEYFILE
ssl_args = {}
if APP_SSL_CERTFILE and APP_SSL_KEYFILE:
    ssl_args = {"ssl_certfile": APP_SSL_CERTFILE, "ssl_keyfile": APP_SSL_KEYFILE}
esquema = "https" if ssl_args else "http"
...
uvicorn.run("app.main:app", host=APP_HOST, port=APP_PORT, reload=False, **ssl_args)
```

Prints passam a usar `{esquema}://{host}:{porta}` (mostra https quando ativo).

### D3 — `scripts/gera_cert_dev.py`

- Detecta o IP LAN (UDP connect trick — sem pacotes: `socket.connect(("10.255.255.255",1))` e lê `getsockname()`), com `--ip` para sobrescrever.
- `openssl req -x509` → CA (`ca.key`, `ca.crt`, CN "SisPatrimônio Pro — CA local (dev)").
- `openssl req` com config mínima embutida (SAN: `IP:<ip>`, `DNS:localhost`, `DNS:sispatrimoniopro.local`, `DNS:<hostname>`) → chave do servidor + CSR → `openssl x509 -req -CA ca.crt -CAkey ca.key -extfile` com `subjectAltName`/`keyUsage`/`extendedKeyUsage=serverAuth`/`basicConstraints=CA:FALSE`.
- Saída em `data/ssl/` (`ca.crt`, `server.crt`, `server.key`, permissão 0600 no key quando POSIX); idempotente (`--force` para regerar); valida que o IP detectado não é loopback/link-local.

### D4 — Testes estruturais (`tests/test_https_config_056.py`)

1. config: defaults `None` sem envs (hermeticidade — monkeypatch delenv).
2. run.py: contém a passagem condicional de `ssl_certfile/ssl_keyfile` e o esquema dinâmico (leitura de texto, padrão 053).
3. script: existe, contém SAN `IP:`/`localhost`/`sispatrimoniopro.local` e `--force`.
4. gitignore: contém `data/ssl/`.

### D5 — Riscos

| Risco | Mitigação |
|---|---|
| Chave privada vazada no git/PRO | `data/` já está no whitelist do PRO, mas `data/ssl/` vai no `.gitignore` (nunca versionada; `git archive` do deploy só leva commitados) |
| Cert DER legado commitado (`sispatrimoniopro.cert`) | **Não é chave privada** (grep -c "PRIVATE KEY" = 0) — é cert público autoassinado vencendo 2029; registrar como dívida de higiene (remover do repo em feature futura), sem ação nesta spec |
| Aparelho não confia na CA | Procedimento de import da `ca.crt` já documentado (Android/iPhone) — mantido e referenciado |
| Porta 8443 bloqueada | Doc registra liberação no firewall do Windows |

## Complexity Tracking

Nenhuma violação.
