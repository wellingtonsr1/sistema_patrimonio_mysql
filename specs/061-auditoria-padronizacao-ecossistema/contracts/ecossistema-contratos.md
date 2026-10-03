# Contracts — Feature 061 (contratos estáveis do ecossistema)

*Contratos que a implementação DEVE preservar e comprovar. Formato textual (scripts/infra); não há API nova. Referências: `specs/027-instalador-producao-linux/contracts/installer-contract.md` (instalador Linux), spec 056 (HTTPS).*

## C1 — Contrato do snapshot PRO (entrada do instalador)

```text
DADO um commit da dev publicado por deploy.sh OU deploy.bat
O snapshot publicado no SisPatrimonioPro (branch main):
  1. contém exatamente: app/ · data/{backups,logs}/.gitkeep · docs/*.md (sem doc_provi*) ·
     .gitignore · README.md · requirements.txt · run.py · seed_demo.py ·
     sistema_patrimonio.png · SPEC-KIT-SISTEMA-ATUAL.md
  2. contém tudo que a instalação precisa (validado por instalação a partir do PRO)
  3. não contém: specs/ · tests/ · scripts/ · install.sh · uninstall.sh · deploy.* ·
     test.bat · Docker · venv · data/ssl/ · .env · logs/backups reais · residuais (*~, *-old, _teste_*)
  4. é idêntico para a mesma dev, gerado por .sh ou .bat (independente do SO)
  5. carrega rastreabilidade: mensagem com commit dev de origem
VIOLAÇÃO: qualquer item divergente sem classificação explícita no relatório (Entregável D)
```

## C2 — Contrato HTTPS da instalação (baseline 056 reproduzido)

```text
DADO o instalador executado (Linux OU Windows), com HTTPS no fluxo padrão de instalação:
  1. certificado + CA gerados (idempotentes; --force para regenerar) com SAN:
     IP:<ip-lan>, DNS:localhost, DNS:sispatrimoniopro.local (+ hostname real quando aplicável)
  2. chave privada em diretório de dados da instalação, FORA do Git/snapshot, permissão restrita
  3. .env resultante define: APP_SSL_CERTFILE, APP_SSL_KEYFILE, APP_PORT=8000,
     AUTH_COOKIE_SECURE=true  (nunca AUTH_COOKIE_SECURE=true sem TLS ativo)
  4. serviço reinicia com TLS ativo na porta 8000; https://host:8000 responde /health
  5. HTTPS sobrevive a: reboot do servidor · reinício do serviço · atualização · reinstalação
     (cert existente válido NÃO é sobrescrito/apagado sem motivo documentado)
  6. acesso http://host:8000 → falha de handshake no cliente (sem redirect nativo; D-002)
  7. firewall: regra nomeada idempotente criada automaticamente para a porta 8000
     (sem privilégio → falha com orientação clara; clarify Q5)
VIOLAÇÃO: qualquer etapa manual pós-instalação para o HTTPS funcionar (SC-003)
```

## C3 — Contrato de banco (paridade MariaDB × MySQL por configuração)

```text
DADO a mesma base de código:
  1. mariadb+pymysql://… (Linux) e mysql+pymysql://… (Windows) funcionam sem editar código
  2. DATABASE_URL montada SOMENTE por montagem programática (percent-encoding de senha
     com caracteres especiais); nenhuma montagem manual em scripts/instaladores
  3. criação/evolução de schema permanece idempotente e aditiva (init_db() da aplicação);
     instaladores apenas garantem banco/usuário/privilégios — nunca DDL próprio
  4. banco/usuário existentes são reutilizados; nenhuma recriação sem --recreate-db (dupla confirmação)
  5. utilitários de backup/restore (mysqldump/cliente) presentes conforme o SGBD detectado
VIOLAÇÃO: comportamento exclusivo de um banco sem registro na matriz (Entregável B)
```

## C4 — Contrato de segurança dos scripts (deploy + instaladores)

```text
1. Nenhuma senha/segredo/chave privada em: Git · snapshot PRO · logs · argv ·
   mensagens de erro · histórico · saída do PowerShell · arquivos temporários
2. coleta de senha sem eco ou geração criptográfica (padrão 027: MYSQL_PWD em ambiente, não argv)
3. .env sempre 0600 (Linux) / equivalente no Windows; existente nunca sobrescrito sem backup+confirmação
4. operações destrutivas: nenhuma automática (banco/dados intocáveis por padrão)
VIOLAÇÃO: SC-009 falha
```

## C5 — Contrato do fluxo ponta a ponta (Fase 5)

```text
dev (sistema_patrimonio_mysql, main)
  → deploy.sh "msg"  (Linux)  ┐
  → deploy.bat "msg" (Windows)┘→ GitHub dev (histórico completo) + PRO (snapshot C1)
  → instalador Linux (install.sh) OU instalador Windows → produção instalada (C2+C3+C4)
  → validação: /health via https://host:8000 · CA instalada no cliente · reboot/restart OK
```
