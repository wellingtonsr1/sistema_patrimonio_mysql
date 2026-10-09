# Technical Research & Decisions: Operador Responsável Vinculado ao Usuário Autenticado

**Feature**: `065-operador-responsavel-autenticado`  
**Date**: 2026-10-09  
**Status**: Completed  

---

## Topic 1: Extração da Identidade do Usuário Autenticado no Servidor

### Context
O sistema utiliza FastAPI com middlewares/dependências de autenticação (`require_permission` e `require_web_auth` em `app/api/deps.py`). Quando uma requisição é autenticada, o objeto `User` é anexado ao estado do request em `request.state.user`.

### Decision
Utilizar a expressão `(user.full_name or user.username)` obtida a partir de `request.state.user` nos endpoints `POST /movements/new` (web) e `POST /api/v1/movements` (API REST). Caso o nome ultrapasse 100 caracteres, truncar com `[:100]`.

### Rationale
- O atributo `request.state.user` é populado com segurança pelo middleware de autenticação validando o cookie de sessão ou token.
- A regra `(user.full_name or user.username)` é o padrão unificado em todo o SisPatrimônio Pro (ex: `app/web/routers/assets.py` L343), garantindo suporte transparente a usuários cadastrados na base local e usuários sincronizados via Active Directory / LDAP.
- Impor a identidade no servidor garante proteção total contra falsificação de dados (anti-spoofing), pois o valor enviado pelo formulário HTML/API é ignorado.

### Alternatives Considered
1. **Confiar no valor do formulário enviado pelo cliente:**  
   *Rejeitado.* Permite que qualquer usuário manipule o HTML ou requisição HTTP e registre movimentações em nome de terceiros, violando a integridade da auditoria.
2. **Consultar o banco de dados novamente na rota:**  
   *Rejeitado.* Desnecessário e ineficiente, pois `request.state.user` já possui o modelo `User` carregado pela dependência de permissão.

---

## Topic 2: Apresentação e UX do Campo no Form de Movimentação

### Context
No formulário `/movements/new`, o campo `Operator Responsável` vinha preenchido com o texto genérico `"Operador do Patrimônio"`.

### Decision
Conforme alinhado na clarificação (Opção A), alterar o template `app/web/templates/movements/new.html` para:
- Preencher o atributo `value` com `{{ current_user.full_name or current_user.username if current_user else 'Operador do Patrimônio' }}`.
- Adicionar o atributo `readonly` para impedir edições.
- Adicionar a classe CSS e texto auxiliar `(Preenchido automaticamente)`.

### Rationale
- O context processor `_inject_current_user` em `app/web/routers/templates_env.py` disponibiliza a variável `current_user` para todos os templates Jinja2.
- O campo `readonly` com estilo padrão de formulário do Bootstrap mantém a coerência visual do sistema e sinaliza claramente ao operador que a sua identidade foi atribuída.

---

## Topic 3: Compatibilidade com o Modelo e Banco de Dados

### Context
A tabela `movements` no banco de dados armazena a coluna `operator_name` como `VARCHAR(100) NOT NULL`.

### Decision
Reutilizar a coluna `operator_name` existente sem realizar qualquer alteração estrutural no banco de dados. Aplicar truncamento defensivo `[:100]` no servidor Python antes de salvar.

### Rationale
- Nenhuma alteração no esquema é necessária.
- Truncar em 100 caracteres garante tolerância a nomes extremamente longos provenientes do AD sem gerar exceções de estouro de coluna no MariaDB/MySQL.
