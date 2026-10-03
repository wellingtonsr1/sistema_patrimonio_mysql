# Quickstart — Feature 061 (validação por fase)

*Guia de execução/validação. A implementação detalhada fica em `tasks.md`. Comandos adaptam-se ao ambiente real encontrado (spec FR-005).*

## Fase 1 — Diagnóstico (somente leitura; checkpoint)

**Pré-requisitos**: acesso de leitura ao GitHub da dev e do PRO; máquina Linux (esta) e, quando disponível, a máquina Windows do operador.

```bash
# 0. Estado limpo antes de começar (e igual ao fim da fase)
git status --short && git branch --show-current

# 1. Inventário da dev
git log --oneline -15
git ls-files | wc -l
git ls-files | grep -E '(~$|-old$|_teste_)'        # residuais commitados?
grep -ri xampp --include='*' -l . 2>/dev/null        # versionado: esperado vazio
grep -rniE 'mysql\+pymysql|mariadb\+pymysql|DATABASE_URL' app/ run.py .env.example

# 2. Baseline HTTPS da dev
sed -n '80,150p' app/config.py                       # APP_PORT/APP_SSL_*/AUTH_COOKIE_SECURE
grep -n ssl run.py
python scripts/gera_cert_dev.py --help               # gerador da 056 (sem executar --force)
ls -la data/ssl/ 2>/dev/null || echo 'sem data/ssl local (ok fora da máquina Windows)'

# 3. Snapshot PRO × whitelist
git clone --depth 5 git@github.com:wellingtonsr1/SisPatrimonioPro.git /tmp/pro-read
git ls-tree -r --name-only HEAD > /tmp/dev-tree.txt  # referência dev
ls /tmp/pro-read                                     # comparar com whitelist do research F1
# procurar o instalador Windows versionado (Q3):
find /tmp/pro-read -iname '*install*' -o -iname '*.bat' -o -iname '*.ps1'

# 4. Baseline de testes (registrar resultado!)
.venv/bin/python -m pytest -q                        # Linux (esperado: padrão da 056 = 889 passed)
```

```powershell
# 5. Na máquina Windows (quando disponível): baseline funcional do HTTPS
Get-Service | Where-Object { $_.Name -match 'mysql|sispat' }
mysql --version ; where.exe mysql
Get-Content .env | Select-String 'APP_|SSL|COOKIE|DATABASE_URL'
Get-NetFirewallRule -DisplayName '*SisPat*' -ErrorAction SilentlyContinue
Test-NetConnection localhost -Port 8000
```

**Resultado esperado**: `specs/061.../diagnostico.md` com causas prováveis/confirmadas (inclui a causa raiz do HTTPS perdido no instalador Windows, com evidência arquivo:linha), matriz B preenchida, baseline de testes registrado, `git status` limpo.

## Fase 2 — Planejamento (contrato de arquivos)

Não há comandos: validar que a lista Alterar/Criar/Remover/Não alterar cobre 100% das causas confirmadas da Fase 1 e nada além (D-005). O responsável aprova a lista.

## Fase 3 — Implementação (por lote; suíte verde ao fim de cada um)

```bash
# após cada lote:
.venv/bin/python -m pytest -q                        # Linux
./test.bat -q                                        # Windows (runner oficial 054)
git status --short                                   # só arquivos da lista da Fase 2
```

## Fase 4 — Validação (matriz de cenários)

| Cenário | Comando/ação | Resultado esperado |
|---|---|---|
| dev Linux + MariaDB | `.venv/bin/python run.py` com `.env` atual | app no ar; TLS conforme envs da máquina (baseline preservado) |
| dev Windows + MySQL | mesma dev na máquina Windows | comportamento idêntico ao baseline |
| instalação Linux limpa | `sudo bash install.sh` (VM limpa) | systemd ativo; `https://<host>:8000/health` 200; CA importada no cliente valida cadeia |
| instalação Windows limpa | instalador Windows corrigido (VM limpa + MySQL nativo, sem XAMPP) | `https://<host>:8000/health` 200 sem passo manual; firewall com regra criada |
| atualização | instalador sobre instalação existente | dados intactos; HTTPS permanece; cert existente não regenerado sem motivo |
| reinstalação | segunda execução do instalador | idempotência: nada recriado; `/health` OK |
| banco existente/inexistente | instalar apontando para banco com dados / sem banco | reutiliza / cria — nunca apaga |
| HTTPS pós-reboot | reiniciar servidor | serviço sobe com TLS (SC-004) |
| http na porta TLS | `curl -sS http://host:8000/health` | falha de handshake (sem redirect — D-002) |
| segredos | `git ls-files | xargs grep -lE 'BEGIN.*PRIVATE KEY|PASSWORD='` + revisão de logs do instalador | nada sensível (SC-009) |

## Fase 5 — Deploy ponta a ponta

```bash
# Linux publica
./deploy.sh pre && ./deploy.sh "Feature 061 — padronização do ecossistema"
# Windows publica a mesma dev
deploy.bat "Feature 061 — padronização do ecossistema"
# comparar os dois snapshots (mesma dev) — devem ser equivalentes (SC-007)
git fetch git@github.com:wellingtonsr1/SisPatrimonioPro.git main
# instalar a partir do PRO em VM limpa e repetir a checagem de HTTPS
```

**Critério de parada de cada fase**: itens do checklist da fase verdes + zero regressão (SC-001) + nada fora da lista da Fase 2 (D-005).
