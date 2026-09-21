# SisPatrimônio Pro 📦🏢

**SisPatrimônio Pro** é um sistema completo e moderno de **Gestão Patrimonial (Controle de Ativo Fixo e Equipamentos)** desenvolvido em **Python**, com **FastAPI**, **SQLAlchemy** e **Bootstrap 5**, focado no **rastreamento auditável e na gravação detalhada do fluxo de movimentação de cada equipamento**.

**Status:** Em desenvolvimento ativo (versão da aplicação: `1.2.0`, conforme `app/config.py`).

> **Documentação:** este README apresenta a visão geral, instalação, arquitetura e principais regras do sistema. Detalhes operacionais e técnicos específicos devem ser mantidos em `docs/`, evitando que o README fique desatualizado ou excessivamente extenso.

---

## ✨ Principais Funcionalidades

### 1. 🔄 Motor de Fluxo de Movimentação & Auditoria

- **Histórico protegido pela aplicação:** cada alteração relevante de localização, colaborador ou estado gera registro histórico com data/hora, origem → destino, motivo e operador. Os registros não possuem edição/exclusão pela aplicação.
- **Tipos de fluxo suportados:**
  - `ENTRADA_AQUISICAO`: cadastro inicial e incorporação ao acervo.
  - `ALOCACAO_CAUTELA`: entrega de equipamento a um colaborador específico.
  - `TRANSFERENCIA_LOCAL`: mudança de filial, prédio, sala ou departamento.
  - `ENVIO_MANUTENCAO`: saída para reparo ou assistência técnica.
  - `RETORNO_MANUTENCAO`: reintegração do bem após conserto.
  - `DEVOLUCAO_ESTOQUE`: recolhimento do bem.
  - `BAIXA_DESCARTE`: descarte por obsolescência, perda, quebra ou leilão.
  - `ATUALIZACAO_ESTADO`: vistoria e alteração do estado de conservação.
- **Linha do tempo visual:** apresenta a vida útil e as movimentações de cada bem.
- **Termo de Responsabilidade & Cautela:** emissão automática de documento com dados institucionais, colaborador e bem, com validação por QR Code.

### 2. 💻 Gestão de Bens & Equipamentos

- Tombamento/tag única e geração de etiquetas QR Code.
- **Etiquetas patrimoniais em lote** na tela `Etiquetas` (`/assets/labels`), com folha A4.
- Ficha técnica: marca, modelo, número de série e especificações.
- Dados fiscais e financeiros: nota fiscal, fornecedor, garantia, data e valor de aquisição.
- **Depreciação linear:** regra de negócio atualmente adotada pelo sistema: 20% ao ano sobre o valor de aquisição.
- Busca e filtros por status, categoria, setor e custodiante.
- **Importação em massa via CSV** de equipamentos, colaboradores e locais, com pré-visualização e confirmação.

### 3. 📋 Inventário Patrimonial

O inventário é uma **conferência física comprobatória** e possui ciclo próprio, separado do cadastro patrimonial.

- Código sequencial no formato `INV-AAAA-NNNN`.
- Escopo opcional por local e/ou setor; vazio = todo o acervo.
- Snapshot textual dos filtros utilizados.
- Lista de bens esperados gerada no momento da criação, preservando a localização/custodiante daquele momento.
- Ciclo de vida: `PLANEJADO → EM_ANDAMENTO → ENCERRADO`.
- Status dos itens: `PENDENTE`, `ENCONTRADO`, `LOCAL_DIFERENTE`, `NAO_ENCONTRADO` e `SEM_IDENTIFICACAO`.
- Conferência em campo por QR Code, busca na ficha do bem ou pela página do inventário.
- Registro de localização encontrada, observação, conferente e data/hora.
- Aceita bens encontrados que não estavam na lista de esperados: a ocorrência é registrada como **observação complementar** (item não previsto), sem alterar o cadastro do bem.
- **Re-conferência deliberada:** itens já conferidos exibem o resultado anterior e exigem confirmação antes de sua substituição.
- Encerramento exige que todos os bens esperados tenham sido conferidos; depois disso os itens ficam travados.
- Ata comprobatória exportável em CSV, Excel e PDF.
- **Regra fundamental:** o inventário não altera automaticamente bens, movimentações ou locais. Divergências são registradas para tratamento pelos fluxos patrimoniais próprios.
- Permissões específicas: `inventario.visualizar`, `inventario.criar`, `inventario.conferir`, `inventario.encerrar`.

### 4. 👥 Gestão de Colaboradores & Departamentos

- Cadastro de colaboradores com visão dos equipamentos sob sua custódia.
- **Identificador provisório:** sem matrícula oficial, o sistema gera `PROV-000001` sequencialmente e identifica o cadastro como provisório. A matrícula oficial pode ser informada posteriormente, preservando o mesmo colaborador, vínculos e histórico.
- Colaboradores com matrícula oficial não têm sua matrícula alterada pela interface.
- **Departamento/Setor como seleção oficial:** o campo é um dropdown alimentado pelos departamentos dos **locais cadastrados**. Não é permitido criar um setor arbitrário digitando um novo nome.
- Pesquisa única por matrícula, nome, cargo, departamento ou e-mail, com correspondência parcial e sem distinção entre maiúsculas/minúsculas.
- Cadastro de unidades físicas, prédios, andares, salas e departamentos.
- Pesquisa de locais por nome/identificação.
- Exportação CSV de locais.
- Importação de locais via CSV, com pré-visualização, aliases de colunas e detecção de duplicatas.

### 5. 🔧 Gestão de Manutenções

- Ordens de Serviço preventiva, corretiva e upgrade.
- Controle de custos acumulados e prestadores.
- Envio e retorno de manutenção integrados ao fluxo do bem.

### 6. 📊 Dashboard, Relatórios & Exportações

- Dashboard com KPIs e gráficos via Chart.js.
- Exportação CSV em UTF-8 com BOM.
- Exportação Excel (`.xlsx`) via OpenPyXL.
- Exportação PDF via ReportLab.
- Relatórios de inventário, movimentações, colaboradores e locais.
- Ata comprobatória de inventários.
- Botões de **Exportar CSV** nas telas aplicáveis.
- Swagger UI em `/docs`.

### 7. 🧭 Central de Ajuda Integrada

- Manual em `/ajuda`.
- Pesquisa textual.
- Artigos por módulo.
- FAQ.
- Tooltips e ajuda contextual nos formulários.

### 8. 🔐 Autenticação Local + Active Directory / Samba AD

- Contas locais autenticam localmente.
- Contas vinculadas ao AD autenticam pelo diretório.
- O **AD não define permissões**.
- O acesso depende do RBAC interno e, no caso do AD, de grupo explicitamente mapeado para perfil do sistema.
- Usuários AD sem grupo autorizado não recebem acesso nem são provisionados no sistema.

---

## 🧩 Modelo Conceitual

O sistema separa deliberadamente **estado atual**, **histórico operacional**, **evidência física** e **auditoria administrativa**:

```text
                         ┌────────────────────┐
                         │       ASSET        │
                         │    Estado atual    │
                         └─────────┬──────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    ↓                             ↓
          ┌──────────────────┐          ┌──────────────────┐
          │    MOVEMENTS     │          │ INVENTARIO_ITEM  │
          │ Histórico        │          │ Evidência física│
          │ operacional      │          │ da conferência   │
          └──────────────────┘          └──────────────────┘

          Ações administrativas/sistêmicas
                         │
                         ↓
                ┌──────────────────┐
                │    AUDIT_LOG     │
                │ Auditoria        │
                │ administrativa   │
                └──────────────────┘
```

- **Asset:** representa o estado patrimonial atual.
- **Movement:** registra a evolução operacional do bem.
- **InventoryItem:** registra o resultado da conferência física em determinado inventário.
- **AuditLog:** registra ações e eventos administrativos/sistêmicos.

---

## 🛠️ Tecnologias

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.10+ |
| Framework web | FastAPI >= 0.110 |
| Servidor ASGI | Uvicorn >= 0.28 |
| ORM / Banco | SQLAlchemy 2 + MariaDB/MySQL (PyMySQL) |
| Validação | Pydantic v2 >= 2.6 |
| Templates | Jinja2 + Bootstrap 5 + Bootstrap Icons |
| Frontend | Chart.js, QRCode.js, tema claro/escuro |
| Exportações | OpenPyXL (.xlsx) · ReportLab (PDF) · CSV UTF-8 BOM |
| Diretório | LDAP/LDAPS via `ldap3` |
| Testes | pytest + TestClient do FastAPI |

> Versões mínimas conforme `requirements.txt`.

---

## 🏗️ Arquitetura

O sistema é organizado em camadas:

```text
Interface Web (Jinja2)          API REST (/api/v1)
        └────────────┬──────────────┘
                     ↓
          Autenticação (provedores)
       local (PBKDF2) · AD (LDAP)
                     ↓
             Services / Regras
                     ↓
              Models / SQLAlchemy
                     ↓
                MariaDB/MySQL
```

### Autenticação x autorização

- **Autenticação:** determina quem é o usuário.
- **Autorização:** determina o que o usuário pode fazer.
- O RBAC é interno ao SisPatrimônio Pro.
- O AD pode fornecer a identidade e, mediante mapeamento explícito, indicar um perfil interno.
- **Permissões nunca são importadas diretamente do AD.**

### Sessões

- Token aleatório seguro.
- Cookie `HttpOnly` + `SameSite=Lax`.
- `Secure` configurável.
- Banco armazena somente o hash SHA-256 do token.
- Expiração no servidor, padrão de 8 horas.
- Revogação no logout.

### Auditoria

`audit_logs` registra eventos de autenticação, alterações, movimentações, importações e acessos negados.

A auditoria é **somente leitura pela aplicação**: não existem rotas para edição ou exclusão dos registros.

### Data e hora

O sistema segue a convenção da feature 004:

- timestamps gerados pelo sistema são persistidos em UTC;
- valores `DATETIME` são tratados como UTC por contrato da aplicação;
- apresentação em telas, relatórios e documentos usa `America/Recife`;
- datas de negócio, como aquisição e vencimento de garantia, não recebem conversão de fuso;
- filtros de período informados em `America/Recife` são convertidos para UTC antes da consulta.

Detalhes: `specs/004-padronizacao-datas-utc/`.

---

## 🚀 Como Executar

### Pré-requisitos

- Python 3.10+
- MariaDB/MySQL acessível
- dependências instaladas

### 1. Instalar dependências

Copie a pasta do sistema para a pasta de destino
```bash
cp -r sis_patrimonio_pro /opt/SisPatrimonioPro
```

Acesse o diretório
```bash
cd /opt/SisPatrimonioPro
```

Crie o ambiente virtual
```bash
python3 -m venv .venv
```

Ative o ambiente
```bash
source .venv/bin/activate
```

Se for preciso, altere o dono do diretório
```bash
sudo chown -R seu_usuario:seu_usuario /opt/SisPratrimonioPro
```

Instalar as dependências usando o pip
```bash
pip install -r requirements.txt
```

Faça o teste
```bash
python -c "import fastapi, sqlalchemy, pymysql, ldap3, reportlab, openpyxl, dotenv; print('DEPENDÊNCIAS OK')"
```

### 2. Configurar banco

Crie o .env
```
nano .env no /opt/SisPatrimonioPro
```

Defina `DATABASE_URL` no `.env`:
```env
DATABASE_URL=mariadb+pymysql://sispat:SENHA@localhost:3306/sispatrimonio
```

Se a senha tiver caracteres especias, será preciso codificá-la
A forma correta é codificar a senha para URL (percent-encoding) antes de colocá-la no DATABASE_URL.

Por exemplo, se a senha fosse:
```
Minha@Senha#2026
```
os caracteres especiais seriam codificados:
```
Minha%40Senha%232026
```
Então:
```
DATABASE_URL=mariadb+pymysql://patrimonio:Minha%40Senha%232026@localhost:3306/sispatrimoniopro
```

Principais caracteres
```
| Caractere | Usar na URL |
| --------- | ----------- |
| `@`       | `%40`       |
| `#`       | `%23`       |
| `%`       | `%25`       |
| `:`       | `%3A`       |
| `/`       | `%2F`       |
| `?`       | `%3F`       |
| espaço    | `%20`       |
```

Uma forma mais segura de fazer isso

Você pode deixar o Python gerar o DATABASE_URL corretamente, sem precisar fazer a conversão manual.

No terminal, não coloque a senha real aqui no chat. Na sua máquina, execute:
```
python -c "from urllib.parse import quote; senha=input('Senha: '); print(quote(senha, safe=''))"
```

Digite a senha quando solicitado.
Se, por exemplo, retornar:
```
Minha%40Senha%232026
```

> **Por que `quote(safe='')` e não `quote_plus`?** O `quote_plus` codifica espaço
> como `+`, mas o parse de URL do SQLAlchemy **não** decodifica `+` como espaço —
> a senha chegaria ao banco errada (Access denied). Com `quote(safe='')` o espaço
> vira `%20`, decodificado corretamente. Vale para qualquer caractere especial:
> `@` → `%40`, `#` → `%23`, `:` → `%3A`, `/` → `%2F`, `%` → `%25`.
>
> **Evite senhas com barra invertida (`\`)**: o MySQL interpreta sequências como
> `\n`/`\t` dentro de literais SQL e isso afeta também a criação do usuário
> (`CREATE USER ... IDENTIFIED BY`). Se precisar usá-la, redobre a barra ao criar
> o usuário no SQL (`\\n`) ou escolha outra senha.

use esse valor no .env:
```
DATABASE_URL=mariadb+pymysql://patrimonio:Minha%40Senha%232026@localhost:3306/sispatrimoniopro
```

Depois podemos testar a conexão sem nunca revelar a senha:
```
python -c "from app.config import DATABASE_URL; from sqlalchemy import create_engine, text; e=create_engine(DATABASE_URL); c=e.connect(); print('CONEXÃO OK'); print('BANCO:', c.execute(text('SELECT DATABASE()')).scalar()); c.close()"
```


A aplicação **não possui fallback para SQLite**. SQLite é utilizado somente pela suíte de testes, quando configurado para isso.

### 3. Iniciar

```bash
python run.py
```

O host e a porta dependem de `APP_HOST` e `APP_PORT`, conforme `app/config.py`.

Endpoints principais:

```text
/
 /login
 /docs
 /health
 /ajuda
```

### 4. Inicar com o sistema
Criar o serviço systemd
```
sudo nano /etc/systemd/system/sispatrimonio.service
```

Coloque
```
[Unit]
Description=SisPatrimônio Pro
After=network-online.target mariadb.service
Wants=network-online.target

[Service]
Type=simple
User=wellington
Group=wellington
WorkingDirectory=/opt/SisPratrimonioPro
EnvironmentFile=/opt/SisPratrimonioPro/.env
ExecStart=/opt/SisPratrimonioPro/.venv/bin/python /opt/SisPratrimonioPro/run.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Recarregar o systemd
```
sudo systemctl daemon-reload
```

Ativar para iniciar com o Linux
```
sudo systemctl enable sispatrimoniopro
```

Iniciar agora
```
sudo systemctl start sispatrimoniopro
```

Verificar
```
sudo systemctl status sispatrimoniopro
```

Você deve encontrar
```
Active: active (running)
```

> Para instalação completa em uma máquina nova, consulte a documentação em `docs/`.

---

## 🖥️ Instalação em uma máquina nova

### Instalador automatizado (recomendado — feature 027)

Em um servidor **Debian/Ubuntu (ou derivada com `apt` + systemd)**, o instalador automatizado prepara tudo — Python ≥ 3.10, Git, MariaDB, banco/usuário, clone, venv, dependências, `.env`, serviço `systemd` e verificação via `/health` — de forma **idempotente** (pode ser executado novamente; banco existente **nunca** é apagado):

```bash
git clone https://github.com/wellingtonsr1/sistema_patrimonio_mysql.git
cd sistema_patrimonio_mysql
sudo bash install.sh                 # modo interativo (pergunta com defaults)
```

Modo automatizado (sem prompts — exige os parâmetros obrigatórios):

```bash
sudo bash install.sh --non-interactive \
  --db-name sispatrimonio --db-user sispat --generate-db-password
```

| Opção | Default | Função |
|---|---|---|
| `--install-dir` | `/opt/SisPatrimonioPro` | Diretório de instalação |
| `--repo` / `--branch` | repositório oficial / `main` | Origem do código |
| `--db-name` / `--db-user` | `sispatrimonio` / `sispat` | Banco e usuário da aplicação |
| `--db-password` \| `--generate-db-password` | — | Senha do banco (fornecida ou gerada; vai direto ao `.env`) |
| `--app-host` / `--app-port` | `0.0.0.0` / `8000` | Bind da aplicação |
| `--service-name` / `--service-user` | `sispatrimoniopro` / `sispatrimonio` | Serviço systemd e usuário Linux dedicado |
| `--recreate-db` | — | **Destrutivo**: apaga e recria o banco da aplicação — só no modo interativo, com dupla confirmação |
| `--update` | — | Reservado (ainda não implementado) |

Garantias do instalador: senha coletada sem eco ou gerada criptograficamente (nunca em log/argv), `.env` criado com permissão `600`, serviço rodando com **usuário dedicado sem login** e privilégios do banco **apenas no banco da aplicação**; criação de tabelas fica a cargo do `init_db()` existente no start do serviço (o instalador não cria schema). Log da instalação: `/var/log/sispatrimonio-install.log` (sem credenciais).

### Desinstalação (feature 027)

Para remover a instalação de produção criada pelo instalador (idempotente; detecta banco/usuário a partir do `.env` — a senha nunca é exibida):

```bash
sudo bash uninstall.sh                        # interativo, confirma cada etapa
sudo bash uninstall.sh --yes                  # remove app+serviço+usuário Linux sem perguntar
                                              # (o BANCO sempre exige confirmação digitando o nome)
sudo bash uninstall.sh --keep-db              # preserva banco e usuário do banco
sudo bash uninstall.sh --purge-mariadb        # remove o MariaDB INTEIRO (TODOS os bancos —
                                              # dupla confirmação; use só em servidor dedicado ao teste)
```

A desinstalação remove nesta ordem: serviço systemd + unit → diretório da aplicação (incluindo `data/logs` e `data/backups` — salve backups importantes antes) → usuário/grupo Linux → banco/usuário do MariaDB (opcional/confirmado) → log do instalador. Pacotes padrão (Python, Git, curl) são mantidos.

### Fluxo manual (alternativa)

Fluxo resumido:

1. Instalar Python 3.10+.
2. Instalar Git.
3. Instalar MariaDB/MySQL.
4. Clonar o projeto.
5. Criar e ativar `.venv`.
6. Executar `pip install -r requirements.txt`.
7. Criar banco e usuário.
8. Configurar `DATABASE_URL`.
9. Executar `python run.py`.
10. Criar o primeiro administrador por uma das formas disponíveis.

Exemplo de banco:

```sql
CREATE DATABASE sispatrimonio
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER 'sispat'@'%' IDENTIFIED BY 'SENHA_FORTE';

GRANT ALL PRIVILEGES ON sispatrimonio.* TO 'sispat'@'%';

FLUSH PRIVILEGES;
```

### Primeiro administrador

Existem três caminhos:

**A — Variáveis de ambiente**

```env
AUTH_ADMIN_USERNAME=admin
AUTH_ADMIN_PASSWORD=SENHA_FORTE
```

**B — Primeiro acesso (`/setup`)**

Em uma instalação que ainda não possui nenhum usuário cadastrado (registro singleton `setup_claims`), a aplicação disponibiliza a página `/setup` para criar o primeiro administrador. Após a criação do primeiro usuário (por qualquer um dos caminhos), a página deixa de estar disponível.

**C — CLI**

```bash
python -m app.cli create-user \
  --username admin \
  --password 'SENHA_FORTE' \
  --name "Administrador" \
  --admin
```

> A senha deve possuir no mínimo 8 caracteres.

### Banco e migração

No startup, `init_db()` cria as tabelas e aplica a migração leve e idempotente atualmente utilizada pelo projeto.

**Não existe comando manual de migração no fluxo atual.**

Para evolução futura, pode ser adotado um sistema formal de migrações versionadas, como Alembic, caso a complexidade do esquema justifique.

---

## 🔐 Autenticação

O sistema exige autenticação para a interface, API e exportações.

### Primeiro acesso

Disponível somente quando:

- não existem usuários;
- `AUTH_ADMIN_PASSWORD` não está configurada.

A criação inicial possui proteção contra condição de corrida e não pode ser repetida depois que a instalação foi inicializada.

### Senhas locais

Senhas locais são armazenadas somente como hash:

- PBKDF2-HMAC-SHA256;
- salt individual;
- 600.000 iterações por padrão.

### Lockout

Após **10 tentativas de login inválidas**, por padrão, a conta fica bloqueada por **15 minutos**.

Configurações:

| Variável | Padrão | Função |
|---|---:|---|
| `AUTH_SESSION_TTL` | `28800` | Sessão em segundos |
| `AUTH_COOKIE_NAME` | `session` | Nome do cookie |
| `AUTH_COOKIE_SECURE` | `false` | Cookie somente HTTPS |
| `AUTH_PBKDF2_ITERATIONS` | `600000` | Iterações PBKDF2 |
| `AUTH_MAX_FAILED_ATTEMPTS` | `10` | Limite de falhas |
| `AUTH_LOCKOUT_SECONDS` | `900` | Duração do bloqueio |

Na API, o bloqueio temporário utiliza `423 Locked`.

### API protegida

A API `/api/v1` exige autenticação, inclusive consultas, porque pode retornar dados como nomes, CPF, números de série e valores patrimoniais.

`/health` permanece público para monitoramento.

`/docs` é público, mas as operações autenticadas continuam protegidas.

---

## 🏢 Active Directory / Samba AD

A integração utiliza LDAP/LDAPS por meio de `ldap3`.

### Princípio fundamental

**Autenticar no AD não concede acesso automaticamente.**

O fluxo é:

```text
Login
  ↓
Conta local existente?
  ├─ Sim → autenticação local
  └─ Não
       ↓
AD habilitado?
       ↓
Conta de serviço consulta o usuário
       ↓
Usuário encontrado
       ↓
Bind com DN do usuário + senha informada
       ↓
Senha validada
       ↓
Consulta de atributos/grupos
       ↓
Conta habilitada?
       ↓
Grupo AD autorizado e mapeado?
       ├─ Não → acesso negado + auditoria
       └─ Sim
            ↓
      Provisionamento/sincronização
            ↓
      Perfil interno do sistema
            ↓
         Sessão
```

### Conta de serviço

Quando configurada, a conta de serviço (`AD_BIND_USER` / `AD_BIND_PASSWORD`) é utilizada para **localizar e consultar usuários/grupos**.

A senha do usuário é validada por bind usando o **próprio DN do usuário e a senha fornecida no login**.

A conta de serviço não recebe nem armazena a senha do usuário.

### Usuário sem grupo autorizado

Se o usuário:

- existir no AD;
- informar credenciais válidas;
- mas não pertencer a grupo AD explicitamente mapeado;

o acesso é negado.

Nesse caso:

- nenhum usuário é criado no SisPatrimônio;
- nenhum colaborador é criado;
- nenhum perfil é atribuído;
- somente a tentativa é registrada na auditoria.

### Provisionamento

O provisionamento ocorre somente depois de:

1. autenticação válida no AD;
2. conta habilitada;
3. grupo AD autorizado/mapeado.

Quando aplicável, o usuário pode ser vinculado a um colaborador existente sem duplicar seu cadastro.

Dados patrimoniais do colaborador não são sobrescritos automaticamente pelo AD.

### Mapeamento Grupo AD → Perfil

Os mapeamentos ficam em `ad_group_roles`.

Quando o usuário pertence a vários grupos mapeados:

- a prioridade numérica determina o perfil;
- menor número = maior prioridade;
- `group_role_priority`, quando utilizado, pode estabelecer uma ordem explícita.

Perfis atribuídos pelo AD são sincronizados conforme os grupos atuais.

Perfis atribuídos manualmente permanecem preservados.

### LDAPS

Para produção, recomenda-se:

- LDAPS;
- porta 636;
- certificado TLS válido;
- validação do certificado.

A validação de certificado pode ser desativada explicitamente pelo administrador em ambientes que ainda não possuem uma CA adequada, quando suportado pela configuração do sistema.

---

## 🔐 Controle de Acesso e Permissões (RBAC)

O sistema utiliza **RBAC (Role-Based Access Control)** com princípio **deny by default**.

```text
Usuário
   ↓
Perfis (roles)
   ↓
Permissões (modulo.acao)
```

Usuários novos não recebem permissões implicitamente.

### Superusuário

`users.is_admin` é um mecanismo legado de superusuário com bypass das verificações normais de permissão.

Ele preserva a compatibilidade do administrador inicial.

Para novos administradores, o mecanismo preferencial é o perfil interno **Administrador**.

### Perfis padrão

| Perfil | Descrição |
|---|---|
| **Administrador** | Administração completa do sistema |
| **Gestor de TI** | Patrimônio, movimentações, manutenção e relatórios, sem administração do sistema |
| **Técnico de TI** | Consulta de equipamentos e manutenção técnica |
| **Patrimônio** | Cadastro, movimentação, inventário, termos e relatórios patrimoniais |
| **Almoxarifado** | Operações de estoque e consulta de equipamentos |
| **Auditor** | Acesso predominantemente somente leitura |
| **Consulta** | Acesso mínimo de consulta |

Perfis de sistema (`is_system=True`) não podem ser excluídos.

### Catálogo de permissões

As permissões seguem `modulo.acao`.

| Módulo | Permissões |
|---|---|
| Patrimônio | `patrimonio.visualizar`, `patrimonio.criar`, `patrimonio.editar`, `patrimonio.excluir` |
| Movimentação | `movimentacao.visualizar`, `movimentacao.criar`, `movimentacao.editar`, `movimentacao.cancelar` |
| Manutenção | `manutencao.visualizar`, `manutencao.criar`, `manutencao.editar`, `manutencao.finalizar` |
| Colaboradores | `colaboradores.visualizar`, `colaboradores.criar`, `colaboradores.editar` |
| Locais | `locais.visualizar`, `locais.criar`, `locais.editar` |
| Usuários | `usuarios.visualizar`, `usuarios.criar`, `usuarios.editar`, `usuarios.bloquear` |
| Perfis | `perfis.visualizar`, `perfis.criar`, `perfis.editar`, `perfis.excluir` |
| Relatórios | `relatorios.visualizar`, `relatorios.exportar` |
| Inventário | `inventario.visualizar`, `inventario.criar`, `inventario.conferir`, `inventario.encerrar` |
| Backup | `backup.gerenciar`, `backup.restaurar` |
| Auditoria | `auditoria.visualizar` |

`movimentacao.cancelar` permanece reservada enquanto não houver fluxo que a utilize.

### Segurança das rotas

A interface pode ocultar botões conforme permissões, mas isso é somente apresentação.

**Toda autorização é validada no backend.**

---

## 🛡️ Proteções administrativas

- usuário não pode bloquear a si próprio;
- último administrador ativo não pode ser removido/desativado;
- troca de senha própria exige a senha atual;
- troca/reset de senha invalida sessões existentes;
- acessos negados são auditados;
- operações administrativas exigem permissões correspondentes.

---

## 🧾 Auditoria

`audit_logs` registra, conforme o evento:

- login;
- falha de login;
- bloqueio;
- logout;
- criação/alteração;
- bloqueio/desbloqueio;
- troca/reset de senha;
- alterações de perfis e permissões;
- movimentações patrimoniais;
- importações;
- acessos negados;
- eventos da integração AD.

Os registros podem conter:

- data/hora;
- usuário;
- ação;
- módulo;
- recurso;
- identificador;
- IP;
- resultado;
- dados anteriores/posteriores em JSON.

**Credenciais e senhas não são registradas.**

---

## 🗄️ Banco de Dados

O banco de produção é MariaDB/MySQL.

Principais estruturas adicionais utilizadas pelo sistema incluem:

```text
roles
permissions
user_roles
role_permissions
audit_logs
ad_settings
ad_group_roles
inventarios
inventario_itens
backup_records
backup_config
setup_claims
```

A tabela `users` possui, entre outras, informações relacionadas a:

```text
failed_login_attempts
locked_until
ad_object_guid
ad_dn
ad_last_sync
auth_provider
```

A criação/migração atual é automática e idempotente por `init_db()`.

> O mecanismo atual prioriza simplicidade e compatibilidade. Uma estratégia formal de migrações versionadas pode ser adotada futuramente conforme a evolução do esquema.

---

## 💻 Interface de Linha de Comando (CLI)

```bash
# Resumo e KPIs
python -m app.cli stats

# Listar equipamentos
python -m app.cli list

# Buscar equipamentos
python -m app.cli list --search "MacBook"

# Ver detalhes e linha do tempo
python -m app.cli show PAT-00101

# Registrar movimentação
python -m app.cli move PAT-00101 \
  --type ALOCACAO_CAUTELA \
  --custodian-id 1 \
  --reason "Alocação pelo terminal"

# Criar administrador
python -m app.cli create-user \
  --username admin \
  --password 'SENHA_FORTE' \
  --name "Administrador" \
  --admin

# Criar usuário com perfil
python -m app.cli create-user \
  --username maria \
  --password 'SENHA_FORTE' \
  --name "Maria" \
  --role "Técnico de TI"

# Redefinir senha de usuário local
python -m app.cli reset-password --username admin
```

`create-user` pode solicitar a senha interativamente quando `--password` não é informado.

`--role` pode ser repetido.

Usuários criados sem `--role` ou `--admin` permanecem sem permissões até receberem um perfil.

`reset-password` destina-se a usuários locais. Usuários autenticados pelo AD devem ter suas credenciais administradas no próprio diretório.

---

## ❓ Central de Ajuda

A central de ajuda está disponível em `/ajuda`.

Recursos:

- pesquisa;
- artigos por módulo;
- FAQ;
- ajuda contextual;
- tooltips;
- conteúdo administrativo condicionado às permissões.

O conteúdo é mantido em `app/services/help_service.py`.

---

## 🧪 Testes Automatizados

Execute:

```bash
pytest -q
```

ou:

```bash
pytest -v
```

A suíte cobre, entre outros:

- autenticação;
- RBAC;
- lockout;
- auditoria;
- administração;
- integração AD com LDAP mockado;
- inventário;
- movimentações;
- bens;
- importações;
- colaboradores;
- locais;
- primeiro acesso;
- central de ajuda;
- backup (manual, automático, retenção, configuração pela tela e restauração);
- exportações CSV/Excel/PDF.

### Banco utilizado pelos testes

Os testes podem utilizar SQLite em memória por padrão, sem depender de MariaDB.

Para executar testes contra outro banco, utilize `DATABASE_URL_TEST` quando suportado pela configuração da suíte.

> **Importante:** o número de testes e o estado de aprovação não são fixados neste README. Eles devem ser obtidos executando `pytest -q`, evitando que a documentação fique desatualizada a cada alteração da suíte.

---

## 📂 Estrutura do Projeto

```text
sistema_patrimonio_mysql/
├── app/
│   ├── api/                  # Endpoints REST e dependências de auth/RBAC
│   ├── models/               # Modelos SQLAlchemy
│   ├── schemas/              # Schemas Pydantic
│   ├── services/             # Regras de negócio
│   ├── web/                  # Interface web e templates
│   ├── cli.py                # Interface de linha de comando
│   ├── config.py             # Configurações
│   ├── database.py           # Banco, sessões e migração leve
│   ├── logging_config.py     # Configuração de logs
│   └── main.py               # Aplicação FastAPI
├── data/                     # Dados e logs locais
├── docs/                     # Documentação detalhada
├── specs/                    # Especificações das features (fluxo Spec Kit)
├── tests/                    # Suíte pytest
├── seed_demo.py              # Dados de demonstração
├── run.py                    # Inicialização
└── requirements.txt          # Dependências
```

> `seed_demo.py` recria as tabelas (`drop_all` + `create_all`). Utilize somente em banco dedicado a demonstração/testes.

---

## 📊 Escopo por Unidade/Setor

O controle de escopo por unidade/setor ainda não faz parte do modelo atual.

Conceitos como:

```text
escopo_global
escopo_unidade
escopo_setor
escopo_proprio
```

foram avaliados como evolução futura.

Uma futura implementação deverá considerar escopos vinculados ao usuário/perfil e aplicar os filtros nos services, preservando o RBAC existente.

---

## 🔒 Segurança

Práticas atualmente implementadas:

- PBKDF2-HMAC-SHA256 para senhas locais;
- salt individual;
- sessões com token aleatório;
- armazenamento somente do hash do token;
- cookie HttpOnly/SameSite;
- expiração e revogação de sessão;
- lockout por tentativas;
- RBAC deny by default;
- autorização validada no backend;
- integração AD sem armazenamento da senha do usuário;
- timeout nas operações LDAP;
- auditoria;
- proteção contra open redirect no parâmetro `next`.

### Recomendações para produção

- utilizar HTTPS;
- definir `AUTH_COOKIE_SECURE=true`;
- utilizar LDAPS com certificado válido;
- manter credenciais de serviço fora do versionamento;
- fornecer `AUTH_ADMIN_PASSWORD` somente quando necessário para a inicialização;
- realizar backups regulares do MariaDB/MySQL;
- restringir acesso administrativo ao banco.

---

## 💾 Backup

### Backup manual pela interface (features 015 e 016)

Usuários com a permissão `backup.gerenciar` (concedida ao perfil Administrador) podem gerar um backup do banco de dados em **Administração → Backups**:

- O backup é um dump SQL consistente do banco (`mysqldump --single-transaction`), gerado pelo utilitário nativo do MariaDB/MySQL;
- **Conteúdo**: o dump contém todos os dados persistidos do sistema (17 tabelas — patrimônio, colaboradores, usuários/perfis/permissões, movimentações, manutenção, inventário e auditoria). Nenhum dado da aplicação vive fora do banco, portanto o dump é o estado completo; arquivos de log, cache e artefatos de desenvolvimento são deliberadamente excluídos;
- O arquivo é comprimido em **gzip** (`.sql.gz`) e gerado **atomicamente**: um temporário `.part` é gravado primeiro e só é renomeado para o nome final após validação (dump íntegro + gzip legível) — nunca há arquivo parcial listável;
- O arquivo é armazenado no servidor em `data/backups/`, nomeado `backup_AAAAMMDD_HHMMSS_micros.sql.gz` com **data/hora em UTC**;
- A tela lista os backups disponíveis (data/hora, tamanho, **Integridade** OK/—/CORROMPIDO e **SHA-256** — o mesmo valor do `sha256sum` do arquivo, útil para conferir o download) e permite baixá-los;
- Backups do formato anterior (`.sql`, sem checksum) continuam listados e baixáveis (Integridade "—");
- Cada operação (geração, falha e download) é registrada na trilha de auditoria — a geração como `Backup Gerado`/`Backup Falhou`; diagnóstico técnico no log rotativo do sistema, sem credenciais;
- **Requisito do servidor (feature 018)**: o utilitário nativo de dump (`mysqldump`) deve estar no PATH do processo — ou ter seu caminho indicado na variável `MYSQLDUMP_PATH` do `.env` (ex.: `MYSQLDUMP_PATH=C:\xampp\mysql\bin\mysqldump.exe` no Windows/XAMPP). Sem isso, a geração falha com a mensagem "utilitário não foi encontrado" e o diagnóstico completo vai ao log técnico (etapa, código de retorno e saída de erro sanitizada — nunca credenciais).
### Backup automático e política de retenção (feature 020)

O backup automático **reutiliza o mesmo mecanismo do backup manual** (mesmo dump, mesma compressão, mesma validação, mesmo diretório e formato de arquivo) — é apenas uma nova forma de disparo. A tela **Administração → Backups** passa a exibir o card "Backup Automático" (estado, horário configurado, próxima execução, último resultado) e a coluna **Tipo** na listagem (MANUAL / AUTOMÁTICO / PRÉ-RESTAURAÇÃO / — para arquivos legados).

**Configuração (todas opcionais; defaults conservadores)** — desde a **feature 021**, administráveis pela interface; desde a **feature 022**, o acesso é pelo **botão ⚙ no canto superior direito da página Administração → Backups**, que abre o **modal "Configurações de Backup"** com os valores atuais (permissão `backup.gerenciar`); a rota direta `/admin/backups/configuracoes` permanece por compatibilidade. As variáveis de ambiente abaixo funcionam como **fallback por campo** enquanto o campo correspondente não estiver persistido (e continuam úteis para deploys automatizados que precisem pré-definir valores). Precedência única por campo, aplicada por `get_effective_config()`: **valor persistido (tela) → variável de ambiente → default da 020**. **Exceção (fallback de boot do scheduler)**: se a leitura da configuração efetiva falhar (ex.: banco indisponível), o scheduler mantém o **snapshot anterior**; sem snapshot anterior, usa o **bootstrap** por env/default até a próxima leitura bem-sucedida — mecanismo de segurança, não caminho normal.

| Variável | Default | Descrição |
|---|---|---|
| `BACKUP_AUTO_ENABLED` | `false` | Ativa (**`true`**) ou desativa o disparo automático — o sistema nasce **desativado**; |
| `BACKUP_AUTO_SCHEDULE` | `daily` | Frequência: `daily` ou `weekly`; |
| `BACKUP_AUTO_TIME` | `02:00` | Horário do disparo no fuso **America/Recife** (HH:MM); |
| `BACKUP_AUTO_WEEKDAY` | `0` | Dia da semana para `weekly` (0=domingo … 6=sábado); |
| `BACKUP_RETENTION_DAILY_DAYS` | `30` | Dias da janela de retenção diária; |
| `BACKUP_RETENTION_WEEKLY_WEEKS` | `12` | Semanas da retenção semanal (âncora: automático mais recente de cada semana ISO); |
| `BACKUP_RETENTION_MONTHLY_MONTHS` | `12` | Meses da retenção mensal (âncora: automático mais recente de cada mês); |
| `BACKUP_RETENTION_KEEP_PRE_RESTORE` | `0` | 0 = preserva **todos** os backups pré-restauração; N>0 = preserva apenas os N mais recentes. |

Valores inválidos não derrubam o sistema: caem no default seguro com registro no log técnico.

**Particularidade de `BACKUP_AUTO_ENABLED`**: o campo persistido `auto_enabled` é **não nulo** — depois que a linha de configuração existe, a variável de ambiente não é reconsultada dinamicamente para esse campo (diferente dos demais, que aceitam env enquanto o campo persistido estiver indefinido). Ela continua valendo na instalação nova (default `false` — o sistema nasce desativado) e no fallback de boot descrito acima.

**Comportamento:**

- O agendador roda em uma **thread interna do próprio processo** (sem Celery/Redis/APScheduler — nada novo para instalar ou operar); a cada 30 s verifica se chegou o horário; em `weekly`, dispara no `BACKUP_AUTO_WEEKDAY` configurado;
- **Após reinicialização** (do servidor, da aplicação ou do processo), se o horário do ciclo corrente já passou e **nenhum backup automático bem-sucedido existe** no ciclo corrente (diário = dia calendário local; semanal = semana iniciando 00:00 local no dia configurado), um **catch-up único e determinístico** executa ~60 s após o start;
- **Sem execução simultânea**: um disparo enquanto outro automático está em andamento é **descartado** (registrado no log); durante uma **restauração**, o disparo é **adiado** para o próximo ciclo;
- Um backup automático só é considerado concluído quando o arquivo existe, tem conteúdo e valida a integridade; falhas registram diagnóstico técnico no log (etapa, exit code, stderr sanitizado — **nunca credenciais**) e evento de auditoria `BACKUP_AUTOMATICO_FALHA`;
- Os metadados (tipo, status, checksum, remoção pela retenção) ficam na tabela nova `backup_records` (criada automaticamente; **nenhum arquivo ou formato existente é alterado**) — o restore existente funciona igualmente com backups manuais e automáticos.
- **Disparo por execução devida (feature 028)**: a verificação de horário passou a usar o mesmo critério determinístico do catch-up ("o horário do ciclo corrente já passou E ainda não há automático bem-sucedido neste ciclo"), com **1 tentativa por ciclo** (marcada em memória) — elimina a condição em que a comparação com a "próxima execução futura" recalculada a cada tick nunca era satisfeita (backup automático silenciosamente não disparava). O card continua exibindo a próxima execução normalmente; guardas, ciclo de 30 s e catch-up existentes permanecem inalterados.

**Política de retenção (executada após cada ciclo automático):**

- Atua **somente sobre backups automáticos** com sucesso, fora da janela diária, com integridade OK — os **backups manuais e pré-restauração são preservados por padrão** (pré-restauração só com `BACKUP_RETENTION_KEEP_PRE_RESTORE` > 0, política explícita do operador);
- Seleção determinística GFS (grandfather-father-son): preserva o automático mais recente de cada semana ISO e de cada mês dentro dos limites configurados;
- **Nunca deixa o sistema sem backup válido**: se uma remoção deixaria 0 backups válidos no disco, o candidato é preservado com motivo `ULTIMO_BACKUP_VALIDO`;
- Cada remoção marca o **registro histórico** (`removed_at`) — o histórico é preservado mesmo após a remoção física do arquivo (rastreabilidade);
- Toda execução registra eventos de auditoria (`BACKUP_RETENCAO_EXECUTADA`, `BACKUP_REMOVIDO_RETENCAO`); falha parcial na remoção → resultado **PARCIAL**, nunca "concluída".

**Configurações de Backup pela interface (features 021/022):**

- O acesso é pelo **botão ⚙ no canto superior direito da página Administração → Backups** (feature 022, alinhado ao título), que abre o **modal "Configurações de Backup"** com os valores atuais; o formulário permite ao administrador alterar: backup automático ativado/desativado, frequência (diário/semanal), horário (fuso America/Recife), dia da semana, retenção diária/semanal/mensal e a política de pré-restauração;
- **Cancelar** fecha o modal sem salvar nada; **Salvar configuração** usa o mesmo fluxo de sempre (validação → persistência → auditoria → mensagem no topo da página);
- A rota direta `/admin/backups/configuracoes` continua existindo por compatibilidade (links antigos) e exibe a mesma página;
- **Aplicação sem reinício**: o agendador renova a configuração efetiva a cada ciclo (≤ 30 s) — alterar `02:00 → 23:00` pela tela vale já no próximo disparo;
- Validação no backend (barreira real, não só HTML): frequência, HH:MM, dia 0–6, quantidades ≥ 1 e pré-restauração ≥ 0; valores inválidos são rejeitados com a configuração anterior intacta;
- Cada alteração registra o evento de auditoria `BACKUP_CONFIGURACAO_ALTERADA` com os valores **antes/depois** por campo alterado (nunca credenciais);
- Continuam sendo **configuração técnica do servidor** (não editáveis pela tela): `MYSQLDUMP_PATH`, `BACKUP_DIR`, `BACKUP_IMPORT_TIMEOUT` e `DATABASE_URL` — a tela não permite alterar caminhos, executáveis nem credenciais;
- A configuração da tela fica na tabela `backup_config` (singleton, criada automaticamente); sem linha persistida, valem ambiente e defaults — o sistema nunca fica em estado indefinido.

Limitações anteriores (backup manual sem agendamento) ficam resolvidas por esta feature; a **restauração** executada pela interface está descrita na próxima seção (feature 017, com correções da feature 019).

### Restauração de backup pela interface (feature 017)

Usuários com a permissão `backup.restaurar` (concedida ao perfil Administrador; distinta de `backup.gerenciar`) podem restaurar um backup em **Administração → Backups → Restaurar**:

- A operação é **destrutiva**: substitui todos os dados atuais pelos dados do backup selecionado;
- Exige **confirmação explícita em duas etapas** (tela de informações com advertência → botão "SIM, RESTAURAR BACKUP" com confirmação adicional do navegador); nunca é executada por GET ou ao abrir a página;
- Antes de qualquer alteração, o sistema cria automaticamente um **backup de segurança do estado atual** (pelo mesmo mecanismo da feature 016) e o valida; se não for possível criá-lo, a restauração **não inicia**;
- O backup selecionado é validado (existência, formato, tamanho, integridade — corrompidos são recusados) antes de qualquer alteração;
- O import é executado pelo cliente nativo do MariaDB/MySQL com as credenciais seguras do ambiente (a senha nunca aparece em logs ou auditoria);
- Após a importação, o sistema valida o resultado (conexão, tabelas essenciais e dados essenciais) antes de informar sucesso;
- Em caso de falha, o backup de segurança **permanece disponível** na listagem para restauração manual (política operacional); nunca é excluído automaticamente;
- **Sessões**: como são registradas no banco, sessões abertas após a data do backup restaurado deixam de ser válidas; sessões existentes na data do backup voltam a valer;
- Restaurações concorrentes são rejeitadas (uma por vez); durante uma restauração, a geração de backup manual fica temporariamente bloqueada;
- Todo o ciclo é registrado na trilha de auditoria (Restauração Iniciada, Backup Pré-Restore Criado, Restauração Concluída/Falhou);
- **Execução em segundo plano (feature 019)**: após a confirmação, a restauração é **agendada** e o sistema entra em **modo de manutenção** — as demais páginas informam a indisponibilidade e o acesso normal retorna automaticamente ao final. O import é executado por um worker interno com o pool de conexões da aplicação drenado (elimina travamento por bloqueio do próprio sistema, corrigido no Windows e preservado no Linux); a tela de Backups acompanha a fase atual e o resultado;
- **Acompanhamento durante a manutenção (feature 028)**: a própria tela **Administração → Backups** permanece acessível em **somente leitura** durante o ciclo (o restante do sistema segue bloqueado) — a listagem aparece com o aviso "Listagem indisponível durante a restauração" e o acompanhamento acontece pelo indicador de fase (polling da 019); escritas continuam bloqueadas (503) e a permissão `backup.gerenciar` continua exigida;
- **Tipos preservados após restaurar (feature 028)**: ao final do ciclo (sucesso ou falha pós-import), o sistema reconcilia os metadados de `backup_records` com os arquivos presentes no disco — os backups que existiam antes (MANUAL, AUTOMÁTICO e PRÉ-RESTAURAÇÃO) voltam a aparecer identificados com o tipo correto na tela, sem depender de inferência pelo nome do arquivo;
- **Tempo limite**: a fase de importação tem prazo de relógio configurável via `BACKUP_IMPORT_TIMEOUT` (em segundos, padrão `900`). Estourou o prazo, o import é interrompido e registrado como falha — nunca fica travado indefinidamente.

Limitações: a restauração é **manual** (sem agendamento); não há rollback automático em caso de falha no meio da importação — o backup de segurança criado antes da operação é o caminho de recuperação (restaurável pela própria interface).

### Backup operacional (servidor)

Além do backup manual da interface, utilize ferramentas nativas do MariaDB/MySQL, como:

```bash
mysqldump
```

ou mecanismos de backup adequados ao ambiente.

O backup deve fazer parte da política operacional do servidor e ser testado periodicamente por meio de restauração.

---

## 📚 Documentação

Este README é a **porta de entrada do projeto**. A documentação detalhada fica em `docs/` e as especificações de cada feature em `specs/`.

Documentação técnica disponível:

```text
docs/
├── ARQUITETURA_E_MANUTENCAO.md
├── BACKUP_AUTOMATICO_TESTES.md
├── GUIA_DE_MANUTENCAO.md
```

As especificações por feature (`specs/NNN-nome/`) registram requisitos, decisões de design e critérios de validação do fluxo de desenvolvimento.

---

## 📄 Licença

Não identificada na implementação atual.

Não há arquivo `LICENSE` identificado no repositório.
