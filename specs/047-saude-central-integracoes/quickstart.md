# Quickstart: 047 — Saúde da Central de Integrações

**Validação ponta a ponta da feature.** Comandos usam `.venv/bin/python` (não `python` crua). Suíte baseline: **748 passed**.

## Pré-requisitos

- Venv com dependências do projeto; banco de teste via `tests/conftest.py` (SQLite em memória) para a suíte.
- Para validação manual com dados reais: login de administrador com permissões `integracoes.visualizar` (e `integracoes.testar` para testes).

## Cenários de validação (mapeiam os Testes A–M do pedido — spec §12)

### Cenário A — Central acessível com 10 componentes (US1)

1. `.venv/bin/python -m pytest tests/test_central_saude.py -q` — teste "painel renderiza 10 cards" verde.
2. Manual: login admin → **Administração → Central de Integrações**.
3. **Esperado**: uma única página com os 10 cards (Aplicação, Banco de Dados, Armazenamento, Active Directory, E-mail, GLPI, Backup Local, Backup Externo, Agendador de Backup, 1Doc); sem subpágina "Visão geral".

### Cenário B — Banco conectado (US1)

1. Teste automatizado da `_database_status_fn` (sessão viva → `ATIVA`/"Conectado").
2. **Esperado**: card Banco de Dados verde com resumo "Consulta: OK"; nenhuma conexão nova criada (a sessão da request é reutilizada).

### Cenário C/D — GLPI honesto (US1)

1. Teste automatizado: sem implementação GLPI → `NAO_CONFIGURADA`, sem botão de teste.
2. **Esperado**: card GLPI cinza "Não Configurada" com a nota de previsão; painel inteiro renderiza (ausência de cliente não quebra nada).

### Cenário E/F — Backup Externo OK × falha (US1)

1. Seed: `BackupExternalConfig` habilitada + último `BackupExternalRecord` SUCCESS → teste da status_fn → `ATIVA`/"OK".
2. Seed alternativo: último registro FAILURE → `COM_ERRO`/"Falha"; aplicação segue de pé (SC-007).
3. **Esperado**: card mostra Habilitado/Destino/Última cópia; **nenhuma cópia nem teste de destino executado ao abrir a página**.

### Cenário G/H — AD e E-mail (regressão da 032)

1. Suíte existente `tests/test_central_integracoes.py` permanece verde.
2. **Esperado**: cards AD/E-mail mantêm comportamento e rótulos atuais; teste do AD segue conduzindo à tela própria (guarda vigente).

### Cenário I — Agendador (US1)

1. Teste automatizado: `scheduler_status()` com `enabled=True` → `ATIVA`/"Ativo" com agendamento e próximo backup; `enabled=False` → `DESABILITADA`/"Desabilitado" (distinto de falha).
2. **Esperado**: card mostra Agendamento/Próximo backup/Último resultado; nenhum thread novo criado pelo painel.

### Backup Local — regra do clarify (US1)

1. Testes automatizados: agendador ativo com último backup válido dentro do ciclo → "OK"; ciclo passado sem backup novo (folga de 1 ciclo) → `ATENCAO`/"Sem backup recente"; nenhum backup válido → `COM_ERRO`; agendador desabilitado com falha registrada → `COM_ERRO`; desabilitado sem falha → "OK".
2. **Esperado**: card mostra Último válido/Válidos no disco/Última falha; nenhum backup gerado ao abrir a página.

### Armazenamento — regra do clarify (US1)

1. Testes automatizados (tmp_path): diretório com espaço livre ≥ tamanho do último backup válido → "OK"; espaço livre < referência → `ATENCAO`/"Espaço limitado"; diretório ausente → `COM_ERRO`; sem backup válido de referência → "OK" com nota.
2. **Esperado**: card mostra Diretório/Livre/Último backup; **nenhum arquivo de teste gravado ao abrir a página**.

### Teste do destino externo pela Central (US2)

1. Com `integracoes.testar` e destino válido (tmp_path em teste): `POST /admin/integracoes/backup_externo/testar`.
2. **Esperado**: mensagem de sucesso da função `test_destination` da 045; registro em `IntegrationExecution` + auditoria (`ACTION_CENTRAL_TESTE_*`); **nenhum backup gerado; nenhum arquivo deixado no destino**; falha de destino → mensagem amigável sanitizada, aplicação de pé.

### Segurança e RBAC (US3)

1. Sem `integracoes.visualizar`: `GET /admin/integracoes` → 403 amigável (auditado — padrão existente).
2. Com permissão e SMTP/1Doc configurados: nenhum segredo na renderização (varredura do teste — SC-003).
3. Carregamentos repetidos do painel: 0 eventos de auditoria criados (apenas testes manuais registram).

### Responsividade e temas (US4 — Testes J/K)

1. Larguras de referência: 1440 (3 colunas), 1024 (2 colunas), 375 (1 coluna) — verificar reordenação sem quebra.
2. Tema claro e escuro: badges (verde/amarelo/vermelho/cinza) legíveis nos dois temas.
3. Redimensionar a janela entre breakpoints: grid reorganiza sem sobreposição (comportamento Bootstrap vigente).

### Regressão (Teste M)

```bash
.venv/bin/python -m pytest tests/ -q   # esperado: 748 passed + novos testes da 047
```

## Comprovação de "consulta ≠ teste" (SC-002)

- Os testes automatizados da `_database_status_fn`/`_storage_status_fn`/`_backup_externo_status_fn` usam fakes/monkeypatch para **contar chamadas** a `BackupService.generate_backup`, `test_destination`, `check_connection`, `ad_ldap.test_connection` — todas **0** durante o `GET` do painel.

## Notas

- Validação manual de responsividade/temas registrada em `validacao.md` na implementação (sem screenshots obrigatórios).
- Falha de qualquer mecanismo externo nos testes = fake/monkeypatch — nunca serviço real (padrão da suíte).
