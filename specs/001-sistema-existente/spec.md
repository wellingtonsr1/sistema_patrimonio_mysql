# Feature Specification: SisPatrimônio Pro — Especificação Funcional do Sistema Existente

**Feature Branch**: `001-sistema-existente`

**Created**: 2026-09-14

**Status**: Draft

**Input**: User description: "Analise o SisPatrimônio Pro como um sistema EXISTENTE que já está em produção/desenvolvimento e possui funcionalidades implementadas. Não trate esta solicitação como a criação de um sistema novo. O objetivo desta especificação é estabelecer uma descrição funcional fiel do sistema existente e servir como base para sua evolução controlada através do Spec Kit. [...] A especificação deve considerar que qualquer evolução futura deve preservar o funcionamento existente e alterar somente o que estiver diretamente relacionado à necessidade especificada."

> **NATUREZA DESTE DOCUMENTO**: Esta especificação descreve um sistema **em operação**.
> Ela documenta o que o sistema **atualmente faz** (funcionalidades confirmadas no código
> — ver `SPEC-KIT-SISTEMA-ATUAL.md` na raiz do projeto para o inventário técnico completo),
> por que cada funcionalidade existe, e quais comportamentos **devem ser preservados** em
> qualquer evolução. Não descreve um sistema novo a ser construído. Recomendações de
> futuro estão isoladas na seção "Pontos que precisam de esclarecimento" e não são
> requisitos desta especificação.

---

## 1. Contexto do Sistema Existente

O SisPatrimônio Pro é um sistema web de **gestão patrimonial** (controle de ativo fixo e
equipamentos) em produção/desenvolvimento contínuo, construído sobre uma arquitetura em
camadas (interface web e API REST sobre serviços de regras de negócio, que acessam o banco
de dados MariaDB). Sua razão de existir é o **rastreamento auditável do fluxo de
movimentação de cada bem**: quem está com o equipamento, onde ele está, qual seu estado de
conservação, e todo o histórico de transferências, manutenções e baixas — com trilha de
auditoria imutável e termo de responsabilidade formal.

Módulos efetivamente implementados e confirmados no código (17):

| Módulo | Finalidade (por que existe) |
|---|---|
| Autenticação e sessões | Garantir que só usuários legítimos acessem dados patrimoniais sensíveis (CPF, valores, números de série) |
| RBAC (perfis e permissões) | Controlar o que cada usuário pode fazer, com negação por padrão (deny by default) |
| Integração Active Directory | Autenticar usuários do domínio corporativo sem abrir mão do controle interno de permissões |
| Auditoria | Prover rastreabilidade comprobatória de todas as operações relevantes, incluindo acessos negados |
| Patrimônio (bens) | Cadastrar e consultar cada equipamento com tombamento único, dados fiscais e depreciação |
| Movimentações | Registrar de forma imutável toda mudança de custódia, localização e estado do bem |
| Termos | Formalizar a entrega de bens a colaboradores com documento imprimível e QR de validação |
| Manutenções | Controlar ordens de serviço e integrá-las automaticamente ao fluxo do bem |
| Colaboradores (custodiantes) | Identificar os responsáveis pela custódia dos bens |
| Locais | Modelar a estrutura física (filial, prédio, andar, sala, departamento) |
| Inventário | Realizar conferência física comprobatória do acervo sem jamais alterar o cadastro |
| Dashboard | Dar visibilidade executiva do acervo (KPIs e gráficos) |
| Relatórios e exportações | Produzir comprovação documental em CSV, Excel e PDF |
| Importações CSV | Permitir carga em massa de bens, colaboradores e locais com pré-visualização |
| Central de ajuda | Reduzir suporte com manual embutido e pesquisa |
| CLI administrativa | Operar tarefas de administração pelo terminal (criar usuários, mover bens, consultar) |
| Interface web | Apresentar todos os módulos com menu dinâmico conforme permissões |

## 2. Problema / Necessidade

O sistema existe e opera, mas **não havia uma especificação funcional formal** que
capture seu comportamento como referência única. Sem ela:

- Evoluções futuras correm risco de alterar inadvertidamente comportamentos corretos
  (regras patrimoniais, RBAC, integridade do inventário, trilha de auditoria).
- Agentes de IA e execuções do Spec Kit não dispõem de uma base fiel para planejar
  mudanças sem reinventar ou presumir funcionalidades.
- Conhecimento sobre limitações e comportamentos incompletos fica disperso.

**Necessidade**: fixar por escrito o que o sistema faz hoje e o que deve ser preservado,
de modo que qualquer evolução seja incremental, controlada e limitada ao escopo da
necessidade que a motivar.

## 3. Objetivos

1. **Descrever fielmente** as capacidades funcionais existentes, sem inventar
  funcionalidades e marcando explicitamente o que não pôde ser confirmado no código.
2. **Preservar comportamentos**: estabelecer a lista explícita de comportamentos que
  qualquer evolução deve manter (seção 10).
3. **Habilitar evolução controlada**: servir de baseline para as próximas etapas do
  Spec Kit (clarify → plan → tasks → implement), com mudanças estritamente incrementais.
4. **Proteger a integridade patrimonial**: assegurar que rastreabilidade, auditoria e
  regras de negócio consolidadas não sejam regressão de novas funcionalidades.

## 4. Usuários Envolvidos

Perfis existentes no sistema (RBAC, 7 perfis padrão + superusuário), com o que
efetivamente podem fazer (verificado no catálogo de permissões):

| Usuário | Papel no sistema | Capacidades principais |
|---|---|---|
| **Administrador** | Administração total do sistema | Todas as permissões: usuários, perfis, permissões, auditoria, AD e todos os módulos |
| **Gestor de TI** | Gestão do parque de TI | Cadastra/edita bens, movimenta, gerencia manutenções, gera relatórios; sem acesso a administração do sistema |
| **Técnico de TI** | Execução técnica | Consulta bens, registra manutenções/diagnósticos; não exclui nem administra |
| **Patrimônio** | Equipe patrimonial | Cadastra/edita/movimenta bens, executa inventários completos (criar/conferir/encerrar), emite termos |
| **Almoxarifado** | Controle de estoque | Movimenta bens (entradas/saídas), consulta acervo |
| **Auditor** | Conformidade | Somente leitura de todos os módulos **+ acesso à trilha de auditoria** |
| **Consulta** | Acesso mínimo | Somente leitura dos módulos explicitamente autorizados (sem exportar, sem auditoria) |
| **Superusuário** (`is_admin`) | Contingência | Bypass total das permissões (flag legado; uso desencorajado na documentação) |
| *(fora do sistema)* | Domínio AD | Usuários do AD autenticam pelo diretório, mas recebem acesso **apenas** via grupo mapeado a um perfil existente |

## 5. Principais Capacidades Funcionais

Funcionalidades confirmadas no código, agrupadas por área:

**Acesso e segurança**
- Login híbrido: contas locais (senha com hash PBKDF2, salt por usuário) e contas do
  diretório AD/LDAP, com provisionamento automático no primeiro login autorizado.
- Sessão server-side com expiração e revogação no logout; proteção contra força bruta
  (bloqueio temporário por conta após tentativas falhas consecutivas).
- Troca de senha própria (exigindo a senha atual) e reset administrativo; ambos
  invalidam sessões existentes.
- RBAC deny-by-default com 29 permissões no padrão `modulo.acao` e 7 perfis padrão
  não-excluíveis; toda rota valida permissão no servidor (a interface é apenas
  apresentação).
- Auditoria somente-leitura de eventos de segurança, operações e acessos negados,
  incluindo dados anteriores/posteriores das alterações.

**Patrimônio**
- Cadastro de bens com tombamento único, número de série único quando informado, dados
  fiscais (nota, fornecedor, garantia, valor) e estado de conservação.
- Busca multifacetada (texto livre em múltiplos campos, status, categoria, local,
  custodiante, departamento, período de compra, situação de manutenção).
- Depreciação linear contábil automática (20% ao ano sobre o valor de aquisição).
- Etiquetas com QR Code em lote apontando para a ficha de cada bem.
- Importação em massa via CSV com pré-visualização e confirmação.

**Movimentação e custódia**
- Motor de movimentações com 8 tipos (aquisição, alocação/cautela, transferência de
  local, envio/retorno de manutenção, devolução ao estoque, baixa, atualização de
  estado), gravando origem → destino, motivo e operador.
- Regra central: alterações de estado, localização e custódia do bem ocorrem **pelo
  fluxo de movimentações**, que mantém o histórico imutável (audit trail).
- Termo de responsabilidade/cautela sequencial (`TR-AAAA-NNNN`) gerado automaticamente
  nas alocações e devoluções, imprimível com QR de validação.
- Bloqueio de movimentação de bens já baixados.

**Manutenção**
- Ordens de serviço (preventiva, corretiva, upgrade) com custos e prestador, integradas
  ao fluxo: abrir OS envia o bem para manutenção; finalizar retorna o bem ao acervo.

**Inventário**
- Inventários com código sequencial (`INV-AAAA-NNNN`) e escopo opcional por local e/ou
  setor; lista de bens esperados gerada como **snapshot** no momento da criação.
- Conferência em campo por bem (via busca do tombamento ou QR da ficha), com resultados
  `ENCONTRADO`, `LOCAL_DIFERENTE`, `NAO_ENCONTRADO`, `SEM_IDENTIFICACAO`; registro de
  bens **não previstos** encontrados em campo.
- Regra de ouro: o inventário **nunca altera o cadastro** — divergências são apenas
  registradas para tratamento pelos fluxos próprios.
- Encerramento exige todos os bens esperados conferidos e trava os itens; ata
  comprobatória exportável em CSV, Excel e PDF.

**Gestão administrativa e apoio**
- Administração de usuários (criar, editar, bloquear, resetar senha) com proteções
  (não bloquear a si mesmo; último administrador ativo não removível).
- Administração de perfis e permissões; tela de integração AD com teste de conexão e
  mapeamento Grupo AD → Perfil com prioridade.
- Dashboard com KPIs e gráficos; relatórios com exportações CSV/Excel/PDF.
- Central de ajuda integrada com pesquisa, artigos por módulo, FAQ e tooltips.

## 6. Fluxos de Negócio

Fluxos reais implementados (reconstruídos do código):

**F1. Autenticação**
```text
Usuário → tela de login → credenciais → provedor local ou AD
  → falha: contador de tentativas → bloqueio temporário após limite
  → sucesso: sessão criada no servidor → cookie seguro → trilha de auditoria
```

**F2. Alocação de bem a colaborador (cautela)**
```text
Usuário com permissão de movimentar → formulário de movimentação
  → valida: bem existe, não está baixado, custodiante de destino obrigatório
  → atualiza custódia/localização do bem → status "em uso"
  → grava movimentação imutável com snapshots origem → destino
  → gera termo TR-AAAA-NNNN → registra auditoria → disponível para impressão
```

**F3. Transferência de local**
```text
Usuário com permissão de movimentar → tipo transferência → local de destino obrigatório
  → localização do bem atualizada → movimentação gravada com snapshots → auditoria
```

**F4. Manutenção**
```text
Abrir OS → bem vai para "em manutenção" + movimentação de envio automática
  → diagnóstico/peças/custos durante a execução
  → finalizar OS → movimentação de retorno automática → bem disponível novamente
```

**F5. Inventário patrimonial (ciclo completo)**
```text
Criar inventário (escopo opcional local/setor) → snapshot dos bens esperados
  → conferência em campo: buscar bem por tombamento/QR → registrar resultado
      (encontrado · local diferente · não encontrado · sem identificação)
  → bens não previstos encontrados: registrados como ocorrência (cadastro intocado)
  → encerramento: exige zero pendentes → itens travados
  → ata comprobatória em CSV/Excel/PDF
```

**F6. Devolução ao estoque e baixa**
```text
Devolução: custódia limpa → bem disponível → termo gerado → "Almoxarifado/Estoque"
Baixa: bem marcado como baixado (condição inservível por padrão) → custódia limpa
  → bem não pode mais ser movimentado → excluído de futuros inventários → auditoria
```

**F7. Importação em massa**
```text
Upload CSV → pré-visualização com validações e detecção de duplicatas
  → confirmação → criação em lote → auditoria da importação
```

**F8. Primeiro acesso / provisionamento**
```text
Instalação nova: tela de primeiro acesso OU variável de ambiente OU CLI
  → criação do administrador → perfis padrão semeados automaticamente
AD: primeiro login autorizado → provisionamento do usuário + vínculo ao colaborador existente
```

## 7. Regras de Negócio (implementadas)

Regras confirmadas no código — **comportamento existente a preservar**:

**Patrimoniais**
1. Tombamento (`tag`) é único e obrigatório; número de série é único quando informado.
2. Toda alteração de estado, localização e custódia de bem ocorre por movimentação
   com motivo (justificativa) obrigatória e operador identificado.
3. Cada movimentação grava snapshots textuais de origem e destino (imunes a edições
   posteriores do cadastro).
4. Bem baixado não pode ser movimentado; baixa define condição inservível por padrão.
5. Bem baixado é excluído da geração de listas de inventário.
6. Depreciação linear de 20% ao ano sobre o valor de aquisição.
7. Bem alocado fica "em uso"; devolvido fica "disponível"; enviado para manutenção fica
   "em manutenção"; retorno restaura disponibilidade (ou "em uso" se re-alocado).

**Inventário**
8. Inventário nunca altera bens, movimentações ou locais — divergência é só registro.
9. A lista de esperados é snapshot do momento da criação (local/custodiante do cadastro).
10. `LOCAL_DIFERENTE` exige informar local diverso do cadastrado.
11. Não previsto não aceita resultado de conferência padrão (sua ocorrência é o registro)
    e não duplica (bem único por inventário).
12. Encerramento exige todos os esperados conferidos; após encerrar, conferências novas
    são travadas.
13. Primeira conferência efetiva inicia formalmente o inventário (planejado → em andamento).

**Acesso e segurança**
14. Negação por padrão: operação só executa com permissão explícita do perfil; usuário
    sem perfil não executa nada (única exceção: superusuário legado).
15. Segurança sempre validada no backend; interface apenas esconde o que o usuário não
    pode fazer.
16. AD autentica, mas não autoriza: acesso só com grupo AD mapeado a perfil existente;
    sem mapeamento, o usuário não é criado no sistema (apenas auditado).
17. Perfis atribuídos pelo AD são resincronizados a cada login; atribuições manuais
    nunca são removidas pela sincronização.
18. Senhas: mínimo 8 caracteres; nunca armazenadas em texto puro; nunca logadas ou
    auditadas (nem as credenciais do diretório).
19. Bloqueio temporário por excesso de falhas de login (por conta, no servidor), com
    tempo de resposta equalizado para usuários inexistentes.
20. Troca/reset de senha invalida todas as sessões existentes do usuário.
21. Sessões expiram no servidor e são revogadas no logout.
22. Usuário não pode bloquear a si mesmo; último administrador ativo não pode ser
    removido ou desativado.
23. Redirecionamento pós-login aceita apenas caminhos internos (proteção contra
    open redirect).

**Auditoria e comprovação**
24. Operações relevantes (autenticação, criação/alteração, bloqueios, senhas, perfis,
    movimentações, manutenções, importações, inventários, acessos negados) geram
    registro de auditoria com usuário, data/hora, recurso, IP, resultado e
    dados anteriores/posteriores.
25. A trilha de auditoria é somente-leitura: não existe forma de editá-la ou apagá-la
    pela aplicação.
26. Termos têm numeração sequencial por ano; movimentações têm identificador único.
27. Inventários têm código sequencial por ano e snapshot textual dos filtros de escopo
    (comprovação de como a lista foi gerada).

## 8. Critérios de Sucesso

Critérios para validar esta especificação e sua função de baseline:

- **SC-001**: A especificação cobre os 17 módulos implementados, cada um com finalidade,
  capacidades e regras de negócio verificáveis no código.
- **SC-002**: Nenhuma funcionalidade inventada: toda afirmação de "o sistema faz" é
  verificável no código; dúvidas estão marcadas como não confirmadas (seção 11).
- **SC-003**: A lista de comportamentos a preservar (seção 10) cobre todas as 27 regras
  de negócio da seção 7.
- **SC-004**: Qualquer tarefa futura guiada por esta especificação pode ser verificada
  contra a suíte de regressão existente (154 testes) sem quebrar testes de
  comportamentos preservados.
- **SC-005**: Evoluções subsequentes alteram apenas arquivos diretamente relacionados à
  necessidade especificada, mantendo a suíte de testes verde e a trilha de auditoria
  íntegra.

## 9. Restrições

Restrições permanente (regras do jogo para qualquer evolução):

1. **Sistema existente**: não há reescrita; evolução é incremental sobre a arquitetura
   atual (interface/API → serviços → persistência).
2. **Escopo controlado**: nenhuma alteração não relacionada à necessidade especificada;
   uma tarefa não pode ser usada como pretexto para refatorações ou melhorias não
   relacionadas.
3. **Comportamento correto é intocável** fora da especificação aprovada da tarefa.
4. **Banco de produção é MariaDB**: alterações estruturais apenas de forma aditiva,
   controlada e idempotente, preservando dados existentes; SQLite é exclusivo da suíte
   de testes.
5. **Autenticação, autorização, RBAC, integração AD e auditoria** não são alteradas sem
   necessidade explícita e especificação aprovada.
6. **Testes são requisito**: funcionalidades novas/alteradas vêm com testes; a suíte
   existente não pode ser removida ou enfraquecida para forçar aprovação.
7. **Dados históricos e auditoria são preservados**: trilha imutável, movimentações
   apensáveis, snapshots não retroativos.
8. **Regras de negócio nos serviços**: novas funcionalidades seguem o padrão existente
   (camada de serviços concentra as regras; interface e API apenas orquestram).
9. **Stack atual mantida**: FastAPI/Python, SQLAlchemy/MariaDB, Jinja2/Bootstrap,
   pytest — nenhuma troca de tecnologia sem emenda da Constitution.
10. **Documentação acompanha**: mudanças de comportamento visível atualizam README/docs
    na mesma tarefa.

## 10. Comportamentos Existentes que Devem Ser Preservados

Lista explícita (extraída das regras da seção 7 e dos fluxos da seção 6). Qualquer
evolução DEVE manter estes comportamentos, salvo alteração explicitamente prevista na
especificação aprovada da tarefa:

| # | Comportamento preservado |
|---|---|
| P1 | Login híbrido local+AD com as regras de provedor por conta (`auth_provider`) — contas locais nunca migram para AD |
| P2 | Sessão server-side: hash do token no banco, expiração e revogação no logout |
| P3 | Lockout por conta com tempo equalizado para usuários inexistentes |
| P4 | RBAC deny-by-default com as 29 permissões do catálogo e perfis padrão semeados |
| P5 | Validação de permissão sempre no backend (401/403/423/503 nos códigos atuais) |
| P6 | Auditoria somente-leitura dos eventos listados, com before/after e acessos negados |
| P7 | Motor de movimentações: 8 tipos, snapshots de origem/destino, motivo obrigatória |
| P8 | Termo sequencial TR-AAAA-NNNN gerado automaticamente em alocação e devolução |
| P9 | Integração manutenção ↔ fluxo (envio/retorno automáticos de movimentação) |
| P10 | Inventário nunca altera o cadastro; snapshot de esperados imune a edições posteriores |
| P11 | Encerramento de inventário exige zero pendentes e trava os itens |
| P12 | Registro de bens não previstos como ocorrência (sem duplicar, sem tocar no cadastro) |
| P13 | Unicidade de tombamento e de número de série; código INV-AAAA-NNNN |
| P14 | Baixa: estado final, condição inservível padrão, bloqueio de movimentação posterior |
| P15 | Depreciação linear 20%/ano |
| P16 | Importações CSV sempre com pré-visualização e confirmação |
| P17 | Proteções administrativas: último admin, auto-bloqueio, perfis de sistema não-excluíveis |
| P18 | Perfis manuais (`local`) preservados na sincronização AD; provisionamento só com grupo mapeado |
| P19 | Nenhuma credencial (senha, token, hash) em logs, auditoria ou respostas |
| P20 | Primeiro acesso apenas em instalação nova (idempotente) |
| P21 | Menu/botões conforme permissões, com tema claro/escuro e ajuda integrada |
| P22 | Exportações CSV (UTF-8 BOM)/Excel/PDF existentes, incluindo ata de inventário |
| P23 | CLI administrativa (`stats`, `list`, `show`, `move`, `create-user`) |
| P24 | Erros de negócio com mensagens claras ao usuário e páginas 403/404 amigáveis |

## 11. Pontos que Precisam de Esclarecimento

Pontos identificados que **não** puderam ser confirmados no código e, portanto, **não são
requisitos desta especificação** — são candidatas a futuras especificações próprias:

1. **Fluxo de assinatura de termo**: o campo de assinatura existe no modelo (inicia não
   assinado), mas nenhum fluxo o altera — como o termo deve ser "assinado"? (presencial
   com controle externo? confirmação eletrônica?)
2. **Permissões reservadas sem funcionalidade**: `movimentacao.editar`,
   `movimentacao.cancelar` e `patrimonio.excluir` existem no catálogo, mas nenhuma rota
   as consome — devem permanecer reservadas, virar funcionalidade ou ser removidas?
3. **Edição/exclusão via interface**: edição de bem e de local existem confirmadas na
   API; não foi identificada página web dedicada — a interface deve expor essas
   operações? E exclusão de bens/colaboradores (não encontrada em nenhuma camada)?
4. **Teste defasado**: um teste de bloqueio por tentativas espera 5 tentativas, enquanto
   a configuração atual é 10 — qual o valor correto do produto? (correção é tarefa
   própria, fora do escopo desta especificação)
5. **Recoverias futuras citadas em docs**: busca global, filtros avançados adicionais e
   escopo por unidade/setor constam como sugestões em documentos de melhorias — não são
   requisitos; decidir se entram em roadmap.

## 12. Limites de Escopo

**Dentro do escopo desta especificação:**
- Descrição funcional fiel do sistema existente, seus fluxos, regras e comportamentos
  a preservar.
- Estabelecimento da baseline para evoluções futuras via Spec Kit.

**Fora do escopo (não serão tratados nesta especificação):**
- Qualquer implementação, correção de bugs, refatoração ou melhoria (incluindo os
  problemas listados na análise técnica).
- Detalhes de implementação técnica (estrutura de código, APIs internas, esquema do
  banco) — cobertos pelo documento técnico `SPEC-KIT-SISTEMA-ATUAL.md` na raiz.
- Novas funcionalidades: cada uma exigirá especificação própria.
- Mudanças de arquitetura, tecnologia, banco, autenticação, autorização ou integrações.

---

### User Scenarios & Testing *(mandatory — resumo dos journeys principais)*

### User Story 1 — Custódia rastreável do bem (Priority: P1)

Como equipe de patrimônio, aloco um equipamento a um colaborador e o sistema registra
quem recebeu, quando, com qual justificativa, gera o termo de responsabilidade e mantém
o histórico imutável — permitindo responder, a qualquer momento, "onde está este bem e
quem está com ele".

**Why this priority**: é a razão de existir do sistema (rastreamento auditável de
custódia); todos os demais módulos orbitam este fluxo.

**Independent Test**: pode ser validado alocando um bem disponível a um colaborador e
conferindo a movimentação registrada, o status do bem, o termo gerado e a auditoria.

**Acceptance Scenarios**:
1. **Given** um bem disponível e um colaborador cadastrado, **When** o usuário autorizado
   registra uma alocação com justificativa, **Then** o bem passa a "em uso" sob custódia
   do colaborador, o histórico registra origem→destino e um termo sequencial é gerado.
2. **Given** um bem já baixado, **When** alguém tenta movimentá-lo, **Then** o sistema
   recusa com mensagem clara e nada é alterado.

### User Story 2 — Inventário comprobatório (Priority: P2)

Como equipe de patrimônio, executo uma conferência física do acervo (total ou por
local/setor), registro encontrados, divergências, ausências e bens não previstos — e o
sistema consolida a ata exportável, **sem jamais alterar o cadastro**.

**Why this priority**: é a função comprobatória perante auditorias externas; depende da
base de bens (US1) mas é executável de forma independente.

**Independent Test**: criar um inventário com escopo, conferir itens (incluindo uma
divergência de local e um não previsto), tentar encerrar com pendências (deve bloquear)
e concluir o encerramento após conferir tudo.

**Acceptance Scenarios**:
1. **Given** um inventário recém-criado com lista de esperados, **When** um bem é
   conferido em local diverso do cadastrado, **Then** o item marca "local diferente"
   exigindo o local informado e o cadastro do bem permanece inalterado.
2. **Given** um inventário com itens pendentes, **When** o usuário tenta encerrá-lo,
   **Then** o encerramento é recusado; após conferir todos os esperados, o
   encerramento trava novas conferências e consolida a ata.

### User Story 3 — Acesso controlado e auditável (Priority: P3)

Como administrador, configuro perfis/permissões e integração AD, e qualquer operação
relevante (inclusive tentativas negadas) fica registrada na trilha de auditoria
somente-leitura.

**Why this priority**: sustenta a segurança e a rastreabilidade de todos os fluxos;
sem ela as US1/US2 perdem valor comprobatório.

**Independent Test**: atribuir um perfil mínimo a um usuário, tentar operações além da
permissão (devem ser negadas com 403 e auditadas) e verificar os registros na tela de
auditoria.

**Acceptance Scenarios**:
1. **Given** um usuário com perfil de somente-leitura, **When** ele tenta registrar uma
   movimentação, **Then** a operação é negada, nada muda e a tentativa aparece na
   auditoria como acesso negado.
2. **Given** um usuário AD cujo grupo não está mapeado a nenhum perfil, **When** ele
   autentica no diretório, **Then** o acesso é negado, nenhum usuário é criado no
   sistema e a tentativa é auditada.

### Edge Cases

- O que acontece quando um bem com número de série duplicado é cadastrado? → recusado
  com mensagem clara (unicidade verificada no cadastro e no banco).
- O que acontece quando dois usuários movimentam o mesmo bem simultaneamente? → a
  numeração de termo usa contagem do banco (ver limitação registrada na análise
  técnica; comportamento atual preservado — qualquer correção é tarefa própria).
- O que acontece quando o AD está indisponível? → erro específico e distinto (503) na
  API/mensagem web, sem fallback silencioso para senha local de contas AD.
- O que acontece ao tentar conferir item de inventário já encerrado? → recusado; itens
  travados após encerramento.
- O que acontece ao tentar bloquear o último administrador ativo? → recusado.

## Requirements *(mandatory)*

### Functional Requirements

Como esta especificação documenta o **sistema existente**, os requisitos abaixo são de
**preservação** (o sistema DEVE CONTINUAR fazendo) — não de criação:

- **FR-001**: O sistema DEVE autenticar usuários locais e do AD conforme as regras
  atuais (provedor por conta, lockout, sessão server-side revogável). *(preservação)*
- **FR-002**: O sistema DEVE manter autorização deny-by-default com o catálogo atual de
  permissões e perfis padrão, validando no backend todas as rotas. *(preservação)*
- **FR-003**: O sistema DEVE manter o registro imutável de movimentações com os 8 tipos,
  justificativa obrigatória, operador e snapshots de origem/destino. *(preservação)*
- **FR-004**: O sistema DEVE manter a geração automática de termo sequencial em
  alocação e devolução ao estoque. *(preservação)*
- **FR-005**: O sistema DEVE manter a integração manutenção↔fluxo (envio/retorno
  automáticos). *(preservação)*
- **FR-006**: O sistema DEVE manter o inventário como processo comprobatório que nunca
  altera o cadastro, com snapshot de esperados, encerramento condicionado e ata
  exportável. *(preservação)*
- **FR-007**: O sistema DEVE manter a auditoria somente-leitura dos eventos atuais,
  com dados anteriores/posteriores e registro de acessos negados. *(preservação)*
- **FR-008**: O sistema DEVE manter unicidade de tombamento e de número de série, e os
  códigos sequenciais de termo e inventário. *(preservação)*
- **FR-009**: O sistema DEVE manter a depreciação linear de 20% ao ano. *(preservação)*
- **FR-010**: O sistema DEVE manter importações CSV em duas fases (pré-visualização e
  confirmação). *(preservação)*
- **FR-011**: O sistema DEVE manter exportações CSV/Excel/PDF existentes, incluindo a
  ata de inventário. *(preservação)*
- **FR-012**: O sistema DEVE manter a central de ajuda integrada e o menu dinâmico por
  permissões. *(preservação)*
- **FR-013**: O sistema DEVE manter as proteções administrativas (último administrador,
  auto-bloqueio, perfis de sistema não-excluíveis, primeiro acesso idempotente).
  *(preservação)*
- **FR-014**: O sistema DEVE garantir que nenhuma credencial (senha, token, hash) seja
  registrada em logs, auditoria ou respostas. *(preservação)*
- **FR-015**: Evoluções futuras DEVEM preservar integralmente a seção 10 (comportamentos
  a preservar), salvo previsão explícita na especificação aprovada da tarefa.
- **FR-016**: Evoluções futuras DEVEM vir acompanhadas de testes que cubram o novo
  comportamento e manter a suíte de regressão existente aprovada.

### Key Entities *(include if feature involves data)*

- **Bem patrimonial (Asset)**: o equipamento tombado — identidade única (tag), dados
  fiscais, estado de conservação, status atual, localização e custodiante atuais.
- **Movimentação (Movement)**: evento imutável do fluxo do bem — tipo, origem→destino
  (com snapshots), status/condição antes/depois, motivo, operador e termo associado.
- **Colaborador (Custodian)**: pessoa física responsável pela custódia de bens —
  matrícula única, cargo e setor.
- **Local (Location)**: estrutura física — filial, prédio, andar, sala, departamento e
  gestor; setor é atributo (não entidade própria).
- **Manutenção (Maintenance)**: ordem de serviço vinculada ao bem, integrada ao fluxo.
- **Inventário / Item de Inventário**: conferência comprobatória e seus itens —
  expectativa (snapshot) e resultado por bem, com conferente e data/hora.
- **Usuário / Sessão**: conta de acesso (local ou AD), sessões server-side.
- **Perfil / Permissão**: modelo RBAC (usuário→perfis→permissões `modulo.acao`).
- **Registro de Auditoria**: trilha imutável de eventos com ator, contexto e
  dados antes/depois.
- **Configuração AD / Mapeamento Grupo→Perfil**: integração de diretório.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-A**: 100% das 24 regras de negócio (seção 7) permanecem válidas após qualquer
  evolução, verificáveis pela suíte de regressão existente.
- **SC-B**: 100% dos 24 comportamentos preserváveis (seção 10) continuam operando após
  evoluções — verificação por testes e inspeção de auditoria.
- **SC-C**: Zero alterações fora do escopo da tarefa em execuções guiadas por esta
  especificação (revisão por checklist da Constitution).
- **SC-D**: A suíte de testes existente (154 testes) mantém-se aprovada (exceto testes
  diretamente ligados ao comportamento sendo alterado pela especificação aprovada).
- **SC-E**: Esta especificação atua como referência única: qualquer nova feature do
  Spec Kit parte dela e cita explicitamente os comportamentos preservados que afeta.

## Assumptions

- O sistema permanece em operação contínua durante a evolução; não há janela de
  reescrita.
- O banco de produção é MariaDB com dados reais; a suíte de testes usa banco isolado.
- A integração AD está implementada e testada contra AD real (conforme documentação e
  código); novas features não devem alterá-la sem necessidade explícita.
- As limitações conhecidas (assinatura de termo, permissões reservadas, testes
  defasados) são tratadas em especificações próprias, uma de cada vez.
- A Constitution (`.specify/memory/constitution.md`) rege em caso de conflito com este
  documento.
