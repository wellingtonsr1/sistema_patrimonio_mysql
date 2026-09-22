# Guia de Implantação em Produção — SisPatrimônio Pro

**Público**: instalador/administrador do servidor de produção.
**Fluxo**: desenvolvimento acontece **somente** na pasta de dev (`sistema_patrimonio_mysql`), que publica com um único push para os dois repositórios GitHub. A produção **nunca edita código** — só recebe via `git pull`.

```
[DESENVOLVIMENTO]                                [PRODUÇÃO]
D:\IA\sistema_patrimonio_mysql                    ...\SisPatrimonioPro (servidor)
        │                                               │
   edita → deploy.bat                          git pull + reinicia serviço
        │                                               │
        ├── push → github.com/wellingtonsr1/sistema_patrimonio_mysql
        └── push → github.com/wellingtonsr1/SisPatrimonioPro ──→ pull na produção
```

Regras de ouro:

1. **Fonte da verdade única**: só se edita na dev. Produção só `pull`;
2. **Um servidor rodando por ambiente** — evita processos fantasmas com código desatualizado;
3. **Nada sensível vai pelo git** — `.env`, `data/logs`, `data/backups` e uploads são gitignored; cada ambiente mantém os seus;
4. **Sempre atualize com tag de versão registrada** (Seção 6) — é o que permite voltar atrás (Seção 8).

---

## 1. Pré-requisitos do servidor

| Item | Requisito |
|---|---|
| SO | Windows ou Linux (o sistema roda nos dois; ver nota do backup na Seção 5) |
| Python | 3.10+ (mesma versão da dev, de preferência) |
| Banco | MariaDB/MySQL em execução, com usuário e senha criados |
| Utilitários | `mysqldump` instalado e acessível no `PATH` (backup/restauração). No Windows, se ficar fora do PATH, definir `MYSQLDUMP_PATH` no `.env` |
| Acesso GitHub | chave SSH ou token com acesso leitura a `wellingtonsr1/SisPatrimonioPro` |

---

## 2. Clone do repositório

```bash
# Linux
git clone git@github.com:wellingtonsr1/SisPatrimonioPro.git
cd SisPatrimonioPro

# Windows (PowerShell/CMD)
git clone git@github.com:wellingtonsr1/SisPatrimonioPro.git
cd SisPatrimonioPro
```

Fixe a versão desejada (recomendado — veja Seção 7 sobre tags):

```bash
git checkout v1.0.0        # ou o nome da tag mais recente: git tag -l
```

---

## 3. Ambiente virtual e dependências

```bash
# Linux
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Windows
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

---

## 4. Configuração (`.env`)

Crie o `.env` **na raiz do projeto** — ele NÃO vem do git (propositamente). Modelo mínimo:

```ini
DATABASE_URL=mysql+pymysql://usuario:senha@localhost:3306/sispatrimonio
SECRET_KEY=<gere uma chave única para este servidor>
TZ=America/Recife
# Opcional — caminho do mysqldump se não estiver no PATH (Windows):
# MYSQLDUMP_PATH=C:\Program Files\MariaDB 11.x\bin\mysqldump.exe
```

> `SECRET_KEY`: gere com `python -c "import secrets; print(secrets.token_hex(32))"`.
> Nunca reutilize a `SECRET_KEY` da dev aqui. Nunca committe o `.env`.

Confira se o `.gitignore` cobre `.env`, `data/logs/`, `data/backups/` e pastas de upload — é o que garante que os dados de produção não são sobrescritos por pull.

---

## 5. Primeira execução / serviço

Teste manual primeiro:

```bash
python run.py
```

Depois configure o serviço para iniciar com o servidor:

- **Linux**: `systemd` (unit com `ExecStart=/caminho/.venv/bin/python run.py`, `WorkingDirectory=` na raiz do projeto, `Restart=always`);
- **Windows**: `NSSM` (Non-Sucking Service Manager) apontando para `...\SisPatrimonioPro\.venv\Scripts\python.exe run.py`, ou Agendador de Tarefas no boot.

⚠️ Garanta **uma única instância** rodando (o incidente histórico de "processo fantasma" veio de dois servidores simultâneos com códigos diferentes).

Backup no Windows: funciona com `mysqldump` no PATH ou `MYSQLDUMP_PATH` configurado (feature 018).

---

## 6. Atualização da produção (rotina)

Na **dev** (seu PC):

```bat
deploy.bat "mensagem do commit"     :: commita e envia pros 2 GitHub
```

Na **produção**:

```bash
git pull                            # traz a versão nova
source .venv/bin/activate           # ou .venv\Scripts\activate no Windows
pip install -r requirements.txt     # se dependências mudaram
# reinicie o serviço (systemd restart / restart no NSSM)
```

Se houver tag de versão no commit publicado (recomendado), prefira:

```bash
git fetch --tags
git checkout v1.0.1
# reinicie o serviço
```

---

## 7. Tags de versão (registradas na dev)

Antes de cada atualização relevante da produção, marque a versão na dev:

```bash
git tag v1.0.1
git push origin main --tags         # --tags propaga para os 2 GitHub
```

Vantagem: a produção pode fixar exatamente uma versão (`git checkout v1.0.1`) em vez de "o último main".

---

## 8. Rollback (voltar para uma versão anterior)

Na produção:

```bash
git fetch --tags
git checkout v1.0.0                 # última versão boa conhecida
# reinicie o serviço
```

Isso NÃO mexe no banco nem nos arquivos de dados — só no código. Se a versão anterior exigia estrutura de banco diferente, restaure o backup mais recente compatível (Administração → Backups → Restaurar) **antes** de reabrir o sistema.

Para reverter a dev ao mesmo ponto:

```bash
git revert <hash-do-commit-problematico>   # histórico preservado
git push origin main
```

---

## 9. Checklist de primeira implantação

- [ ] `git clone` concluído e `git checkout` na tag da versão aprovada
- [ ] venv criado e `pip install -r requirements.txt` sem erros
- [ ] `.env` criado localmente (DATABASE_URL, SECRET_KEY própria, TZ)
- [ ] `mysqldump` acessível (ou `MYSQLDUMP_PATH` definido)
- [ ] `python run.py` sobe sem erro e o login funciona
- [ ] Serviço configurado e **único** (só 1 processo do sistema)
- [ ] Primeiro **backup manual** gerado e verificado na tela Administração → Backups
- [ ] Tag da versão instalada registrada (`git describe --tags` na produção)
