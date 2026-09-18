# Research: Backup Manual — Briefing Completo

**Feature**: 016-backup-manual-completo | **Data**: 2026-09-17
**Entrada**: spec.md (gap 015→briefing) + verificação de código (arquivo/linha citados)

---

## R1. Atomicidade: arquivo temporário `.part` → renomear (§27 do briefing)

**Decisão**: `generate_backup` grava o gzip em `<BACKUP_DIR>/<nome-base>.part` (nome-base único por microssegundos) e só **renomeia** para `<nome-base>.sql.gz` **após** a validação completa (dump OK + gzip fechado + tamanho > 0 + SHA-256 calculado). Em qualquer falha, o `.part` é removido.

**Rationale**: atende literalmente o §27 ("arquivo temporário → backup concluído → renomear para nome final"); como a listagem só reconhece arquivos que casam o regex final (`.sql.gz`/`.sql`), o `.part` nunca é listável nem baixável — por construção, sem estado extra. Renomeação no mesmo diretório/filesystem é atômica em POSIX. O fake executor dos testes grava no caminho recebido — o teste de atomicidade verifica que `.part` não existe ao final e que o arquivo final nasce completo.

**Alternativas rejeitadas**: gravar direto no nome final (janela de parcial — hoje mitigada só pela regex, mas o briefing exige o padrão temporário); diretório `tmp/` separado (renomeação entre filesystems não é atômica; complexidade desnecessária).

---

## R2. Compressão gzip via stdlib Python, em streaming (§15, §32)

**Decisão**: o fluxo usa dois temporários com o **mesmo nome-base único**: dump nativo → `<base>.part` (SQL) → compressão streaming (`gzip.open` + cópia por blocos de 1 MB) → `<base>.part.gz` → validação + SHA-256 → **renomear** para `<base>.sql.gz`. Ambos os temporários ficam fora do regex final e são removidos/renomeados ao fim — nunca há parcial listável (**esquema padronizado conforme o contract — remediação I1**).

**Rationale**: o briefing (§15) pede compressão **se não introduzir complexidade** — `gzip.open` da stdlib não adiciona dependência nem assume binário externo (§32: não assumir ferramenta; alternativa `mysqldump | gzip` dependeria de `gzip` no PATH, quebrando a regra de não-assunção). Streaming mantém memória constante para dumps grandes. Proporção típica de dump SQL textual: ~5–10× menor.

**Alternativas rejeitadas**: `gzip` binário via subprocess (dependência externa); zip (§15 cita `.sql.gz`); sem compressão (perde a melhoria pedida).

---

## R3. SHA-256 calculado pós-conclusão, derivado do arquivo (§16)

**Decisão**: `hashlib.sha256` em streaming sobre o `.sql.gz` final, **antes** da renomeação/registro; o hash viaja no evento `BACKUP_CRIADO` (`new_data.sha256`) e na listagem (calculado on-demand por arquivo, com cache implícito de custo baixo — listagem é pequena).

**Rationale**: §16 pede "informação de integridade como SHA-256" após validar o processo. Derivar do arquivo (não persistir em tabela) mantém o zero-DDL da 015 e a regra §10/§31 (sem tabela para o que se obtém dos arquivos). On-demand: um hash de ~dezenas de MB por listagem é custo aceitável para tela administrativa; sem estado duplicado dessincronizável.

**Alternativas rejeitadas**: tabela de metadados (zero-DDL vetado); hash no nome do arquivo (§14 exige nome identificável por data/hora, não hash); SHA-256 só no log (não exibível na tela).

---

## R4. Integridade exibida: coluna "Integridade" com OK / — (§18)

**Decisão**: na listagem, cada backup exibe `Integridade` = **OK** quando (a) o arquivo é legível, (b) o SHA-256 da listagem casa com recomputação leve (tamanho > 0 e, para `.sql.gz`, o `gzip` abre e lê o trailer com sucesso) e (c) existe checksum referenciado; **—** para backups `.sql` antigos da 015 (sem checksum) e para casos onde a verificação não se aplica.

**Rationale**: §18 exige a coluna; §16 limita a validação ao que foi implementado (checksum "quando implementado"). Verificação completa por recomputação em cada render seria redundante — a listagem calcula o hash uma vez (R3) e compara com o trailer válido do gzip; arquivos corrompidos falham na leitura e exibem status de erro controlado (CORROMPIDO), nunca "OK".

**Alternativas rejeitadas**: coluna de "válido/inválidos" complexa com testes de dump (§16 veda ferramenta de restauração nesta feature).

---

## R5. Evento de falha `BACKUP_FALHA` (§25) — constante aditiva

**Decisão**: nova constante `ACTION_BACKUP_FAILED = "BACKUP_FALHA"` + rótulo `"Backup Falhou"` em `audit_service.py` (precedente do par `ACTION_BACKUP_CREATED`/rótulo). A falha passa a gravar `action=BACKUP_FALHA` (resultado FALHA); sucesso segue `BACKUP_CRIADO`/SUCCESS; download segue `BACKUP_DOWNLOAD`.

**Rationale**: o briefing §25 define o modelo literal de eventos (BACKUP_CRIADO/SUCESSO, BACKUP_FALHA/FALHA, BACKUP_DOWNLOAD). A 015 usava `BACKUP_CRIADO`+`result=FAILURE` — equivalente funcional, mas o briefing pede o rótulo próprio. Mudança aditiva: nenhum evento histórico é alterado (trilha imutável, Princípio IX); a tela de auditoria lista a nova ação automaticamente (get_distinct_actions).

**Alternativas rejeitadas**: manter FAILURE em `BACKUP_CRIADO` (não literal ao briefing); renomear eventos antigos (vedado — trilha imutável).

---

## R6. Log técnico: `logging.getLogger(__name__)` no service (§26)

**Decisão**: instrumentar `backup_service.py` com o logger padrão do projeto (precedente `ad_service.py:41`): `logger.info` no início (sem dados sensíveis), `logger.info` na conclusão (duração, tamanho, sha256), `logger.warning/error` em falhas (exceção/exit code — **sem** stderr completo que possa conter o comando, sem credenciais).

**Rationale**: §26 manda usar o sistema de logging existente — `app/logging_config.py` já fornece rotativo (`data/logs/app.log`, 5 MB × 5). O logger de módulo cai automaticamente no handler de root configurado. Nenhum segundo sistema de logging é criado; nenhum segredo no log (a mensagem de dump falho da 015 já é sanitizada — o log registra apenas a exceção controlada `BackupError`).

**Alternativas rejeitadas**: log de arquivo próprio `backup.log` (vedado — mecanismo paralelo); registrar stderr do mysqldump (risco de segredo/comando).

---

## R7. Compatibilidade de transição: `.sql` (015) e `.sql.gz` (016) coexistem

**Decisão**: `_BACKUP_NAME_RE` passa a aceitar **ambos** os sufixos (`\.sql(\.gz)?$` com grupos capturados); listagem/janelas/`get_backup_path` funcionam para os dois; a coluna Integridade exibe **—** para `.sql` antigos (sem checksum registrado) e OK para `.sql.gz` novos; download serve qualquer um (rota intocada).

**Rationale**: a 015 está em produção — pode haver backups reais `.sql` no repositório. A quebra de compatibilidade forçaria descarte/renomeação manual. Regra de mínima alteração (§36): um regex, não uma migração.

**Alternativas rejeitadas**: converter antigos on-the-fly (escopo novo desnecessário); descontinuar `.sql` imediatamente (quebra repositório real).

---

## R8. `.part` com nome-base único e fora do padrão final (§20, §27)

**Decisão**: o `.part` herda o nome-base único (microssegundos) — dois backups simultâneos nunca competem pelo mesmo temporário; o regex da listagem não casa `.part` (termina em `.part`, não em `.sql.gz`), e o download continua validando apenas nomes finais.

**Rationale**: §20 pede evitar sobrescrita concorrente "com nomes únicos baseados em data/hora" — o mecanismo existente (microssegundos) já resolve; estendê-lo ao `.part` é coerente e sem lock/queue (§20 veda mecanismo complexo). A checagem de existência prévia do nome final permanece como segunda barreira (BV-3 da 015).

**Alternativas rejeitadas**: lock de arquivo/fila (vedado §20); UUID no temporário (nome único já garantido; hash não: timestamp).

---

## R9. Testes A–J (§34) — mapeamento e lacunas na suíte 015

**Decisão**: a suíte 015 já cobre A (autorizado), B (não autorizado), C/D (download), E (inexistente), F (path traversal), parte de G (falha sem falso sucesso) e parte de H (múltiplos no service). Incrementos de teste: **G literal** (falha → `BACKUP_FALHA`), **H via web** (2 gerações pela rota, nomes distintos, listagem com 2), **I** (arquivo legível, gzip válido, SHA-256 recomputado == exibido), **J** (regressão completa), **novos**: atomicidade (`.part` não existe ao final; nunca listável), compatibilidade `.sql` antigo listável/baixável.

**Rationale**: §34 lista os testes obrigatórios; mapear evita duplicar o que já existe (regra de mínima alteração) e mostra exatamente o que falta. O fake executor grava dump determinístico; o SHA-256 do teste é recomputado do arquivo gravado e comparado ao retorno/auditoria.

**Alternativas rejeitadas**: reescrever a suíte 015 (vetado — Princípio I); testar o gzip com ferramenta externa (§32).
