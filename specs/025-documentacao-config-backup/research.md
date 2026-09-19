# Research: Correção da Documentação da Configuração de Backup

**Feature**: 025 | **Data**: 2026-09-19
**Fonte**: relatório da Feature 024 (`specs/024-auditoria-config-backup/relatorio.md` — achados AT-1/AT-2/AT-3) + código verificado nesta sessão. **Nada é herdado cegamente**: as passagens-alvo foram relidas hoje e estão citadas literalmente abaixo.

---

## R1 — Target AT-1: `docs/GUIA_DE_MANUTENCAO.md` (~L111–113)

**Passagem atual (literal)**: "…A configuração operacional do backup (features 021/022) fica na tabela `backup_config` e é administrada pelo modal aberto pelo botão ⚙ no topo direito da página de Backups (`templates/admin/backups.html`); as env `BACKUP_*` são fallback da primeira inicialização (service: `backup_config_service.py`)."

**Problema (024/AT-1)**: "fallback da primeira inicialização" — impreciso; o fallback é por campo, a cada resolução, enquanto o campo persistido estiver indefinido (`backup_config_service.py:122–185`).

**Correção proposta (texto-alvo)**:
> "…A configuração operacional do backup (features 021/022) fica na tabela `backup_config` (singleton `id=1`) e é administrada pelo modal aberto pelo botão ⚙ no topo direito da página de Backups (`templates/admin/backups.html`). As variáveis de ambiente `BACKUP_*` funcionam como **fallback por campo** durante a resolução da configuração efetiva (`get_effective_config()`): valem quando o respectivo campo persistido está indefinido (`None` = "não definido") e também no bootstrap/fallback de boot do scheduler (ver `ARQUITETURA_E_MANUTENCAO.md`). Particularidade: o campo `auto_enabled` é não-nulo (`models/backup_config.py`), portanto `BACKUP_AUTO_ENABLED` não é reconsultado dinamicamente depois que a linha existe — vale na instalação nova e no fallback de boot (service: `backup_config_service.py`)."

**Rationale**: substitui a única afirmação factualmente incorreta identificada pela 024 por descrição fiel ao código (FR-004/FR-006/FR-009); consolida AT-1+AT-3 no ponto onde um mantenedor procura "onde ficam as configurações".

**Alternatives considered**: reescrever a seção inteira — rejeitado (NFR-003: preservar o texto correto; a frase final é o único problema).

## R2 — Target AT-2 no `README.md` (~L972–973)

**Passagem atual (literal)**: "As variáveis de ambiente abaixo continuam valendo como **fallback** na primeira inicialização e em deploys automatizados. Precedência única por campo: **valor persistido (tela) → variável de ambiente → default da 020**:"

**Problema (024/AT-2)**: a precedência documentada omite o fallback de boot do scheduler; e "fallback na primeira inicialização" repete a imprecisão do AT-1 (o fallback por campo é dinâmico).

**Correção proposta (texto-alvo)**:
> "As variáveis de ambiente abaixo funcionam como **fallback por campo** enquanto o campo correspondente não estiver persistido (e continuam úteis para deploys automatizados que precisem pré-definir valores). Precedência única por campo, aplicada por `get_effective_config()`: **valor persistido (tela) → variável de ambiente → default da 020**. **Exceção (fallback de boot do scheduler)**: se a leitura da configuração efetiva falhar (ex.: banco indisponível), o scheduler mantém o **snapshot anterior**; sem snapshot anterior, usa o **bootstrap** por env/default até a próxima leitura bem-sucedida — mecanismo de segurança, não caminho normal."

**Rationale**: corrige a imprecisão e acrescenta o AT-2 exatamente onde a precedência é apresentada (FR-004/FR-005/FR-007); preserva a tabela de variáveis seguinte (fiel — 024 veredicto FIEL).

**Alternatives considered**: incluir o fallback de boot como "4º nível" da precedência — rejeitado: é caminho de exceção, não nível normal; apresentá-lo como nível criaria a impressão de dupla fonte (briefing §13).

## R3 — Target AT-2/AT-3 complementar: `README.md` (nota após a tabela das variáveis)

**Passagem atual (literal)**: "Valores inválidos não derrubam o sistema: caem no default seguro com registro no log técnico." (L994)

**Correção proposta (inserir após)**:
> "**Particularidade de `BACKUP_AUTO_ENABLED`**: o campo persistido `auto_enabled` é **não nulo** — depois que a linha de configuração existe, a variável de ambiente não é reconsultada dinamicamente para esse campo (diferente dos demais, que aceitam env enquanto o campo persistido estiver indefinido). Ela continua valendo na instalação nova (default `false` — o sistema nasce desativado) e no fallback de boot descrito acima."

**Rationale**: AT-3 documentada no lugar de maior visibilidade, junto às demais regras das variáveis (FR-006/FR-013); factual conforme `models/backup_config.py:23` e `backup_config_service.py:155`.

## R4 — Target AT-2 complementar: `docs/ARQUITETURA_E_MANUTENCAO.md` (~L1215)

**Passagem atual (literal, trecho final)**: "…evento `BACKUP_CONFIGURACAO_ALTERADA` (before/after), snapshot renovado por tick no `backup_scheduler` (aplicação sem reinício)".

**Correção proposta (extensão)**:
> "…evento `BACKUP_CONFIGURACAO_ALTERADA` (before/after), snapshot renovado por tick no `backup_scheduler` (aplicação sem reinício; **fallback de boot**: em falha de leitura o scheduler mantém o snapshot anterior ou usa env/default se ainda não houver snapshot)"

**Rationale**: o registro técnico de fluxos deste doc fica completo com o caminho de exceção (FR-005), no ponto onde o mecanismo é descrito para mantenedores; mínimo invasivo (uma cláusula).

**Alternatives considered**: nova seção dedicada — rejeitada (NFR-003; o doc é um inventário, não um tutorial).

## R5 — Verificação de que NÃO há outros pontos incorretos

**Decision**: varredura confirmou que não existem outras afirmações "primeira inicialização" ou de fonte concorrente nos 3 arquivos-alvo: `README.md:972–995` (precedência FIEL — 024 §7 itens 1–6, 8, 9; tick 30 s `:987`; catch-up `:988`; retenção `:995`), `docs/ARQUITETURA_E_MANUTENCAO.md:264,1215` (FIEL), `docs/GUIA_DE_MANUTENCAO.md:113` (única imprecisão). Portanto o escopo de edição é **exatamente** R1–R4 (briefing §25: alterar somente o que é incorreto/incompleto).

**Rationale**: FR-015/NFR-003 — evita reescrita desnecessária; registra a base factual do "não alterar todos obrigatoriamente".

## R6 — Consolidação do fluxo (US4) — onde encaixar sem duplicar

**Decision**: as 8 respostas do briefing §38 já estão hoje distribuídas e fiéis: "onde configuro / onde fica salvo" (README `:972`, GUIA `:108–113`), "quem resolve" (`get_effective_config` citado no GUIA R1-corrigido e no ARQUITETURA `:1215`), "quem usa" (README `:987–995`; ARQUITETURA `:1215`), "para que serve config.py" (README R2-corrigido), "dupla fonte" (explícita no R2: "precedência única por campo" + exceção única documentada), "reiniciar/30 s" (README `:987` "a cada 30 s"; ARQUITETURA `:1215` "sem reinício"), "banco falhar" (R2). As edições R1–R4 fecham as lacunas; **nenhuma seção nova é criada**.

**Rationale**: NFR-003 — consolidação por correção pontual, não por reestruturação; risco de contradição interna diminui (briefing §34).

## R7 — Preservações obrigatórias (o que NÃO muda)

**Decision**: intocados nesta feature: tabela das 8 variáveis do README (`:974–981` — veredicto FIEL da 024), seção de comportamento do scheduler/catch-up/retenção (`:987–995`), o restante do GUIA e do ARQUITETURA, todos os arquivos de `app/`, `tests/`, `specs/020–022` (contexto histórico), `app/config.py` (comentário interno permanece — briefing §26).

**Rationale**: briefing §25/§40; NFR-003.

## R8 — Validação e relatório final

**Decision**: validação por: (1) `git diff --stat` = somente os 3 arquivos do FR-002; (2) busca por resquícios: `rg -n "primeira inicialização" README.md docs/` não retorna afirmação incorreta sobre `BACKUP_*` (a frase pode existir em outro contexto legítimo — verificar caso a caso); (3) `rg -n "BACKUP_AUTO_ENABLED" README.md docs/` retorna o texto com a particularidade AT-3; (4) conferência cruzada das afirmações novas com o código (trechos da 024 revalidados); (5) relatório final em `specs/025-documentacao-config-backup/relatorio.md` (decidido; Assumption 4 resolvida) com os 13 itens do briefing §39.

**Rationale**: FR-017/FR-018; briefing §34/§36/§39.
