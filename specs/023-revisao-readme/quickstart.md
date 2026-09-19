# Quickstart — Validação da Revisão do README (feature 023)

> Procedimento de validação documental (briefing §39) e roteiro do relatório final (§41). Não há instalação a executar — a validação é por inspeção comparativa README ↔ código.

## 1. Pré-requisitos

```bash
git status --short          # ambiente conhecido; anotar arquivos alterados antes de começar
```

A aplicação NÃO precisa estar em execução. A suíte pytest só é executada se alguma afirmação do README precisar de confirmação comportamental (spec §39 — "executar testes somente se necessário").

## 2. Validação item a item (briefing §39)

| # | Verificação | Como validar | Fonte de confirmação |
|---|---|---|---|
| 1 | Comandos CLI | comparar cada comando/flag do README com `app/cli.py` | `cli.py` L206–245 |
| 2 | Caminhos | existência real de cada arquivo/diretório citado | `ls` |
| 3 | Endpoints | comparar rotas citadas com `app/main.py`, `app/web/routes.py`, `app/web/help_routes.py`, `app/api/` | grep |
| 4 | Nomes de arquivos | árvore da seção "Estrutura" vs repositório real | `ls` |
| 5 | Tecnologias | tabela vs `requirements.txt` | leitura |
| 6 | Banco | MariaDB produção / SQLite testes consistentes em todas as menções | `config.py`, `tests/conftest.py` |
| 7 | Autenticação | variáveis `AUTH_*` e defaults vs `config.py`; 423 vs `auth_service.py` | grep |
| 8 | AD | fluxo grupo→perfil vs `ad_service.py`/`ad_group_role.py` | grep |
| 9 | RBAC | perfis e permissões vs `permission_service.py` (36 permissões, 7 perfis) | grep |
| 10 | Inventário | regra "não altera bens" vs `inventario_service.py` | L305 |
| 11 | Movimentações | 8 tipos vs `enums.py`/`MovementService` | grep |
| 12 | Backup/Restauração | recursos citados vs rotas em `admin_routes.py`; acesso ⚙/modal da 022 | grep |
| 13 | CLI (repetida) | idem 1 | — |
| 14 | Testes | sem número fixo; `pytest -q` presente; cobertura citada vs `tests/` real | `ls tests/` |
| 15 | Links internos | caminhos relativos citados existem | `ls` |
| 16 | Blocos de código | comandos executáveis conforme documentados (inspeção) | — |
| 17 | Markdown | títulos/índices/tabelas renderizam sem quebra | render/inspeção |

## 3. Verificação de escopo (SC-001)

```bash
git diff --stat             # deve listar SOMENTE README.md
git diff --name-only        # idem, forma estrita
```

Confirmações do relatório:

```text
Código alterado: NÃO
Banco alterado: NÃO
Configuração alterada: NÃO
```

## 4. Confirmações pontuais já executadas na fase de plan (referência)

- `python -m app.cli stats|list|show|move|create-user|reset-password` → existem com os parâmetros documentados;
- `/setup` GET/POST existe (`routes.py` L1644/L1658) e é condicionado à inexistência de usuários (`setup_claims` singleton);
- `/health` público (`main.py` L144); `/ajuda` em `help_routes.py` L31;
- catálogo real = 36 permissões (inclui `backup.gerenciar`, `backup.restaurar`);
- ata de inventário disponível em CSV, PDF e Excel (`report_service.py` L556/L612/L731);
- `docs/` real = 4 `.md` + 2 itens auxiliares; a lista "sugestão" do README atual não existe.

## 5. Relatório final (briefing §41) — estrutura esperada

### Arquivo alterado
```text
README.md
```

### Principais melhorias
- Seções reorganizadas: (descrever quais, se houver)
- Informações corrigidas: (mapear D1–D15 aplicadas)
- Informações removidas: (ex.: lista fictícia de `docs/`)
- Informações adicionadas: (ex.: módulo Backup no catálogo; acesso ⚙ às configurações)
- Comandos corrigidos: (se aplicável)
- Inconsistências eliminadas: (listar)

### Verificações
- Informar as fontes consultadas (arquivos/linhas) por seção.

### Limitações
- Informar qualquer fato que não tenha sido possível confirmar diretamente (ex.: comportamento visual em navegador, ambiente Windows real).
