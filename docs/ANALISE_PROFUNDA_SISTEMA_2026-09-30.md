# Análise Profunda do Sistema — SisPatrimônio Pro

**Data**: 2026-09-30 · **Natureza**: diagnóstico — **nenhum código foi alterado** · **Suíte no momento**: 895 passed / 0 failed (64,8s, hermética)

**Método**: leitura de código-fonte pós-mudanças, logs de runtime (`data/logs/`), histórico git (HEAD = `d53e036`, árvore limpa, **dev = PRO**), comparação com a análise de 2026-09-29 e execução da suíte completa. Esta análise **substitui** a de 2026-09-29 como referência corrente (aquela permanece como histórico).

---

## 1. Panorama executivo

| Dimensão | Estado | Evidência |
|---|---|---|
| Suíte | ✅ **895 passed / 0 failed** — pela 1ª vez 100% verde, hermética (sem MariaDB) | `pytest tests/` (64,8s); 875 funções de teste |
| Arquitetura | ✅ Sólida (051: 10 routers de domínio) | `routes.py` facade; handlers magros |
| Segurança | ✅ Boa e **melhorou**: cookie de sessão agora respeita `AUTH_COOKIE_SECURE` (wire real no `set_cookie`) | `session_service.py:98` |
| HTTPS/PWA | ✅ TLS nativo ativo no servidor; SW v32; PWA instalável de qualquer tela (057) | `.env` com `APP_SSL_*`; manifest no login |
| Deploy | ✅ Dev e PRO sincronizados (`d53e036`; snapshot do PRO no mesmo commit) | `git rev-list FETCH_HEAD..HEAD` = 0 |
| Dívida | ⚠️ 3 focos novos + 4 herdados da análise anterior | §3 |

**Mudanças desde a última análise (todas saneadoras):** 053 (respondWith duplo do SW corrigido + bump v32), 054 (suíte hermética), 055 (2 failures POSIX corrigidos), 056 (HTTPS nativo uvicorn), 057 (PWA instalável em qualquer tela), normalização multiplataforma de caminhos TLS (`config.py`), fail-fast de cert no `run.py` + `timeout_graceful_shutdown=5`, `AUTH_COOKIE_SECURE` no `.env.example`, estabilização de testes flaky de restore (019), remoção do `sispatrimoniopro.cert` legado e bloqueio de material TLS solto no `.gitignore`, whitelist do `deploy.bat` incluiu `scripts/` (para o `gera_cert_dev.py` chegar ao PRO).

---

## 2. Achados NOVOS desta análise

### M-N1. `timeout_graceful_shutdown=5` mudou o comportamento de shutdown — decisão consciente, mas com efeito colateral (Média)
`run.py` agora corta conexões após 5s. **Ação em progresso**: requisições longas (import de CSV grande, restore de backup, geração de relatório pesado) **podem ser abortadas** no Ctrl+C/restart se passarem de 5s. O restore import tem `BACKUP_IMPORT_TIMEOUT=900` (15 min) — a aplicação não morre no meio, mas um restart no momento errado pode truncar uma operação longa.
→ **Recomendação**: baixo risco hoje (reinícios são manuais e raros), mas registrar: se um dia houver serviço que reinicia automaticamente (NSSM/systemd com restart), aumentar o valor ou torná-lo configurável (`APP_SHUTDOWN_TIMEOUT`).

### M-N2. `.env.example` ganhou variáveis, mas o `.env` de produção real não tem `AUTH_COOKIE_SECURE=true` (Média–Alta)
Com HTTPS **ativo** no servidor (`APP_SSL_*` presentes), o cookie de sessão ainda é enviado **sem o flag Secure** — o ganho de segurança do TLS está parcialmente desaproveitado (o cookie poderia vazar se uma URL `http://` respondesse por engano ou via outro serviço na máquina).
→ **RESOLVIDO (2026-09-30, mesmo dia)**: linha ativada no `.env` e validada em produção (header `Set-Cookie` com `Secure` + login real em navegador sobre HTTPS; ver V9 do `validacao.md` da 056). Custo zero (o app já só é servido em TLS; qualquer cliente HTTP já não acessa). Cuidado operacional: se alguém um dia desligar o HTTPS sem remover o flag, o login para de funcionar — a doc do `.env.example` já alerta isso.

### M-N3. Ruído de `ConnectionResetError` (WinError 10054) no log de erros (Baixa)
Toda desconexão abrupta de cliente (celular dormindo, keep-alive cortado) vira um traceback de ~15 linhas no `app.error.log`. É inofensivo, mas polui o log e pode esconder erros reais.
→ **Recomendação**: filtrar/logar como DEBUG essas exceções do asyncio no `logging` config (handler específico para `asyncio` com nível WARNING→ERROR exceto 10054/10038), ou simplesmente documentar como ruído conhecido.

### M-N4. Import `Location` em `inventario.py` — verificado, é usado (não é achado)
O import adicionado pós-057 (`app/web/routers/inventario.py:23`) é consumido (filtro de departamentos L74, contexto de locais). Falsa alarme descartada.

### M-N5. Snapshot do PRO feito de outra máquina ("pop-os") (Informativo)
O PRO foi publicado por um commit com sufixo "(snapshot de produção de pop-os, commit dev d53e036)". Ou seja, **existe um segundo ambiente** gerando snapshots com a mesma árvore. Atentar para: (a) mesma versão do `deploy.bat`/whitelist nas duas máquinas, (b) risco de sobrescrita de snapshot se dois deploys partirem de árvores diferentes. Funcionou corretamente (o PRO está em `d53e036`), mas é um ponto de atenção operacional.

---

## 3. Dívidas herdadas — status atualizado (da análise de 2026-09-29)

| ID | Débito | Status hoje |
|---|---|---|
| M1 | Suíte dependente do MariaDB | ✅ **RESOLVIDO (054)** — hermética, 64s |
| M3 / R1 | respondWith duplo no `sw.js` | ✅ **RESOLVIDO (053)** — v32 publicada |
| M9 | `sispatrimoniopro.cert` legado no repo | ✅ **RESOLVIDO** — removido + `.gitignore` bloqueia material TLS solto |
| M5 | `base.html:271` — atributo style quebrado no menu do usuário (`";;border-color:`) | ✅ **RESOLVIDO (2026-09-30, feature 058)** |
| M6 | CDN externo no `base.html` (7 ocorrências jsdelivr/googlefonts) — sistema não funciona 100% sem internet | ✅ **RESOLVIDO (2026-09-30, feature 059)** — 100% vendored (Chart.js 4.4.1 fixado, QRCode, fonte local); SW v33; guard anti-CDN na suíte |
| M8 | Falhas SMTP sem visibilidade | ❌ ABERTO (não reapareceu nos logs recentes — 0 ocorrências hoje; melhorar só se voltar) |
| M7 | `admin_routes.py` com 1.440 linhas; `backup_service.py` com 1.408 | ❌ ABERTO (aceito conscientemente; split físico do backup segue recusado pelo Amendment A1 da 051) |
| M10 | 3 documentos de melhorias paralelos | ❌ ABERTO — este relatório + `Melhorias_SisPatrimonio_Pro.md` + `Coisas a corrigir ou melhorar.md` |
| M11 | `seed_demo.py` na raiz (sem interativo, mas em prod) | ❌ ABERTO (baixo: nada o executa sozinho) |
| — | 10 arquivos ainda usam `datetime.utcnow()` (deprecation Python 3.12+, warning na suíte) | ❌ ABERTO — 3347 warnings na suíte; migração mecânica para `datetime.now(UTC)`, candidata a micro-feature |
| — | Botão "Voltar" estoura viewport 375px (desde a 036) | ❌ ABERTO |
| — | Documentação de cenários de rede (internet × LAN × servidor) ausente no produto | ✅ **RESOLVIDO (2026-09-30, feature 060)** — artigo na Central de Ajuda + dica do `localhost:8000` na página offline do PWA (SW v34) |
| — | Ruído `ConnectionResetError` 10054 no `app.error.log` (M-N3) | ✅ **RESOLVIDO (2026-09-30, feature 058)** — filtro no logger `asyncio` |

### Pendências da lista do usuário (`Coisas a corrigir ou melhorar.md`)
Itens ainda sem "OK": **2** (ciclo de regularização de divergência — evolução de módulo), **4** (decidir exportação PDF/CSV/Excel vs. ajuste de impressão), **9** (nome de quem já está cadastrado na importação), **12** (cor do check da tela de conferência). Os demais estão marcados como resolvidos.

---

## 4. Fila de prioridades recomendada

1. **P1 — `AUTH_COOKIE_SECURE=true` no `.env` de produção** (M-N2): 1 linha, fecha o ciclo da 056. Feito isso, fazer um deploy para o PRO só se o `.env` do servidor de produção for gerenciado pelo snapshot (não é — é manual; então é ação direta no servidor).
2. **P1 — Spec 052 (Alembic)**: continua sendo **a correção mais urgente de infraestrutura** e a análise anterior permanece válida: necessária (drift real já ocorreu em produção: `backup_config` inexistente em 2026-09-23), e não prejudica o sistema (zero DDL no deploy de adoção, guard SQLite, tolerância à corrida). **Pré-requisitos agora satisfeitos**: M1 (suíte hermética) ✅ e régua 100% verde ✅. É o próximo passo natural com a melhor régua possível.
3. **P2 — ~~M5 (style quebrado)~~ + ~~M-N3 (ruído 10054)~~**: ✅ RESOLVIDOS na feature 058 (2026-09-30).
4. **P2 — ~~M6 (vendoring dos CDNs)~~**: ✅ RESOLVIDO na feature 059 (2026-09-30).
5. **P3 — `utcnow()` → `now(UTC)`** (10 arquivos): migração mecânica, elimina 3.3k warnings e protege contra o Python 3.14+ (esta máquina já roda 3.14 — a remoção está agendada em versões futuras da stdlib).
6. **P3 — fila de produto**: divergências (item 2 do usuário), exportações (item 4), spec 049 (pesquisa em movimentações, pronta p/ implementar).

---

## 5. Veredito sobre a spec 052 (reafirmado com o estado novo)

**Sim, implementar — e agora é o melhor momento desde que ela foi escrita.** Três razões novas: (1) a pré-requisito M1 foi resolvida (suíte hermética, sem risco de "quebrar o XAMPP" durante o TDD da 052); (2) a régua é 100% verde — qualquer regressão será inequivocamente da 052; (3) o fluxo HTTPS/PWA está estabilizado, liberando a fila de infraestrutura. Os riscos já foram analisados e mitigados no plano (zero DDL na adoção, guard SQLite, boot concorrente tolerante, edge case de restore coberto por FR-008). Nada que mudou desde a análise de 2026-09-29 altera o veredito — pelo contrário, o robustece.

---

## 6. Anexos — evidências citadas

- Suíte: `pytest tests/ -q` → **895 passed / 0 failed in 64.84s** (3347 warnings — maioria `utcnow()`)
- `git log --oneline -1` → `d53e036` (dev); `FETCH_HEAD` do `SisPatrimonioPro` → snapshot do mesmo commit; `git rev-list --count FETCH_HEAD..HEAD` = **0**
- `app/config.py:110-123` (normalização TLS multiplataforma), `run.py:29-40` (fail-fast de cert), `run.py:56-60` (`timeout_graceful_shutdown=5`)
- `app/services/session_service.py:91-98` (`set_cookie` com `secure=AUTH_COOKIE_SECURE` — wire real)
- `.env` do servidor: `APP_SSL_*` presentes ✅ · `AUTH_COOKIE_SECURE=true` ✅ (resolvido no mesmo dia; validação V9 da 056)
- `app/web/templates/base.html:271` (style quebrado), 7 ocorrências de CDN em `base.html`
- `data/logs/app.error.log` — apenas `ConnectionResetError 10054` do asyncio (nenhum erro de aplicação); `app.log` sem ERROR/WARNING de aplicação e 0 ocorrências SMTP
- `wc -l`: `admin_routes.py` 1440, `backup_service.py` 1408
- `sw.js:13` — `CACHE_VERSION = "inventario-offline-v32"` (bump da 053 ativo)
