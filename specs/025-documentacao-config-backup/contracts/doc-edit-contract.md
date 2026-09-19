# Contract: Edições Documentais Permitidas (Feature 025)

**Feature**: 025 | **Data**: 2026-09-19
Este contrato fixa o **universo fechado de edições** desta feature documental (briefing §25/§40; spec FR-002/NFR-003). Qualquer edição fora deste contrato viola o escopo.

---

## 1. Arquivos editáveis e edições autorizadas

### 1.1 `docs/GUIA_DE_MANUTENCAO.md` (AT-1 + AT-3)

- **Localização**: seção "Onde ficam as configurações?", parágrafo final (~L111–113).
- **Edição E1**: substituir a frase "as env `BACKUP_*` são fallback da primeira inicialização (service: `backup_config_service.py`)" pelo texto de correção do research **R1** (fallback por campo dinâmico + bootstrap de boot + particularidade do `auto_enabled`).
- **Invariante**: o restante do parágrafo e da seção permanece idêntico.

### 1.2 `README.md` (AT-1/AT-2 + AT-3)

- **Edição E2**: substituir o parágrafo introdutório da precedência (~L972–973, "As variáveis de ambiente abaixo continuam valendo como **fallback** na primeira inicialização e em deploys automatizados. Precedência única por campo: …") pelo texto do research **R2** (fallback por campo + precedência atribuída a `get_effective_config()` + parágrafo do fallback de boot como exceção).
- **Edição E3**: inserir, após "Valores inválidos não derrubam o sistema: caem no default seguro com registro no log técnico." (~L994), a nota do research **R3** (particularidade de `BACKUP_AUTO_ENABLED` — campo não nulo).
- **Invariante**: a tabela das 8 variáveis (`:974–981`) e as seções de comportamento/catch-up/retenção (`:987–995`) permanecem **idênticas**.

### 1.3 `docs/ARQUITETURA_E_MANUTENCAO.md` (AT-2)

- **Edição E4**: estender o registro do fluxo de configuração (~L1215) com a cláusula do research **R4** ("**fallback de boot**: em falha de leitura o scheduler mantém o snapshot anterior ou usa env/default se ainda não houver snapshot").
- **Invariante**: nada mais nesta linha/seção é alterado.

## 2. Edições PROIBIDAS (mesmo parecendo melhorias)

1. Alterar qualquer arquivo fora dos 3 acima (inclui `app/**`, `tests/**`, `.env`, `specs/020–022`, `docs/*` outros).
2. Alterar a tabela das 8 variáveis do README (valores/defaults/ícones).
3. Alterar `app/config.py` — inclusive comentários (briefing §26; a exceção de "inconsistência factual grave" NÃO se aplica: o comentário é coerente com o código).
4. Criar seção/documento novo ou reestruturar seções existentes.
5. Tratar `BACKUP_*` como segredo ou citar qualquer credencial.
6. Sugerir remoção de constantes, alteração de modelo (`auto_enabled` nullable) ou de lógica (tick, snapshot, precedência).
7. Apresentar o fallback de boot como 4º nível da precedência normal (é exceção de segurança).
8. Usar "config.py é a fonte efetiva", "env vale só na primeira inicialização" ou qualquer sugestão de fonte concorrente.

## 3. Invariantes de conteúdo (toda frase nova DEVE)

- Ter correspondência verificável no código atual: precedência por campo (`backup_config_service.py:122–185`), fallback de boot (`backup_scheduler.py:107–124`), `auto_enabled` não-nullable (`models/backup_config.py:23` + leitura direta `backup_config_service.py:155`), tick 30 s (`backup_scheduler.py:64`), defaults (`config.py:67–87`).
- Distinguir **caminho normal** (persistido → env → default) de **exceção** (fallback de boot).
- Manter a separação parâmetros operacionais × credenciais (Constitution VI).
- Ser em português técnico claro, no estilo dos docs existentes.

## 4. Critério de conclusão do contrato

- [ ] E1–E4 aplicadas (somente elas).
- [ ] `git diff --stat` = exatamente `README.md`, `docs/GUIA_DE_MANUTENCAO.md`, `docs/ARQUITETURA_E_MANUTENCAO.md`.
- [ ] Nenhum resquício de afirmação incorreta (verificação R8 do research).
- [ ] Todas as frases novas conferem com o código atual.
