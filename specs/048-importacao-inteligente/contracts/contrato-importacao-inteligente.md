# Contract: Importação Inteligente (048) — Fluxo, UI e Comportamento

Contrato da evolução dos importadores CSV (Equipamentos `/assets/import`, Colaboradores `/custodians/import`, Locais `/locations/import`). Define o que **não pode quebrar** e o comportamento obrigatório das novas fases. Nenhum contrato de dados/API muda.

## §1 Contrato de rotas e compatibilidade (§36 do pedido)

| Regra | Exigência |
|---|---|
| URLs | As 6 rotas existentes (GET form + POST process + POST confirm × 3 entidades) permanecem; nenhuma URL nova; nenhuma removida |
| Permissões | `patrimonio.criar` / `colaboradores.criar` / `locais.criar` — inalteradas, em todas as fases |
| Comportamento legado | O fluxo de duas fases continua funcionando; com mapeamento aceito como sugerido, o resultado é idêntico ao atual (R9 — testes existentes verdes sem alteração) |
| Execução | `execute_*` dos 3 services permanecem a ÚNICA instância de gravação; `movement_service` intocado |

## §2 Fases do fluxo (server-rendered, mesmas URLs — R5)

| Fase | Entrada | Saída | Banco |
|---|---|---|---|
| 1. Upload | `POST import` com `file` | Passo **mapeamento** (`step=map`): colunas + sugestões + dropdown alterar/ignorar + arquivo oculto | Nenhum |
| 2. Mapeamento | `POST import` com `step=analyze` + mapping + arquivo oculto | **Pré-visualização** classificada com filtros e resoluções por linha (NÃO ENCONTRADO) | Nenhum |
| 3. Confirmação | `POST import/confirm` (existente) + linhas resolvidas + `skip_duplicates` | **Resultado**: resumo + relatório por linha | Escrita via `execute_*` |

- Cada fase reexecuta a análise server-side (nunca confia só no cliente).
- Cancelar em qualquer fase (link "Cancelar"/voltar) não produz efeito no banco (Teste M).

## §3 Passo de mapeamento (clarify: passo dedicado)

- Tabela: coluna original → campo do sistema sugerido, com `select` por coluna: campo sugerido, outros campos válidos da entidade, "não utilizada".
- `confidence=auto` → pré-selecionado; `ambigua` → sem seleção + destaque "confirme o campo"; `desconhecida` → "não utilizada" + destaque.
- Resumo do arquivo: delimitador detectado, total de registros, guardas de erro (vazio/sem cabeçalho/corrompido/encoding) antes de tudo.
- Avançar exige mapeamento válido (obrigatórios da entidade mapeados — os campos canônicos exigidos por `_validate_row`).

## §4 Pré-visualização classificada

- **Resumo**: Total · Válidos · Válidos com aviso · Duplicados · Erros · Não encontrados · Ignorados.
- **Tabela por linha**: Linha | identificadores (Tombamento/Nome conforme entidade) | campos principais | Situação | Problema.
- **Badges** (existentes do sistema — P-2): VÁLIDO `bg-success` · AVISO `bg-warning text-dark` · DUPLICADO `bg-secondary` · ERRO `bg-danger` · NÃO ENCONTRADO `bg-info text-dark` · IGNORADO `bg-light text-dark border` (enums internos do código, sem acento: `VALIDO`/`AVISO`/`DUPLICADO`/`ERRO`/`NAO_ENCONTRADO`/`IGNORADO` — data-model §2.3; os rótulos acima são os de exibição).
- **Filtros**: Todos / Válidos / Avisos / Erros / Duplicados / Ignorados (links server-side ou tabs existentes — sem componente novo).
- **Resolução NÃO ENCONTRADO** (R4/clarify): por linha, escolher `Pular` · `Importar sem custódia (aviso)` · `Atribuir a…` (busca de colaborador existente; candidatos exibidos quando o nome é ambíguo).
- **Avisos informacionais**: "Responsável não informado" / "Local não informado" nas linhas com opcionais vazios quando a regra da entidade permite (F3) — AVISO, não ERRO.

## §5 Confirmação e gravação

- Resumo obrigatório antes de gravar (total/válidos/avisos/duplicados/erros) + `skip_duplicates` explicitado: marcado → duplicados pulados; desmarcado → reimportação atualiza equipamento (regra 029 preservada — clarify).
- Registros ERRO nunca gravados; `resolutions` (skip/sem_custodia/assign) aplicadas antes do `execute_*`; linhas IGNORADO excluídas.
- Gravação = `execute_import`/`execute_custodian_import`/`execute_locations_import` (transacionalidade vigente: commit por linha documentado da 029; rollback da linha em erro; erro comunicado claramente — Teste N).
- Fluxo patrimonial: entrada/custódia exclusivamente via `MovementService` (029) — intocado.

## §6 Relatório final

- Resumo: Total analisado / Importados / Avisos / Duplicados / Erros / Ignorados.
- Tabela por linha processada: Linha | Situação | Tombamento (ou identificador) | Motivo — construída do retorno aditivo `row_results` dos `execute_*` (R8).
- Reprocessamento: reenviar o CSV corrigido reexecuta a análise contra o estado atual do banco (já importados → DUPLICADO) — nada duplicado (Teste da 033 do pedido/FR-018).

## §7 Segurança e auditoria

- Upload: extensão `.csv`, tamanho ≤ limite vigente, conteúdo validado na análise; sem execução de conteúdo; sem path traversal; sem armazenamento permanente.
- Auditoria: `write_audit` existente do confirm, agora com quantidades por classificação na description; nunca segredos.
- Nenhum segredo/credencial em qualquer tela, log ou estrutura em memória.

## §8 Não-vazamento de escopo

- Alterações permitidas: 3 `*_import_service.py` (extensões), novo `import_intelligence.py` (camada transversal), 3 rotas de import em `routes.py` (mesmas URLs, fase `step`), 3 templates `import.html` evoluídos + parcial de mapeamento, `tests/test_importacao_inteligente.py`, docs/ajuda.
- **Intocados**: `movement_service`, modelos, `permission_service`, auditoria (mecanismo), backup/AD/e-mail/1Doc/GLPI/inventário, demais telas, `style.css`/`base.html`.
- Zero tabela/coluna nova; zero permissão nova; zero CSS global novo; zero dependência nova.
