# Data Model: Atualização da Ajuda/Manual e do README.md (feature 009)

**Natureza**: feature documental — **nenhum modelo, schema, tabela ou entidade de dados é criado ou alterado**. Zero DDL (Constitution VII). O "modelo" abaixo descreve a estrutura dos artefatos textuais que serão editados, cuja **forma é preservada** (apenas conteúdo muda).

## Artefato 1 — Conteúdo da Ajuda (`app/services/help_service.py`)

### `ARTICLES` (lista de dicts — 21 itens atuais; estrutura inalterada)

| Chave | Papel | Alteração prevista |
|---|---|---|
| `id` | Identificador estável do artigo (URL `/ajuda/{id}`) | **Inalterado** (nenhum artigo renomeado/removido) |
| `title` / `module` / `icon` / `audience` / `summary` / `keywords` | Metadados de apresentação e busca | Ajustes pontuais de texto (ex.: `summary`/`keywords` de `exportar-csv` para incluir locais) |
| `sections` | Lista de blocos `heading` + `steps`/`body`/`note` | **Conteúdo atualizado** para refletir telas reais (006/007/008 + guarda-chuva de consistência) |

### `FAQ` (lista de dicts — 12 itens; chaves `question`/`answer`)

- Estrutura inalterada; itens de exportação/locais podem ter o `answer` complementado se a revisão evidenciar lacuna (não identificado na análise).

### `CATEGORIES` (lista de dicts — 7 categorias; `article_ids` preservados)

- **Inalterada**: nenhum artigo novo exige categoria nova; a exportação de locais entra no artigo `exportar-csv` existente (categoria `relatorios`) e é reforçada em `cadastrar-locais` (categoria `colaboradores`).

## Artefato 2 — `README.md` (raiz do repositório)

| Seção | Ação |
|---|---|
| Status/contagem de testes (L23, seção 🧪) | **Corrigir**: 154/153 → quantitativo verificado nesta revisão (282; 281 passed / 1 failed conhecido) + instrução de obter o número atual |
| 🚀 Como Executar | **Corrigir** padrões `APP_HOST`/`APP_PORT` reais; **acrescentar** link para a nova seção de instalação completa |
| ✨ Principais Funcionalidades | **Acrescentar**: exportação CSV de locais (008), pesquisas de colaboradores (006) e locais (007), Etiquetas em lote (`/assets/labels`) |
| 🔐 Endpoints protegidos (tabela RBAC) | **Acrescentar**: `GET /api/v1/reports/locations/csv` → `relatorios.exportar` |
| **NOVA — Instalação em uma máquina nova** | **Criar**: 11 pontos (FR-006), sobre a configuração real (ver research D3) |
| Demais seções (Arquitetura, AD, RBAC, CLI, Banco, Segurança, Estrutura) | **Revisar** (guarda-chuva): sem divergência identificada na análise além dos itens acima; correções cirúrgicas se algo surgir na execução |

## Regras de consistência (validáveis)

1. Toda afirmação factual dos dois artefatos deve ter correspondência verificável em código/config (rastreabilidade no research D2/D3).
2. Nenhum comportamento "reservado/não exposto" (ex.: `movimentacao.cancelar`) apresentado como disponível.
3. Nenhuma credencial/IP/senha real nos textos; placeholders fictícios (`SenhaForte@123`, `usuario:senha@host:3306/banco`).
4. Estruturas das listas da ajuda e das rotas/templates **intactas** — validado por `test_help.py` verde e renderização.

## Validações e transições de estado

Nenhuma — operação documental, read-only sobre o sistema (nenhum estado, dado ou comportamento alterado; Constitution IX não se aplica).
