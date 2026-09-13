# 🔍 RELATÓRIO DE AUDITORIA TÉCNICA — SisPatrimônio Pro (`sistema_patrimonio_mysql`)

**Data da auditoria:** 12/09/2026
**Natureza:** Auditoria técnica, funcional e estrutural **exclusivamente de leitura** — nenhum arquivo, banco de dados ou configuração foi alterado durante a auditoria.
**Objetivo:** Diagnóstico completo do estado atual do sistema + base organizada para futura adoção de **Spec Kit / desenvolvimento orientado a especificações**.
**Método:** Todos os achados abaixo foram verificados diretamente no código-fonte (64 arquivos Python, ~14.900 LOC em `app/`, 13 arquivos de teste com 154 funções de teste, 10 documentos versionados).

---

## 1. Resumo Executivo

O sistema é **maduro e bem arquitetado** para sua missão central: cadastro patrimonial com tombamento único, trilha de movimentação imutável, custódia, locais, manutenções, termos de responsabilidade com QR, autenticação local + AD, RBAC deny-by-default, trilha de auditoria abrangente e importação CSV com prévia. A arquitetura em camadas (web/api → services → models) é limpa e deve ser **preservada e evoluída incrementalmente**.

**Não foram encontrados defeitos P0 (críticos / bloqueadores de segurança).** As principais fragilidades são:

1. Mistura de `datetime.now()`/`utcnow()` corrompendo a ordenação da linha do tempo;
2. Exportações PDF/Excel que quebram em runtime por dependências ausentes no `requirements.txt`;
3. Ausência de tokens CSRF e headers de segurança (mitigado parcialmente por `SameSite=Lax`);
4. Fluxo formal de *baixa patrimonial* e ciclo de aceite do termo que ainda não existem;
5. QR Codes que codificam URLs dependentes do host.

Fatos verificados:

- **64 arquivos Python**, **154 funções de teste** em 13 arquivos (o README alega 106 — desatualizado);
- **~14.900 LOC** no código da aplicação;
- **10 documentos versionados** em `docs/`;
- `.env` corretamente fora do Git;
- ⚠️ `tests/` atualmente **ignorado pelo `.gitignore`** — a suíte de testes **não está versionada**.

---

## 2. Arquitetura Encontrada

| Camada | Implementação | Avaliação |
|---|---|---|
| Framework web | FastAPI + Uvicorn, templates Jinja2, Bootstrap 5 | Sólida |
| API REST | Routers `/api/v1` (auth, assets, movements, custodians, locations, reports), todos atrás de `require_api_auth` + `require_permission` | Sólida |
| Services | 20 serviços; regras de negócio centralizadas; rotas enxutas | Sólida |
| Models | 16 modelos SQLAlchemy, MariaDB via `pymysql`, pool ajustado (10+20, pre_ping, recycle 1800) | Sólida |
| Autenticação | PBKDF2-HMAC-SHA256 (600k iter), sessões server-side (hash SHA-256 do token), lockout, provedor híbrido AD/LDAP | Sólida |
| RBAC | Catálogo em `permission_service` (31 permissões, incl. 4 de inventário), 7 perfis seeded, deny-by-default, bypass `is_admin` (documentado) | Sólida |
| Auditoria | `audit_logs` somente leitura, JSON antes/depois, log de acessos negados, sem credenciais | Sólida |
| Migrações | `create_all` + `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` ad-hoc; **sem Alembic** | Ponto fraco |
| Frontend | Server-rendered + Chart.js + QRCode.js (CDN); página de etiquetas; tema claro/escuro | Sólida |

---

## 3. Mapa de Módulos (classificação de estado)

| Módulo | Arquivos principais | Estado |
|---|---|---|
| Autenticação & sessões | `auth_service`, `session_service`, `auth_provider`, `/login`, `/setup` | **COMPLETO** |
| RBAC | `permission_service`, `admin_routes` | **COMPLETO** |
| Integração AD/LDAP | `ad_service`, `ad_ldap`, tela `admin/ad`, mapeamento grupo→perfil com prioridade | **COMPLETO** (testado com mock; claims de AD real conforme docs) |
| Patrimônio (bens) | `asset_service`, `assets_api`, templates | **FUNCIONAL** |
| Movimentações + Termos | `movement_service`, `term.html` | **FUNCIONAL** (falta ciclo de aceite do termo) |
| Inventário físico | `inventario_service`, templates `inventarios/*`, models `Inventario`/`InventarioItem` | **COMPLETO** para o escopo projetado; sem evidência fotográfica |
| Manutenções | `maintenance_service` | **FUNCIONAL** |
| Relatórios | `report_service` (CSV/Excel/PDF), dashboard | **INCONSISTENTE** (dependências Excel/PDF ausentes) |
| QR/etiquetas | `assets/labels.html`, `detail.html`, `term.html` | **PARCIAL** (URLs dependentes do host) |
| Importação CSV | `import_service`, `custodian_import_service`, `location_import_service` | **COMPLETO** |
| Auditoria | `audit_service`, `/admin/audit` | **COMPLETO** |
| Baixa patrimonial | apenas `MovementType.WRITE_OFF` + status `BAIXADO` | **PARCIAL / NÃO IMPLEMENTADO** (sem fluxo) |
| Gestão documental | — | **NÃO IMPLEMENTADO** |

---

## 4. O Que Está Funcionando Corretamente (verificar antes de tocar)

- Segurança de sessão: token com hash no banco, cookie HttpOnly+Lax, TTL e revogação server-side (logout/troca de senha).
- Senha: PBKDF2 600k, equalização de tempo com hash dummy, lockout com auditoria (`LOGIN_BLOQUEADO`), sem enumeração de usuários.
- Proteção contra open redirect no `?next=`; páginas amigáveis 403/404; auditoria de acessos negados.
- RBAC: deny-by-default no backend em tudo que foi inspecionado; menu/botões são apenas apresentação; proteção do último administrador; perfis de sistema não podem ser excluídos.
- Regras do AD respeitadas no código: sem grupo mapeado → nenhum usuário criado (apenas auditoria); contas locais nunca reautenticam via AD; AD nunca define permissões; senha de serviço apenas em env.
- Integridade das movimentações: o schema `AssetUpdate` deliberadamente **exclui** `status/location_id/custodian_id` — mudanças de estado só via movimentações (decisão de design excelente).
- Regra de ouro do inventário implementada e garantida em `record_check`: **divergências nunca alteram o cadastro do bem**; encerramento trava itens; bens não previstos viram ocorrências.
- Cálculo de depreciação com piso em zero; exportações CSV UTF-8 com BOM.

---

## 5–8. Backlog de Problemas (por prioridade)

### P1 — Alto

```text
ID: BUG-001
Título: Mistura de datetime.now() e datetime.utcnow() no sistema
Categoria: Backend / Integridade de dados
Local: asset_service.py, movement_service.py (now() local ingênuo)
       vs serviços de auth/sessão/auditoria (utcnow())
Problema: Timestamps de movimentação/bem usam hora local; auditoria/sessão usam UTC.
          get_timeline_for_asset() COMBINA as duas fontes e ordena por timestamp.
Impacto: No horário de Brasília (UTC-3), eventos de auditoria aparecem até 3h
         fora de ordem na linha do tempo do bem; exportações/auditorias futuras não confiáveis.
Recomendação: Política única (armazenar UTC, exibir hora local) — requer plano de migração.
Precisa de SPEC: SIM (SPEC-dados-temporais) — toca em linhas existentes.
```

```text
ID: BUG-002
Título: Exportações PDF/Excel de relatórios quebram em runtime (dependências ausentes)
Categoria: Backend / Relatórios
Local: report_service.py:143 (openpyxl), :256/:574 (reportlab); requirements.txt
Problema: Imports preguiçosos de openpyxl/reportlab NÃO estão no requirements.txt.
Impacto: Endpoints Excel/PDF de /reports levantam ImportError → 500 em produção.
Recomendação: Adicionar ambos ao requirements.txt (tarefa simples, sem SPEC) + testes.
```

```text
ID: BUG-003
Título: Geração de código de termo tem condição de corrida e 3 esquemas inconsistentes
Categoria: Backend / Regra de negócio
Local: movement_service.create_movement (count+1 → TR-YYYY-NNNNN),
       asset_service.create (TR-INIC-YYYY-<asset_id>),
       movement_service.get_term_details (fallback TR-YYYY-<movement_id>)
Impacto: Movimentações simultâneas podem duplicar códigos de termo; numeração não unificada.
Recomendação: Tabela de sequência dedicada ou coluna auto-incremento no banco. SPEC-003.
```

```text
ID: SEC-001
Título: Diretório tests/ ignorado pelo .gitignore — suíte fora do versionamento
Categoria: Processo / Risco
Local: .gitignore ("# Testes  tests/")
Impacto: A base de regressão (154 testes) vive apenas nesta máquina; um clone novo = zero testes.
Recomendação: Remover a regra de ignore e versionar os testes. Tarefa simples, fazer primeiro.
```

### P2 — Médio

```text
ID: SEC-002
Título: Sem tokens CSRF e sem headers de segurança
Categoria: Segurança
Local: todos os formulários POST web; nenhum middleware no main.py (grep: 0 ocorrências
       de csrf/X-Frame-Options/CSP)
Problema: SameSite=Lax mitiga o POST cross-site clássico, mas não há defesa em camadas,
          nem X-Frame-Options/CSP/X-Content-Type-Options.
Impacto: Médio-baixo. Recomendação: token CSRF nos formulários + middleware de headers.
Precisa de SPEC: SIM (SPEC-seguranca-http).
```

```text
ID: BUG-004
Título: /health vaza sessões do banco quando o AD está configurado via env
Categoria: Backend / Confiabilidade
Local: main.py health_check — cria SessionLocal() duas vezes sem fechar
       (get_ad_settings(SessionLocal()), ad_enabled(SessionLocal()));
       SessionLocal().close() fecha uma sessão diferente, recém-criada.
Impacto: Mitigado pelo GC do CPython, mas incorreto; polling de monitoramento gera churn.
Recomendação: Usar uma única sessão com try/finally. Tarefa simples.
```

```text
ID: DB-001
Título: Sem ferramenta de migração de schema
Categoria: Banco
Local: database._ensure_schema_migrations
Problema: ALTER TABLE ... ADD COLUMN IF NOT EXISTS escritos à mão (MariaDB 10.5+);
          create_all ignora mudanças em modelos existentes; risco de drift.
Recomendação: Adotar Alembic numa SPEC (SPEC-dados-temporais ou própria).
```

```text
ID: DB-002
Título: Valores monetários armazenados como Float
Categoria: Banco
Local: assets.purchase_value (Float)
Problema: Ponto flutuante binário para moeda; anomalias de arredondamento em relatórios.
Recomendação: DECIMAL(12,2) — exige migração (Alembic primeiro).
```

```text
ID: BUG-005
Título: Bens baixados permanecem totalmente editáveis
Categoria: Regra de negócio
Local: AssetService.update — sem guarda de status; apenas movimentações são bloqueadas
       (create_movement recusa não-ACQUISITION em WRITTEN_OFF).
Impacto: patrimonio.editar pode alterar tag/valores de um bem baixado, quebrando a
         garantia de "histórico até a baixa".
Recomendação: Bloquear edições (ou restringir a notas) após a baixa. Parte da SPEC-baixa.
```

```text
ID: BUG-006
Título: term_signed nunca é alterado
Categoria: Regra de negócio
Local: models/movement.py:45, movement_service:146 — sempre False; nenhum endpoint
       ou rota marca o aceite.
Impacto: Ciclo de vida do termo (aceite/devolução) não rastreado. → SPEC-termo.
```

```text
ID: RBAC-001
Título: 3 permissões do catálogo sem pontos de aplicação
Categoria: RBAC / Consistência
Local: patrimonio.excluir (sem endpoint DELETE), movimentacao.editar e
       movimentacao.cancelar (nenhum endpoint as usa).
Impacto: Telas de perfil prometem capacidades que não existem; confunde auditoria.
Recomendação: Marcar como "reservado" na UI ou implementar; documentar a decisão.
```

### P3 — Baixo / Informativo

- **SEC-003**: `/health` expõe publicamente o status de banco/AD (monitoramento precisa; considerar token). Baixo.
- **SEC-004**: sem rate limiting por IP no login (o lockout por conta permite bloqueio temporário direcionado de usuários conhecidos — tradeoff padrão). Baixo.
- **SEC-005**: `AUTH_COOKIE_SECURE=false` por padrão e host padrão fixo `192.168.0.9` no config; documentar checklist de produção. Informativo.
- **SEC-006**: vários docs versionados contêm contexto de ambiente/credenciais (`docs/configuração mariaDB.md`, `docs/Criação do usuário admin.txt` — este último contém apenas placeholder). Recomenda-se revisão manual para remover qualquer dado real do histórico do Git. Atenção média, tarefa simples.
- **BUG-007**: `seed_demo.py` roda `drop_all` sem guarda de ambiente de produção (apenas aviso documentado). Recomenda-se guarda por variável de confirmação. Tarefa simples.
- **BUG-008**: `serial_number` de string vazia/espaços escapa da normalização de nulo; unicidade em string vazia pode colidir. Baixo.
- **BUG-009**: movimentação de mudança de condição grava `operator_name="Sistema"` em vez do usuário real. Baixo.
- **BUG-010**: `create_movement` muta o input Pydantic (`data.new_condition = ...`). Cheiro de estilo/correção. Baixo.
- **BUG-011**: `InventarioService.next_code` tem corrida na criação (a unique constraint garante integridade, mas o usuário vê erro). Baixo.
- **ARCH-001**: `routes.py` tem 2.163 linhas — dividir por módulo. **OPCIONAL/RECOMENDADO depois; NÃO necessário agora.**
- **DOC-001**: README diz "106 testes" — o real é 154; seções de instalação duplicadas. Tarefa simples.
- **DB-003**: ENUM nativo do MariaDB exige `ALTER TABLE` quando membros do enum são adicionados; comentários do código já reconhecem isso. Informativo.
- **DB-004**: sessões expiradas só são purgadas no login. Baixo.
- **FEAT-INFO**: depreciação fixa em 20%/ano — não configurável por categoria (classes patrimoniais de órgão público diferem); tratar como funcionalidade futura, não como bug.

---

## 9–12. Resumos: Segurança / Banco / UX / Regras de Negócio

**Segurança:** fundamentos fortes (hashing, sessões, RBAC, auditoria, open redirect, timing). Lacunas: tokens CSRF, headers, defaults de cookie seguro, revisão de credenciais em docs. Nada crítico.

**MariaDB:** engine/pool corretamente configurados; SQLite existe **apenas nos testes** (`conftest.py`, override via `DATABASE_URL_TEST`) — sem lógica SQLite no código de produção, sem PRAGMA. Lacunas reais: sem Alembic, Float para moeda, datetimes ingênuos, restrição de evolução de enums.

**UX:** o fluxo de conferência em campo força "buscar → filtrar lista" em vez de abrir a conferência do item diretamente (atrito na leitura de QR); mensagens de erro via query string na URL (sem flash messages); botões PDF/Excel podem dar 500 (BUG-002). No restante (estados vazios, tooltips, central de ajuda, CSS de impressão de etiquetas, tema escuro) é consistente — **nenhum redesign puramente estético se justifica**.

**Regras de negócio:** a *baixa* não tem fluxo (classificação de motivos, aprovação, documento, trava pós-baixa); ciclo do termo incompleto; movimentações de mudança de condição perdem a identidade do operador; depreciação não configurável.

---

## 13–14. Funcionalidades Faltantes e Redundantes

**Faltantes (backlog FEAT):**

| ID | Funcionalidade | Prioridade |
|---|---|---|
| FEAT-001 | Baixa patrimonial formal (motivos, aprovação, docs, trava) | P1 |
| FEAT-002 | Ciclo de vida do termo: rastreio de aceite/devolução | P1 |
| FEAT-003 | Gestão documental (NF, termos assinados, fotos por bem/movimentação/inventário) | P2 |
| FEAT-004 | Evidência fotográfica no inventário | P2 |
| FEAT-005 | Recuperação autônoma de senha | P2 |
| FEAT-006 | QR/etiquetas estáveis em relação ao host (codificar tombamento ou caminho estável) | P1 |
| FEAT-007 | Depreciação configurável por categoria + valor residual | P3 |
| FEAT-008 | Escopo por unidade/setor nas permissões (já adiado conscientemente) | P3 |
| FEAT-009 | Rate limiting por IP + orientação de enforcement HTTPS | P2 |

**Redundâncias:** triplicação da numeração de termos (BUG-003); `ReportService.get_filtered_assets` é um repasse fino (aceitável); duplicação no README; três permissões sem uso (RBAC-001). **Não foram encontradas telas duplicadas nem conceitos de domínio duplicados.**

---

## 15. Inventário × Relatório Contábil-Físico

| | Relatório Contábil-Físico | Módulo Inventário |
|---|---|---|
| Natureza | Listagem analítica pontual (todos os bens + depreciação + valor contábil) | Processo operacional formal de conferência em campo |
| Implementação | `generate_inventory_csv/excel/pdf` | `inventarios` + `inventario_itens` com snapshot da expectativa, resultado por item, conferente/data-hora, divergências, ocorrências de não previstos, trava de encerramento, consolidação, eventos próprios de auditoria, CSV/PDF/Excel próprios |
| Veredito | ÚTIL (incompleto enquanto Excel/PDF estiverem quebrados) | **COMPLETO** para o escopo projetado |

**Relação: complementaridade — separação correta.** A única sobreposição é a listagem de bens por baixo. Integração recomendada (futuro): a partir de um inventário encerrado, gerar as movimentações de divergência com um clique pelos fluxos existentes (nunca automático — manter a regra de ouro).

---

## 16. NÃO ALTERAR / PRESERVAR (lista obrigatória)

1. Modelo de sessão (tokens com hash, TTL/revogação server-side) e esquema PBKDF2, incluindo equalização de tempo e lockout.
2. RBAC deny-by-default, catálogo + seed idempotente, proteções do último admin, perfis de sistema não deletáveis.
3. Regras do AD: sem grupo mapeado → sem acesso e sem provisionamento; contas locais nunca migram; AD nunca define permissões.
4. **Imutabilidade das movimentações + a decisão de design de que `AssetUpdate` não pode tocar status/localização/custodiante.**
5. **Regra de ouro do inventário: a conferência nunca altera o cadastro do bem; o encerramento trava os itens.**
6. Trilha de auditoria: somente leitura, log de acessos negados, JSON antes/depois, zero credenciais.
7. Arquitetura em camadas (web/api → services → models) — evoluir, não reescrever.
8. Serviços de importação com prévia/confirmação; handlers 403/404; guarda de open redirect.
9. A suíte de 154 testes como base de regressão (após versioná-la — SEC-001).

---

## 17–19. Instantâneo de Priorização

| ID | Item | P | Alteração necessária? | SPEC? |
|---|---|---|---|---|
| SEC-001 | Versionar `tests/` (remover regra do gitignore) | P1 | NECESSÁRIO (tarefa) | NÃO |
| BUG-001 | Unificação de timezone | P1 | NECESSÁRIO | **SIM** |
| BUG-002 | Adicionar reportlab/openpyxl ao requirements | P1 | NECESSÁRIO (tarefa) | NÃO |
| BUG-005 | Travar edições após baixa | P1 | NECESSÁRIO | via SPEC-baixa |
| BUG-003 | Numeração de termos | P1 | NECESSÁRIO | **SIM** |
| SEC-002 | CSRF + headers | P2 | RECOMENDADO | **SIM** |
| DB-001/002 | Alembic + DECIMAL | P2 | RECOMENDADO | **SIM** |
| SEC-006 | Limpar credenciais de docs/histórico | P2 | RECOMENDADO (tarefa) | NÃO |
| BUG-004/007/008/010, DOC-001, RBAC-001 | Correções pequenas | P2/P3 | RECOMENDADO (tarefas) | NÃO |
| ARCH-001 | Dividir routes.py | P3 | OPCIONAL | NÃO |

---

## 20. Dependências

```text
SEC-001 (versionar testes)   →  todo o resto (segurança de regressão)
BUG-002 (dependências)       →  SPEC-relatorios
DB-001 (Alembic)             →  DB-002 (DECIMAL) → BUG-001 (migração de timezone)
SPEC-baixa (BUG-005)         →  FEAT-001 → FEAT-003 (documentos)
SPEC-termo (BUG-003/006)     →  FEAT-002 → FEAT-003
SPEC-qr (FEAT-006)           →  SPEC-inventario-evolucao (fluxo de campo)
```

---

## 21–22. SPECs Recomendadas e Critérios de Aceitação

```text
specs/
├── dados-temporais-migracoes/   (BUG-001, DB-001, DB-002)  P1
├── baixa-patrimonial/           (FEAT-001, BUG-005)         P1
├── termo-responsabilidade/      (FEAT-002, BUG-003/006)     P1
├── qr-etiquetas-estaveis/       (FEAT-006)                  P1
├── seguranca-http/              (SEC-002, FEAT-009)         P2
├── gestao-documental/           (FEAT-003, FEAT-004)        P2
├── inventario-evolucao/         (gerador de movimentação de divergência, evidências) P2
└── recuperacao-senha/           (FEAT-005)                  P2
```

Exemplos de critérios de aceitação (testáveis):

- **CA-001** Bem com status `BAIXADO` rejeita qualquer edição exceto notas (403/400 + registro de auditoria).
- **CA-002** A baixa exige: motivo classificado + justificativa + aprovador com permissão; gera documento; registra data/responsável.
- **CA-003** Duas movimentações simultâneas no mesmo segundo nunca produzem códigos de termo duplicados.
- **CA-004** Toda movimentação/evento de auditoria ordena corretamente na linha do tempo, independentemente do fuso do servidor.
- **CA-005** QR da etiqueta decodificado em outro host ainda resolve para o bem correto.
- **CA-006** POST de formulário sem token CSRF válido retorna 403; a auditoria registra a negação.
- **CA-007** O encerramento de inventário continua bloqueando novas conferências após qualquer das mudanças acima (regressão — os testes existentes devem continuar passando).

---

## 23. Ordem Recomendada de Implementação

```text
FASE 0  Baseline: versionar tests/, .env.example, limpar docs, correções do README   (tarefas)
FASE 1  HOTFIXES: dependências do requirements, sessões do /health, política de timezone (tarefas + SPEC-dados-temporais)
FASE 2  SPEC-seguranca-http (CSRF, headers, defaults de cookie/HTTPS)
FASE 3  SPEC-baixa-patrimonial + SPEC-termo-responsabilidade
FASE 4  SPEC-qr-etiquetas-estaveis
FASE 5  SPEC-gestao-documental + SPEC-inventario-evolucao
FASE 6  SPEC-recuperacao-senha, rate limiting, DB-002 (DECIMAL via Alembic)
FASE 7  ARCH-001 (divisão de rotas), FEAT-007 (depreciação configurável), FEAT-008 (escopos)
```

---

## 24–25. Riscos e Conclusão

**Riscos:**

1. A migração de timezone toca linhas existentes — exige backup + plano Alembic antes de executar;
2. As SPECs de baixa/termo alteram o modelo de movimentação — mitigar com a suíte existente de 154 testes;
3. Mudar o conteúdo do QR invalida etiquetas já impressas — programar reimpressão em lote;
4. O histórico do Git pode conter credenciais — tratar antes de qualquer remoto público.

**Conclusão:** o código está **saudável e preservável**. O caminho correto é exatamente para o que a auditoria foi desenhada: corrigir primeiro as tarefas P1 (são pequenas), depois conduzir SPEC por SPEC — baixa → termo → QR → documentos — com a suíte de testes versionada como rede de segurança em cada etapa. **Nenhuma reescrita se justifica em nenhum ponto.**

---

## Fluxo de Trabalho Proposto

```text
AUDITORIA   →  BACKLOG  →  PRIORIZAÇÃO  →  SPEC  →  PLANO
                                                   ↓
VALIDAÇÃO  ←  TESTES  ←  IMPLEMENTAÇÃO  ←  TAREFAS ←┘
```

**PRINCÍPIO FUNDAMENTAL DO PROJETO:**

> O SisPatrimônio Pro existente é a base a ser preservada. O objetivo não é reconstruí-lo, mas corrigir, aprimorar e evoluir o sistema de forma incremental, controlada, rastreável e segura.
