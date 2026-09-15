# Phase 1 — Quickstart: Validação da Baseline (001-sistema-existente)

**Objetivo**: provar que a baseline está correta e que o sistema permanece íntegro
(sem alteração de comportamento). Esta feature não altera código — a validação é
**executar a suíte existente e conferir os artifacts**.

## Pré-requisitos
- Python 3.10+ e dependências instaladas (`pip install -r requirements.txt`).
- **NÃO** é necessário MariaDB para a suíte: os testes usam SQLite em memória por
  padrão (`tests/conftest.py`). **Não** defina `DATABASE_URL` para rodar os testes.
- Nenhuma variável de ambiente de produção é necessária.

## 1. Validação de não-regressão (obrigatória)

```bash
pytest -v
```

**Resultado esperado**: **153 aprovados, 1 falha conhecida**
(`tests/test_rbac.py::test_lockout_after_failed_attempts` — o teste espera bloqueio
após 5 tentativas; a configuração atual é 10; defasagem pré-existente documentada em
`SPEC-KIT-SISTEMA-ATUAL.md` §25 e plan §13).

> Qualquer falha **diferente** dessa indica regressão real → investigar antes de
> prosseguir. Nenhum teste deve ser editado nesta feature.

## 2. Validação dos artifacts da baseline (revisão)

Conferir que os documentos existem, são fiéis e não deixaram placeholders:

| Arquivo | Verificação |
|---|---|
| `specs/001-sistema-existente/spec.md` | 12 seções solicitadas + template; 27 regras (§7); 24 preservações (§10); sem `[NEEDS CLARIFICATION]` |
| `specs/001-sistema-existente/plan.md` | Constitution Check 12/12 PASS; §15/§16 (arquivos a criar/não modificar) coerentes |
| `specs/001-sistema-existente/research.md` | Decisões R1–R8 com verificação de código |
| `specs/001-sistema-existente/data-model.md` | 17 tabelas espelhadas; nenhuma alteração de schema (§7) |
| `specs/001-sistema-existente/contracts/*.md` | Rotas/endpoints/CLI conferem com o código (`app/web`, `app/api`, `app/cli.py`) |
| `specs/001-sistema-existente/checklists/requirements.md` | Todos os itens aprovados |

## 3. Verificação de integridade do repositório (opcional, leitura)

```bash
git status --porcelain          # apenas specs/ e .specify/feature.json novos
git diff --stat                 # vazio: nenhum arquivo rastreado modificado
```

**Esperado**: nenhum arquivo de `app/`, `tests/`, `docs/`, `.env`, `requirements.txt`
modificado; nenhum commit executado.

## 4. Checklist de conformidade (Constitution) — para a entrega

- [ ] Escopo: somente artifacts em `specs/001-sistema-existente/`
- [ ] Comportamento existente preservado (suíte verde, exceto falha conhecida)
- [ ] Nenhuma credencial/segredo nos artifacts
- [ ] Banco: nenhum DDL executado; nenhuma conexão de escrita
- [ ] Documentação fiel ao código (afirmações verificáveis; não-confirmados marcados)

## 5. Critérios de aceite da feature (da spec)

- **SC-001/SC-002**: 17 módulos descritos sem funcionalidades inventadas (revisão §2).
- **SC-003**: 24 preservações (P1–P24) cobrem as 27 regras (conferência cruzada
  spec §7 ↔ §10).
- **SC-D**: suíte executada com resultado esperado (153/154).

## Próxima etapa
`/speckit.tasks` → tarefas de entrega/revisão da baseline (e, para features futuras,
uso desta baseline como referência obrigatória de não-regressão).
