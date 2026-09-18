# Feature Specification: Correção do Deadlock da Restauração de Backup

**Feature Branch**: `019-import-deadlock`

**Created**: 2026-09-18

**Status**: Draft

**Input**: A restauração de backup travou indefinidamente no Windows (e no Linux): `SHOW PROCESSLIST` mostrou `DROP TABLE IF EXISTS audit_logs` esperando 933 s por metadata lock, enquanto uma conexão ociosa do pool da aplicação segurava o lock há o mesmo tempo. O import é executado dentro do processo web e o timeout interno (900 s) nunca dispara porque o bloqueio ocorre no write do pipe, antes do `wait()`. Corrigir o deadlock (import fora do processo web), garantir timeout real e impedir uso concorrente do sistema durante a restauração (tela de manutenção), preservando o ciclo seguro da 017 e o comportamento no Linux.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Restauração conclui sem travar o sistema (Priority: P1)

Um administrador com permissão de restaurar inicia a restauração de um backup pela tela. A operação é concluída (sucesso ou falha) em tempo limitado, sem que o import fique eternamente esperando um bloqueio mantido pela própria aplicação. Ao final, o banco está íntegro (validação pós-restauração existente) e a aplicação continua respondendo normalmente.

Caso real documentado (2026-09-18): o import travou 933 s esperando metadata lock mantido por conexão ociosa do pool da própria aplicação; o banco ficou inacessível (timeouts de leitura) até intervenção manual no processo do cliente de import.

**Why this priority**: A restauração é a recuperação de desastre do sistema — travar indefinidamente durante uma emergência é o pior cenário possível.

**Independent Test**: Com sessões abertas da aplicação e banco em uso, iniciar uma restauração → ela conclui (sucesso ou falha diagnosticável) dentro do tempo limite, o banco fica íntegro e a aplicação segue respondendo.

**Acceptance Scenarios**:

1. **Given** o sistema em operação com sessões ativas e conexões do pool abertas, **When** o administrador restaura um backup válido, **Then** a operação conclui em tempo finito, a validação pós-restauração passa e a resposta de sucesso é exibida.
2. **Given** a mesma operação, **When** o import é executado, **Then** nenhum bloqueio do banco que a própria aplicação mantenha pode impedir sua conclusão (o import não disputa locks com o processo que o executa).
3. **Given** a conclusão (sucesso ou falha), **When** qualquer página do sistema é acessada, **Then** a aplicação responde normalmente (sem travamentos residuais, sem conexões órfãs).

---

### User Story 2 - Falha de import é detectada em tempo finito (Priority: P1)

Se o processo de import demorar além do limite ou falhar, o sistema detecta em tempo finito, registra o diagnóstico técnico (sem credenciais), remove/libera o estado de "restauração em andamento", informa o operador com mensagem clara e deixa o backup de segurança disponível — nunca um travamento silencioso sem timeout.

**Why this priority**: O timeout atual nunca dispara (conta apenas o `wait()`, não o bloqueio no write do pipe). Sem detecção em tempo finito, qualquer falha vira travamento indefinido.

**Independent Test**: Simular um import que excede o limite de tempo (executável/fake que bloqueia) → o sistema aborta no prazo, registra o diagnóstico, libera o estado e reporta falha clara.

**Acceptance Scenarios**:

1. **Given** um import cuja execução excede o limite de tempo configurado, **When** o limite é atingido, **Then** o sistema encerra o processo de import, registra o diagnóstico no log técnico, marca a restauração como falha e informa o operador.
2. **Given** um import que termina com erro (código de retorno diferente de zero), **When** o resultado é processado, **Then** o comportamento existente é preservado (falha registrada, backup de segurança disponível) — nenhum falso sucesso.
3. **Given** qualquer falha de restauração, **When** o estado de "restauração em andamento" é consultado, **Then** ele foi liberado (novas restaurações e geração de backup voltam a ser aceitas).

---

### User Story 3 - Sistema em manutenção durante a restauração (Priority: P2)

Enquanto a restauração executa, o sistema entra em modo de manutenção: as demais páginas informam de forma amigável que há uma restauração em andamento e que o sistema está indisponível para uso, sem iniciar novas operações de negócio. A tela de backups reflete o estado da operação (em andamento/concluída/falha — sem prometimento de progresso percentual). Isso reduz a janela do problema original (sessões/conexões ativas segurando locks) e protege a integridade da operação.

**Why this priority**: Defesa em profundidade — mesmo com o import fora do processo, uso concorrente intenso durante a restauração é indesejável; e o operador precisa de feedback visível de que a operação está em andamento.

**Independent Test**: Iniciar restauração → enquanto durar, acessar outras páginas como outro usuário → todas exibem a página de manutenção; ao concluir, o acesso normal retorna.

**Acceptance Scenarios**:

1. **Given** uma restauração em andamento, **When** qualquer usuário (exceto o fluxo da própria restauração) acessa páginas do sistema, **Then** recebe uma página amigável de manutenção informando a restauração em andamento — sem erro técnico.
2. **Given** a conclusão da restauração (sucesso ou falha), **When** os usuários acessam o sistema, **Then** o acesso normal é restabelecido sem intervenção manual.
3. **Given** o travamento do processo web durante o import (pior caso histórico), **When** o serviço é reiniciado pelo operador, **Then** o sistema sobe fora do modo de manutenção (o estado não persiste travado).

---

### Edge Cases

- Sessões autenticadas durante a manutenção: acesso bloqueado de forma amigável; após a conclusão, as sessões podem ter ficado inválidas (o backup restaurado contém as sessões da época) — o sistema deve tratar sessão inválida com o fluxo normal de login.
- O próprio operador que iniciou a restauração não deve precisar da página de manutenção para acompanhar (feedback na tela de backups) — mas se sua sessão cair, nada deve ficar travado.
- Processo web reiniciado/crash durante a restauração: nenhum estado persistido pode deixar o sistema permanentemente em manutenção ou com o slot de concorrência ocupado.
- Timeout configurável e razoável: limite de tempo do import deve superar com folga a duração normal (banco atual ~70 KB de dump) e ser configurável para bancos maiores.
- Espaço em disco temporário: se a abordagem escolhida exigir materializar o dump descomprimido (.sql) antes do import, o projeto deve considerar que o .sql é substancialmente maior que o .gz (custo de disco no servidor).
- `DROP/CREATE DATABASE` vs. recriação tabela a tabela: a abordagem de reconstrução não pode depender de privilégios que o usuário do banco da aplicação não possui (verificar no diagnóstico/plan; se não possuir, usar caminho alternativo equivalente).
- Concorrência: duas tentativas de restauração simultâneas continuam bloqueadas pela guarda existente (apenas uma por vez).
- Geração de backup durante a restauração permanece proibida (guarda existente da 017).
- Encoding de mensagens e logs no Windows (padrão da 018).

## Requirements *(mandatory)*

### Functional Requirements

**Diagnóstico primeiro (padrão da 018)**

- **FR-001**: A implementação DEVE ser precedida de diagnóstico conclusivo nos artefatos de planejamento, confirmando no código real: (a) onde o import executa hoje em relação ao processo web; (b) por que o timeout existente não detecta o bloqueio; (c) qual conexão/mecanismo manteve o metadata lock no incidente; (d) os privilégios do usuário do banco para as abordagens de reconstrução avaliadas; (e) qual a menor alteração que elimina o deadlock sem quebrar o Linux.
- **FR-002**: É PROIBIDO presumir a causa ou escolher a solução sem comprovação no código/ambiente (padrão da 018 — não inventar arquitetura transacional nova).

**Execução do import sem auto-bloqueio**

- **FR-003**: O processo de import NÃO pode disputar bloqueios de banco com o processo web que o dispara: ou executa fora do processo web (subprocesso independente do serviço de banco), ou o processo web drena/encerra todas as suas conexões de banco durante o import (recriando o pool ao final) — a alternativa escolhida deve ser justificada no plan contra os critérios de menor alteração, robustez e preservação do Linux.
- **FR-004**: O ciclo seguro existente da 017 é preservado: validação da fonte → evento INICIADO → backup de segurança obrigatório e validado → evento PRE_RESTORE → import → validação pós-restauração real (conexão, tabelas essenciais, dados essenciais) → evento SUCCESS/FAILURE. Nenhum falso sucesso.
- **FR-005**: O backup de segurança criado antes da restauração permanece disponível na listagem em qualquer cenário de falha (comportamento existente).
- **FR-006**: Nenhuma alteração na conexão principal do banco além do necessário para drenar/recriar o pool (quando essa for a abordagem); `DATABASE_URL` intocado.

**Timeout real e diagnóstico**

- **FR-007**: A detecção de timeout deve cobrir TODAS as fases do import — incluindo a escrita de dados no processo de import, onde o bloqueio real do incidente ocorreu — por meio de um prazo total de relógio (wall-clock) que aborta o import ao expirar, independentemente da fase em que ele esteja. Detecção adicional de falta de progresso é reforço opcional, nunca substituto do prazo total.
- **FR-008**: O limite de tempo do import deve ser configurável (variável de ambiente, com padrão sensato documentado) para acomodar bancos maiores; nenhum valor hardcoded inalterável.
- **FR-009**: Em qualquer falha (timeout, código de retorno, erro de validação), o diagnóstico técnico vai ao log (etapa, tipo/mensagem, código de retorno, saída sanitizada — sem credenciais, padrão 018), a mensagem ao operador é clara e o estado de concorrência é liberado de forma garantida (mesmo em crash/restart do processo web).

**Modo de manutenção**

- **FR-010**: Durante a restauração, o sistema entra em modo de manutenção: todas as páginas (exceto as necessárias para o ciclo da restauração e o login/logout) exibem página amigável informando restauração em andamento, com status HTTP apropriado — sem expor detalhes técnicos sensíveis. A página de manutenção DEVE ser servida SEM depender de acesso ao banco de dados (verificação em memória, antes da autenticação/consulta de sessão) — caso contrário ela própria falharia exatamente quando o banco estiver indisponível ou o pool drenado.
- **FR-011**: O modo de manutenção é gerenciado pelo estado de concorrência existente da restauração (não criar mecanismo paralelo) e NUNCA persiste travado após restart do processo web.
- **FR-012**: Ao concluir (sucesso ou falha), o modo de manutenção é encerrado automaticamente e o acesso normal retoma sem intervenção manual.
- **FR-013**: A tela de backups deve refletir o estado (restauração em andamento) e a resposta final (sucesso/falha) ao operador que iniciou a operação, no padrão visual existente.

**Preservação do sistema existente**

- **FR-014**: Nenhuma alteração de schema do banco, RBAC, permissões, AD ou módulos não relacionados; a permissão `backup.restaurar` existente continua governando o acesso.
- **FR-015**: A geração de backup manual (018) permanece funcionando; a guarda de não gerar backup durante restauração é preservada.
- **FR-016**: O comportamento no Linux permanece funcional: o mesmo mecanismo serve aos dois sistemas, sem bifurcação por SO (diferenciação somente se tecnicamente indispensável e justificada no plan).
- **FR-017**: A auditoria existente de restauração (INICIADO, PRE_RESTORE, SUCCESS, FALHA) é preservada, sempre sem credenciais; a trilha permanece imutável.
- **FR-018**: Fora do escopo: agendamento, retenção, restauração automática, novo sistema de backup/auditoria, alteração de permissões, refatoração de módulos não relacionados.

### Key Entities *(include if feature involves data)*

- **Backup (arquivo)**: entidade existente, derivada do repositório de arquivos — inalterada.
- **Estado de restauração em andamento**: mecanismo existente em memória do processo (guarda de concorrência da 017) — passa a também governar o modo de manutenção; nunca persistido (crash-safe por construção).
- **Registro de auditoria**: eventos existentes reutilizados sem mudança de formato.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Uma restauração executada com o sistema em uso (sessões ativas, pool com conexões abertas) conclui em tempo finito com banco íntegro e aplicação responsiva — reproduzível em teste real no Windows (e no Linux quando disponível).
- **SC-002**: Um import simulado além do limite de tempo é abortado dentro do prazo configurado (verificável em teste automatizado com fake bloqueante) — zero travamentos indefinidos.
- **SC-003**: Durante a restauração, 100% das páginas acessadas por outros usuários exibem a manutenção amigável; após a conclusão, 100% do acesso normal retorna.
- **SC-004**: Zero credenciais em logs/auditoria em todos os cenários (padrão 018).
- **SC-005**: A suíte existente permanece no patamar (exceto testes diretamente ligados ao comportamento alterado pela especificação) + testes novos cobrindo: import sem auto-bloqueio, timeout real, liberação de estado, modo de manutenção, crash-safety.
- **SC-006**: O diagnóstico (FR-001) responde as cinco perguntas antes de qualquer alteração de código.

## Assumptions

- **Banco de produção**: MariaDB/XAMPP no Windows (ambiente atual) e MariaDB no Linux. Privilégios CONFIRMADOS em 2026-09-18 (SHOW GRANTS): o usuário da aplicação possui `ALL PRIVILEGES` escopados ao banco (`sispatrimoniopro.*`), SEM privilégio global — portanto `DROP DATABASE`/`CREATE DATABASE` NÃO é viável com o usuário atual; a reconstrução é por tabela (que é o conteúdo natural do dump existente). Qualquer mudança nesse quadro exigiria privilégios novos no servidor — decisão do operador, fora do escopo do código.
- **Travamento de 2026-09-18**: tratado como fato documentado (`docs/AVISO_RESTORE_DEADLOCK.md`), com evidências do `SHOW PROCESSLIST`; a especificação não reabre a causa.
- **Restauração manual fora do sistema**: permanece válida como fallback operacional (documentada no aviso); esta feature não a substitui.
- **Executor fake na suíte**: os testes automatizados usam fakes para o cliente de import (padrão 015–018); a prova real é manual (Windows obrigatório; Linux quando disponível).
- **Processo web único**: a aplicação roda como um único processo (uvicorn) — assumição do design atual da 017, confirmada no incidente; mecanismos multi-worker estão fora do escopo.
