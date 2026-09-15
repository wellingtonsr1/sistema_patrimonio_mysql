# Contract — CLI `reset-password` — estado proposto (feature 002)

**Base**: extensão da CLI existente (`app/cli.py`), seguindo os padrões atuais dos
subcomandos. Este contrato define a interface do novo subcomando para implementação,
testes e validação.

## Comando

```text
python -m app.cli reset-password --username <usuario>
```

| Elemento | Regra |
|---|---|
| Subcomando | `reset-password` (kebab-case inglês, padrão da CLI — decisão D-4) |
| `--username` | Obrigatório. Username do usuário alvo (local). Normalização: strip; match exato (mesma do login) |
| Senha | **NUNCA** aceita como argumento, opção, env ou arquivo. Fornecida exclusivamente por prompt sem eco (`getpass`), duas vezes (entrada + confirmação — decisão D-1) |

## Prompts (interativos, sem eco)

1. `Nova senha: `
2. `Confirme a nova senha: `

Nenhum prompt é exibido antes das verificações de usuário (inexistente/AD abortam antes).

## Saídas e códigos de saída

| Situação | Saída (stdout/stderr no padrão atual da CLI) | Exit |
|---|---|---|
| Sucesso | `Sucesso: senha redefinida para o usuário '<username>'. Sessões ativas foram invalidadas.` | 0 |
| Usuário inexistente | `Erro: usuário '<username>' não encontrado.` | 1 |
| Usuário AD | `Erro: '<username>' autentica pelo Active Directory. Este comando redefine apenas a senha local do SisPatrimônio e não altera credenciais do AD.` | 1 |
| Política de senha (nova senha < 8 caracteres) | `Erro: A nova senha deve ter no mínimo 8 caracteres.` (mensagem atual do serviço de autenticação) | 1 |
| Confirmação divergente | `Erro: as senhas não conferem.` | 1 |
| Entrada vazia / EOF / interrupção no prompt | `Erro: entrada de senha indisponível. Operação abortada.` | 1 |
| Falha de banco / erro inesperado na gravação | `Erro: falha ao atualizar a senha. Tente novamente.` (sem detalhes internos) | 1 |

Nota: em caso de erro, o estado do usuário alvo permanece inalterado (a gravação do
serviço é atômica) e é gerado 1 registro de auditoria de falha.

## Efeitos colaterais (por execução)

- **Sucesso**: hash da senha substituído (mecanismo existente); `failed_login_attempts` e
  `locked_until` zerados; **todas** as `user_sessions` do alvo excluídas; 1 registro
  `RESET_SENHA`/`SUCCESS` em `audit_logs` com ator nulo + username do alvo + origem CLI
  (decisão D-2). `is_active`, perfis, permissões e demais atributos **intactos** (D-3).
- **Qualquer falha**: nenhum dado do usuário alterado; 1 registro `RESET_SENHA`/`FAILURE`
  em `audit_logs` com motivo curto não sensível.

## Regras de não-regressão do contrato CLI

1. Nenhum subcomando existente (`stats`, `list`, `show`, `move`, `create-user`) muda de
   comportamento, nome ou opções.
2. O comando NUNCA registra a senha (ou parte) em auditoria, logs ou saídas.
3. O comando NUNCA altera usuário com `auth_provider='ad'` nem qualquer credencial AD.
4. Toda execução gera exatamente 1 registro de auditoria.
5. A política de senha e o hash permanecem os existentes (nenhuma segunda implementação).
