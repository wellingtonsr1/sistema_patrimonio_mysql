# Contract: Relatório de Auditoria (`relatorio.md`)

**Feature**: 024 | **Data**: 2026-09-19
**Natureza**: a feature não expõe interface alguma ao usuário (nenhuma rota, CLI ou API nova). O único "contrato" é a **estrutura obrigatória do relatório de diagnóstico** — artefato entregue em `specs/024-auditoria-config-backup/relatorio.md`. Este documento fixa esse contrato (briefing §28–§31; spec FR-016–FR-019).

---

## 1. Contrato de conteúdo

### §1.1 Seções obrigatórias (12 — briefing §30)

1. **Resumo executivo** — poucas linhas: a arquitetura atual está correta? Veredito global.
2. **Fonte efetiva da configuração** — diagrama do fluxo **real** (não o documentado), com `arquivo:linha` em cada seta.
3. **Análise do config.py** — para cada uma das 8 constantes: `Nome / Uso encontrado / Arquivo / Função / Classificação (A–H) / Fallback? / Configuração efetiva? / Conclusão`.
4. **Análise do scheduler** — como ele obtém, com evidência: ativação, frequência, horário, dia da semana.
5. **Análise da retenção** — como obtém os 4 valores, com evidência.
6. **Análise da tela** — fluxo real de persistência (rota → service → tabela → leitura → scheduler/retention).
7. **Análise de precedência** — `DOCUMENTADO` vs `REAL ENCONTRADO`; divergências destacadas.
8. **Dupla fonte de verdade** — `Existe / Não existe` + justificativa (inclui cenários-limite: fallback de boot, env válida vencendo default — nunca o persistido).
9. **Cache e atualização** — mecanismo, renovação, janela máxima de desatualização, aplicação sem reinício; comportamento após reinício.
10. **Testes existentes** — inventário (`test_backup_config.py`, `test_backup_automatico.py`, `test_backup_retencao.py`, `test_backup_monitoramento.py`) e cobertura por tema (persistida / fallback / defaults / precedência / tela / scheduler / retenção / inválidos / instalação nova).
11. **Problemas encontrados** — cada achado com rótulo: `OK / ATENÇÃO / INCONSISTÊNCIA / RISCO / BLOQUEADOR`.
12. **Recomendação** — SOMENTE o que deveria ser corrigido em tarefa futura; nada implementado nesta feature.

### §1.2 Tabela das variáveis de ambiente (briefing §18)

Uma linha por variável: `Variável | Necessária? | Função atual | Fonte efetiva | Observação`. Regra: não concluir "desnecessária" apenas por existir configuração na tela — distinguir "não usada diretamente" de "desnecessária" (considerar bootstrap, fallback, instalação nova, compatibilidade, testes).

### §1.3 Respostas-chave (briefing §28 — veredito SIM/NÃO/PARCIAL + evidência)

1. A configuração da tela é a fonte efetiva?
2. `config.py` é apenas fallback?
3. Existe dupla fonte de verdade?
4. O scheduler usa a configuração da tela?
5. A retenção usa a configuração da tela?
6. `get_effective_config()` realmente centraliza a configuração?
7. Alguma constante de `config.py` pode ser removível? (rótulo: `POTENCIALMENTE REMOVÍVEL` / `DEVE SER MANTIDA COMO FALLBACK` — com justificativa; nada é removido)

### §1.4 Critérios de conclusão (briefing §31 — 14 itens, cada um com evidência `arquivo:linha`)

- [ ] Onde a configuração da tela é persistida
- [ ] Onde a configuração efetiva é lida
- [ ] Se `get_effective_config()` existe e funciona como documentado
- [ ] Se o scheduler utiliza a configuração efetiva
- [ ] Se a retenção utiliza a configuração efetiva
- [ ] Qual é a função real das constantes de `config.py`
- [ ] Se as variáveis de ambiente são fallback ou configuração efetiva
- [ ] Se existe dupla fonte de verdade
- [ ] Se existe cache
- [ ] Se alterações da tela são aplicadas sem reinício
- [ ] O que acontece em instalação nova sem `backup_config`
- [ ] Se os defaults são coerentes com a regra atual
- [ ] Se existem testes para a precedência
- [ ] Se existe risco de a configuração da tela ser ignorada

### §1.5 Classificação de achados (briefing §29)

| Rótulo | Critério |
|---|---|
| OK | Implementação compatível com a arquitetura documentada |
| ATENÇÃO | Comportamento que merece revisão, mas não quebra a arquitetura |
| INCONSISTÊNCIA | Implementação real diverge da regra documentada |
| RISCO | Possibilidade de a configuração da tela não ser respeitada / dupla fonte |
| BLOQUEADOR | A configuração da tela não controla efetivamente o comportamento |

## 2. Contrato de forma (invariáveis de qualidade)

- **Evidência**: toda afirmação com `arquivo:linha` + trecho citado; afirmação não verificável marcada como tal (nunca apresentada como fato) — NFR-002/FR-019.
- **Neutralidade**: nenhuma recomendação de remoção sem análise bootstrap/fallback/instalação nova/compatibilidade/testes (NFR-003).
- **Segurança**: nenhuma credencial/segredo citado; valores de env descritos por função e default, não por conteúdo real de `.env` (Constitution VI).
- **Zero diff**: o relatório não vem acompanhado de nenhuma alteração de produção; verificação `git status --porcelain` limpa fora de `specs/` + `.specify/feature.json` (SC-001).
- **Idioma**: português técnico claro (padrão do projeto).
- **Falsos positivos**: casos excluídos da classificação (ex.: `ACTION_BACKUP_AUTO_SUCCESS/FAILED` — rótulos de auditoria, research R7) listados com justificativa, provando exaustão da varredura.

## 3. Contrato do processo de auditoria (o que a execução DEVE/NÃO DEVE fazer)

**DEVE**:
- Reconfirmar linha a linha o mapa preliminar do plan (a auditoria não herda conclusões — spec US1–US3).
- Cobrir 100% dos matches das 8 constantes + termos (`get_effective_config`, `backup_config`, `BackupConfig`, scheduler/schedule/retention/cleanup/pre_restore).
- Registrar condições de exceção com a condição exata (ex.: fallback de boot L117–124 — "Falha ao ler configuração efetiva — mantendo snapshot anterior", L107–109).
- Registrar a janela de desatualização do snapshot (tick de 30 s — confirmar no código do loop).

**NÃO DEVE**:
- Executar a aplicação, suíte de testes, migrations ou qualquer acesso de escrita a banco.
- Alterar qualquer arquivo de produção (código, template, docs, testes, `.env`).
- Implementar qualquer correção dos problemas encontrados.
- Declarar variável desnecessária sem a análise do §1.2.
