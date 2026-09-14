Crie a Constitution oficial do projeto SisPatrimônio Pro.

IMPORTANTE: este é um sistema EXISTENTE e em produção/desenvolvimento contínuo. A Constitution deve preservar e formalizar os princípios que já são verdadeiros no projeto, e não inventar uma nova arquitetura ou impor padrões incompatíveis com o código existente.

Antes de gerar a Constitution:

1. Analise o repositório atual de forma ampla e somente para leitura.
2. Leia o README.
3. Analise a arquitetura atual, incluindo:
   - organização das camadas;
   - routes/endpoints;
   - services;
   - models;
   - autenticação;
   - autorização/RBAC;
   - integração AD/LDAP;
   - auditoria;
   - movimentações patrimoniais;
   - inventário;
   - banco de dados;
   - testes;
   - documentação.
4. Considere também o relatório de auditoria técnica existente no projeto, caso esteja disponível.
5. Identifique quais princípios realmente representam o estado atual do sistema e quais devem ser tratados como regras permanentes para futuras alterações.

A Constitution deve estabelecer, no mínimo, os seguintes princípios:

- preservação do sistema existente;
- evolução incremental em vez de reescrita;
- escopo estritamente controlado;
- nenhuma alteração não relacionada à tarefa;
- preservação da arquitetura existente;
- fluxo arquitetural preferencial Web/API → Services → Models/Persistência;
- regras de negócio concentradas nos Services;
- preservação das regras patrimoniais;
- movimentações como mecanismo de alteração de estado, localização e custódia quando aplicável;
- integridade e rastreabilidade patrimonial;
- integridade do inventário;
- segurança por padrão;
- preservação da autenticação existente;
- preservação do RBAC deny-by-default;
- preservação das regras de integração com Active Directory;
- nunca registrar senhas, tokens ou credenciais;
- MariaDB como banco de produção;
- proteção dos dados existentes;
- alterações estruturais de banco realizadas de forma controlada;
- testes como requisito de não regressão;
- preservação dos testes existentes;
- auditoria das operações relevantes;
- consistência visual e funcional da interface;
- documentação compatível com o comportamento real do sistema;
- desenvolvimento orientado por especificações para mudanças relevantes;
- validação antes de considerar uma alteração concluída.

REGRAS IMPORTANTES PARA A CONSTITUTION:

1. NÃO transforme o backlog da auditoria em Constitution.
2. NÃO inclua BUGs, FEATs ou tarefas específicas como regras constitucionais.
3. NÃO transforme problemas encontrados na auditoria em obrigações permanentes, a menos que sejam realmente princípios do projeto.
4. NÃO invente tecnologias, padrões ou processos que o projeto não utiliza.
5. NÃO proponha refatoração do sistema durante esta etapa.
6. NÃO altere código da aplicação.
7. NÃO altere banco de dados.
8. NÃO altere configurações da aplicação.
9. NÃO implemente nenhuma funcionalidade.
10. NÃO corrija problemas encontrados durante a análise.
11. A tarefa é exclusivamente criar a Constitution.

A Constitution deve deixar explícito o seguinte princípio:

"Nenhuma implementação deve alterar comportamento existente considerado correto sem que a mudança esteja explicitamente prevista na especificação aprovada."

Também estabeleça como regra permanente que uma tarefa específica não pode ser usada como justificativa para realizar refatorações, correções ou melhorias não relacionadas ao seu escopo.

IMPORTANTE SOBRE O ESTADO ATUAL:

O sistema já possui arquitetura em camadas. A Constitution deve PRESERVAR essa arquitetura, não criá-la.

O banco de produção atualmente é MariaDB. Não trate SQLite como banco de produção.

Os testes existentes devem ser considerados uma base de regressão e não devem ser removidos ou enfraquecidos apenas para fazer uma implementação passar.

A Constitution deve ser objetiva, normativa e adequada para orientar futuras execuções do Spec Kit e agentes de IA.

Depois da análise, crie ou atualize:

.specify/memory/constitution.md

Ao finalizar:

1. Mostre um resumo dos princípios criados.
2. Informe a versão da Constitution.
3. Liste qualquer ponto que não pôde ser confirmado no código/documentação e que, portanto, não foi transformado em regra.
4. Confirme que nenhum arquivo da aplicação, banco de dados ou configuração foi alterado.
5. Não execute nenhuma outra etapa do Spec Kit, como specify, plan, tasks ou implement.