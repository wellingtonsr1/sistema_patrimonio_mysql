# Quickstart: Validação da Notificação por E-mail de Movimentações (feature 030)

Protocolo de validação ponta a ponta. Executar após o `/speckit-implement`.

## 1. Pré-requisitos

- Ambiente ativo (Python 3.10+; `pip install -r requirements.txt` — nenhuma dependência nova);
- MariaDB via `DATABASE_URL` (o `init_db` cria as tabelas novas `notifications` e `email_config` automaticamente no start);
- **SMTP de teste**: para validar sem servidor real, preencha `SMTP_*` no `.env` apontando para uma conta de teste institucional (ou valide os cenários de falha deixando `SMTP_HOST` vazio/apontando para host inexistente);
- Usuário com a permissão `notificacoes.gerenciar` concedida (o admin concede no cadastro de perfis — permissão nova, ninguém a tem por padrão);
- Um bem cadastrado + 2 colaboradores + 2 locais.

## 2. Suíte automatizada (primeira validação)

```bash
python -m pytest tests/ -q
```

**Esperado**: 100% verde — incluindo o novo `tests/test_notificacoes.py` (13 cenários da spec Seção 14: sucesso, falha de SMTP, movimentação inválida, desativado, destinatários, conteúdo, idempotência, segurança, lote CSV, tipos fora do alcance, configuração/RBAC, auditoria, não-regressão).

## 3. Cenário A — Sucesso ponta a ponta (US1)

1. Login como admin → **Administração → Notificações** (`/admin/notificacoes`);
2. Ativar notificações; preencher destinatários (ex.: `patrimonio@test.local`); salvar;
   - **Esperado**: flash de sucesso; auditoria registra `CONFIG_NOTIFICACAO_ALTERADA` (before/after).
3. Em **Bens**, concluir uma **Alocação/Cautela** do bem para um colaborador;
4. Verificar:
   - [ ] e-mail recebido pelo destinatário configurado (e somente por ele);
   - [ ] assunto: `[SisPatrimônio Pro] Nova movimentação patrimonial - <TAG>`;
   - [ ] corpo contém: tombamento, identificação, tipo "Alocação / Cautela", local/custodiante de origem e destino, data/hora local (America/Recife), operador (usuário autenticado);
   - [ ] **sem link** no e-mail;
   - [ ] auditoria: `NOTIFICACAO_ENVIADA` com módulo "notificacoes", recurso movement/<id>, resultado SUCCESS;
   - [ ] movimentação concluída normalmente na tela (nenhum erro/latência perceptível além do timeout).

## 4. Cenário B — SMTP indisponível (US2 — regra fundamental)

1. Editar `.env`: `SMTP_HOST=smtp.invalido.teste` (host inexistente); reiniciar;
2. Concluir uma **Transferência de Local** válida;
3. Verificar:
   - [ ] movimentação **concluída e persistida** (sucesso normal na tela);
   - [ ] nenhuma mensagem de erro ao operador; nenhuma exposição de credencial/host/senha;
   - [ ] auditoria: `NOTIFICACAO_FALHOU` com descrição técnica sanitizada, resultado FAILURE;
   - [ ] tempo da resposta dentro do timeout configurado (default 10 s).

## 5. Cenário C — Desativado (default de fábrica / US3.3)

1. Na tela de Notificações, **desativar** e salvar;
2. Concluir uma **Devolução ao Estoque**;
3. Verificar:
   - [ ] nenhum e-mail; nenhum registro em `notifications`; nenhum evento de notificação na auditoria;
   - [ ] movimentação concluída normalmente.

## 6. Cenário D — Idempotência e tipos fora do alcance (US4/Q1)

1. Com notificações **ativadas**:
2. Incluir um bem por **Entrada por Aquisição** (tipo fora do alcance — RN-002):
   - [ ] movimentação gravada; **nenhum** e-mail e nenhum registro de notificação;
3. (Via suíte) executar duas vezes o fluxo de notificação para a mesma movimentação:
   - [ ] somente 1 registro `Notification` e 1 e-mail (fake) — idempotência;
4. (Via suíte) importar um CSV de bens com movimentações:
   - [ ] nenhum e-mail por linha do lote (RN-002/Q2).

## 7. Cenário E — RBAC (US3.2)

1. Login com usuário **sem** `notificacoes.gerenciar`;
2. Acessar `/admin/notificacoes` diretamente:
   - [ ] acesso negado (padrão 403 amigável do sistema); auditado como `ACESSO_NEGADO`.

## 8. Checklist final de aceite (espelha spec Seção 15)

- [ ] Suíte completa verde (incluindo não-regressão);
- [ ] E-mail somente após persistência (RN-003); falha de e-mail nunca afeta a movimentação (RN-001);
- [ ] Assunto/conteúdo conforme RN-005/FR-008; sem link (RN-008);
- [ ] Destinatários/ativação configuráveis pela tela; credenciais só em `.env` (nenhuma credencial em tela/banco/logs/auditoria);
- [ ] Máx. 1 notificação por movimentação (SC-003);
- [ ] Documentação atualizada (README `SMTP_*`, docs/ARQUITETURA, artigo em `/ajuda`).
