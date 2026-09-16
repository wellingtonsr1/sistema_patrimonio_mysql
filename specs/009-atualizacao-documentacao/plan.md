# Implementation Plan: Atualização da Ajuda/Manual e do README.md

**Branch**: `009-atualizacao-documentacao` | **Date**: 2026-09-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/009-atualizacao-documentacao/spec.md`

## Summary

Atualização exclusivamente documental para alinhar dois artefatos ao funcionamento real verificado no código: (1) a **Ajuda/Manual embutida** — conteúdo centralizado em `app/services/help_service.py` (`ARTICLES`/`FAQ`/`CATEGORIES`), apresentado em `/ajuda` —, incorporando as funcionalidades 006 (pesquisa de colaboradores — já parcialmente documentada), 007 (pesquisa de locais — já documentada) e **008 (exportação CSV de locais — ausente)**; e (2) o **README.md**, corrigindo fatos divergentes (contagem de testes 154→282; padrão `APP_HOST` 127.0.0.1→192.168.0.9; endpoints de exportação sem `locations/csv`) e acrescentando a seção obrigatória **Instalação em uma máquina nova** (11 pontos, construída sobre a configuração real: `run.py` + `init_db` automático, `DATABASE_URL` obrigatória, 3 caminhos reais de primeiro admin). Nenhum código de produção é alterado; suíte permanece no patamar atual.

## Technical Context

**Language/Version**: Python 3.10+ (stack existente, Constitution §Restrições) — alterações apenas em texto Markdown/Python-docstrings de conteúdo

**Primary Dependencies**: Nenhuma nova — edição de `app/services/help_service.py` (conteúdo de listas existentes) e `README.md` (Markdown puro)

**Storage**: N/A (feature documental; banco apenas consultado para validação de suíte)

**Testing**: pytest — suíte completa executada antes e depois; `tests/test_help.py` como guardião de não-regressão da ajuda; sem testes novos (não há comportamento novo a testar; a spec/plan não exigem TDD para conteúdo)

**Target Platform**: Documentação (renderizada no navegador pela `/ajuda` existente e lida no repositório)

**Project Type**: Aplicação web monolítica existente (FastAPI + Jinja2 server-side) — feature documental

**Performance Goals**: N/A (conteúdo estático; renderização da `/ajuda` inalterada)

**Constraints**:
- Escopo de arquivos FECHADO: somente `app/services/help_service.py` (conteúdo das listas `ARTICLES`/`FAQ`) e `README.md` (FR-012/SC-006) — nenhum template, rota, service de comportamento, teste ou config.
- Nenhuma funcionalidade inexistente documentada; permissões reservadas permanecem marcadas como reservadas (FR-008).
- Nenhuma credencial ou IP/senha real de produção nos documentos (FR-015) — exemplos com placeholders fictícios.
- Estilo e estrutura da ajuda preservados (tom, "Passo a passo"/"body"/"note", keywords, categorias) — ajustes cirúrgicos, não reescrita (FR-011).
- Suíte verde no patamar atual (281 passed / 1 failed conhecido — lockout defasado) (FR-013).

**Scale/Scope**: 21 artigos de ajuda (revisão integral, ajustes em ~4–6 deles), 1 artigo/FAQ reforçado se necessário, README com ~6 correções factuais + 1 seção nova de instalação (11 pontos)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Princípio | Status | Evidência |
|---|---|---|---|
| I | Preservação do sistema existente | ✅ PASS | Feature documental; nenhum módulo reescrito ou removido; ajustes cirúrgicos em conteúdo textual; a própria spec proíbe alterações fora do escopo |
| II | Arquitetura em camadas | ✅ PASS | Conteúdo da ajuda permanece no service (`help_service.py`), onde já vive; nenhuma regra nova em rotas/templates |
| III | Regras de negócio nos services | ✅ PASS | Nenhuma regra de negócio tocada; texto documental apenas descreve regras existentes |
| IV | Integridade patrimonial | ✅ PASS | Nenhum fluxo patrimonial alterado |
| V | Integridade do inventário | ✅ PASS | Nenhum fluxo de inventário alterado |
| VI | Segurança (auth, RBAC, AD) | ✅ PASS | Nenhum gate alterado; documentos NÃO incluirão credenciais reais (FR-015); exemplos com placeholders |
| VII | Banco MariaDB e proteção dos dados | ✅ PASS | Zero DDL; banco somente consultado pela suíte (SQLite em memória) |
| VIII | Testes como não regressão | ✅ PASS | Suíte executada antes/depois; `test_help.py` intacto e verde; nenhum teste editado/removido; sem testes novos (não há comportamento novo) |
| IX | Auditoria | ✅ PASS/N-A | Nenhuma operação de sistema realizada; edição de documentos não é operação auditável |
| X | Interface consistente | ✅ PASS | A `/ajuda` renderiza os artigos pela estrutura existente; nenhum template/layout alterado |
| XI | Documentação fiel | ✅ PASS | É o OBJETO da feature: docs alinhados ao comportamento real verificado em código; afirmações não verificáveis marcadas como tal |
| XII | Spec-driven + validação | ✅ PASS | Fluxo Spec Kit em curso; validação final = suíte verde + revisão artigo-vs-tela + `git status` com escopo fechado |

**Post-design re-check**: sem violações — o desenho não introduz código, camada, permissão, formato ou comportamento novo (Complexity Tracking vazio).

## Project Structure

### Documentation (this feature)

```text
specs/009-atualizacao-documentacao/
├── plan.md              # This file
├── research.md          # Phase 0 — decisões D1–D4
├── data-model.md        # Phase 1 — estrutura dos artefatos documentais
├── contracts/           # (não aplicável — nenhum contrato de API/CLI; ver research D4)
└── quickstart.md        # Phase 1 — protocolo de validação
```

(`tasks.md` será criado por `/speckit-tasks` — não por este comando.)

### Source Code (repository root)

```text
app/services/help_service.py      # ALTERAR (somente conteúdo): artigo exportar-csv
                                  #   (incluir locais.csv/008), revisão dos demais
                                  #   artigos contra as telas reais
README.md                         # ALTERAR: correções factuais (contagem de testes,
                                  #   APP_HOST, endpoints/permissões) + seção nova
                                  #   "Instalação em uma máquina nova" (11 pontos)
```

**Nenhum outro arquivo** é criado ou alterado (sem testes novos, sem templates, sem rotas, sem docs de `docs/`).

**Structure Decision**: Feature documental de escopo mínimo — dois arquivos alvo, ambos já existentes; estrutura do projeto intocada.

## Implementation Flow (ordem de integração)

1. **Ajuda/Manual** (`app/services/help_service.py`):
   a. Artigo `exportar-csv`: acrescentar a exportação de locais (botão "Exportar CSV" na tela de Locais, download direto de `locais.csv`, conjunto completo, sem colunas de interface, permissão `relatorios.exportar`) e ajustar o resumo/keywords.
   b. Artigo `cadastrar-locais`: conferir que pesquisa (007) e exportação (008) constam coerentemente (a seção "Exportar locais" já existe da 008; validar texto e coerência com o artigo de exportações).
   c. Artigo `cadastrar-colaboradores`: validar a seção de pesquisa (006) contra o comportamento real (termo único: matrícula/nome/cargo/departamento/e-mail, parcial, case-insensitive).
   d. Revisão rápida dos demais 18 artigos + FAQ vs. telas: corrigir apenas instruções contraditórias encontradas (nada foi identificado na análise além dos itens acima; a revisão é guarda-chuva do SC-001).
2. **README.md**:
   a. Correções factuais cirúrgicas: contagem de testes (154→quantitativo verificado 282, com nota de como obter o número atual), padrões `APP_HOST`/`APP_PORT` reais, tabela de endpoints protegidos (+ `GET /api/v1/reports/locations/csv` → `relatorios.exportar`), funcionalidades (acrescentar exportação CSV de locais, pesquisa de colaboradores/locais, Etiquetas em lote `/assets/labels`), catálogo de permissões (conferir igualdade com `PERMISSION_CATALOG`).
   b. **Nova seção "Instalação em uma máquina nova"** (11 pontos, FR-006): pré-requisitos → obtenção do projeto → ambiente virtual → dependências → instalação/inicialização do MariaDB → criação de banco/usuário/permissões → `.env` (`DATABASE_URL` obrigatória, sem `sqlite` na aplicação; placeholders fictícios) → estrutura do banco pelo `init_db` automático no `run.py` (sem comandos de migração inventados) → primeiro admin pelos 3 caminhos reais (env `AUTH_ADMIN_*`; tela `/setup`; CLI `create-user`) → inicialização (`python run.py`, host/porta reais) → primeiro acesso → validação (health `/health`, web, `pytest`, diagnósticos comuns).
   c. Atualizar a seção "Central de Ajuda e Manual" (contagem de artigos, se nova) e a "Estrutura do Projeto" apenas se algum texto citado divergir.
3. **Validação** (quickstart): suíte completa antes/depois (patamar 281/1), renderização da `/ajuda` (artigos alterados), percorrida artigo-vs-tela dos itens alterados, `git status` com escopo fechado.

## Error Handling

| Cenário | Comportamento |
|---|---|
| Texto novo conflita com teste existente (ex.: contagem fixada em teste) | Verificado na análise: `test_help.py` não fixa contagens de artigos/FAQ — nenhum conflito esperado; se surgir, o conteúdo se ajusta (não o teste) |
| Divergência docs-vs-código nova descoberta durante a execução | Corrigida na documentação (regra de consistência da spec) e registrada no relatório; código nunca alterado |
| Comportamento não verificável no código | Não documentado como fato; marcado como tal ou omitido (Constitution XI / FR-015) |
| Template Jinja quebrar por erro de sintaxe no conteúdo | Risco ~zero (strings literais em listas); validado por renderização no navegador + `test_help.py` verde |
| Credencial/IP real em risco de entrar em exemplo | Revisão obrigatória da seção de instalação antes de fechar (FR-015) |

## Security & Permissions

- Nenhuma permissão nova ou alterada; nenhum gate tocado.
- **Nenhuma credencial real** nos documentos: `DATABASE_URL` com placeholders (`usuario:senha@host:3306/banco`), senhas de exemplo claramente fictícias (`SenhaForte@123`), sem IPs/ senhas de produção (o IP do servidor real não entra no README; o padrão do código será citado como está no `config.py`).
- A ajuda é conteúdo servido a usuários autenticados; artigos admin continuam gated como hoje.

## Testing Strategy

- **Sem testes novos** (não há comportamento novo); a estratégia é não-regressão:
  1. Baseline antes da edição: `python3 -m pytest tests/ -q --tb=no` → patamar 281 passed / 1 failed.
  2. Após edição: suíte completa novamente no mesmo patamar; `test_help.py` 100% verde.
  3. Renderização real: abrir `/ajuda` e os artigos alterados no navegador (servidor de desenvolvimento/produção local) confirmando apresentação correta.
  4. Revisão de consistência: percorrida artigo-vs-tela dos conteúdos alterados + verificação cruzada das afirmações do README com config/rotas/código.
- Testes existentes NÃO são editados (Constitution VIII).

## Risks & Mitigations

| Risco | Mitigação |
|---|---|
| README ganhar conteúdo desalinhado do real na seção de instalação | Cada passo construído sobre artefato verificado (`run.py`, `config.py`, `database.py init_db`, CLI, `/setup`); proibido inventar comandos |
| Ajuda perder estilo/estrutura | Ajustes cirúrgicos por `str_replace` preservando formato das listas; renderização validada no navegador |
| Divulgar credencial/IP de produção por descuido | Seção de instalação revisada com placeholders fictícios; IP real ausente do README |
| Contagem de testes envelhecer de novo | Citar quantitativo verificado nesta revisão + instrução explícita de como obter o número atual (`pytest`) |
| Escopo vazar para outros docs (`docs/*.md`) | Escopo fechado na spec (FR-012) e verificado no fechamento via `git status` |

## Complexity Tracking

> Sem violações de Constitution — tabela vazia por design.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
