# Quickstart: Validação da Central de Integrações (feature 032)

## 1. Pré-requisitos

- Ambiente Python do projeto (`.venv`), dependências de `requirements.txt` (nada novo).
- Banco de teste: SQLite em memória via suíte (`conftest.py`), como nas features 030/031.

## 2. Suíte automatizada

```bash
python -m pytest tests/ -q
# esperado: suíte existente (617+novos das 030/031) VERDE + novos testes de test_central_integracoes.py
python -m pytest tests/test_central_integracoes.py -q
# esperado: 100% dos cenários da spec §22 verdes
```

## 3. Validação manual — acesso e RBAC

1. Login como `admin` → menu Administração → **Central de Integrações** (entrada visível com `integracoes.visualizar`).
2. Painel: 4 cards — E-mail (ATIVA ou conforme SMTP), 1Doc (**PENDENTE** — aguardando fornecedor), GLPI (NÃO CONFIGURADA), AD (ATIVA se habilitado / DESABILITADA senão).
3. Login com usuário SEM `integracoes.visualizar` → entrada de menu ausente; acesso direto a `/admin/integracoes` → 403 amigável, evento `ACESSO_NEGADO` na Auditoria.
4. Conceder `integracoes.visualizar` (sem `integracoes.testar`) a um perfil de teste → painel e histórico visíveis; botão "Testar conexão" não aciona (e-mail/1doc exigem `integracoes.testar`); teste do AD redireciona à tela AD (guarda `usuarios.editar` + `perfis.editar` vigente).

## 4. Validação manual — diagnóstico, teste e histórico

1. Detalhe do E-mail: mostra configuração efetiva com `SMTP_PASSWORD` **mascarado** ("configurada") — nunca o valor.
2. "Testar conexão" no E-mail (com SMTP válido do ambiente): mensagem de sucesso com latência; registro em histórico e evento `TESTE_INTEGRACAO_SUCESSO` na Auditoria. Com SMTP inválido: `TESTE_INTEGRACAO_FALHA`, mensagem amigável classificada (autenticação × indisponibilidade), sem segredo no texto.
3. Detalhe do 1Doc: status PENDENTE ("aguardando informações do fornecedor"); teste interno apenas (verificação de configuração) — nenhuma chamada HTTP externa.
4. Histórico do e-mail: filtre por status/operação/período; paginação funcional; detalhes sanitizados.
5. Propagação: abra uma movimentação com e-mail SENT + 1Doc PENDING → "✓ enviado / ⚠ pendente / — não aplicável (GLPI)"; movimentação antiga sem registros → colunas "—".
6. Reprocessamento 1Doc: a partir do detalhe, link conduz à tela existente `/admin/integracao-1doc` (permissão `integracao1doc.reprocessar` vigente); após reprocesso, o card 1Doc reflete o novo estado.
7. Janela de falhas: card exibe "Falhas recentes (24h): N" — contagem coerente com o histórico.

## 5. Validação REAL externa (não bloqueia a Central)

- E-mail real: teste com o SMTP do IPMJP (produção/homologação) — opcional, não destrutivo.
- 1Doc: bloqueado até C-1..C-8 do fornecedor (`docs/SOLICITACAO_API_1DOC.md`).
- GLPI: sem integração nesta versão — nada a validar externamente.

## 6. Escopo final (Constitution XII)

```bash
git status --short
# esperado: APENAS arquivos do plan.md — integration_execution.py, integration_center_service.py,
# toques mínimos (email_provider, notification_service, onedoc_service, permission_service,
# audit_service, database.py, admin_routes.py, base.html), 4 templates novos, tests/test_central_integracoes.py, docs.
# INTOCADOS: movement_service, backup_*, ad_service/ad_ldap, onedoc_client, telas admin existentes.
```
