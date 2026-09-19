# Contract — Contrato de conteúdo do README.md (feature 023)

> Contrato entre a spec e a execução: cada seção do README final, os fatos que DEVE conter (todos verificados — data-model §1) e a fonte. O contrato é de **conteúdo documental**, não de API.

## §1. Contrato geral

1. Toda afirmação factual do README tem correspondência no código (spec FR-002/FR-003);
2. Divulgação de segredos: proibida — exemplos de `.env` com placeholders (`usuario`, `SENHA`) (FR-015/SC-006);
3. Sem números fixos de testes (FR-019/SC-005);
4. Referências externas somente para: `docs/ARQUITETURA_E_MANUTENCAO.md`, `docs/GUIA_DE_MANUTENCAO.md`, `docs/INVENTARIO_TECNICO.md`, `docs/AVISO_RESTORE_DEADLOCK.md`, `specs/` (FR-023/SC-007);
5. Nenhuma funcionalidade planejada documentada como existente; evolução futura permanece claramente marcada como tal (FR-003/§33);
6. Consistência interna: MariaDB/MySQL produção em todas as menções; SQLite só em testes; AD sem conceder permissões; inventário sem alterar bens (FR-026/SC-004).

## §2. Seções do README final (ordem atual preservada — research R2)

| # | Seção | Fatos obrigatórios (verificados) | Divergência aplicada |
|---|---|---|---|
| 1 | Título/Introdução/Status | nome, descrição, foco (rastreabilidade auditável), status; versão citada uma vez, "conforme `app/config.py`" | — |
| 2 | Principais Funcionalidades | módulos reais; tipos de movimentação (8); inventário como conferência física; identificações provisórias `PROV-`; etiquetas `/assets/labels`; depreciação linear 20%/ano (`asset_service.py` L249) | D9 |
| 3 | Modelo Conceitual | Asset/Movement/InventoryItem/AuditLog — estado atual, histórico, evidência, auditoria | — |
| 4 | Tecnologias | tabela = requirements.txt real (data-model §1.2) + frontend | — |
| 5 | Arquitetura | camadas Web/API → auth → services → models → MariaDB/MySQL | — |
| 6 | Como Executar / Instalação | pré-requisitos, `pip install -r requirements.txt`, `DATABASE_URL` (sem fallback SQLite), `python run.py`, `APP_HOST/APP_PORT`; banco SQL de exemplo; 3 mecanismos do 1º admin (env `AUTH_ADMIN_*`, `/setup` condicional, CLI `create-user`); migração = `init_db()` + `_ensure_schema_migrations()` idempotente | D2 |
| 7 | Autenticação | local PBKDF2 (salt, iterações 600000), sessão (token+hash, cookie), lockout 10×900s, 423 na API, `/health` público, `/docs` público | D7 |
| 8 | Active Directory | AD autentica, não autoriza; grupo mapeado → perfil; prioridade numérica; sem mapeamento = sem acesso; conta de serviço só consulta; LDAPS | D5 |
| 9 | RBAC | deny-by-default; perfis padrão (7); catálogo de permissões **incluindo `backup.gerenciar`/`backup.restaurar`**; `movimentacao.cancelar` reservada; backend valida tudo | D6 |
| 10 | Auditoria | eventos/campos reais; sem credenciais | D14 |
| 11 | Banco de Dados | MariaDB/MySQL produção; `init_db()` automático; tabelas citadas + `backup_records`/`backup_config`; sem sugestão de migração obrigatória | D15 |
| 12 | CLI | comandos/parâmetros conforme `cli.py` (data-model §1.4) | D3 |
| 13 | Central de Ajuda | `/ajuda`, pesquisa, artigos, FAQ | — |
| 14 | Testes | `pytest -q`; cobertura por módulos **incluindo backup (7 arquivos)**; SQLite/`DATABASE_URL_TEST` | D12 |
| 15 | Estrutura do Projeto | árvore real (data-model §1.7) — `specs/` incluído; nota `seed_demo.py` | D10 |
| 16 | Segurança | implementado × recomendações (HTTPS, cookie secure, LDAPS) | D14 |
| 17 | Backup e Restauração | manual 015/016, automático/retenção 020, configurações **via ⚙ na página de Backups (021/022 — modal)**, rota `/admin/backups/configuracoes` mantida por compatibilidade; restauração 017/019; backup operacional | D4 |
| 18 | Documentação | referências aos 4 arquivos reais de `docs/` + `specs/`; lista fictícia removida | D1 |
| 19 | Pontos de atenção / limitações | somente limitações reais verificadas | — |

## §3. Critérios de aceite do contrato

- [ ] Nenhuma das 15 divergências (D1–D15) persiste no README final;
- [ ] Nenhum fato do data-model §1 é contradito pelo README;
- [ ] `git diff` mostra somente `README.md`;
- [ ] Checklist do briefing §39 integralmente executado (quickstart).
