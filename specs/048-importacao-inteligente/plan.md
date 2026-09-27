# Implementation Plan: Importação Inteligente (048)

**Branch**: `048-importacao-inteligente` | **Date**: 2026-09-26 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/048-importacao-inteligente/spec.md`

## Summary

Evoluir os três importadores CSV existentes (Equipamentos/029, Colaboradores/014, Locais) com uma **camada inteligente pré-gravação**: análise do arquivo com identificação automática de colunas (evoluindo os aliases existentes), **passo intermediário dedicado de mapeamento** (decisão clarify), classificação por registro (VÁLIDO/AVISO/DUPLICADO/ERRO/NÃO ENCONTRADO/IGNORADO) sobre as validações reais de cada entidade, duplicidade interna ao arquivo, pré-visualização com filtros, resolução interativa de responsáveis não encontrados (atribuir/busca · sem custódia com aviso · pular), confirmação com `skip_duplicates` explicitado, gravação pelos `execute_*` existentes (transacionalidade vigente) e relatório detalhado. Zero parser novo, zero importador paralelo, zero rota nova, zero permissão nova.

## Technical Context

**Language/Version**: Python 3.10+ (`.venv/bin/python`)

**Primary Dependencies**: FastAPI + SQLAlchemy 2 + Jinja2/Bootstrap 5 (stack vigente); parsers/serviços de importação existentes

**Storage**: MariaDB produção / SQLite suíte. **Zero migração** (nenhuma tabela/coluna nova — a análise vive em memória e o estado entre fases via formulários ocultos)

**Testing**: pytest + TestClient (baseline **775 passed**); fixtures CSV existentes (`tests/*.csv`) + novos CSVs de teste inline

**Target Platform**: Linux server; navegadores desktop/mobile

**Project Type**: Web application monolítica

**Performance Goals**: análise de arquivos pequenos/médios (centenas a poucos milhares de linhas) no request normal — sem jobs/filas (spec §28)

**Constraints**: menor alteração possível; `execute_import`/`execute_custodian_import`/`execute_locations_import` e `movement_service` intocados salvo o previsto; nenhuma alteração em inventário/backup/AD/e-mail/1Doc/GLPI/RBAC

**Scale/Scope**: 3 services estendidos, 3 rotas evoluídas (mesmas URLs), 3 templates evoluídos + 1 template novo de mapeamento, 1 novo arquivo de testes

## Constitution Check

*GATE: aprovado antes da Phase 0; reavaliado após Phase 1 — sem alteração.*

| Princípio | Status | Evidência |
|---|---|---|
| I. Evolução incremental | ✅ | Extensão dos 3 importadores existentes; mesmas URLs; zero paralelismo |
| II/III. Camadas/services | ✅ | Toda a inteligência em services (`*_import_service.py`); rotas delegam |
| IV. Fluxo patrimonial | ✅ | Gravação continua via `execute_import` → `MovementService.create_movement` (029) — intocado |
| V. Inventário | ✅ | Não afetado |
| VI. RBAC/segurança | ✅ | Permissões existentes (`patrimonio.criar`, `colaboradores.criar`, `locais.criar`); sem permissão nova |
| VII. Banco aditivo | ✅ | Zero migração |
| VIII. Testes | ✅ | Novos testes TDD; suíte 775 verde |
| IX. Auditoria | ✅ | `write_audit` existente reutilizado; sem segredos |
| X. UI consistente | ✅ | Passo de mapeamento no padrão visual vigente; zero CSS global |
| XI. Documentação | ✅ | Ajuda/docs na mesma tarefa |
| XII. Validação | ✅ | Suíte + validação registrada |

**Resultado: SEM violações.**

## Project Structure

### Documentation (this feature)

```text
specs/048-importacao-inteligente/
├── plan.md · research.md · data-model.md · quickstart.md · tasks.md
├── contracts/contrato-importacao-inteligente.md
└── checklists/requirements.md
```

### Source Code (repository root)

```text
app/
├── services/
│   ├── import_service.py            # ESTENDIDO: analyze_csv, classificação, resolução
│   ├── custodian_import_service.py  # ESTENDIDO (mesma camada)
│   ├── location_import_service.py   # ESTENDIDO (mesma camada)
│   └── import_intelligence.py       # NOVO: camada compartilhada (ver R2)
├── web/
│   ├── routes.py                    # EVOLUÍDO: mesmas URLs + fase de mapeamento
│   └── templates/
│       ├── assets/import.html       # EVOLUÍDO
│       ├── custodians/import.html   # EVOLUÍDO
│       ├── locations/import.html    # EVOLUÍDO
│       └── (partials do passo de mapeamento)
tests/
└── test_importacao_inteligente.py   # NOVO
```

**Structure Decision**: projeto único vigente. A inteligência é uma **camada transversal compartilhada** (`import_intelligence.py`) consumida pelos três services — evita triplicar a mesma lógica de análise/classificação (o pedido proíbe duplicação de parser/validação/preview) sem criar um "framework universal" (§35): só o que os três importadores compartilham de fato.

## Decisões de plan (P-1/P-2/P-3 + R1–R9)

| ID | Decisão |
|---|---|
| **P-1 (transporte de estado)** | Reutilizar o mecanismo atual de serialização no formulário (`csv_rows \| tojson` em textarea oculto — já vigente nos 3 confirm): entre as novas fases, o arquivo original + o mapeamento escolhido viajam como campos ocultos (JSON assinado não é necessário — a análise é reexecutada server-side a cada fase, o mapeamento é apenas um dicionário coluna→campo). Nenhuma sessão/temp-table nova |
| **P-2 (rótulos/badges)** | VÁLIDO→`bg-success`; AVISO→`bg-warning text-dark`; DUPLICADO→`bg-secondary`; ERRO→`bg-danger`; NÃO ENCONTRADO→`bg-info text-dark`; IGNORADO→`bg-light text-dark border` — badges existentes do sistema |
| **P-3 (formato do mapeamento)** | **RESOLVIDA no clarify**: passo intermediário dedicado — nova fase server-rendered após o upload (mesma rota POST com `step=map`), template parcial reutilizado pelos 3 importadores |
| **R1 (análise de colunas)** | `analyze_columns(content, kind)` em `import_intelligence.py`: lê cabeçalho com o parser existente (mesma detecção de delimitador), sugere campo para cada coluna usando os `COLUMN_ALIASES` dos 3 services (união, sem duplicar), classifica sugestão como `auto` (alias único), `ambigua` (2+ campos candidatos exatamente iguais no score) ou `desconhecida`; nunca mapeia silenciosamente o ambíguo |
| **R2 (camada compartilhada)** | `app/services/import_intelligence.py` novo, consumido pelos 3 services; contém: análise de colunas, classificação por registro (casca sobre as validações existentes), detecção de duplicidade interna, montagem da classificação unificada. **Não** contém regras específicas de entidade (continuam nos services de cada importador) |
| **R3 (classificação)** | `classify_rows(rows, db, kind, mapping, overrides)` retorna por linha: `status` (VALIDO/AVISO/DUPLICADO/ERRO/NAO_ENCONTRADO/IGNORADO) + `problems` (lista legível). Reusa `_validate_row` de cada service (via chamada), verificações de duplicata existentes (tag/serial, matrícula/email, nome) e **duplicidade interna** (chave natural já vista no mesmo arquivo). Campos opcionais ausentes → AVISO informacional ("Responsável não informado") sem bloquear, conforme F3 |
| **R4 (resolução interativa)** | Linhas NÃO ENCONTRADO (responsável) recebem na preview um campo de resolução por linha: `resolve_action` = `skip` \| `sem_custodia` \| `assign:<id>` (busca de colaborador no cadastro reutilizando a pesquisa existente); os overrides viajam na confirmação (JSON no formulário oculto) e são aplicados na montagem das linhas antes do `execute_import` — **nenhuma mudança em `execute_import`** (o service recebe as linhas já resolvidas: com custodiante resolvido, sem custodiante, ou sem a linha) |
| **R5 (fases e rotas)** | Mesmas URLs, fase via campo `step`: `POST /assets/import` com `file` → renderiza **map** (passo dedicado); `POST /assets/import` com `step=analyze&mapping=…&csv_data=…` → renderiza **preview** classificada; `POST /assets/import/confirm` (existente) recebe `csv_data` já com as linhas resolvidas/filtradas + `skip_duplicates` (explicitado). Idem nos 3 importadores. Nenhuma URL nova, nenhuma quebra de compatibilidade |
| **R6 (arquivos inválidos)** | Guardas na análise: vazio, só BOM, sem registros, sem cabeçalho (todas as colunas vazias), encoding inválido (`UnicodeDecodeError` capturado → mensagem amigável), tamanho > limite do upload (10 MB já vigente no template) — nenhuma exceção cruza para o usuário |
| **R7 (normalização)** | Comparação de duplicidade/relacionamento usa os normalizadores existentes (`_fold`, `_normalize_registration_code`, `ilike`); o valor **original** do CSV é o gravado (comportamento atual dos services mantido) |
| **R8 (relatório final)** | Os dicts de resultado dos `execute_*` (imported/skipped/errors) são reapresentados com a tabela por linha (linha/status/identificadores/motivo) — os services ganham apenas a enumeração das linhas processadas no retorno (aditivo), sem mudar assinatura |
| **R9 (compatibilidade)** | Se o usuário não alterar o mapeamento, o comportamento final é idêntico ao atual (mesmos aliases, mesmas validações, mesma execução); a fase de mapeamento não é opcional mas o fluxo de confirmação/execute permanece o mesmo — testes existentes devem continuar verdes sem alteração (regressão) |

## Research & design decisions

Ver `research.md` (decisões consolidadas), `data-model.md` (estruturas em memória), `contracts/contrato-importacao-inteligente.md` (contrato de UI/fluxo) e `quickstart.md` (cenários A–Q).

## Complexity Tracking

> Nenhuma violação — tabela vazia.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|