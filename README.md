# SisPatrimônio Pro 📦🏢

**SisPatrimônio Pro** é um sistema completo e moderno de **Gestão Patrimonial (Controle de Ativo Fixo e Equipamentos)** desenvolvido em **Python** com **FastAPI**, **SQLAlchemy** e **Bootstrap 5**, focado no **rastreamento auditável e gravação detalhada do fluxo de movimentação de cada equipamento**.

**Status:** Em desenvolvimento ativo · Suite com **282 testes automatizados** (`pytest`; no estado atual, 281 passando e 1 falhando — detalhes na seção de testes; execute `pytest -q` para ver o número atual).

---

## ✨ Principais Funcionalidades

### 1. 🔄 Motor de Fluxo de Movimentação & Auditoria (Audit Trail)
- **Gravação Imutável de Histórico**: Cada alteração de localização, colaborador ou estado gera um snapshot histórico indelével com data/hora, origem → destino, motivo e operador.
- **Tipos de Fluxo Suportados**:
  - `ENTRADA_AQUISICAO`: Cadastro inicial e incorporação ao acervo.
  - `ALOCACAO_CAUTELA`: Entrega de equipamento a um colaborador específico.
  - `TRANSFERENCIA_LOCAL`: Mudança de filial, prédio, sala ou departamento.
  - `ENVIO_MANUTENCAO`: Saída para reparo ou assistência técnica externa/interna.
  - `RETORNO_MANUTENCAO`: Reintegração do bem após conserto.
  - `DEVOLUCAO_ESTOQUE`: Recolhimento do bem (demissão ou substituição).
  - `BAIXA_DESCARTE`: Descarte por obsolescência, perda, quebra ou leilão.
  - `ATUALIZACAO_ESTADO`: Vistoria e alteração do estado de conservação.
- **Linha do Tempo Visual (Interactive Timeline)**: Visualização gráfica no estilo GitHub/Jira da vida útil e de todas as transferências de cada bem.
- **Termo de Responsabilidade & Cautela**: Emissão e formatação automática de termo formal com dados da empresa, colaborador, especificações do bem e validação via QR Code, pronto para impressão e assinatura.

### 2. 💻 Gestão de Bens & Equipamentos
- Tombamento / Tag única com geração dinâmica de etiquetas QR Code.
- **Etiquetas patrimoniais em lote** (tela Etiquetas, `/assets/labels`): seleção de bens e folha de impressão A4 com QR Code.
- Ficha técnica completa (marca, modelo, número de série, especificações).
- Gestão fiscal e financeira (Nota Fiscal, fornecedor, garantia, data e valor de compra).
- **Cálculo de Depreciação Linear Contábil** automática (20% ao ano sobre o valor de aquisição).
- Busca e filtros multifacetados por status, categoria, setor e custodiante.
- **Importação em massa via CSV** (equipamentos, colaboradores e locais) com pré-visualização e confirmação.

### 3. 📋 Inventário Patrimonial (Conferência Física Comprobatória)
- Inventários com código sequencial (`INV-AAAA-NNNN`) e escopo opcional por local e/ou setor (vazio = todo o acervo), com snapshot textual dos filtros para comprovação.
- Geração da **lista de bens esperados** no momento da criação (snapshot da localização/custodiante cadastrados, imune a edições posteriores do cadastro).
- Ciclo de vida `PLANEJADO → EM_ANDAMENTO → ENCERRADO`; cada item registra `PENDENTE`, `ENCONTRADO`, `LOCAL_DIFERENTE`, `NAO_ENCONTRADO` ou `SEM_IDENTIFICACAO`.
- **Conferência em campo por bem** (via QR Code/busca na ficha do bem ou pela página do inventário): registra localização encontrada, observação, conferente e data/hora; aceita registro de **bens não previstos** na lista.
- **Re-conferência visível e deliberada**: enquanto o inventário estiver aberto, itens já conferidos exibem quem conferiu antes, quando e o resultado anterior, e exigem confirmação antes de um novo registro substituir o resultado anterior (itens `PENDENTE` registram diretamente; encerrado permanece travado).
- **Encerramento exige todos os bens esperados conferidos** e trava os itens (nenhuma conferência nova é aceita).
- **Ata comprobatória exportável** em CSV, Excel (.xlsx) e PDF.
- O inventário **nunca altera o cadastro** (bens, movimentações, locais): divergências são apenas registradas para tratamento pelos fluxos próprios.
- Permissões próprias: `inventario.visualizar`, `inventario.criar`, `inventario.conferir`, `inventario.encerrar`.

### 4. 👥 Gestão de Colaboradores & Departamentos
- Cadastro de colaboradores com visão instantânea de todos os equipamentos sob a custódia de cada um.
- **Identificador provisório de colaborador**: a matrícula é opcional no cadastro — sem ela, o sistema gera automaticamente um identificador sequencial `PROV-000001`, exibido com a marcação "provisória" na listagem, nos detalhes e nos termos. O colaborador provisório participa normalmente das operações patrimoniais; a matrícula oficial pode ser informada depois na edição (mesmo colaborador, vínculos e histórico preservados — registros antigos mantêm a identificação da época). Colaboradores com matrícula oficial continuam com ela inalterável pela interface.
- **Departamento/Setor como campo de seleção (dropdown)**: no cadastro e na edição de colaborador, o campo "Departamento / Setor" é um dropdown com a lista oficial — derivada ao vivo dos departamentos dos **locais** cadastrados (novos valores oficiais surgem do fluxo de locais). Não é possível criar um setor digitando um nome novo; a obrigatoriedade é validada no servidor.
- **Pesquisa na listagem de colaboradores**: um único termo é comparado com matrícula, nome, cargo, departamento e e-mail (correspondência parcial, sem diferenciar maiúsculas de minúsculas).
- Cadastro de unidades físicas, prédios, andares, salas e departamentos.
- **Pesquisa de locais** pelo Nome / Identificação e **exportação CSV de locais** (`locais.csv`) pelo botão Exportar CSV do cabeçalho da tela.
- **Importação em massa de locais via CSV** (obrigatórios: nome, filial e departamento; opcionais: prédio, andar, sala, gestor e descrição) com pré-visualização, alias de colunas e detecção de duplicatas.

### 5. 🔧 Gestão de Manutenções
- Abertura de Ordens de Serviço (Preventiva, Corretiva, Upgrade).
- Controle de custos acumulados de reparo e prestadores de serviço.
- Envio e retorno de manutenção com atualização automática do fluxo do bem.

### 6. 📊 Dashboard, Relatórios & Exportações
- Dashboard com KPIs operacionais, gráficos de pizza e barras (Chart.js).
- Exportação de inventário, movimentações, colaboradores e **locais** em **CSV** (UTF-8 com BOM, abre direto no Excel) e dos relatórios também em **Excel (.xlsx via OpenPyXL)** e **PDF (ReportLab)** — incluindo a ata comprobatória de cada inventário. Além dos relatórios, as telas Colaboradores, Dashboard, Movimentações e Locais possuem o botão **Exportar CSV** para download direto.
- Documentação interativa da **API REST via Swagger UI** (`/docs`).

### 7. 🧭 Central de Ajuda Integrada
- Manual embutido (`/ajuda`) com pesquisa em texto completo, artigos por módulo, FAQ e tooltips contextuais nos formulários.

### 8. 🔐 Autenticação Local + Active Directory / Samba AD (LDAP)
- Login híbrido: contas locais (PBKDF2) e contas do diretório (`ldap3`), com provisionamento automático no 1º login.
- RBAC completo (perfis e permissões) permanece 100% interno — o AD nunca define permissões.

---

## 🛠️ Tecnologias

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.10+ |
| Framework web | FastAPI |
| Servidor ASGI | Uvicorn |
| ORM / Banco | SQLAlchemy 2 + MariaDB/MySQL |
| Validação | Pydantic v2 |
| Templates | Jinja2 + Bootstrap 5 + Bootstrap Icons |
| Frontend | Chart.js, QRCode.js, tema claro/escuro |
| Exportações | OpenPyXL (Excel .xlsx) · ReportLab (PDF) |
| Diretório | LDAP/LDAPS padrão via `ldap3` (Microsoft AD ou Samba AD DC) |
| Testes | pytest (+ TestClient do FastAPI) |

---

## 🏗️ Arquitetura

O sistema é organizado em **camadas desacopladas**:

```text
Interface Web (Jinja2)          API REST (/api/v1)
        └────────────┬──────────────┘
                     ↓
        Autenticação (provedores)
        local (PBKDF2 no banco) · AD (LDAP bind)
                     ↓
                Services (regras de negócio)
        assets · movements · custodians · locations ·
        maintenance · reports · help · import · RBAC · auditoria
                     ↓
        Models (SQLAlchemy) → Banco de dados
```

- **Autenticação** (quem você é): via `app/services/auth_provider.py`, que resolve entre o provedor **local** e o provedor **Active Directory**. Contas locais existentes sempre autenticam localmente; contas `auth_provider='ad'` autenticam sempre no diretório.
- **Autorização** (o que você pode fazer): **RBAC interno** — o AD apenas indica um *perfil* existente do sistema via mapeamento Grupo AD → Perfil. Permissões nunca vêm do AD.
- **Sessões**: token aleatório (`secrets.token_urlsafe`) gravado em cookie **HttpOnly + SameSite=Lax** (Secure opcional); o banco armazena apenas o **hash SHA-256** do token. Expiração no servidor (padrão 8h) e revogação no logout.
- **Auditoria**: trilha somente-leitura (`audit_logs`) com eventos de autenticação, alterações, movimentações e acessos negados.
- **Convenção de data e hora** (feature 004): todo timestamp gerado pelo sistema é **gerado e persistido em UTC** (naive) pelo mecanismo central `app/utils/time_utils.py` (`now_utc()`); na **apresentação** (templates, relatórios, documentos), os valores são convertidos para `America/Recife` pelo filtro Jinja `localtime` / helper `format_local()`. Valores naive lidos de colunas `DATETIME` são tratados como **UTC por contrato da aplicação**. **Datas de negócio** (`purchase_date`, `warranty_expiry`, datas de CSV/formulários) **não recebem conversão de fuso**. Filtros de período sobre timestamps interpretam o intervalo informado em `America/Recife` e o convertem para UTC antes de comparar. Detalhes: `specs/004-padronizacao-datas-utc/`.

---

## 🚀 Como Executar o Sistema

### Pré-requisitos
- Python 3.10 ou superior instalado e um banco **MariaDB/MySQL** acessível (guia completo: seção **Instalação em uma máquina nova** mais abaixo).

### 1. Instalar as dependências
```bash
pip install -r requirements.txt
```

### 2. (Opcional) Popular o banco de dados com dados de teste
Para iniciar o sistema já com equipamentos, colaboradores e histórico de movimentações pré-carregados:
```bash
python seed_demo.py
```
> ⚠️ O seed **recria as tabelas** (`drop_all` + `create_all`): use apenas em banco dedicado a testes/demo.

### 3. Iniciar o servidor
```bash
python run.py
```

Acesse no seu navegador — o endereço depende das variáveis `APP_HOST` e `APP_PORT`
(padrões definidos em `app/config.py` — configuráveis por `APP_HOST`/`APP_PORT` no `.env`; ajuste conforme o seu ambiente):
- **Interface Web**: [http://localhost:8000](http://localhost:8000)
- **API REST (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health check**: [http://localhost:8000/health](http://localhost:8000/health)

---

## 🖥️ Instalação em uma máquina nova

Guia completo para instalar o sistema do zero em um servidor novo, usando apenas este documento. Os comandos de exemplo usam Linux; as diferenças do Windows são indicadas onde existem. Todos os valores de exemplo (usuário, senha, banco) são **fictícios** — use credenciais próprias e mantenha o `.env` fora do versionamento.

### 1. Pré-requisitos

- Linux ou Windows com acesso ao servidor onde ficará o banco.
- **Python 3.10 ou superior** (`python3 --version`).
- **Git** (para obter o projeto).
- **MariaDB ou MySQL** instalado e em execução (pode ser na própria máquina).

### 2. Obter o projeto

```bash
git clone <url-do-repositorio>
cd sistema_patrimonio_mysql
```

### 3. Ambiente virtual Python

Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 4. Dependências

```bash
pip install -r requirements.txt
```

### 5. Instalar e iniciar o MariaDB

- **Linux (Debian/Ubuntu)**: `sudo apt install mariadb-server` e `sudo systemctl enable --now mariadb`.
- **Windows**: instale pelo instalador oficial do MariaDB (ou MySQL) e deixe o serviço iniciado.

### 6. Criar banco, usuário e permissões

Conecte ao MariaDB como root/administrador e execute (valores de exemplo):

```sql
CREATE DATABASE sispatrimonio CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'sispat'@'%' IDENTIFIED BY 'SenhaForte@123';
GRANT ALL PRIVILEGES ON sispatrimonio.* TO 'sispat'@'%';
FLUSH PRIVILEGES;
```

### 7. Criar o arquivo `.env`

Não existe arquivo de exemplo no repositório: crie o `.env` na raiz do projeto. A variável **obrigatória** é a `DATABASE_URL` — sem ela a aplicação não inicia (não há fallback para SQLite na aplicação; SQLite é usado apenas pela suíte de testes):

```env
DATABASE_URL=mariadb+pymysql://sispat:SenhaForte@123@localhost:3306/sispatrimonio

# Opcionais:
# APP_HOST=0.0.0.0        # interface de escuta (padrão atual do código: ver app/config.py)
# APP_PORT=8000
# AUTH_ADMIN_USERNAME=admin
# AUTH_ADMIN_PASSWORD=SenhaForte@123   # use SOMENTE no primeiro start (passo 9)

# Para integrar o Active Directory, veja a seção de AD (AD_SERVER, AD_BASE_DN,
# AD_BIND_USER, AD_BIND_PASSWORD etc.) — o bind pode ser feito também pela tela.
```

### 8. Estrutura do banco

Nada a fazer manualmente: ao iniciar, o `run.py` executa o `init_db()`, que cria as tabelas e aplica a migração leve e idempotente de colunas novas. **Não existe comando de migração manual** — se alguém indicar um, está desatualizado.

### 9. Primeiro administrador (3 caminhos)

- **Opção A — variável de ambiente**: defina `AUTH_ADMIN_USERNAME` e `AUTH_ADMIN_PASSWORD` no `.env`/shell apenas para o primeiro start; o admin é criado automaticamente.
- **Opção B — tela de Primeiro Acesso**: com o banco **sem usuários** e sem `AUTH_ADMIN_PASSWORD`, a tela de login exibe o link **"Primeiro acesso"**, que leva a `/setup` para criar o admin pelo navegador.
- **Opção C — CLI**:

```bash
python -m app.cli create-user --username admin --password 'SenhaForte@123' --name "Administrador" --admin
```

### 10. Iniciar e acessar

```bash
python run.py
```

O servidor escuta na interface/porta definidas por `APP_HOST`/`APP_PORT` (padrões atuais em `app/config.py`; ajuste no `.env` para o IP da sua máquina — `0.0.0.0` escuta em todas as interfaces). Com um navegador, acesse `http://<host>:<porta>/`:

- **Interface Web**: página de login do sistema.
- **API REST (Swagger)**: `http://<host>:<porta>/docs`.
- **Health check**: `http://<host>:<porta>/health`.

### 11. Validação da instalação

- **Health check**: `curl http://localhost:8000/health` (rota pública) deve responder com status saudável.
- **Acesso web**: login com o administrador criado no passo 9.
- **Suíte de testes** (opcional, não exige o MariaDB — usa SQLite em memória): `pytest`.

**Problemas comuns**:

| Sintoma | Causa provável |
|---|---|
| A aplicação não inicia citando `DATABASE_URL` | Variável ausente no `.env` (ou `.env` fora da raiz do projeto) |
| `Can't connect to MySQL server` | MariaDB parado, host/porta errados ou credenciais inválidas na `DATABASE_URL` |
| Não acessa de outra máquina | `APP_HOST` restrito a uma interface — use o IP da máquina ou `0.0.0.0` |
| Porta ocupada | Ajuste `APP_PORT` no `.env` |

---

## 🔐 Autenticação

O sistema exige **login** para a interface web, para a API REST e para as exportações de dados.

### Primeiro usuário (administrador)

O SisPatrimônio Pro oferece **três formas** de criar o primeiro administrador:

**Opção A — Variável de ambiente** (criação automática no primeiro start):

```bash
AUTH_ADMIN_USERNAME=admin AUTH_ADMIN_PASSWORD='SenhaForte@123' python run.py
```

**Opção B — Interface web (Primeiro Acesso):**

Se não houver usuários no banco e `AUTH_ADMIN_PASSWORD` não estiver definida, o sistema exibe automaticamente a tela de **Configuração Inicial** (`/setup`) com um link "Primeiro acesso" na tela de login. Nesta tela, o administrador cria sua conta diretamente pelo navegador:

1. Acesse [http://localhost:8000/login](http://localhost:8000/login)
2. Clique no link **"Primeiro acesso"** (ou acesse diretamente `/setup`)
3. Preencha nome, usuário, e-mail e senha (mínimo 8 caracteres)
4. O sistema criará o administrador e os perfis padrão automaticamente

> ℹ️ A tela de primeiro acesso só está disponível quando **não existem usuários** no banco e **não há** `AUTH_ADMIN_PASSWORD` configurada. Após a criação do primeiro administrador, o link desaparece.

**Opção C — Linha de comando:**

```bash
python -m app.cli create-user --username admin --password 'SenhaForte@123' --name "Administrador" --admin
```

> ⚠️ A senha deve ter **no mínimo 8 caracteres**. Nunca é armazenada em texto puro:
> o sistema grava apenas o hash **PBKDF2-HMAC-SHA256** (salt aleatório por usuário,
> 600.000 iterações por padrão) usando apenas a biblioteca padrão do Python.

### Login e logout

- Acesse [http://localhost:8000/login](http://localhost:8000/login) e entre com usuário/senha.
- O menu do usuário (canto superior direito) exibe o nome logado e o botão **Sair** (`POST /logout`).
- A sessão fica em **cookie HttpOnly + SameSite=Lax**, com token aleatório seguro;
  o banco armazena **apenas o hash** do token. A sessão expira no servidor
  (padrão 8h) e é **revogada no logout** — mesmo que o cookie ainda exista,
  ele deixa de valer.

### O que exige autenticação

| Área | Comportamento sem login |
|---|---|
| Páginas web (`/`, `/assets`, `/custodians`, `/reports/...`, etc.) | Redirecionamento para `/login` (o caminho original é preservado via `?next=`) |
| `/setup` (Primeiro Acesso) | Disponível somente em instalação nova (banco vazio sem usuários) |
| API REST `/api/v1/*` (mutações, consultas e relatórios) | `401 Unauthorized` |
| Exportações CSV (`/api/v1/reports/*/csv`) | `401 Unauthorized` |
| `/health` | Público (monitoramento) |
| `/docs` (Swagger) | Público; as chamadas "Try it out" exigem sessão |
| `/api/v1/auth/login` e `/api/v1/auth/logout` | Públicos (são o ponto de autenticação) |
| `/api/v1/auth/me` | `401` sem sessão |

**Decisão:** toda a API `/api/v1` (inclusive consultas GET) foi protegida porque os
retornos contêm dados sensíveis (CPF, números de série, valores, nomes). Não há
consumidor público da API — ela é o backend administrativo do sistema.

### Primeiro acesso (instalação nova)

Quando uma instalação **não possui nenhum usuário** e **não tem** `AUTH_ADMIN_PASSWORD` configurada:

1. A tela de login (`/login`) exibe um link **"Primeiro acesso"** que leva à página `/setup`
2. O administrador preenche: nome completo, usuário, e-mail (opcional) e senha (mínimo 8 caracteres)
3. O sistema valida os dados e cria o primeiro administrador
4. Os perfis padrão são gerados automaticamente
5. O administrador é redirecionado para o login e pode acessar o sistema

**Proteções do primeiro acesso:**
- Só funciona em instalação nova (banco vazio)
- `AUTH_ADMIN_PASSWORD` desabilita o fluxo (admin já criado pelo env)
- Verificação idempotente contra condição de corrida
- Não é possível repetir a criação inicial depois que o sistema foi inicializado
- Auditoria registra a criação sem expor senha ou credencial

### API via script (curl)

```bash
# 1. Login: guarda o cookie de sessão
curl -c cookies.txt -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=admin&password=SenhaForte@123"

# 2. Usar a API com a sessão
curl -b cookies.txt http://localhost:8000/api/v1/assets
curl -b cookies.txt -o colaboradores.csv http://localhost:8000/api/v1/reports/custodians/csv

# 3. Logout (revoga a sessão no servidor)
curl -b cookies.txt -c cookies.txt -X POST http://localhost:8000/api/v1/auth/logout
```

### Variáveis de ambiente de autenticação

| Variável | Padrão | Descrição |
|---|---|---|
| `AUTH_PROVIDER` | `local` | Provedor ativo (`local` ou `ad`) |
| `AUTH_ADMIN_USERNAME` | `admin` | Usuário admin inicial (criado se `AUTH_ADMIN_PASSWORD` definida) |
| `AUTH_ADMIN_PASSWORD` | *(vazio)* | Senha do admin inicial (mín. 8 caracteres) |
| `AUTH_ADMIN_NAME` | `Administrador` | Nome exibido do admin inicial |
| `AUTH_SESSION_TTL` | `28800` (8h) | Duração da sessão em segundos |
| `AUTH_COOKIE_NAME` | `session` | Nome do cookie de sessão |
| `AUTH_COOKIE_SECURE` | `false` | `true` envia o cookie apenas via HTTPS |
| `AUTH_PBKDF2_ITERATIONS` | `600000` | Iterações do PBKDF2 para hash de senha |
| `AUTH_MAX_FAILED_ATTEMPTS` | `10` | Tentativas de login falhas antes do bloqueio temporário |
| `AUTH_LOCKOUT_SECONDS` | `900` | Duração (s) do bloqueio por excesso de tentativas |

### Proteção contra força bruta (lockout)

Após **10 tentativas de login com senha errada** (padrão atual, configurável via
`AUTH_MAX_FAILED_ATTEMPTS`), a conta fica bloqueada por **15 minutos**
(`AUTH_LOCKOUT_SECONDS`) no servidor (`423 Locked` na API; mensagem na web).
O bloqueio é por conta, registrado na trilha de auditoria (`LOGIN_BLOQUEADO`),
e não revela a existência da conta (o tempo de resposta é equalizado para
usuários inexistentes).

### Fluxo de primeiro acesso

Quando uma instalação **não possui nenhum usuário** e **não tem** `AUTH_ADMIN_PASSWORD` configurada:

1. A tela de login exibe um link **"Primeiro acesso"** que leva à página `/setup`
2. O administrador preenche: nome completo, usuário, e-mail (opcional) e senha
3. O sistema valida: senha mínimo 8 caracteres, confirmação iguais, usuário não vazio
4. Após a criação, os perfis padrão são gerados automaticamente e o administrador é vinculado ao perfil "Administrador"
5. O link "Primeiro acesso" deixa de aparecer após a criação

**Proteções do primeiro acesso:**
- Só funciona em instalação nova (banco vazio sem usuários)
- `AUTH_ADMIN_PASSWORD` desabilita o fluxo (já existe admin pelo env)
- Verificação idempotente: se outra requisição criar o usuário simultaneamente, a segunda é redirecionada para o login
- Não é possível repetir a criação inicial depois que o sistema foi inicializado

---

## 🏢 Integração Active Directory / Samba AD

O sistema autentica via **Active Directory** (Microsoft AD ou **Samba AD DC**)
usando apenas LDAP/LDAPS padrão (biblioteca `ldap3`), **sem substituir** a
autenticação local nem o RBAC existente. Integração **implementada e testada
contra AD real** (bind, busca por `sAMAccountName`, validação de senha por bind
do usuário, leitura de grupos e provisionamento).

### Fluxo de autenticação (implementação real)

```text
Usuário (login com sAMAccountName + senha)
   ↓
SisPatrimônio (resolve_authentication)
   ↓
Conta local existente (auth_provider='local')? → autenticação local (PBKDF2)
   ↓ (não)
AD habilitado?
   ↓
Bind LDAP com a CONTA DE SERVIÇO (AD_BIND_USER / AD_BIND_PASSWORD)
   ↓
Busca do usuário por sAMAccountName (Base DN / DN de busca)
   ↓
Bind LDAP com o DN ENCONTRADO + senha digitada  ← valida a senha
   ↓
Rebind de serviço → leitura de atributos e memberOf (grupos)
   ↓
Conta desabilitada no AD (userAccountControl)? → ACESSO NEGADO
   ↓
Mapeamento Grupo AD → Perfil (prioridade determinística)
   ↓
Sem grupo autorizado/mapeado? → ACESSO NEGADO — somente auditoria
   (usuário NÃO é criado no SisPatrimônio)
   ↓
Provisionamento/atualização do usuário local (guid, DN, e-mail, nome)
   ↓
Perfil atribuído (assigned_by='ad'; perfis manuais preservados)
   ↓
Sessão criada → acesso ao sistema (RBAC interno)
```

> **A autenticação AD NÃO concede acesso.** O acesso só é concedido a
> usuários pertencentes a grupos AD explicitamente autorizados e mapeados
> para perfis existentes. Usuários do domínio sem grupo mapeado têm acesso
> negado e NÃO recebem usuário, colaborador, perfil ou permissões — apenas a
> tentativa é registrada na auditoria.

> **Bind direto do usuário**: cada usuário autentica no AD com a própria
> conta/senha (UPN derivado da Base DN, UPN digitado ou `DOMÍNIO\\sam`) —
> sem conta de serviço. Atributos e grupos (`memberOf`) são lidos na MESMA
> conexão autenticada. A senha nunca é persistida, logada ou auditada.

### Comportamentos garantidos pelo código

- **Login híbrido**: contas locais (ex: `admin`) continuam autenticando como antes; contas `auth_provider='ad'` autenticam sempre no diretório (nunca por senha local).
- **Provisionamento no 1º login**: apenas após confirmar **grupo AD autorizado/mapeado** — cria o usuário do sistema e o vincula ao **colaborador existente** por e-mail/matrícula (nunca duplica cadastro). Usuários do AD não sobrescrevem dados patrimoniais do colaborador (matrícula, CPF, cargo, setor).
- **Sem perfil mapeado**: o usuário é autenticado no AD, porém **não recebe acesso** — mensagem específica ("autenticado, mas não possui um perfil autorizado"), distinta de credencial inválida. **Nenhum usuário/colaborador é criado no banco**; apenas a tentativa fica na auditoria (`GRUPO_AD_SEM_MAPEAMENTO`).
- **Conta desabilitada no AD**: login negado (`userAccountControl`, bit ACCOUNTDISABLE), com histórico/colaborador preservados.
- **Erros diferenciados**: AD indisponível (503), credencial inválida (401), conta desabilitada (401) e falta de perfil (401) têm mensagens e tratamentos próprios.
- **Segurança**: senha do usuário AD nunca é armazenada/logada; a senha da conta de serviço existe somente em variáveis de ambiente (`AD_BIND_PASSWORD`); timeout obrigatório em todas as operações; nenhuma credencial vai para logs ou auditoria.
- **Auditoria**: eventos próprios na trilha existente (`LOGIN_AD_AUTORIZADO`, `LOGIN_AD`, `LOGIN_AD_FALHA`, `CONTA_AD_DESABILITADA`, `USUARIO_AD_PROVISIONADO`, `USUARIO_AD_VINCULADO_COLABORADOR`, `GRUPOS_AD_IDENTIFICADOS`, `GRUPO_AD_SEM_MAPEAMENTO`, `CONFLITO_GRUPOS_AD`, `PERFIL_SINCRONIZADO_AD`, `FALHA_COMUNICACAO_AD`, `ALTERACAO_CONFIG_AD`, `TESTE_CONEXAO_AD`) — sem credenciais.

### Como ativar

1. Tela **Administração → Integração AD**: marque *Habilitar*, informe **Servidor** e **Base DN**, teste a conexão e salve.
2. Cadastre os mapeamentos **Grupo AD → Perfil** na mesma tela (o nome do grupo é o `CN`/`sAMAccountName` do grupo, ex.: `GRP-SISPAT-TECNICOS-TI` ou `Administrators`).
3. Defina as variáveis de ambiente da conta de serviço no processo do servidor:

```env
# Exemplos — NÃO use credenciais reais em repositórios
AD_SERVER=192.168.0.10
AD_BIND_USER=usuario_de_servico@empresa.local
AD_BIND_PASSWORD=senha_da_conta_de_servico
```

Variáveis de ambiente suportadas (fallback/valor inicial dos campos da tela):

| Variável | Função |
|---|---|
| `AD_SERVER` | Host/IP do controlador de domínio |
| `AD_PORT` | Porta (`389` LDAP · `636` LDAPS) |
| `AD_USE_SSL` | `true` para LDAPS |
| `AD_BASE_DN` | Base DN da busca (ex.: `DC=empresa,DC=local`) |
| `AD_USER_DN` | DN de busca de usuários (escopo; vazio = usa a Base DN) |
| `AD_GROUP_BASE_DN` | Base DN de grupos (reservado) |
| `AD_BIND_USER` | Conta de serviço para consultas |
| `AD_BIND_PASSWORD` | Senha da conta de serviço — **somente ambiente, nunca no banco** |

> **Dica operacional**: se o "DN de busca de usuários" estiver vazio, a busca
> usa a Base DN inteira (funciona independentemente da OU onde os usuários
> estão). Um DN de busca apontando para uma OU que não contém os usuários faz
> o login falhar como "credencial inválida" — verifique o log, que registra a
> base usada quando a busca não encontra o usuário.

### Mapeamento Grupo AD → Perfil

- Armazenado na tabela `ad_group_roles` (grupo único → perfil existente + prioridade).
- **Usuário em vários grupos mapeados**: vence a **menor prioridade numérica** (1 = maior). Opcionalmente, o campo `group_role_priority` da tela (CSV de nomes de grupos, em ordem) sobrepõe a prioridade numérica.
- **Sincronização**: perfis atribuídos via AD são marcados `assigned_by='ad'` e substituídos a cada login conforme os grupos atuais; perfis atribuídos **manualmente** (`assigned_by='local'`) **nunca são removidos** pela sincronização.
- **Sem mapeamento**: autentica no AD, mas não recebe acesso — **nenhum usuário é criado no SisPatrimônio** (auditoria `GRUPO_AD_SEM_MAPEAMENTO` com os grupos identificados).

### LDAPS

O uso de **LDAPS (636) com validação de certificado** é o recomendado em
produção (`Usar LDAPS` + `Validar certificado TLS` na tela). Ambientes sem CA
publicada podem desativar a validação explicitamente (`Validar certificado
TLS` desmarcado) — o sistema nunca silencia TLS sem escolha do administrador.
LDAP simples (389) funciona igualmente, incluindo Samba AD DC.

---

## 🔐 Controle de Acesso e Permissões (RBAC)

O sistema implementa **RBAC (Role-Based Access Control)** com o princípio
**deny by default**: um usuário só executa uma operação se possuir
explicitamente a permissão necessária. Nenhuma permissão é concedida por
padrão — usuários novos começam **sem perfil** até um administrador atribuir.

```text
Usuário ──> Perfis (roles) ──> Permissões (modulo.acao)
   N:N                        N:N
```

### Superusuário (`is_admin`)

O flag legado `users.is_admin` é tratado como **superusuário**: ignora todas as
verificações de permissão (bypass total). Ele preserva o comportamento do
usuário administrador inicial. Na prática, recomendamos usar o **perfil
Administrador** para novos administradores (o flag permanece imutável pela
interface — só pode ser concedido via CLI/env).

### Perfis padrão (seed automático e idempotente)

| Perfil | Acesso |
|---|---|
| **Administrador** | Total: usuários, perfis, permissões, auditoria e todos os módulos |
| **Gestor de TI** | Visualiza e cadastra/edita patrimônio, movimenta, registra manutenção, gera relatórios. Sem permissões de sistema |
| **Técnico de TI** | Consulta equipamentos, registra manutenção/diagnóstico/peças, consulta histórico. Não exclui nem administra |
| **Patrimônio** | Cadastra, edita e movimenta bens, cria/confere/encerra inventários, termos e relatórios patrimoniais |
| **Almoxarifado** | Estoque: entradas/saídas e consulta de equipamentos |
| **Auditor** | Somente leitura (patrimônio, movimentações, inventários, histórico, auditoria, relatórios) |
| **Consulta** | Somente leitura dos módulos autorizados (acesso mínimo) |

Perfis padrão (`is_system=True`) **não podem ser excluídos**; podem ser
editados (nome/descrição/permissões) pela interface.

### Catálogo de permissões

Todas as permissões seguem o padrão `modulo.acao`:

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
| Auditoria | `auditoria.visualizar` |

> `movimentacao.cancelar` consta no catálogo, porém é **reservada**: não há tela ou endpoint que a utilize atualmente.

### Endpoints protegidos (API)

| Método | Endpoint | Permissão |
|---|---|---|
| `GET` | `/api/v1/assets`, `/api/v1/assets/{id}`, `/api/v1/assets/tag/{tag}`, `/api/v1/assets/{id}/timeline`, `/api/v1/assets/{id}/depreciation` | `patrimonio.visualizar` |
| `POST` | `/api/v1/assets`, `/api/v1/assets/import/csv` | `patrimonio.criar` |
| `PUT` | `/api/v1/assets/{id}` | `patrimonio.editar` |
| `GET` | `/api/v1/movements`, `/api/v1/movements/{id}`, `/api/v1/movements/{id}/term` | `movimentacao.visualizar` |
| `POST` | `/api/v1/movements` | `movimentacao.criar` |
| `GET` | `/api/v1/custodians*` | `colaboradores.visualizar` |
| `POST` | `/api/v1/custodians`, `/import/csv` | `colaboradores.criar` |
| `PUT` | `/api/v1/custodians/{id}` | `colaboradores.editar` |
| `GET` | `/api/v1/locations*` | `locais.visualizar` |
| `POST` | `/api/v1/locations` | `locais.criar` |
| `PUT` | `/api/v1/locations/{id}` | `locais.editar` |
| `GET` | `/api/v1/reports/dashboard-stats` | `relatorios.visualizar` |
| `GET` | `/api/v1/reports/inventory/{csv,excel,pdf}` | `relatorios.exportar` |
| `GET` | `/api/v1/reports/inventarios/{id}/{csv,excel,pdf}` | `inventario.visualizar` + `relatorios.exportar` |
| `GET` | `/api/v1/reports/movements/csv`, `/api/v1/reports/custodians/csv` e `/api/v1/reports/locations/csv` | `relatorios.exportar` |
| `GET` | `/api/v1/auth/me`, login/logout | Autenticado (público) |

**Status HTTP:** `401` não autenticado · `403` autenticado sem permissão ·
`404` recurso não encontrado · `423` conta temporariamente bloqueada ·
`503` Active Directory indisponível.

### Páginas web protegidas

Toda página exige autenticação + a permissão do módulo (ex: `/assets` →
`patrimonio.visualizar`, `/assets/new` → `patrimonio.criar`, `/admin/users` →
`usuarios.visualizar`). O menu lateral e os botões são renderizados conforme
as permissões do usuário (`can('patrimonio.criar')` nos templates), mas a
**segurança nunca depende da interface** — o backend valida em todas as rotas.

### Administração

| Rota | Permissão |
|---|---|
| `/admin/users` (listar/pesquisar) | `usuarios.visualizar` |
| `/admin/users/new` | `usuarios.criar` |
| `/admin/users/{id}/edit` (dados + perfis) | `usuarios.editar` |
| `/admin/users/{id}/toggle-active` (bloquear/desbloquear) | `usuarios.bloquear` |
| `/admin/users/{id}/reset-password` | `usuarios.editar` |
| `/admin/roles*` | `perfis.*` |
| `/admin/audit` | `auditoria.visualizar` |
| `/admin/ad` (Integração AD) | superusuário **ou** `usuarios.editar` + `perfis.editar` |
| `/profile/password` (troca de senha própria) | autenticado |

**Proteções:** o usuário não pode bloquear a si mesmo; o **último
administrador ativo** não pode ser removido/desativado; a troca de senha
própria exige a senha atual e invalida as sessões existentes; o reset
administrativo também invalida sessões.

### Auditoria (`audit_logs`)

Registra: login, falha de login, login bloqueado, logout, criação, alteração,
bloqueio, desbloqueio, reset/troca de senha, alteração de perfil e
permissões, movimentação patrimonial, importação CSV e **acessos negados
(403)**. Cada registro contém data/hora, usuário (snapshot), ação, módulo,
recurso, ID, IP, resultado e dados anteriores/posteriores (JSON).
A integração AD adiciona os eventos listados na seção de AD — sempre sem
credenciais.

A auditoria é **somente-leitura**: não existe rota de escrita/exclusão e a
consulta exige `auditoria.visualizar`.

### Banco de dados (migração segura)

Tabelas novas: `roles`, `permissions`, `user_roles`, `role_permissions`,
`audit_logs`, `ad_settings`, `ad_group_roles`, `inventarios`, `inventario_itens`,
`setup_claims`. Colunas novas em `users`:
`failed_login_attempts`, `locked_until`, `ad_object_guid`, `ad_dn`,
`ad_last_sync`, `auth_provider`. A migração é automática e idempotente
(`init_db` + `_ensure_schema_migrations` com `ALTER TABLE ADD COLUMN`
condicional) — **nenhum dado existente é alterado ou removido**.

### Como criar uma nova permissão

1. Adicione ao catálogo em `app/services/permission_service.py`
   (`PERMISSION_CATALOG`), no padrão `modulo.acao`.
2. Associe-a aos perfis desejados na interface `Perfis & Permissões` (ou no
   seed `DEFAULT_ROLES` para perfis padrão).
3. O catálogo é sincronizado automaticamente no startup (`ensure_default_roles`).

### Como criar um novo perfil

Use a tela **Administração → Perfis & Permissões → Novo Perfil** (marque as
permissões desejadas). Por código: `permission_service.create_role(...)` +
`update_role(..., permission_names=[...])`.

### Como proteger uma nova rota/endpoint

**API:**
```python
from app.api.deps import require_permission

@router.post("/algo", dependencies=[Depends(require_permission("modulo.acao"))])
def criar_algo(request: Request, db: Session = Depends(get_db)):
    ...
```

**Web:**
```python
@web_router.get("/algo", dependencies=[Depends(require_permission("modulo.acao"))])
def ver_algo(request: Request, db: Session = Depends(get_db)):
    ...
```

**Frontend:** use `{% if can('modulo.acao') %}` no template para exibir/ocultar
botões e itens de menu (apenas apresentação — a validação é no backend).

### Escopo por unidade/setor (evolução futura)

A arquitetura atual não possui conceito de unidade/setor no usuário, então o
controle por escopo (`escopo_global`, `escopo_unidade`, `escopo_setor`,
`escopo_proprio`) foi **avaliado e adiado**. Caminho sugerido: adicionar
`users.department`/`users.unit`, tabelas `user_scopes`/`role_scopes`, e filtrar
os services de patrimônio (ex: `AssetService.get_all`) pelo escopo do usuário
logado, mantendo os testes de RBAC como base.

---

## 💻 Interface de Linha de Comando (CLI)

O SisPatrimônio Pro também inclui uma ferramenta de terminal (`app/cli.py`):

```bash
# Ver resumo e KPIs
python -m app.cli stats

# Listar equipamentos
python -m app.cli list

# Buscar equipamentos
python -m app.cli list --search "MacBook"

# Ver detalhes e linha do tempo de um equipamento
python -m app.cli show PAT-00101

# Registrar uma movimentação pelo terminal
python -m app.cli move PAT-00101 --type ALOCACAO_CAUTELA --custodian-id 1 --reason "Alocação pelo terminal"

# Criar um usuário (login do sistema)
python -m app.cli create-user --username admin --password 'SenhaForte@123' --name "Administrador" --admin

# Criar um usuário com perfil específico (menor privilégio)
python -m app.cli create-user --username maria --password 'SenhaForte@123' --name "Maria" --role "Técnico de TI"
python -m app.cli create-user --username joao --password 'SenhaForte@123' --name "João" --role "Consulta" --role "Auditor"

# Redefinir a senha de um usuário local (senha oculta, pedida duas vezes)
python -m app.cli reset-password --username admin
```

> `create-user` solicita a senha interativamente se `--password` for omitido.
> `--role` pode ser repetido para múltiplos perfis. Sem `--role` nem `--admin`,
> o usuário é criado sem permissões (deny by default) até um administrador
> atribuir perfis pela interface.
>
> `reset-password` redefine a senha de um **usuário local** pelo terminal: a senha
> é sempre digitada de forma oculta (nunca como argumento), com confirmação dupla,
> invalida as sessões ativas do usuário e mantém perfis e situação da conta.
> Usuários autenticados pelo **Active Directory** devem ser tratados no próprio AD.

O catálogo de permissões e os perfis padrão são garantidos automaticamente a
cada execução do CLI (`ensure_default_roles`).

---

## ❓ Central de Ajuda e Manual

O sistema possui uma **central de ajuda integrada** (`/ajuda`), acessível pelo
botão ❓ no cabeçalho ou pelo item "Ajuda e Manual" no menu.

> ℹ️ Os artigos administrativos exigem permissões específicas (usuários, perfis ou auditoria) para visualização.

- **Pesquisa** no manual (artigos e FAQ por texto completo).
- **Artigos** por módulo (primeiros passos, patrimônio, movimentação, manutenção,
  inventários, colaboradores/locais, relatórios, administração — incluindo a
  integração AD) com passos a passo.
- **FAQ** (perguntas frequentes) em acordeão.
- **Ajuda contextual**: tooltips em campos de formulários e botões
  "Como faço isso?" em telas-chave.

O conteúdo fica centralizado em `app/services/help_service.py` (listas
`ARTICLES`, `FAQ` e `CATEGORIES`) — para adicionar um artigo basta criar um
item na lista. Artigos de administração (`audience="admin"`) só são exibidos
para usuários com permissão administrativa.

---

## 🗄️ Banco de Dados e Backup

- **Tecnologia**: MariaDB/MySQL acessado via SQLAlchemy — **serviço de banco externo necessário**.
- **Criação**: automática no primeiro start (`init_db`), incluindo a migração leve e idempotente de colunas novas (seção RBAC acima).
- **Configuração**: via variável de ambiente `DATABASE_URL` (ex: `mariadb+pymysql://usuario:senha@host:3306/banco`).
- **Backup**: utilize as ferramentas nativas do MariaDB (`mysqldump`, `mysqlpump`) ou soluções de backup do sistema operacional.

---

## 🧪 Executando os Testes Automatizados

Para rodar a suite de testes unitários e de integração:

```bash
pytest -v
```

A suite tem **282 testes** e cobre: **controle de acesso** (`tests/test_rbac.py`):
autorização por perfil em APIs e páginas, deny by default, menu dinâmico,
bloqueio/desbloqueio de usuário, lockout por tentativas, auditoria,
proteção do último administrador e tentativas de escalação de privilégios;
**autenticação** (`tests/test_auth.py`); **integração AD** (`tests/test_ad.py`,
com a camada LDAP mockada — inclui regressões do retorno `bool` de
`Connection.search()` e do `raw_values` do `objectGUID`); **inventário
patrimonial** (`tests/test_inventario.py` — fluxo completo via web, RBAC e
exportações CSV/Excel/PDF); movimentações, bens, importações (equipamentos,
colaboradores e locais), navegação/menu, primeiro acesso e central de ajuda.

> ⚠️ Estado atual: 281 testes passam e **1 falha**
> (`tests/test_rbac.py::test_lockout_after_failed_attempts`) — o teste ainda
> espera bloqueio após **5** tentativas, enquanto o padrão de
> `AUTH_MAX_FAILED_ATTEMPTS` em `app/config.py` passou a ser **10**.

Os testes usam **SQLite em memória** por padrão (sem depender do MariaDB);
para executá-los contra outro banco, defina `DATABASE_URL_TEST`.

---

## 📂 Estrutura do Projeto

```
sistema_patrimonio/
├── app/
│   ├── api/                  # Endpoints REST (FastAPI) + dependências de auth/RBAC
│   │   └── v1_router.py      # Agrega: auth, assets, movements, custodians, locations, reports
│   ├── models/               # Modelos SQLAlchemy: User, Session, Role, Permission,
│   │                         #   AuditLog, Asset, Movement, Custodian, Location,
│   │                         #   Maintenance, ADSettings, ADGroupRole,
│   │                         #   Inventario, InventarioItem, SetupClaim
│   ├── schemas/              # Schemas de validação (Pydantic)
│   ├── services/             # Regras de negócio: auth/sessão/RBAC, auditoria,
│   │                         #   asset/movement/custodian/location/maintenance,
│   │                         #   inventario (conferência patrimonial),
│   │                         #   reports/dashboard/help,
│   │                         #   import + custodian_import + location_import (CSV),
│   │                         #   ad_ldap (protocolo LDAP) + ad_service (integração AD)
│   ├── web/                  # Interface Web e Templates Jinja2
│   │   ├── routes.py         # Páginas do sistema (com permissões)
│   │   ├── admin_routes.py   # Administração: usuários, perfis, auditoria, Integração AD
│   │   ├── help_routes.py    # Central de ajuda (/ajuda)
│   │   ├── static/           # CSS e JS customizados
│   │   └── templates/        # HTML (Dashboard, CRUD, inventarios/*, admin/*, 403/404)
│   ├── cli.py                # Interface de linha de comando (create-user --role)
│   ├── config.py             # Configurações gerais (app, auth, AD via env)
│   ├── database.py           # Conexão, sessão SQLAlchemy e migração leve
│   ├── logging_config.py     # Logs técnicos com rotação (data/logs/app.log)
│   └── main.py               # Aplicação principal FastAPI (lifespan, handlers 403/404)
├── data/                     # Diretório de dados (logs, uploads) — não versionar dados sensíveis
├── docs/                     # Documentação técnica e guias internos
├── tests/                    # Suite pytest (auth, rbac, ad, api, assets, movements, inventario, imports, help)
├── seed_demo.py              # Carga de dados de teste realistas (recria as tabelas)
├── run.py                    # Script de inicialização do servidor
└── requirements.txt          # Dependências do projeto
```

---

## 🔒 Segurança

Práticas implementadas (verificáveis no código):

- **Senhas locais**: PBKDF2-HMAC-SHA256 com salt por usuário (600.000 iterações), apenas biblioteca padrão.
- **Sessões**: token de 32 bytes (`secrets.token_urlsafe`) em cookie HttpOnly/SameSite=Lax (Secure configurável); banco guarda apenas o hash SHA-256; expiração e revogação no servidor.
- **Lockout**: bloqueio temporário por conta após N falhas, com timing equalizado para usuários inexistentes.
- **RBAC deny by default** validado no backend em todas as rotas; menu/botões são apenas apresentação.
- **AD/LDAP**: senha do usuário nunca persistida/logada; timeout em todas as operações; LDAPS com validação de certificado recomendado; cada usuário autentica com a própria conta (bind direto, sem conta de serviço).
- **Auditoria** imutável e somente-leitura, incluindo acessos negados, com dados before/after em JSON — nunca credenciais.
- **Open redirect**: o parâmetro `next` do login aceita apenas caminhos internos.

Recomendações para produção: defina `AUTH_COOKIE_SECURE=true` atrás de HTTPS, use LDAPS com certificado válido, forneça `AUTH_ADMIN_PASSWORD` apenas no primeiro start e mantenha `AD_BIND_PASSWORD` fora de arquivos versionados.

---

## 📄 Licença

Não identificada na implementação atual (nenhum arquivo `LICENSE` no repositório).
