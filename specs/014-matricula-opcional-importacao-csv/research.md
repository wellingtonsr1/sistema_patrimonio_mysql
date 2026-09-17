# Research: Matrícula Opcional na Importação de Colaboradores via CSV

**Feature**: 014-matricula-opcional-importacao-csv | **Data**: 2026-09-17
**Entrada**: spec.md + análise de código verificada (arquivo/linha citados)

> Todas as decisões abaixo foram verificadas contra o código real. Nenhuma biblioteca ou mecanismo novo é introduzido sem precedente no projeto.

---

## R1. Reutilizar o gerador único da feature 010 — fachada pública mínima

**Decisão**: expor o gerador existente via **fachada pública** `CustodianService.generate_available_provisional_code(db)` que chama `_next_provisional_code(db)` e repete até achar código não existente (`get_by_registration_code` — já existente), retornando o `PROV-%06d`.

**Rationale**: a spec (FR-002) proíbe segunda implementação. `_next_provisional_code` é estático e privado; a fachada de 1 método o torna consumível pelo importador **sem alterar sua lógica interna** e sem quebrar chamadores atuais do método privado. A repetição com `get_by_registration_code` replica no importador o loop pré-inserção que o `create` já faz (linha "colisão determinística"), mantendo o mesmo comportamento. A garantia final segue sendo a constraint UNIQUE (ver R7).

**Alternativas consideradas**: (a) importar e chamar `_next_provisional_code` diretamente do importador — acopla ao detalhe privado e dispensa a verificação pré-inserção; (b) duplicar a contagem no importador — **vetado** (FR-002); (c) mover a lógica do `create` para usar também a fachada — refatoração além do escopo.

---

## R2. Ponto exato da geração: `execute_custodian_import`, na criação nova

**Decisão**: na execução, para cada linha com `registration_code` vazio (após trim), gerar a provisória **no ramo de criação nova** (antes de `db.add`), com o mesmo tratamento de exceção do loop atual.

**Rationale**: `execute_custodian_import` cria colaboradores diretamente por modelo (verificado) — é o único ponto onde a matrícula efetiva é definida. Gerar ali mantém o fluxo de erro/`continue`/commit parcial intacto (regra do briefing: não alterar transação/rollback).

**Alternativas consideradas**: (a) gerar no `parse` — viola FR-007 (fabricaria números antes da execução, possivelmente diferentes dos efetivos); (b) delegar a criação da linha a `CustodianService.create` — mudaria validações de e-mail/duplicidade e semântica de transação do importador (vetado: não alterar regras existentes); (c) gerar no preview — idem (a).

---

## R3. Preview: matrícula vazia NÃO é erro nem duplicata por matrícula

**Decisão**: `preview_custodian_import` mantém o registro na lista de previews; para linha sem matrícula, `registration_code` permanece vazio e a **duplicata passa a ser verificada somente por e-mail** (consulta por matrícula vazia é inócua e é removida); adiciona flag `will_generate_provisional: true` nas entradas sem matrícula (não usada pelo template atual — extensão aditiva, sem mudança visual obrigatória).

**Rationale**: com a obrigatoriedade removida em `_validate_row`, a linha chega ao preview; buscar `_find_by_registration_code(db, "")` retornaria falso positivo para outro registro vazio (que não existe, pois a linha vazia nunca é criada com código vazio). A duplicata por e-mail permanece — regra atual preservada. FR-007: sem fabricar número antecipado; a indicação textual fica a cargo da UI/documentação (US4/AS1).

**Alternativas consideradas**: (a) manter a busca por matrícula vazia — sem efeito prático, consulta inútil; (b) exibir número projetado no preview — viola FR-007.

---

## R4. `_validate_row`: remover SOMENTE a regra de matrícula

**Decisão**: excluir o bloco `if not row.get("registration_code", "").strip(): errors.append("... matricula é obrigatória")` (verificado, ~linha 120). Todas as demais validações permanecem byte-a-byte: nome, e-mail (obrigatório + regex), cargo, setor, `ativo` (valores inválidos).

**Rationale**: a única mudança de regra autorizada pela spec é "ausência deixou de ser erro" (FR-001/FR-008). Validações informadas (normalização trim+upper em `_normalize_registration_code`, unicidade, duplicidade) seguem nos pontos atuais.

**Alternativas consideradas**: nenhuma — remoção cirúrgica do único bloco de obrigatoriedade de matrícula.

---

## R5. Transporte `csv_rows` (preview → confirm): nenhuma alteração necessária

**Decisão**: manter o transporte atual (textarea oculto `csv_data` com `{{ csv_rows | tojson }}` reparseado em `confirm_import_custodians` — verificado em `routes.py:1130`).

**Rationale**: JSON serializa string vazia como `""` e o campo ausente como chave ausente — ambos chegam à execução como ausência (execução já usa `row.get("registration_code", "")`). A regra por linha (FR-005) sobrevive ao transporte sem qualquer mudança nas rotas.

**Alternativas consideradas**: nenhuma — evidência de que `routes.py` não precisa ser tocado.

---

## R6. Unicidade dentro da mesma importação (várias linhas sem matrícula)

**Decisão**: a geração por linha usa a fachada R1 imediatamente antes de cada `db.add` + `db.flush()` (flush já existe no loop). Como o flush grava a linha na transação, a consulta do gerador na linha seguinte já enxerga a provisória anterior → sequencial único por colaborador (Teste 7 do briefing).

**Rationale**: mesmo mecanismo de unicidade do cadastro individual (sequencial + UNIQUE + retentativa — R7); nenhuma contagem paralela.

**Alternativas consideradas**: (a) pré-alocar N sequenciais antes do loop — duplicaria contagem (vetado); (b) depender só da UNIQUE (sem flush prévio) — geraria colisões evitáveis dentro da própria importação.

---

## R7. Concorrência: reutilizar a estratégia existente; lacunas documentadas, não corrigidas

**Decisão**: manter a estratégia do cadastro individual — maior `PROV-` bem-formado + 1, verificação pré-inserção e constraint UNIQUE como garantia final. No importador, a colisão cai no except genérico do loop (erro "Linha N: ..." + commit parcial — comportamento existente). A janela teórica de corrida entre dois processos (consulta→insert) é herdada, **documentada e não corrigida** (diretriz do briefing).

**Rationale**: FR-002 exige o mecanismo existente; a spec (Edge Cases) veda corrigir vulnerabilidades de concorrência nesta feature.

**Alternativas consideradas**: (a) lock/`SELECT ... FOR UPDATE` — mudaria o mecanismo compartilhado (vetado, fora de escopo); (b) retentativa específica no importador — nova regra não prevista; a retentativa já vive na fachada (pré-inserção) e a UNIQUE cobre o restante.

---

## R8. Matrícula informada com prefixo `PROV-` no CSV (anti-fabricação)

**Decisão**: NENHUMA alteração no comportamento atual do importador para esse caso — o CSV com `PROV-...` informado continua sendo aceito como está hoje (o importador não valida prefixo; verificado). A lacuna fica **documentada** nesta decisão para avaliação em feature futura.

**Rationale**: a spec (Edge Cases) define que a anti-fabricação do cadastro individual não é estendida ao importador nesta feature (nenhuma nova regra de validação além da geração por ausência). Alinhar o importador ao anti-fabricação do `create` seria mudança de regra não autorizada pelo briefing ("Não alterar mensagens/validações existentes... a única mudança de regra é a ausência").

**Alternativas consideradas**: (a) bloquear `PROV-` informado — nova regra fora de escopo; (b) tratar como ausência e gerar — viola FR-003/FR-008 (informada é usada).

---

## R9. Template `import.html`: documentação apenas

**Decisão**: atualizar somente textos de documentação: (1) parágrafo das colunas obrigatórias — `matricula` sai da lista de obrigatórias; (2) tabela de colunas — badge "Sim"→"Não" (vermelho→cinza) e observação "Se informada, será utilizada. Quando não informada, o sistema gerará automaticamente uma matrícula provisória, seguindo a mesma regra do cadastro individual."; (3) exemplo de CSV passa a ilustrar importação mista (linhas com e sem matrícula). Nenhuma mudança estrutural, de fluxo ou de preview visual (a tabela de preview exibe a matrícula vazia como está). **Remediação I1**: a spec torna a indicação no preview permissiva ("PODE indicar" — FR-007), coerente com esta decisão de diff mínimo; a flag `will_generate_provisional` (R3) é a sinalização disponível para uso de UI, presente ou futuro.

**Rationale**: FR-011 e Princípio XI (documentação fiel); o fluxo de tela (parse→preview→confirm) não muda.

**Alternativas consideradas**: (a) adicionar badge "Provisória" no preview usando a flag R3 — opcional/futuro; o design mantém a flag disponível sem mudança visual obrigatória, mantendo o diff mínimo.

---

## R10. Testes existentes: única edição autorizada

**Decisão**: `tests/test_custodian_import.py::test_parse_custodian_csv_reports_missing_required_fields` **asserta o erro removido** ("matricula é obrigatória") — comportamento diretamente alterado pela spec (FR-012; exceção prevista pela Constitution VIII). A edição converte o cenário: matrícula vazia deixa de estar entre os erros esperados (permanece para nome/email/cargo/setor) e/ou passa a asserar que matrícula vazia não gera erro. Demais testes existentes usam matrículas informadas → intactos.

**Rationale**: FR-012/AC-10; Princípio VIII permite ajuste apenas de testes ligados ao comportamento alterado.

**Alternativas consideradas**: manter o teste antigo — falharia por design (asserta o erro que a spec elimina).

---

## R11. Casos de borda de células: trim, acentos e ausência de chave

**Decisão**: ausência de matrícula = célula vazia, só espaços **ou chave inexistente**. O código novo usa `(row.get("registration_code", "") or "").strip()` — cobre chave ausente (coluna fora do CSV) e valor `None`. A normalização `_normalize_registration_code` (trim+upper) permanece para valores informados; após o trim vazio, o ramo de geração é acionado.

**Rationale**: o `parse` já normaliza células com `(value or "").strip()` (verificado), mas a execução pode ser chamada diretamente (API/transporte) — a guarda defensiva garante Testes 2/3/4 uniformes em todos os caminhos.

**Alternativas consideradas**: confiar só no parse — frágil para chamadores diretos do service.
