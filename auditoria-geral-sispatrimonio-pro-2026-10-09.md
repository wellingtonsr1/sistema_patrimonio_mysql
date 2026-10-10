# Auditoria geral de qualidade e proposição de novas features do SisPatrimônio Pro

**Data do exame**: 2026-10-09  
**Modo**: diagnóstico, auditoria e planejamento — **sem implementação**, sem criação de specs, sem alteração de arquivos, sem execução de testes que pudessem mexer dados fora do escopo de leitura, sem instalação de dependências, sem alteração de configuração, sem commit/implantação.  
**Repositório neste momento**: limpo (confirmado por `git status` e `git diff` sem alterações).

---

## A. Resumo executivo

**Avaliação geral da qualidade atual**  
O SisPatrimônio Pro parece ser um sistema maduro e coerente para gestão patrimonial institucional. Ele tem modelo de domínio bem definido (bens, movimentações, locais, colaboradores, inventário, auditoria), um fluxo de movimentação que parece bem embasado, e uma arquitetura que separa rotas, serviços, modelos e relacionamentos de forma consistente com o padrão FastAPI + SQLAlchemy + Pydantic.

Por cima do que foi lido, o sistema parece mais forte em:
- rastreabilidade do patrimônio (movimentações com snapshots, inventário comprobatório que não altera o cadastro, auditoria de operações e acessos),
- controle de acesso (RBAC, perfis, deny by default, embutido no backend),
- boa memória evolutiva (specs numeradas, documentação de diagnóstico existente, suíte de testes).

Por cima do que foi lido, os riscos mais importantes não parecem estar em “o sistema não tem regras”, mas sim em pontos de:
- validade institucional do que é automatizado hoje versus o que o patrimônio da instituição exige,
- compatibilidade e operação em ambientes diferentes,
- cobertura/controle de regressão,
- limiares de uso institucional: recuperação de acesso, assinatura de termo, escopo por unidade/setor, e decisões de backup/monitoramento.

**Principais pontos fortes**
- Arquitetura em camadas usada de forma consistente e documentada.
- Fluxo de movimentação com tipos, transições, snapshots e trilha, sem edição do histórico.
- Inventário com ciclo próprio, snapshot de expectativa e convergência por conferência, sem reescrever o cadastro.
- RBAC com perfis padrão, autenticação local e AD separado, sessão server-side, lockout, auditoria de acesso negado.
- Backup com mecanismo nativo, geração segura, restauração sequenciada, retenção com lógica explícita e falhas diagnosticáveis.
- Documentação e organização de specs que permitem acompanhar a evolução e evitar operar no “feijão com arroz na memória”.

**Principais riscos**
- Compatibilidade/real execução do banco: o sistema suporta MySQL/MariaDB, mas não foi possível afirmar que não haja comportamento de borda em colações, conversões ou SQL/native sem ver o banco real e os usos reais.
- Fuso e hora: a política parece considerar UTC/local, mas foi observado uso misto de `datetime.now()`/`datetime.utcnow()` em alguns services; isso foi tratado como ponto de atenção, não como afirmação de defeito.
- Lacunas institucionais possíveis: recuperação de senha por e-mail, assinatura/termo de responsabilidade, escopo por unidade/setor podem ser neutros ou relevantes conforme o uso real.
- Decisões operacionais de backup: o mecanismo parece sólido, mas a adequação da retenção e do monitoramento ao volume e ao valor do patrimônio é decisão de gestão/operação, não apenas técnica.
- Risco de regressão em determinadas áreas se a equipe alterar comportamentos sem cobertura/ancoras adequadas.

**Cinco melhorias mais importantes**, em ordem de prioridade provisória
1. **Ajuste pontual de cobertura/ancoragem antes de qualquer mudança sensível** — principalmente em fluxos de movimentação, inventário e importação, onde o risco de regressão é maior.
2. **Acompanhar/investigar compatibilidade e comportamento de banco** — confirmar que consultas, unicidades, colações e conversões reais se comportam igual nos ambientes usados; e confirmar regras que dependem de SQL ou de comportamento do SGBD.
3. **Trabalhar a usabilidade/institucionalidade do inventário e conferência** — o mecanismo parece bom; o que pode ganhar valor é o fluxo de divergência e regularização no dia a dia do patrimônio.
4. **Decisão institucional sobre recuperação de senha e/ou termo de responsabilidade** — hoje parece haver lacunas/parcialidades; é questão de política e de especificação separada, não só de código.
5. **Reforçar observabilidade de backup/retention/restore** — não para “criar backup”, mas para que falhas, retenção e próximos disparos sejam claros para TI/operação e não dependam de leitura crua de estado.

---

## B. Inventário técnico

**Componentes identificados**
- `app/main.py` — aplicação FastAPI, lifespan, middleware de manutenção, handlers de erro básico, healthcheck.
- `app/config.py` — configuração central por variáveis de ambiente (.env), com ligação para DB, backup automático, retenção, AD, SMTP, 1Doc, HTTPS nativo.
- `app/database.py` — engine, pool, sessions, create_all tolerante à corrida, compreensão básica de Alembic, `init_db`.
- `app/services/*` — camada de regras: movimentação, inventário e inventário offline, importações e inteligência de importação, backup, scheduler de backup, permissões, autenticação, auditoria, AD, notificações, 1Doc, integração central, central de ajuda, etc.
- `app/models/*` — entidades principais: Asset, Movement, Maintenance, Custodian, Location, Inventario, InventarioItem, InventarioOfflineColeta, User, Session, Role/Permission/UserRole/RolePermission, AuditLog, ADSettings/ADGroupRole, BackupRecord, BackupConfig, BackupExternal*, OnedocIntegration/OnedocMessage/OnedocClient, IntegrationExecution, SetupClaim, Notification, etc.
- `app/schemas/*` — Pydantic Create/Update/Read para asset, custodian, location, movement, user, etc.
- `app/web/routes.py` e `app/web/routers/*` — interface web (Jinja2) e fluxos.
- `app/web/admin_routes.py`, `app/web/help_routes.py`.
- `app/api/*` — endpoints REST, incluindo `deps.py` com autenticação/autorização.
- `app/web/templates/*` — templates por módulo.
- `tests/*` — suíte com arquivos por domínio (auth, rbac, inventário, colaboradores, importações, locais, movimento, backups, integração, saúde, etc.), com `conftest.py` e manifest de rotas em `tests/route_manifest.json`.
- `docs/`, `specs/`, `requirements.txt`, `Makefile`, `Dockerfile`, `docker-compose.yml`, `run.py`, `seed_demo.py`, `install.sh`, `uninstall.sh`, `deploy.sh`, `scripts/`, etc.

**Tecnologias efetivamente utilizadas (confirmado pelo código)**
- Python; FastAPI; Uvicorn; SQLAlchemy com MariaDB/MySQL (PyMySQL); Pydantic v2; Jinja2 + Bootstrap 5 + Bootstrap Icons; Chart.js, QRCode.js (front end); OpenPyXL (Excel), ReportLab (PDF), CSV UTF-8 BOM; ldap3 para AD/LDAP; pytest + TestClient; ponto único de configuração por `.env`.

**Funcionalidades encontradas**
- Autenticação local, sessão, lockout; primeiro acesso via /setup ou admin via env/CLI.
- RBAC com catálogo de permissões e perfis padrão.
- AD/LDAP integrado, com zona de decisão por grupo/perfil.
- Auditoria somente-leitura com registro de eventos e diffs.
- Patrimônio: cadastro/importação, depreciação linear, etiquetas QR, buscas/filtros, edição via API.
- Movimentações por tipos com motor, snapshots e geração de termo sequencial.
- Termo de responsabilidade/cautela com geração automática em alocação/devolução (assinatura não aparece implementada na linha lida).
- Manutenções integradas ao fluxo.
- Colaboradores com cadastro/importação, sem exclusão identificada.
- Locais com criação/importação; edição via API; sem rota web de edição identificada para local.
- Inventário com ciclo completo, conferência, itens esperados, não previstos, encerramento, exportações/ata.
- Relatórios e exportações CSV/XLSX/PDF; dashboard.
- Central de ajuda embutida.
- CLI administrativa.
- Backup manual, automático, retenção GFS, restauração segura, monitoramento/integração central, destino externo, configurações via tela e env.
- Coleta offline de inventário com sincronização, conflitos e reconciliação.

**Estado da documentação e dos testes**
- Documentação robusta: README + múltiplos docs/ + specs organizadas + especificação reversa (SPEC-KIT-SISTEMA-ATUAL.md).
- Testes: suíte com cobertura por domínios principais (autenticação, RBAC, inventário, colaboradores, locais, importações, movimentação, backups, integração, saúde etc.), com testes de integração de rotas em corpo relevante.
- O SPEC-KIT-SISTEMA-ATUAL.md reporta quantidade de funções de teste e uma falha conhecida relacionada a lockout/testes de configuração; isso foi tratado como “não executei testes agora, mas há registro claro do estado documentado”.

---

## C. Matriz de qualidade

| Dimensão | Evidência encontrada | Avaliação | Risco | Recomendação |
|---|---|---|---|---|
| Arquitetura e manutenção | Separação Web/API → services → models; rotas delegam regras; configs centralizadas; specs organizadas | Boa/Consistente | Risco de regressão se o padrão de contribuição não for seguido | Manter disciplina de escopo por feature; evitar regras em rotas; continuar usando services como fonte |
| Banco de dados e integridade | FKs, unicidades, snapshots imutáveis, inventário que não altera cadastro, create_all tolerante, alembic básico, backup/restore com validação | Boa | Comportamento real pode variar com colações/SQL/native; concorrência em algumas ações (termo, código de inventário) pode precisar de validação | Confirmar em produção; vigiar geração de termo e código de inventário; validar comportamento de unicidade/colação nos ambientes reais |
| Segurança | RBAC deny-by-default; lockout; sessão server-side; hash de senha; timing-safe; open redirect mitigado; credenciais apenas em ambiente; auditoria de acessos negados | Boa | Uso do flag legacy is_admin como bypass; ausência de recuperação de senha por e-mail pode ser institucional; configurações de HTTPS/AD/SMTP são decisões operacionais | Validar políticas de concessão de admin; confirmar HTTPS/certificado/AD/SMTP na operação; histriar recuperação de acesso conforme necessidade institucional |
| Desempenho e escalabilidade | Estruturas com índices, paginação em alguns pontos, exportações streams em alguns casos, importação prévia/classificação; pool configurado | Plausível/bom sinal | Não se afirma gargalos sem medição; relatórios/exportações grandes podem pesar conforme volume | Medir com dados reais antes de declarar problema; aferir exportações grandes e imports; revisar paginação/filtros onde houver uso intenso |
| Testes e confiabilidade | Suíte por domínios principais; testes de auth, rbac, inventário, importações, backups, integrações; manifest de rotas | Boa base | Nem todo comportamento crítico precisa de cobertura igual; pontos institucionais podem não ter teste | Priorizar cobertura de fluxos de risco antes de mudanças; adicionar testes de regressão para comportamentos institucionais reais |
| Interface e experiência do usuário | Bootstrap 5; layouts/sidebar responsiva; ajuda contextual; mensagens de erro visíveis; formulários com validação; tema claro/escuro; impressão em alguns relatórios/termos | Bom/funcional | Uso institucional pode exigir melhorias de usabilidade mais específicas | Avaliar pelo uso real; priorizar clareza em conferência, divergências, importações e erros de importação |
| Auditoria, rastreabilidade e relatórios | AuditLog com diffs; movimentos imutáveis com snapshots; termos com número sequencial; inventário com ata/export; auditoria de acesso/operação | Forte | Nenhuma regra de edição do histórico parece existir — bom sinal; mas o valor patrimonial depende de como os resultados são usados na prestação de contas | Manter imutabilidade; garantir que divergências e trilha sejam explorados nos fluxos reais; revisar se o que é exportado responde ao necessário |
| Backup e implantação | dump nativo; senha só em ambiente; geração segura; restore com validação pós; retenção com política; expostos com sistema e monitoramento; deploy/install scripts | Boa base | Adequação à política institucional e ao volume; testes reais de restauração; monitoramento de falhas | Exercitar restauração e retenção na operação; monitorar falhas; confirmar ritmo e política com TI/operação; validar HTTPS/AD nas instalações |

---

## D. Registro de achados

**AUD-001**  
Descrição: O sistema parece ter base de segurança e controle de acesso consistente, mas há um mecanismo legado de “superusuário” (`is_admin`) que pode coexistir com perfis.  
Evidência: `app/services/permission_service.py` trata `is_admin` como exceção de acesso; `app/config.py` traz variáveis/admin inicial; manifest/rotas e specs apontam admin legado.  
Gravidade: Médio.  
Impacto potencial: Concessão equivocada ou persistência de conta com acesso total além do perfil pretendido.  
Recomendação: Decidir institucionalmente se novo admin deve usar perfil Administrador em vez do flag legado; evitar mistura; validar quais contas realmente usam o mecanismo legado.  
Nível de confiança: Médio.

**AUD-002**  
Descrição: Pode haver inconsistência de fuso/tempo em alguns services (uso misto de `datetime.now()` e `datetime.utcnow()`).  
Evidência: `app/services/movement_service.py` vs `app/services/inventario_service.py`; `app/utils/time_utils.py`; o SPEC-KIT-SISTEMA-ATUAL.md já sinaliza isso como ponto de atenção.  
Gravidade: Médio.  
Impacto potencial: Registros com interpretação/semântica de tempo não uniforme, se não for apenas legado isolado.  
Recomendação: Investigar se há uso real incompatível; padronizar no ponto correto quando houver justificativa; não mudar por mudança.  
Nível de confiança: Baixo/Médio (precisa de confirmação no código/execução real dos pontos).

**AUD-003**  
Descrição: Termo de responsabilidade parece gerado, mas o campo de assinatura/confirmção parece não ter fluxo implementado na linha lida.  
Evidência: `app/models/movement.py` tem `term_signed` default False; leitura de código e spec/SPEC-KIT-SISTEMA-ATUAL.md aponta ausência de alteração desse campo para True.  
Gravidade: Médio (depende do uso institucional).  
Impacto potencial: Se a instituição espera registro de aceite/assinatura, o campo pode ser enganoso ou inoperante para esse fim.  
Recomendação: Decidir se assinatura/validação é necessária; se for, especificar fluxo separado; se não for, manter apenas como lembrete/documento.  
Nível de confiança: Alto para “campo existe e parece sem fluxo de alteração”; Médio para “isso é lacuna ou não, dependendo da política”.

**AUD-004**  
Descrição: Geração de termo sequencial pode, sob concorrência, gerar duplicidade de código, pois parece usar contagem +1 sem constraint unique.  
Evidência: comportamento em `app/services/movement_service.py`; leitura de movimento/locais e spec.  
Gravidade: Médio.  
Impacto potencial: Código de termo duplicado ou não determinístico em condições de concorrência.  
Recomendação: Investigar se houver uso concorrente real; considerar geração mais robusta se necessário; não “resolver” sem evidência de risco real.  
Nível de confiança: Médio (hipótese plausível, não afirmação de defeito observado).

**AUD-005**  
Descrição: Código sequencial de inventário pode ter comportamento sensível a ordenação lexicográfica/concorrência em certas condições.  
Evidência: `app/services/inventario_service.py` e leitura de inventário; documentação/especificações existentes.  
Gravidade: Médio.  
Impacto potencial: Código pode não ser sequencial estritamente ou pode gerar choque em condições específicas de criação concorrente.  
Recomendação: Confirmar uso real; validar se geração atual atende ao necessário; considerar mudança apenas com evidência.  
Nível de confiança: Médio.

**AUD-006**  
Descrição: Algumas rotas fazem consulta direto no ORM ao invés de passar por serviço.  
Evidência: `app/web/routes.py` e `app/web/admin_routes.py` (busca de inventário, trechos administrativos).  
Gravidade: Baixo/Médio.  
Impacto potencial: Pode ser benigno, mas pode dificultar manutenção ou centralizar lógica fora do lugar esperado.  
Recomendação: Revisar ponto a ponto; mover para serviço quando houver valor claro; só alterar com escopo claro.  
Nível de confiança: Médio.

**AUD-007**  
Descrição: Permissões existem no catálogo que não parecem ter rotas consumidoras claras (ex.: editar/cancelar movimentação, excluir patrimônio).  
Evidência: `app/services/permission_service.py` e leitura de rotas + SPEC-KIT-SISTEMA-ATUAL.md.  
Gravidade: Baixo.  
Impacto potencial: Superfície de permissão maior que funcionalidade visível, o que pode gerar dúvida ou concessão sem uso claro.  
Recomendação: Manter mesmo que “reservado” se for intencional; documentar uso previsto ou limpar o catálogo conforme política.  
Nível de confiança: Alto.

**AUD-008**  
Descrição: Ausência de rota web identificada para edição de local e exclusão de colaborador/bem em algumas leituras.  
Evidência: leitura de rotas/web e manifest/rotas + SPEC-KIT-SISTEMA-ATUAL.md.  
Gravidade: Baixo.  
Impacto potencial: Instabilidade percebida se a UI sugerir gestão completa e o fluxo não esteja disponível no web.  
Recomendação: Alinhar expectativa institucional; se a ausência for proposital, documentar; se não for, cobrar via feature própria.  
Nível de confiança: Médio.

**AUD-009**  
Descrição: Provável ponto de atenção em compatibilidade/real execução do banco dependendo do ambiente e de SQL/native usado.  
Evidência: estrutura geral, leitura de alguns services/importações, ausência de execução real no banco nesta análise.  
Gravidade: Médio.  
Impacto potencial: Comportamento diferente entre ambientes ou em dados reais.  
Recomendação: Validar nos bancos de produção/desenvolvimento com dados reais; testar geração de termo, códigos, unicidades e exports sob volume.  
Nível de confiança: Baixo para “existe defeito”; Alto para “é válido investigar antes de mudanças”.

**AUD-010**  
Descrição: Ausência de recuperação de senha por e-mail/autoatendimento parece ser uma lacuna funcional atual.  
Evidência: leitura de auth/rota e documentação.  
Gravidade: Médio (dependendo do uso institucional).  
Impacto potencial: Dificuldade de acesso ou dependência de reset administrativo.  
Recomendação: Decidir se é necessário; se for, planejar especificação separada com política de reenvio/segurança; se não for, documentar como limitação.  
Nível de confiança: Alto para “não está implementado na linha lida”; Médio para impacto institucional.

---

## E. Catálogo de features propostas

**1. Inventário com fluxo de divergência e regularização**  
Problema que resolve: o sistema registra divergências, mas pode não apoiar bem o ciclo divergente → tratado → regularizado no dia a dia.  
Evidências: comportamento de inventário/conferência lido em `app/services/inventario_service.py` e rotas; specs e docs.  
Benefício institucional: maior clareza na prestação de contas e na condução de bens com posição diferente da esperada.  
Usuários/perfis: Patrimônio, Auditor, Gestor de TI.  
Escopo resumido: resultados/divergências com rastros de regularização e/ou ações vinculadas sem alterar a imutabilidade do cadastro.  
Dependências: decidir política de regularização; alinhar com movimentação se necessário.  
Complexidade: Média.  
Riscos: criar “status extra” sem necessidade; introduzir semântica nova sem clareza.  
Critérios preliminares: divergência registrada; ação/regularização rastreada; sem quebra do inventário/ata.  
Prioridade recomendada: P2.  
Impactos sobre existente: baixo, se feito com cuidado para não alterar regras já coerentes.

**2. Recuperação de senha institucional (se desejável)**  
Problema que resolve: ausência de autoatendimento pode gerar dependência de reset administrativo.  
Evidências: leitura de auth e rotas; documentação.  
Benefício institucional: redução de chamados/admin; se aceitável institucionalmente, melhor usabilidade.  
Usuários/perfis: todos os usuários com senha local; TI/operação.  
Escopo resumido: fluxo de recuperação com política de segurança, provisória, com expiração, sem cair em fraquezas básicas.  
Dependências: política de segurança; decisão se vale a pena.  
Complexidade: Baixa/Média.  
Riscos: outros canais de recuperação; confusão com reset admin; necessidade de e-mail/DNS; segurança de token.  
Critérios preliminares: recuperação funcionando; sem conceder acesso sem validação adequada; sem quebrar lockout/sessão.  
Prioridade recomendada: P2/P3 conforme necessidade institucional.

**3. Fortalecimento de cobertura/ancoragem de regressão nos fluxos críticos**  
Problema que resolve: reduzir risco de regressão em movimentação, inventário, importações e backups antes de mudanças.  
Evidências: suíte existente e manifest de rotas; ausência de execução nesta análise.  
Benefício institucional: mais segurança na evolução; menos risco de quebrar comportamento patrimonial.  
Usuários/perfis: TI/dev; Patrimônio como beneficiário indireto.  
Escopo resumido: exercícios de regressão em rotas/services críticos; testes de importante comportamento com dados representativos; casos de falha documentados.  
Dependências: definir quais fluxos são críticos institucionalmente; tempo para execução/medição.  
Complexidade: Baixa/Média.  
Riscos: sobrecarga desnecessária se feito sem foco.  
Critérios preliminares: cobertura alinhada ao risco real; sem enfraquecer testes atuais.  
Prioridade recomendada: P1.

**4. Ajustes pontuais de compatibilidade e uso do banco**  
Problema que resolve: confirmar que comportamento real de SQL/colação/unicidade/concorrência não causa surpresas em produção.  
Evidência: estrutura geral; leitura de alguns services; ausência de execução nesta análise.  
Benefício institucional: evitar comportamentos surpresa em dados reais; maior segurança em alterações futuras.  
Usuários/perfis: TI/operação; Patrimônio.  
Escopo resumido: validar em banco real unicidades, conversões, edge de colação, concorrência em termo/código; documentar achados.  
Dependências: acesso ao banco e a dados representativos; tempo de análise.  
Complexidade: Baixa/Média.  
Riscos: intervir sem evidência; confundir “diferença” com “problema”.  
Critérios preliminares: evidência de comportamento real; recomendação ancorada em dados.  
Prioridade recomendada: P1/P2.

**5. Observabilidade reforçada de backup/retention/restore**  
Problema que resolve: deixar mais claro para operação o que está acontecendo com backups, retenção e próximos disparos.  
Evidências: backup_service, scheduler, backup_record, configs; monitoramento/integração central.  
Benefício institucional: mais clareza; menor dependência de leitura crua de estado.  
Usuários/perfis: TI/operação.  
Escopo resumido: tornar visível estado do scheduler, próxima execução, último resultado, retenção, falhas recentes, de forma legível.  
Dependências: decidir quais métricas são úteis; evitar duplicar monitoramento.  
Complexidade: Baixa.  
Riscos: poluir interface sem benefício; assumir significado operacional errado.  
Critérios preliminares: visibilidade que ajuda a operação; sem inventar eventos novos desnecessários.  
Prioridade recomendada: P2.

**6. Assinatura/validação de termo (se necessário)**  
Problema que resolve: se o patrimônio precisar registrar aceite/termo de responsabilidade de forma eletrônica, há um campo sem fluxo.  
Evidência: movement_service, models, docs.  
Benefício institucional: melhor rastreio de responsabilidade, se a instituição exigir.  
Usuários/perfis: Patrimônio, Auditor.  
Escopo resumido: fluxo de assinatura/validação com política institucional; sem reescrever movimentação.  
Dependências: decisão institucional; definição de que significa “assinatura” na prática.  
Complexidade: Média/Alta.  
Riscos: inventar significado; acoplar coisa que não é necessária.  
Critérios preliminares: fluxo claro; sem quebrar movimentação/inventário; compatível com uso real.  
Prioridade recomendada: P2/P3.

---

## F. Roadmap recomendado

Fase 1 — Correções de segurança e integridade
- Validar concessão de admin e uso do flag legado.
- Confirmar política de recuperação de acesso; se relevante, planejar recuperação de senha.
- Manter imutabilidade do histórico; revisar rastros de termo/divergências.

Fase 2 — Estabilização e fortalecimento dos testes
- Reforçar cobertura em fluxos críticos antes de mudanças.
- Adicionar testes de regressão em comportamentos institucionais reais.
- Documentar casos de uso crítico e como verificá-los sem mexer dados onde não for seguro.

Fase 3 — Melhorias operacionais e de usabilidade
- Inventário com suporte melhor ao ciclo de divergência/regularização (se institucionalmente relevante).
- Observabilidade de backup/retention/restore para TI/operação.
- Ajustes de usabilidade nos pontos de maior uso: conferência, importação, mensagens de erro, exportações.

Fase 4 — Evolução funcional e gerencial
- Termo de responsabilidade, se a instituição exigir.
- Escopo por unidade/setor, se necessário e se a política subsidiar.
- Relatórios/exportações orientados às necessidades de prestação de contas.
- Melhorias graduais de buscas/filtros/dashboard, se a necessidade for demonstrada.

Fase 5 — Recursos avançados e integrações
- Inventário offline/PWA, se a operação em campo demandar.
- Integração GLPI/integrações institucionais, se houver necessidade real e contrato claro.
- Outros recursos avançados só quando houver benefício demonstrado e não forem “ideias soltas”.

---

## G. Matriz de dependências

- Quase tudo que envolve **rastreabilidade e prestação de contas** depende de decidir política antes de implementar: termo, divergências, escopo por unidade/setor, recuperação de senha.
- **Testes/regressão** é pré-requisito razoável para mudanças em movimentação, inventário, importações, backups e permissões.
- **Validações de banco/compatibilidade** deve vir antes de mudanças que toquem unicidades, geração de códigos ou termos, ou qualquer coisa que dependa de SQL/comportamento real.
- **Backup/retention/restore_monitoramento** depende de TI/operação definir ritmo, política e o que é “ok”.
- **Recursos avançados** (offline, integrações) devem vir depois de estabilizar o essencial e só quando houver necessidade real.

---

## H. Plano de validação

Para cada melhoria proposta, a ideia geral de validação é:

- **Sem mexer dados sensíveis antes de ter isolamento claro**: rodar validação em ambiente próprio ou com dados representativos; não assumir que qualquer teste de diagnóstico é neutro sem checar efeitos colaterais.
- **Movimentação/inventário**: confirmação de que o histórico, snapshots e resultados continuam coerentes; sem quebra da imutabilidade nem do inventário.
- **Importação**: validar classificação, duplicidade, campos obrigatórios, pré-processamento e que nada incompatível é gravado.
- **Segurança/RBAC**: verificar concessão, negação, lockout, sessão, e que credenciais/configurações não aparecem em logs/auditoria.
- **Backup/restore**: validar geração, restauração, retenção, monitoramento e que falhas são diagnosticáveis sem expor segredos.
- **Banco/compatibilidade**: confirmar em dados reais; validar unicidades, códigos, termos, colações, conversões, concorrência nos casos relevantes.
- **Interface/usabilidade**: teste com os perfis reais de uso antes de generalizar.

Para cada item, o ideal é ter: o que se espera, como se testa, quais dados/configs são necessários, e o que não se pode assumir.

---

## I. Recomendações para o Spec Kit

- **Correções pontuais**: AUD-001/002/003/008 e as questões de permissões “reservadas” podem virar pequenas tarefas/documentação antes de qualquer feature grande.
- **Melhorias técnicas internas**: padronizar/validar uso de tempo; revisar pontos onde rotas fazem ORM direto se isso prejudicar manutenção; ancorar comportamento de geração sequencial se for criticável.
- **Novas specs de features**: sugiro escrever specs separadas para: campanha de divergência/regularização do inventário; recuperação de senha (se for querer); observabilidade de backup/retention; e qualquer uma das demais features que a instituição considerar relevante.
- **Atualizações de testes e documentação**: cobertura nos fluxos críticos; documentar o que já está “reservado” versus “ausente”; atualizar docs se a operação mudar.
- **Investigações adicionais antes de qualquer implementação**: validação no banco real de compatibilidade, concorrência, códigos e termos; uso real de admin/lockout/recuperação; e se a retenção/backup está adequado ao volume do patrimônio.

Para cada proposta de spec, o resumo inicial de escopo deve vir com: quem beneficia, o problema real, o que entra e o que fica fora, e como vai provar que não quebrou nada.

---

## J. Conclusão

Na prática, a recomendação principal é: **não tentar resolver tudo de uma vez**.

1. Primeiro, alinhar com os perfis de doadorão/instituição o que é obrigatório versus o que é “legal ter”: admin, recuperação de senha, termo, escopo por unidade/setor, observabilidade de backup.
2. Depois, fortalecer teste/regressão nos fluxos críticos antes de mexer em movimentação, inventário, importação ou backup.
3. Só então, avançar com specs pequenas e priorizadas, no ritmo da equipe e sem presumir grande refatoração.

---

*Documento gerado exclusivamente por leitura do código, estrutura e documentação existentes; nenhum arquivo do sistema foi modificado durante a análise.*
