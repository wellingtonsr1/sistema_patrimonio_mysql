# Research — Feature 061 (Fase 0: fatos verificados + decisões do plano)

**Data**: 2026-10-02 · **Método**: somente leitura (Fase 1 do sistema ainda não executa) · Fontes: repositório atual (dev), `deploy.sh`/`deploy.bat`/`install.sh`/`test.bat`, `app/config.py`, `run.py`, `scripts/gera_cert_dev.py`, git log.

## Fatos verificados

### F1 — Fluxo de deploy real (whitelist extraída dos scripts)

`deploy.sh` (196 linhas) e `deploy.bat` (248 linhas), subcomandos `publicar / pre / historico / rollback`:

```text
publicar:  1) git add -A + commit (se pendências) na dev
           2) git push origin HEAD:main          → GitHub da dev (histórico completo)
           3) git archive HEAD → tmp → filtrar whitelist → git init + add -A (+ add -f data)
              → 1 commit "… (snapshot de produção de <host>, commit dev <hash>)"
              → git push --force PRO REPO main
rollback:  mesma whitelist sobre o commit dev <hash> citado, push --force no PRO
```

**Whitelist do snapshot** (o que `git archive` mantém no nível raiz): `app/`, `data/`, `docs/`, `.gitignore`, `README.md`, `requirements.txt`, `run.py`, `seed_demo.py`, `sistema_patrimonio.png`, `SPEC-KIT-SISTEMA-ATUAL.md`; em `docs/`: apenas `*.md` (removidos `doc_provi*` e não-`.md`); criados `data/backups/.gitkeep` e `data/logs/.gitkeep`.

**Consequências a auditar na Fase 1** (insumo para divergências dev×PRO):

- A whitelist **não** envia ao PRO: `specs/`, `tests/`, `scripts/` (inclui `gera_cert_dev.py`), `install.sh`, `uninstall.sh`, `deploy.*`, `test.bat`, Docker — cada um deve ser classificado (necessário no PRO? onde o instalador Windows busca o gerador de certificado?).
- A whitelist **pode** enviar itens acidentais presentes na raiz/arquivos commitados (ex.: `app/config.py~`, `_teste_smtp_direto.py` se commitados — a confirmar com `git ls-files`).
- Equivalência `deploy.sh` × `deploy.bat` a provar linha a linha (248 vs 196 linhas — divergência de tamanho justificável por sintaxe, não por conteúdo).
- Push `--force` no PRO: comportamento intencional (snapshot), mas qualquer rollback oficial deve partir do `deploy.sh rollback`, não do `git reset` manual.
- **Nota (plan, 2026-10-02)**: existe um **terceiro repositório** (`SisPatrimonioPro-install`) na arquitetura real — ver F5. As tarefas T008/T009 passam a considerar os 3 repos.

### F2 — Baseline de configuração da aplicação (código atual, confirma a 056)

- `app/config.py` (linhas 93–143): `APP_HOST` default `0.0.0.0` (o `192.168.0.9`/`10.39.0.16` dos docs antigos é específico do operador), `APP_PORT` default `8000`, `APP_SSL_CERTFILE`/`APP_SSL_KEYFILE` com normalização de caminho (`_normaliza_caminho_cert`) e default `None` (sem TLS), `AUTH_COOKIE_SECURE` default `false` (`session_service.py` aplica `secure=` no cookie).
- `run.py` passa `ssl_certfile/ssl_keyfile` ao `uvicorn.run` quando os dois envs existem; sem envs, HTTP byte-a-byte (056 FR-002).
- `scripts/gera_cert_dev.py`: único script em `scripts/` — CA local + cert de servidor (SAN `IP:<lan>`, `DNS:localhost`, `DNS:sispatrimoniopro.local`) em `data/ssl/` (fora do versionamento).
- `.env` da máquina Windows (baseline a documentar na Fase 1 a partir da máquina): porta atual em uso pode ser **8001** (commit `a50cbf9` "Alteração de porta de 8000 para 8001") — a decisão da spec (D-006) fixa **8000 na instalação/produção**; o `.env` da instalação instalará `APP_PORT=8000` (clarity: dev pode diferir; instalar é normativo).
- Residual classificado já no plan: `app/config.py~` (backup de editor com defaults antigos), `..env.un~`, `uninstall.sh-old`, `_teste_smtp_direto.py`, `mnt/` vazio no workspace Linux — Fase 1 verifica se estão commitados (`git ls-files`) e propõe destino (Remover/Não alterar).

### F3 — XAMPP no repositório versionado: **0 ocorrências**

Varredura `-i xampp` no tree versionado: nenhuma. Conclusão preliminar: a dependência XAMPP não vive nesta dev — candidatas a abrigá-la: (a) instalador Windows versionado (a localizar no PRO — Q3 do clarify confirmou existência versionada); (b) arquivos locais/ignorados da máquina Windows do operador (XAMPP em `C:\xampp`, `.env` local); (c) relato descreve estado já corrigido. A Fase 1 investiga essas três frentes (PRO, máquina, gitignore) antes de qualquer removal.

### F4 — Instalador Linux (027) é a referência de contrato

`install.sh`: 1.198 linhas, 15 etapas, idempotente, banco existente nunca apagado (`--recreate-db` com dupla confirmação interativa; proibido em `--non-interactive`), sem segredo em argv (usa `MYSQL_PWD` no ambiente), `.env` 0600, unit systemd com `EnvironmentFile`, health `/health` com timeout 120 s, log `/var/log/sispatrimonio-install.log`. Defaults: repo `https://github.com/wellingtonsr1/SisPatrimonioPro.git` (confirma o fluxo PRO→instalador), `/opt/SisPatrimonioPro`, db `sispatrimoniopro_db`, usuário `sispat`, app host `0.0.0.0`, porta `8000`, serviço `sispatrimoniopro`. **Sem etapa de SSL** (decisão D4 da 027) — adicionar HTTPS aqui é uma das correções da Fase 2 (instalação Linux também precisa de HTTPS).

### F5 — Repositório de instalação (terceiro repo) e instalador Windows — CONFIRMADO (2026-10-02)

**Localização**: `git@github.com:wellingtonsr1/SisPatrimonioPro-install.git` (checkout local: `~/IA/SisPatrimonioPro-install`, branch `main`). É um **terceiro repositório**, além da dev e do snapshot PRO — a arquitetura real tem 3 repos: dev → PRO (snapshot) → produção (instaladores deste repo consomem o PRO). O diagrama do briefing (§22) não o menciona; o diagnóstico (T008/T009) documenta o fluxo real com ele incluído.

Conteúdo verificado:

- `install no windows/nativa/install.ps1` (**982 linhas**) + `uninstall.ps1` — **instalador Windows nativo (PowerShell)**; alvo principal da correção (FR-018).
- `install no windows/docker/` e `install no linux/docker/` — variantes Docker (classificar no diagnóstico se permanecem suportadas).
- `install no linux/nativa/install.sh` — **idêntico** ao `install.sh` da dev (diff vazio, 1198 linhas): paridade dev×install-repo OK hoje; sincronização futura entra na auditoria.
- `README.md` (38 KB) + `install no windows/TROUBLESHOOTING.md` — docs de instalação (fonte para FR-029).
- Residual: arquivo `backup-$` (6 bytes) na raiz — classificar em T006-equivalente.

**Achados preliminares no `install.ps1`** (grep; a confirmar com leitura integral em T010):

- Consome `https://github.com/wellingtonsr1/SisPatrimonioPro.git` — confirma o fluxo instalador→PRO.
- Serviço = **Tarefa Agendada do Windows** (`Register-ScheduledTask`, gatilho `AtStartup`, `RestartCount 3`, `ServiceAccount`, `RunLevel Limited`) — responde o mecanismo de serviço (data-model §4/§5).
- Firewall: **já cria** regra de entrada para a porta da aplicação (alinha com a decisão A do clarify Q5 — o trabalho será revisá-la para cobrir a porta 8000/TLS e idempotência, não criá-la do zero).
- **Nenhuma referência a SSL/certificado/HTTPS** em todo o script → **causa provável nº 1** da perda do HTTPS na instalação Windows: o instalador não gera/aponta `APP_SSL_CERTFILE`/`APP_SSL_KEYFILE` nem grava `AUTH_COOKIE_SECURE=true` → sistema instalado sobe em HTTP. A confirmar em T010 (leitura integral + baseline da máquina Windows).

**XAMPP: 0 ocorrências também neste repositório** — as referências XAMPP restantes, se existirem, estão na máquina Windows (ex.: `MYSQLDUMP_PATH` apontando para `C:\\xampp\\mysql\\bin`, `.env` local) ou são históricas; T012 confirma na máquina real.

## Decisões do plano

**RD1 — A Fase 1 (diagnóstico) é a primeira etapa executável e termina em checkpoint**: relatório (Entregável A) revisado pelo responsável antes da Fase 2. *Rationale*: regra fundamental da spec e Constitution I; Bloqueia: qualquer alteração de arquivo funcional. *Alternativa rejeitada*: começar a implementação em paralelo (viola regra de escopo).

**RD2 — Correção do HTTPS do Windows pela reutilização do mecanismo da 056**: o instalador Windows corrigido passa a gerar/apontar `APP_SSL_CERTFILE`/`APP_SSL_KEYFILE` (com `scripts/gera_cert_dev.py` como gerador,levado ao PRO ou executado na máquina — decisão detalhada na Fase 2) e grava `AUTH_COOKIE_SECURE=true` (FR-020). Sem segunda implementação (D-003). *Alternativa rejeitada*: novo mecanismo/proxy (violaria D-002/D-003).

**RD3 — Comparação dev×PRO sem ferramentas novas**: clone de leitura do PRO + whitelist extraída dos scripts (F1) + `git ls-files`. Nenhuma dependência de auditoria nova (regra 18.13). *Alternativa rejeitada*: CI ou scanner de repo (fora de escopo).

**RD4 — Relatório de diagnóstico**: artefato da feature (`specs/061.../diagnostico.md` na tarefa da Fase 1), atualizado por seção com causas Prováveis/Confirmadas. A revisão final pode ser resumida em `docs/` conforme FR-029 (documentação de usuário).

**RD5 — Porta da instalação: 8000** na produção instalada (D-006 da spec); dev usa a porta atual da máquina (baseline documentado, possivelmente 8001 — reconfirmar na Fase 1).

## Riscos carregados para tasks.md

- Whitelist omitindo arquivo necessário ao PRO (novos diretórios surgidos na dev) → task de teste de conteúdo de snapshot.
- `app/config.py~` e similares podendo entrar no snapshot → task de varredura de `git ls-files` + whitelist negativa.
- Certificado com SAN sem o IP atual da máquina → regeneração via `gera_cert_dev.py --force` documentada.
- Divergência de tamanho 248×196 linhas entre `deploy.bat` e `deploy.sh` → equivalência testada pela lista de conteúdo do snapshot.
