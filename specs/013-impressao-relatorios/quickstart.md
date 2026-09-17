# Quickstart — Validação da feature 013

**Feature**: 013-impressao-relatorios
**Objetivo**: provar que os três relatórios imprimem integralmente em A4 (sem página em branco, sem truncamento, tabelas contínuas com cabeçalho repetido) e que Etiquetas/Termo permanecem inalterados — com zero mudança funcional.

> Referências: [research.md](./research.md) (R1–R9) · [css-contract.md](./css-contract.md) (C1–C10) · spec (AC-01..AC-08).

---

## Pré-requisitos

1. Ambiente pronto (`requirements.txt`; Python 3.10+); app executável (`python3 run.py` com `DATABASE_URL` de teste/demo).
2. Banco com massa mínima: pelo menos **1 local**, **2 colaboradores** e **bens suficientes para gerar 2+ páginas** no Relatório Contábil-Físico (idealmente 50+ bens; use `seed_demo.py` em banco de demo se disponível).
3. Navegadores para validação: Chrome/Chromium **e** Firefox (pré-visualização de impressão, papel A4, margens "padrão" — o `@page` do CSS define 10mm). **Orientação**: retrato é o padrão; a opção **paisagem** deve estar selecionável no diálogo (validar que o relatório também preenche bem a folha em paisagem — largura fluida).

## 1. Regressão — suíte existente permanece verde (Constitution VIII)

```bash
python3 -m pytest -q
```

**Esperado**: 100% dos testes passando **sem nenhuma edição** (exceto a falha pré-existente do baseline `test_rbac.py::test_lockout_after_failed_attempts`, externa a esta feature — registrada em `tasks.md` da feature 012).

**Falha se**: qualquer teste novo precisar de edição, ou qualquer rota de relatório mudar de status/dados.

## 2. Roteiro de validação de impressão (por relatório)

Repita os 6 passos para cada página: **Trilha de Auditoria & Fluxo** (`/reports/movements`), **Relação de Colaboradores** (`/reports/custodians`) e **Relatório Contábil-Físico** (`/reports/inventory`):

| # | Passo | Esperado (AC) |
|---|---|---|
| 1 | Abrir o relatório | Tela idêntica à atual (nenhuma mudança visual — AC-07) |
| 2 | Clicar em **Imprimir** | Pré-visualização abre em A4 |
| 3 | Observar a 1ª página | Cabeçalho do relatório (empresa + título) **e** início da tabela presentes — **nenhuma página em branco antes** (AC-01/AC-02) |
| 4 | Navegar por **todas** as páginas | Nenhuma coluna cortada nas laterais; valores R$/% completos; motivo do movimento completo (sem "…" de clamp) (AC-04) |
| 5 | Verificar continuidade | Tabela continua entre páginas; **cabeçalho das colunas repete** em cada página (AC-05); nenhuma linha cortada ao meio (AC-06) |
| 6 | Alternar tema escuro e repetir passos 2–5 | Impressão continua com paleta clara e legível (edge case) |

Repetir o roteiro também no **Firefox** (mesmos critérios, dentro das limitações normais).

## 3. Não-regressão — Etiquetas e Termo (AC-08)

| Módulo | Passo | Esperado |
|---|---|---|
| **Etiquetas** (`/assets/labels`) | Selecionar 6+ bens → Imprimir etiquetas | Folha 3 colunas idêntica à atual; quebras apenas entre etiquetas; **nenhuma** influência das regras novas |
| **Termo** (movimento com termo → visualizar termo → Imprimir) | Imprimir | Layout do termo idêntico ao atual |

**Verificação estática adicional**: o diff da implementação não pode conter alterações em `assets/labels.html`, `movements/term.html`, `base.html` nem nos blocos `@media print` existentes de `style.css` (linhas ~896 e ~1476) — apenas o **novo bloco no final** do arquivo e a classe `report-print` nos 3 templates de relatório.

## 4. Definition of Done

- [ ] Suíte completa verde (sem edição em testes existentes).
- [ ] Roteiro da Seção 2 aprovado nos 3 relatórios, nos 2 navegadores.
- [ ] Etiquetas e Termo sem alteração de comportamento (Seção 3).
- [ ] `git diff` mostra apenas: `style.css` (bloco novo no final) + `report-print` nos 3 templates de relatório.
- [ ] Nenhuma alteração em rotas, services, models, schemas, permissões, filtros ou dados.
