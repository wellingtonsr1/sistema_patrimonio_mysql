<!--
=== SYNC IMPACT REPORT ===
Version change: (none) → 1.0.0
Rationale: Initial adoption (MINOR/MAJOR bump rules apply only to amendments).
Modified principles: (none — first version)
Added sections:
  - Core Principles I–XII (12 principles)
  - Section 2: Restrições de Tecnologia e Dados
  - Section 3: Fluxo de Desenvolvimento e Controle de Escopo
  - Governance
Removed sections: (none)
Deferred items / TODOs: (none — all placeholders resolved)
Source basis: README.md, docs/ARQUITETURA_E_MANUTENCAO.md,
  docs/INVENTARIO_TECNICO.md, app/config.py, app/api/deps.py,
  app/services/* (movement, inventario, audit, ad_service, permission),
  tests/* (suite pytest). Principles formalize verified behavior;
  backlog items (docs/Melhorias_SisPatrimonio_Pro.md) intentionally
  NOT converted into constitutional rules.
Note: remove this report comment before committing.
=== END SYNC IMPACT REPORT ===
-->

# SisPatrimônio Pro Constitution

Constitution do sistema SisPatrimônio Pro — Gestão Patrimonial (FastAPI + SQLAlchemy +
Jinja2/Bootstrap), sistema **existente**, em desenvolvimento contínuo e com dados reais.
Este documento **preserva e formaliza princípios já verdadeiros no projeto**; ele não cria
nova arquitetura nem impõe padrões incompatíveis com o código atual. Aplica-se a toda
alteração feita por pessoas, agentes de IA e execuções do Spec Kit.

## Core Principles

### I. Preservação do Sistema Existente e Evolução Incremental

O sistema em produção é o ativo a proteger. Toda alteração DEVE ser incremental sobre o
código existente. É PROIBIDO reescrever módulos, trocar frameworks/bibliotecas de base ou
remover funcionalidades existentes como parte de uma tarefa que não prevê explicitamente
essa remoção. Evolução ocorre por extensão (novos endpoints, novos services, novas
colunas/tabelas), nunca por substituição implícita do que já existe e funciona.

**Regra permanente de escopo:** uma tarefa específica NÃO pode ser usada como justificativa
para realizar refatorações, correções, melhorias, renomeações ou limpezas não relacionadas
ao seu escopo. Nenhuma alteração não relacionada à tarefa é permitida, mesmo que o agente
identifique problemas no caminho — problemas encontrados são registrados (relatório,
especificação ou backlog) e tratados em tarefa própria.

**Princípio de compatibilidade de comportamento:** nenhuma implementação deve alterar
comportamento existente considerado correto sem que a mudança esteja explicitamente
prevista na especificação aprovada.

### II. Arquitetura em Camadas (Web/API → Services → Models)

A arquitetura existente DEVE ser preservada: **Interface Web (Jinja2) e API REST
(`/api/v1`) → Services (regras de negócio, `app/services/`) → Models (SQLAlchemy,
`app/models/`) → Banco de dados**. Rotas (web e API) não concentram regras de negócio:
elas autenticam/autorizam, validam entrada via schemas Pydantic e delegam aos services.
Novas funcionalidades seguem o mesmo fluxo; código de negócio não pode ser colocado em
rotas, templates ou scripts quando um service é o local estabelecido.

### III. Regras de Negócio nos Services

Toda regra de negócio (validações patrimoniais, cálculos, transições de estado, regras de
importação, integração AD, permissões) DEVE ficar concentrada nos services
(`app/services/`). As rotas chamam services; services falam com os models. Regras
duplicadas em rota e service são proibidas — quando existir regra em service, a rota a
consome; novos endpoints de negócio não reimplementam regras já existentes nos services.

### IV. Integridade Patrimonial e Movimentações

As regras patrimoniais existentes são imutáveis por padrão. Alterações de **estado,
localização e custódia** de um bem ocorrem, quando aplicável, pelo **mecanismo de
movimentações** (`MovementService.create_movement`), que gera histórico com origem →
destino, motivo e operador (tipos: `ENTRADA_AQUISICAO`, `ALOCACAO_CAUTELA`,
`TRANSFERENCIA_LOCAL`, `ENVIO_MANUTENCAO`, `RETORNO_MANUTENCAO`, `DEVOLUCAO_ESTOQUE`,
`BAIXA_DESCARTE`, `ATUALIZACAO_ESTADO`). É PROIBIDO alterar localização, custodiante ou
estado de um bem por caminho que contorne o motor de movimentações. A trilha histórica
(audit trail) é imutável e apensável — nunca editável ou apagável. Identificadores de
negócio permanecem únicos (`tag` do bem; `serial_number` único quando aplicável).

### V. Integridade do Inventário

O inventário patrimonial é instrumento de conferência, não de cadastro: **o inventário
nunca altera o cadastro** (bens, movimentações, locais, colaboradores). Divergências
(`LOCAL_DIFERENTE`, `NAO_ENCONTRADO`, `SEM_IDENTIFICACAO`) são apenas registradas para
tratamento pelos fluxos próprios (movimentações, manutenção). A lista de bens esperados é
um **snapshot gerado na criação** do inventário, imune a edições posteriores do cadastro.
O encerramento exige todos os bens esperados conferidos e trava os itens; a ata
comprobatória é exportável. Regras de status do item e validações de conferência
existentes não podem ser relaxadas.

### VI. Segurança por Padrão (Autenticação, RBAC e AD)

**Autenticação** existente é preservada: híbrida local (PBKDF2-HMAC-SHA256, salt por
usuário) + Active Directory/LDAP (`auth_provider.py`), com sessão server-side (token
aleatório, banco guarda apenas o hash SHA-256, cookie HttpOnly/SameSite=Lax, expiração e
revogação no servidor). **Autorização** é RBAC interno **deny by default**: usuário só
executa uma operação se possuir explicitamente a permissão `modulo.acao`; nenhuma
permissão é concedida por padrão. A validação é sempre no backend — a interface (menu,
botões via `can()`) é apenas apresentação. O AD **autentica, mas não autoriza**: acesso só
é concedido a grupos AD explicitamente mapeados para perfis existentes; permissões nunca
vêm do AD; usuários sem mapeamento não são criados no sistema. Toda nova rota web e de API
DEVE exigir autenticação e a permissão correspondente, seguindo o padrão existente
(`require_api_auth`, `require_web_auth`, `require_permission`).

**Credenciais:** é PROIBIDO registrar senhas, tokens, hashes de sessão, credenciais de
serviço (`AD_BIND_PASSWORD`) ou qualquer segredo em logs, auditoria, respostas de API,
templates ou arquivos versionados. Eventos de auditoria de autenticação e AD jamais
incluem credenciais.

### VII. Banco de Dados: MariaDB e Proteção dos Dados

MariaDB/MySQL (via SQLAlchemy, driver PyMySQL) é o banco de produção; a conexão é
fornecida por `DATABASE_URL` (`mariadb+pymysql://...`), sem fallback para SQLite na
aplicação. SQLite é restrito à suíte de testes (`sqlite:///:memory:` ou
`DATABASE_URL_TEST`). Dados existentes são intocáveis: alterações estruturais (novas
tabelas, novas colunas, índices) são realizadas de forma controlada, aditivas e
idempotentes, seguindo o mecanismo existente (`init_db` + `_ensure_schema_migrations` com
`ALTER TABLE` condicional). É PROIBIDO, em tarefa de funcionalidade: remover ou renomear
colunas/tabelas existentes, alterar tipos de dados em produção, executar `drop_all` contra
banco com dados (o `drop_all` é exclusivo do `seed_demo.py` em banco de demo) ou exigir
migração destrutiva sem especificação aprovada que a preveja explicitamente.

### VIII. Testes como Requisito de Não Regressão

A suíte pytest existente é a base de regressão do sistema. Toda alteração de código DEVE
manter a suíte verde (exceto testes diretamente ligados ao comportamento sendo
especificamente alterado na especificação aprovada). É PROIBIDO remover, desabilitar,
pular ou enfraquecer testes existentes apenas para fazer uma implementação passar.
Funcionalidades novas ou alteradas DEBEM vir acompanhadas de testes que as cubram,
seguindo os padrões existentes (`tests/test_rbac.py`, `test_auth.py`, `test_ad.py`,
`test_inventario.py`, `test_movements.py`, `test_assets.py`, entre outros).

### IX. Auditoria das Operações Relevantes

Operações relevantes continuam auditadas pela trilha `audit_logs` (somente-leitura, sem
rota de escrita/exclusão): autenticação (login, falha, bloqueio, logout), criação,
alteração, bloqueio/desbloqueio, troca/reset de senha, movimentações, importações CSV e
acessos negados (403). Alterações relevantes novas DEBEM registrar evento via
`audit_service` (`write_audit` / `write_change_audit`) com dados before/after quando
aplicável — sempre sem credenciais (Princípio VI). A imutabilidade da trilha é permanente.

### X. Interface Consistente e Funcional

A interface web (Jinja2 + Bootstrap 5 + tema claro/escuro, padrões visuais e de
navegação existentes) DEVE manter consistência visual e funcional: novas telas seguem os
templates, componentes e convenções existentes (menu conforme permissões, 403/404
amigáveis, tooltips, central de ajuda `/ajuda`). Nenhuma alteração de UI pode quebrar
fluxos existentes (login, movimentação, inventário, administração) ou remover acessos sem
previsão na especificação.

### XI. Documentação Fiel ao Comportamento Real

README.md, docs/ e central de ajuda embutida DEVEM permanecer compatíveis com o
comportamento real do sistema. Alterações que mudem comportamento visível (endpoints,
permissões, variáveis de ambiente, fluxos de tela, banco) DEVEM atualizar a documentação
correspondente na mesma tarefa. Documentação não inventa comportamento: afirmações não
verificáveis no código são marcadas como tal, no estilo dos docs existentes
(`ARQUITETURA_E_MANUTENCAO.md`, `INVENTARIO_TECNICO.md`).

### XII. Desenvolvimento Orientado por Especificações e Validação

Mudanças relevantes (novas funcionalidades, mudanças de comportamento, alterações de
banco, de permissões ou de integrações) são orientadas por especificação antes da
implementação (fluxo Spec Kit: specify → plan → tasks → implement). Nenhuma tarefa é
considerada concluída sem validação: suíte de testes executada, comportamento existente
preservado (Princípio I), escopo respeitado e, quando aplicável, documentação atualizada.
A validação é parte da definição de pronto.

## Restrições de Tecnologia e Dados

O stack abaixo é o stack do projeto e não pode ser substituído sem emenda desta
Constitution:

| Camada | Tecnologia estabelecida |
|---|---|
| Linguagem | Python 3.10+ |
| Framework web | FastAPI + Uvicorn |
| ORM | SQLAlchemy 2 |
| Banco de produção | MariaDB/MySQL (PyMySQL) — SQLite apenas em testes |
| Validação | Pydantic v2 |
| Templates/UI | Jinja2 + Bootstrap 5 (+ Chart.js, QRCode.js) |
| Diretório | LDAP/LDAPS via `ldap3` (Microsoft AD / Samba AD DC) |
| Exportações | OpenPyXL (.xlsx), ReportLab (PDF), CSV UTF-8 BOM |
| Testes | pytest (+ TestClient do FastAPI) |

Regras permanentes complementares:

- Configuração por variáveis de ambiente via `app/config.py` (`AUTH_*`, `AD_*`,
  `DATABASE_URL`); segredos nunca em código ou repositório.
- O backlog de auditoria/melhorias (ex.: `docs/Melhorias_SisPatrimonio_Pro.md`) e a lista
  de BUGs/FEATs conhecidos NÃO constituem obrigações desta Constitution; são entradas
  candidatas a especificações futuras.
- Modelos `enums.py` (status/condição/categoria/tipos) são vocabulário controlado do
  domínio; novos valores são aditivos e previstos em especificação.

## Fluxo de Desenvolvimento e Controle de Escopo

1. **Mudança relevante** → especificação aprovada antes de implementar (Spec Kit).
2. **Implementação** → estritamente dentro do escopo da especificação; segue as camadas
   (Princípio II/III); nada de alterações não relacionadas (Princípio I).
3. **Segurança** → toda rota nova protegida (Princípio VI); auditoria nas operações
   relevantes (Princípio IX).
4. **Banco** → apenas alterações aditivas controladas (Princípio VII).
5. **Testes** → suíte verde; novos testes para o novo comportamento (Princípio VIII).
6. **Documentação** → atualizada junto à mudança (Princípio XI).
7. **Validação final** → princípio XII antes de declarar conclusão.

Checklist de conformidade obrigatório em revisões (humanas ou por agente):

- [ ] Escopo: nenhuma alteração fora da tarefa/especificação?
- [ ] Comportamento existente preservado, exceto o previsto na especificação?
- [ ] Regras de negócio nos services; rotas delegam?
- [ ] Estado/localização/custódia alterados via movimentações, quando aplicável?
- [ ] Rotas novas com autenticação + permissão RBAC?
- [ ] Nenhuma credencial em logs/auditoria/código?
- [ ] Banco: apenas alterações aditivas idempotentes, dados preservados?
- [ ] Testes existentes intactos e passando; cobertura nova adicionada?
- [ ] Documentação atualizada e fiel ao comportamento?

## Governance

- Esta Constitution prevalece sobre qualquer prática, instrução de tarefa ou prompt que a
  contrarie. Em conflito, a Constitution vence e o conflito deve ser reportado ao
  responsável pelo projeto.
- **Emendas:** exigem documentação da mudança, justificativa, aprovação do responsável e
  atualização do versionamento. Versionamento semântico: MAJOR para remoção/incompatibilidade
  de princípios; MINOR para novo princípio ou expansão material; PATCH para esclarecimentos.
- **Revisão de conformidade:** toda revisão de PR/entrega de agente verifica o checklist
  da seção anterior. Violações bloqueiam a entrega.
- **Agentes de IA e execuções do Spec Kit** DEVEM ler esta Constitution antes de
  implementar; instruções que conflitem com ela devem ser sinalizadas, não obedecidas
  silenciosamente.

**Version**: 1.0.0 | **Ratified**: 2026-09-14 | **Last Amended**: 2026-09-14
