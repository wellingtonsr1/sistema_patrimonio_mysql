# Quickstart: Instalador Automatizado de Produção Linux — Feature 027

**Data**: 2026-09-19 | **Como validar**: shellcheck (se disponível) + suíte pytest pré/pós (regressão de `app/`) + cenários operacionais em **VM/servidor de teste limpo** (a validação real do instalador é funcional — nenhum teste de bash na suíte do projeto).

> **Importante**: nada deste guia roda na máquina de desenvolvimento do projeto contra produção. Use snapshot/VM (Debian 12 ou Ubuntu 22.04/24.04 recomendados). Os testes operacionais marcados **[OPERADOR]** ficam para quem tem o ambiente; o implementador valida o que for possível localmente (sintaxe, shellcheck, suíte).

---

## Passo 1 — Regressão da aplicação (implementador)

```bash
pytest -q          # PRÉ: baseline verde antes de tocar em qualquer coisa
# ... implementar install.sh + docs ...
pytest -q          # PÓS: mesma suíte verde — zero diff esperado em app/
git diff --stat    # escopo: install.sh (novo), README.md, docs/GUIA_DE_MANUTENCAO.md, specs/027-*/
```

**Esperado**: suíte verde pré/pós; `git status` sem nenhum arquivo em `app/`/`tests/` (contract §2).

## Passo 2 — Qualidade estática do script (implementador)

```bash
bash -n install.sh                                   # sintaxe
shellcheck install.sh                                # se disponível (apt install shellcheck)
```

**Esperado**: sem erros de sintaxe; shellcheck limpo ou com ressalvas justificadas no relatório (nenhuma do tipo SC2086 de variável sem aspas em contexto sensível).

## Passo 3 — Instalação limpa interativa **[OPERADOR]**

VM limpa Debian/Ubuntu:

```bash
git clone https://github.com/wellingtonsr1/sistema_patrimonio_mysql.git
cd sistema_patrimonio_mysql
sudo bash install.sh
```

**Esperado** (contract §3):
1. Gates: sudo/distro/systemd/conectividade OK.
2. Python ≥ 3.10 confirmado (ou instalado e **re-verificado**); Git; MariaDB instalado e ativo.
3. Banco + usuário criados (utf8mb4); senha coletada sem eco (ou gerada); teste de conexão OK.
4. Clone em `/opt/SisPatrimonioPro`; venv; `pip install` com validação de imports.
5. `.env` gerado (0600); unit `sispatrimoniopro.service` habilitada; serviço ativo.
6. `/health` responde `healthy` (ou `degraded` com WARNING explicado).
7. Resumo final: URL, `/docs`, `/health`, comandos systemctl, instruções do 1º admin, sem senha.

Conferências pós-instalação (contract §4):

```bash
sudo grep -F '<SENHA_USADA>' /var/log/sispatrimonio-install.log    # vazio
stat -c '%a %U' /opt/SisPatrimonioPro/.env                          # 600 sispatrimonio
mysql -e "SHOW GRANTS FOR 'sispat'@'localhost';"                    # sem privilégios globais
curl -fsS http://127.0.0.1:8000/health                              # {"status":"healthy",...}
```

## Passo 4 — Idempotência **[OPERADOR]**

```bash
sha256sum /opt/SisPatrimonioPro/.env > /tmp/env.sha
mysql -e "SELECT COUNT(*) FROM sispatrimonio.users" > /tmp/users.cnt
sudo bash install.sh     # 2ª execução (mesmos valores)
sha256sum -c /tmp/env.sha; mysql -e "SELECT COUNT(*) FROM sispatrimonio.users" | diff - /tmp/users.cnt
```

**Esperado**: 2ª execução exit 0 com "reutilizado" nas etapas; `.env` byte-idêntico; contagem de usuários inalterada; serviço continua saudável.

## Passo 5 — Modo não interativo e guardas **[OPERADOR]**

```bash
sudo bash install.sh --non-interactive                        # deve FALHAR (exit 2) listando faltantes
sudo bash install.sh --non-interactive --recreate-db \
  --db-name x --db-user y --generate-db-password              # exit 2 ANTES de qualquer mutação
sudo bash install.sh --non-interactive --db-name sispat2 \
  --db-user sispat2 --generate-db-password --install-dir /opt/teste-sispat  # instala sem prompts
sudo bash install.sh --update                                  # mensagem clara + exit 2 (NFR-005)
```

## Passo 6 — Fluxos adversos **[OPERADOR]**

- **Porta ocupada**: serviço de teste na 8000 → mensagem específica, abort antes do start.
- **Diretório não-vazio sem `.git`**: `/opt/SisPatrimonioPro` com arquivo solto → abort pedindo decisão (não sobrescreve).
- **`.env` existente**: cria `.env.bak-<ts>`, não sobrescreve valores, oferta completar chaves.
- **Banco existente**: 2ª execução NÃO emite DROP (verificar via log geral do MariaDB, se habilitado) — banco intocável.
- **`--recreate-db` interativo**: dupla confirmação (digitar nome do banco 2×) antes de qualquer DROP.
- **Falha simulada** (sem rede para o GitHub): log contém etapa/erro sem credenciais; serviço não fica habilitado quebrado.

## Passo 7 — 1º administrador e primeiro acesso **[OPERADOR]**

Seguir o resumo final: criar admin via CLI (`python -m app.cli create-user --username admin --name "Administrador" --admin`, senha oculta ≥ 8) **ou** `/setup` **ou** env (opcional). Login na UI; `backup.gerenciar` visível em Administração → Backups (confirma `init_db()` + `ensure_default_roles` sadios).

**Esperado**: autenticação funcional; banco com tabelas criadas pelo start (instalador nunca criou schema).
