# Quickstart: Validação da Correção Documental (Feature 025)

**Feature**: 025 | **Data**: 2026-09-19
**Natureza**: validação pós-edição — a feature não possui código novo; a conferência é documental (briefing §34/§36).

---

## Pré-requisitos

- Edições E1–E4 aplicadas (contrato `contracts/doc-edit-contract.md` §1).
- Ferramentas: `git diff`, `rg`. **Não é necessário** banco, `.env` real ou execução da aplicação.

## Passo 1 — Escopo do diff (SC-001 / briefing §36)

```bash
git status --porcelain
git diff --stat
```

**Esperado**: exatamente `README.md`, `docs/GUIA_DE_MANUTENCAO.md`, `docs/ARQUITETURA_E_MANUTENCAO.md` (+ `specs/025-…` da feature). Qualquer caminho em `app/`, `tests/`, `data/`, `.env` → investigar imediatamente e reverter (briefing §36/§37).

## Passo 2 — Eliminação dos resquícios incorretos (AT-1)

```bash
rg -n "primeira inicialização" README.md docs/
rg -n "fallback" README.md docs/GUIA_DE_MANUTENCAO.md
```

**Esperado**: nenhuma frase afirmando que as env `BACKUP_*` valem **somente** na primeira inicialização; as novas descrições falam em "fallback por campo" e "bootstrap/fallback de boot". (Ocorrências de "primeira inicialização" em outro contexto legítimo — ex.: criação do admin — são aceitáveis; verificar caso a caso.)

## Passo 3 — Presença dos novos conteúdos (AT-2/AT-3)

```bash
rg -n "fallback de boot" README.md docs/
rg -n "não nulo|não-nulo" README.md docs/GUIA_DE_MANUTENCAO.md
rg -n "get_effective_config" README.md docs/
```

**Esperado**: fallback de boot citado no README e no ARQUITETURA (E2/E4) com a ordem correta (falha → snapshot anterior → bootstrap env/default); particularidade do `auto_enabled` presente (E1/E3); `get_effective_config()` atribuída como resolvedora da precedência.

## Passo 4 — Conferência factual contra o código (US5/FR-018)

Para cada frase nova ou alterada, confirmar a evidência (data-model §2):

1. Precedência por campo → `backup_config_service.py:122–185`.
2. Fallback de boot (condição, ordem, log) → `backup_scheduler.py:107–124`.
3. `auto_enabled` não-nullable e leitura direta → `models/backup_config.py:23`, `backup_config_service.py:155`.
4. Tick 30 s → `backup_scheduler.py:64`.
5. Defaults `false/daily/02:00/0/30/12/12/0` → `app/config.py:67–87`.
6. **Tabela das 8 variáveis do README** (somente contexto — sem edição): conferir que cada linha permanece fiel (finalidade/default) e que o parágrafo da E2 cobre "quando funciona como fallback" e "relação com o valor persistido" para o conjunto — particularidade por linha somente para `BACKUP_AUTO_ENABLED` (briefing §11, "quando tecnicamente apropriado").

**Falha se**: qualquer afirmação sem correspondência no código atual.

## Passo 5 — Preservações (briefing §40)

- [ ] Tabela das 8 variáveis do README intacta (`git diff` não a toca).
- [ ] Seções de comportamento/catch-up/retenção do README intactas.
- [ ] `app/config.py`, `app/services/**`, `app/models/**`, `tests/**` ausentes do diff.
- [ ] Nenhuma credencial/segredo citado; `BACKUP_*` permanecem como parâmetros operacionais.

## Passo 6 — Consistência interna (briefing §34)

- Mesma precedência, mesmos defaults e mesmo papel do `config.py` nos 3 arquivos.
- Fallback de boot apresentado como **exceção de segurança**, nunca como 4º nível normal.
- Nenhuma sugestão de fonte concorrente (`config.py` × `backup_config`).

## Resultado esperado final

| Verificação | Critério |
|---|---|
| Diff | somente os 3 docs + specs/025 |
| AT-1 | zero resquício "primeira inicialização" para `BACKUP_*` |
| AT-2 | fallback de boot documentado (README + ARQUITETURA) |
| AT-3 | particularidade `auto_enabled` documentada |
| Fatos | 100% conferidos com o código atual |
| Preservação | todo o resto intocado |

Todos os passos verdes → checklist de aceitação do briefing §35 (18 itens) satisfeito; produzir o relatório final (13 itens do §39) em `specs/025-documentacao-config-backup/relatorio.md`.
