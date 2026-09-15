# Phase 1 — Quickstart: Validação da Feature 002 (CLI reset-password)

**Objetivo**: provar que o subcomando funciona fim a fim, falha de forma segura e não
regrediu nada. Pré-requisitos: Python 3.10+, dependências instaladas, **sem** `DATABASE_URL`
definida para a suíte (testes usam SQLite in-memory — não configurar banco de produção).

## 1. Suíte de não-regressão (obrigatória)

```bash
pytest -v
```

**Resultado esperado**: todos os testes existentes no estado atual conhecido
(**153 aprovados, 1 falha defasada conhecida** —
`tests/test_rbac.py::test_lockout_after_failed_attempts`, documentada na baseline 001)
**+ os novos testes de `tests/test_cli_reset_password.py` aprovados**.

> Qualquer falha **diferente** dessa indica regressão real → investigar antes de prosseguir.
> Nenhum teste existente é editado nesta feature.

## 2. Validação funcional do subcomando (manual, contra MariaDB)

Executar contra o MariaDB configurado em `DATABASE_URL` do ambiente de teste/demonstração
(banco **não produtivo**; a aplicação não opera sem essa variável — `app/config.py`):

```bash
# 2.1 Sucesso (senha nunca aparece na tela):
python -m app.cli reset-password --username <usuario_local_existente>
#   → digitar nova senha (≥ 8 caracteres) duas vezes, sem eco
#   Esperado: "Sucesso: senha redefinida..." e exit 0

# 2.2 Sessões invalidadas: com o usuário alvo logado na aplicação antes do reset,
#     após o reset qualquer requisição dele deve redirecionar para o login.

# 2.3 Confirmação divergente:
#   → digitar duas senhas diferentes
#   Esperado: "Erro: as senhas não conferem." e exit 1; senha antiga continua válida

# 2.4 Política: digitar senha de 7 caracteres
#   Esperado: "Erro: A nova senha deve ter no mínimo 8 caracteres." e exit 1

# 2.5 Usuário inexistente:
python -m app.cli reset-password --username nao_existe_xyz
#   Esperado: "Erro: usuário 'nao_existe_xyz' não encontrado." e exit 1

# 2.6 Usuário AD (se houver em ambiente com AD):
python -m app.cli reset-password --username <usuario_ad>
#   Esperado: mensagem de recusa (apenas senha local; não altera AD) e exit 1

# 2.7 Exposição: durante a execução, conferir em outro terminal
#   - `ps -ef | grep reset-password` → a senha NÃO aparece nos argumentos
#   - tail -f data/logs/app.log data/logs/app.error.log → a senha NÃO aparece
```

## 3. Auditoria (verificação na tela Administração → Auditoria ou via banco de leitura)

Para cada execução da seção 2 deve existir **exatamente 1** registro com:

- Ação: **Redefinição de Senha** (`RESET_SENHA`); Usuário (ator): vazio; Username: alvo;
- Resultado: `SUCCESS`/`FAILURE` conforme o caso; Descrição: menciona origem CLI;
- **Nenhum registro contém a senha** (nem substring dela).

## 4. Checklist de conformidade (Constitution) — para a entrega

- [ ] Escopo: somente `app/cli.py` + novo teste + documentação (plan §10/§11)
- [ ] Comportamento existente preservado (suíte no estado conhecido)
- [ ] Nenhuma credencial/segredo em logs, auditoria, testes ou docs
- [ ] Banco: nenhum DDL executado; nenhuma conexão de escrita fora do serviço
- [ ] Documentação atualizada na mesma tarefa (README, 2 docs de manutenção, central de ajuda)

## 5. Critérios de aceite da feature (da spec)

- **SC-001**: reset completo (comando + prompts ocultos) em < 2 min usando apenas `--help`.
- **SC-002**: 1 registro de auditoria por execução, sempre.
- **SC-003**: zero ocorrências da senha em argv/logs/auditoria/saídas (seção 2.7 e testes).
- **SC-004**: todos os casos de erro com mensagem clara não sensível e alvo inalterado.
- **SC-005**: 100% das sessões anteriores do alvo invalidadas após o reset.
- **SC-006**: suíte de autenticação existente 100% aprovada + novos testes aprovados.
