

Vou considerar o ambiente que você já está usando:

* Banco: `sispatrimoniopro`
* Usuário: `patrimonio`
* Host: `localhost`
* Porta: `3306`
* Driver Python: `PyMySQL`

## 1. Entrar no MariaDB como administrador

No terminal:

```bash
sudo mariadb
```

Você deverá ver:

```text
MariaDB [(none)]>
```

---

## 2. Criar o banco

Dentro do MariaDB:

```sql
CREATE DATABASE IF NOT EXISTS sispatrimoniopro
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;
```

Confira:

```sql
SHOW DATABASES;
```

Deve aparecer:

```text
sispatrimoniopro
```

---

## 3. Criar o usuário da aplicação

Ainda como administrador:

```sql
CREATE USER IF NOT EXISTS 'patrimonio'@'localhost'
IDENTIFIED BY 'p@tr1m0n10';
```

**Use a mesma senha que você colocou no `DATABASE_URL`.**

Se o usuário já existir, não precisa executar esse comando novamente.

---

## 4. Dar permissão ao usuário

Execute:

```sql
GRANT ALL PRIVILEGES ON sispatrimoniopro.*
TO 'patrimonio'@'localhost';
```

Depois:

```sql
FLUSH PRIVILEGES;
```

Confira:

```sql
SHOW GRANTS FOR 'patrimonio'@'localhost';
```

Você deverá encontrar algo semelhante a:

```text
GRANT ALL PRIVILEGES ON `sispatrimoniopro`.* TO `patrimonio`@`localhost`
```

---

## 5. Testar o usuário diretamente

Saia do MariaDB:

```sql
EXIT;
```

Agora teste:

```bash
mariadb -u patrimonio -p -h localhost sispatrimoniopro
```

Digite a senha do usuário.

Se funcionar, aparecerá:

```text
MariaDB [sispatrimoniopro]>
```

Agora:

```sql
SELECT DATABASE();
```

Resultado esperado:

```text
sispatrimoniopro
```

E:

```sql
SELECT VERSION();
```

Isso confirma que o usuário da aplicação consegue acessar o banco.

Saia:

```sql
EXIT;
```

---

# 6. Configurar o `DATABASE_URL`

No terminal do projeto:

```bash
cd ~/IA/sistema_patrimonio_mysql
```

Configure:

```bash
export DATABASE_URL="mariadb+pymysql://patrimonio:SUA_SENHA@localhost:3306/sispatrimoniopro"
```

Substitua `SUA_SENHA` pela senha real.

### Importante

Se a senha tiver caracteres como:

```text
@
#
/
:
%
?
&
```

ela pode precisar ser codificada na URL.

Para o primeiro teste, uma senha simples facilita bastante.

---

# 7. Confirmar a variável

Execute:

```bash
echo "$DATABASE_URL"
```

Deve aparecer algo semelhante a:

```text
mariadb+pymysql://patrimonio:********@localhost:3306/sispatrimoniopro
```

**Não publique sua senha aqui.**

---

# 8. Testar o SQLAlchemy

Você já fez esse teste e ele funcionou:

```bash
python3 -c "from sqlalchemy import create_engine; import os; e=create_engine(os.environ['DATABASE_URL']); c=e.connect(); print('CONEXÃO COM MARIADB OK'); c.close()"
```

O resultado:

```text
CONEXÃO COM MARIADB OK
```

significa que essa etapa está **OK**.

---

# 9. Verificar se o banco está vazio

Entre novamente:

```bash
mariadb -u patrimonio -p -h localhost sispatrimoniopro
```
python3 -m pip install python-dotenv
Execute:

```sql
SHOW TABLES;
```

Se aparecer:

```text
Empty set
```

**está tudo certo.**

Isso significa que o banco foi criado, mas ainda não possui as tabelas do SisPatrimônio.

Não crie as tabelas manualmente.

Saia:

```sql
EXIT;
```

---

# 10. Deixar a aplicação criar o schema

Agora, no diretório:

```bash
cd ~/IA/sistema_patrimonio_mysql
```

com o `DATABASE_URL` ainda configurado:

```bash
python3 run.py
```

O seu `run.py` executa o `init_db()`, portanto a aplicação deverá criar as tabelas necessárias através do SQLAlchemy.

**Não interrompa imediatamente.** Observe o terminal.

Se iniciar normalmente, você deverá chegar a algo semelhante a:

```text
http://127.0.0.1:8000
```

---

# 11. Conferir as tabelas criadas

Deixe o servidor rodando e abra outro terminal:

```bash
mariadb -u patrimonio -p -h localhost sispatrimoniopro
```

Execute:

```sql
SHOW TABLES;
```

Agora você deverá ver várias tabelas do SisPatrimônio.

Por exemplo, dependendo dos seus modelos:

```text
users
roles
permissions
...
```

Não use esses nomes como referência para criar tabelas manualmente; o importante é verificar o que **o próprio sistema** criou.

---

# 12. Conferir a quantidade de tabelas

Você pode executar:

```sql
SELECT COUNT(*) AS quantidade_tabelas
FROM information_schema.tables
WHERE table_schema = 'sispatrimoniopro';
```

Isso fornece a quantidade de tabelas criadas.

---

# 13. Conferir o mecanismo das tabelas

É importante que as tabelas estejam usando um mecanismo adequado para MariaDB, normalmente **InnoDB**.

Execute:

```sql
SELECT TABLE_NAME, ENGINE
FROM information_schema.tables
WHERE TABLE_SCHEMA = 'sispatrimoniopro'
ORDER BY TABLE_NAME;
```

O esperado é encontrar:

```text
InnoDB
```

nas tabelas.

---

# 14. Conferir charset

Execute:

```sql
SELECT
    TABLE_NAME,
    TABLE_COLLATION
FROM information_schema.tables
WHERE TABLE_SCHEMA = 'sispatrimoniopro'
ORDER BY TABLE_NAME;
```

Idealmente as tabelas estarão utilizando uma collation baseada em `utf8mb4`.

Isso é especialmente importante para o sistema porque ele poderá armazenar:

* nomes;
* endereços;
* descrições;
* setores;
* observações;
* caracteres acentuados;
* símbolos.

---

# 15. Testar gravação

Depois que o sistema criar as tabelas, **não faça INSERT manualmente ainda**.

Entre pelo sistema e teste uma operação real, por exemplo:

1. Login.
2. Abrir uma funcionalidade que consulte o banco.
3. Criar um registro de teste.
4. Alterar o registro.
5. Consultar novamente.
6. Verificar se a alteração permanece.

Depois confira no MariaDB.

---

# 16. Muito importante: não migrar o `patrimonio.db` ainda

Neste momento temos duas coisas diferentes:

### Banco novo

```text
MariaDB
└── sispatrimoniopro
```

### Banco antigo

```text
SQLite
└── data/patrimonio.db
```

**Não apague o `patrimonio.db` ainda.**

Primeiro precisamos confirmar que:

* todas as tabelas foram criadas;
* os modelos funcionam;
* login funciona;
* usuários funcionam;
* permissões funcionam;
* patrimônio funciona;
* auditoria funciona;
* AD funciona;
* gravações funcionam.

Se você ainda precisa dos **dados existentes do SQLite**, aí teremos uma segunda etapa: **migração dos dados do `patrimonio.db` para o MariaDB**.

Essa etapa é diferente de simplesmente criar o banco.

---

## Sequência que eu recomendo para você

```text
1. MariaDB instalado                         ✅
2. Banco sispatrimoniopro criado             ✅
3. Usuário patrimonio criado                 ✅
4. Permissões concedidas                     ✅
5. Login direto no MariaDB                   ✅
6. SQLAlchemy → MariaDB                      ✅
7. DATABASE_URL configurado                  ✅
8. Executar python3 run.py                   ← AGORA
9. Sistema criar as tabelas                  ← AGORA
10. SHOW TABLES                              
11. Testar login
12. Testar CRUD
13. Validar funcionalidades
14. Migrar dados do SQLite, se necessário
15. Remover definitivamente SQLite
```

### O próximo passo agora é simples

Execute:

```bash
python3 run.py
```

Se aparecer algum erro, **pare aí e me mande o erro completo**. Principalmente se for relacionado a `database.py`, `SQLite`, `ALTER TABLE`, `CREATE TABLE`, `AUTO_INCREMENT`, `DATETIME` ou `SQLAlchemy`.

A partir desse erro dá para ajustar **somente o necessário para a migração MariaDB**, sem sair alterando o restante do SisPatrimônio.





python3 -m pip install python-dotenv

*** Alterar a senha do usuario do banco
ALTER USER 'patrimonio'@'localhost'
IDENTIFIED BY 'p@tr1m0n10';

Depois:

FLUSH PRIVILEGES;

E saia:

EXIT;

