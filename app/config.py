import os
from pathlib import Path

# Imports de terceiros
from dotenv import load_dotenv

# Diretórios base
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Configurações do Banco de Dados
# O sistema utiliza exclusivamente MariaDB/MySQL.
# A URL de conexão deve ser fornecida via variável de ambiente DATABASE_URL.
#
# Formato esperado:
#   mariadb+pymysql://USUARIO:SENHA@HOST:3306/BANCO
#
# Exemplo:
#   export DATABASE_URL="mariadb+pymysql://sispatrimonio:senha@localhost:3306/sispatrimonio_pro"
#
# Não há fallback para SQLite. Se DATABASE_URL não estiver configurada,
# a aplicação não será iniciada.

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL não configurada. "
        "Configure a variável no arquivo .env."
    )

# Configurações da Aplicação
APP_NAME = "SisPatrimônio Pro"
APP_DESCRIPTION = "Sistema Integrado de Gestão Patrimonial e Fluxo de Movimentação de Equipamentos"
APP_VERSION = "1.0.0"
APP_HOST = os.getenv("APP_HOST", "127.0.0.1")
APP_PORT = int(os.getenv("APP_PORT", "8000"))

# Organização padrão para emissão de termos
COMPANY_NAME = "© Instituto de Previdência do Municipio de João Pessoa."
COMPANY_CNPJ = "40.955.403/0001-09"
COMPANY_ADDRESS = "Rua Engenheiro Clodoaldo Gouveia, 166, Centro, João Pessoa/PB"

# ============================================================================
# AUTENTICAÇÃO
# ============================================================================

# Provedor de autenticação ativo. Valores: "local" (padrão).
# "ad"/"ldap"/"ldaps" estão reservados para futura integração com Active Directory.
AUTH_PROVIDER = os.getenv("AUTH_PROVIDER", "local")

# Duração da sessão em segundos (padrão: 8 horas)
AUTH_SESSION_TTL = int(os.getenv("AUTH_SESSION_TTL", "28800"))

# Nome do cookie de sessão
AUTH_COOKIE_NAME = os.getenv("AUTH_COOKIE_NAME", "session")

# Marcar o cookie de sessão como Secure (enviar apenas via HTTPS).
# Em produção atrás de HTTPS, defina AUTH_COOKIE_SECURE=true.
AUTH_COOKIE_SECURE = os.getenv("AUTH_COOKIE_SECURE", "false").strip().lower() == "true"

# Iterações do PBKDF2-HMAC-SHA256 para hash de senha (padrão OWASP 2023)
AUTH_PBKDF2_ITERATIONS = int(os.getenv("AUTH_PBKDF2_ITERATIONS", "600000"))

# Proteção contra força bruta no login: após N tentativas falhas consecutivas,
# a conta fica bloqueada por X segundos (o bloqueio é por conta, no servidor).
AUTH_MAX_FAILED_ATTEMPTS = int(os.getenv("AUTH_MAX_FAILED_ATTEMPTS", "5"))
AUTH_LOCKOUT_SECONDS = int(os.getenv("AUTH_LOCKOUT_SECONDS", "900"))

# Usuário administrador inicial criado automaticamente no primeiro start
# quando AUTH_ADMIN_PASSWORD não estiver vazio. Use o CLI (python -m app.cli
# create-user) para criar outros usuários sem variáveis de ambiente.
AUTH_ADMIN_USERNAME = os.getenv("AUTH_ADMIN_USERNAME", "admin")
AUTH_ADMIN_PASSWORD = os.getenv("AUTH_ADMIN_PASSWORD", "")
AUTH_ADMIN_NAME = os.getenv("AUTH_ADMIN_NAME", "Administrador")

# ============================================================================
# ACTIVE DIRECTORY / LDAP — Integração (tela Administração → Integração AD;
# variáveis abaixo funcionam como fallback/valor inicial dos campos vazios).
# A SENHA do usuário de serviço NUNCA vai para o banco: só ambiente.
# ============================================================================
AD_SERVER = os.getenv("AD_SERVER", "")
AD_PORT = int(os.getenv("AD_PORT", "636"))
AD_USE_SSL = os.getenv("AD_USE_SSL", "false").strip().lower() == "true"
AD_BASE_DN = os.getenv("AD_BASE_DN", "")
AD_USER_DN = os.getenv("AD_USER_DN", "")
AD_GROUP_BASE_DN = os.getenv("AD_GROUP_BASE_DN", "")
AD_BIND_USER = os.getenv("AD_BIND_USER", "")                # conta de serviço (consulta)
AD_BIND_PASSWORD = os.getenv("AD_BIND_PASSWORD", "")        # senha do serviço (somente ambiente)
