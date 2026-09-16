# Phase 1 — Quickstart: Validação da Feature 006 (Pesquisa de Colaboradores)

**Objetivo**: provar que a pesquisa funciona fim a fim, sem regressão da tela existente.

## 1. Suíte automatizada (obrigatória)

```bash
# Novos testes da pesquisa
pytest tests/test_custodians_search.py -v

# Suíte completa (não-regressão)
pytest -v
```

**Resultado esperado**: novos testes aprovados + suíte existente no estado conhecido
(**230 passed, 1 failed** — `test_lockout_after_failed_attempts`, falha defasada conhecida,
documentada nas baselines). Nenhum teste existente é editado.

## 2. Validação manual (navegador, contra o ambiente local)

Pré-requisitos: usuário com `colaboradores.visualizar`; pelo menos 2 colaboradores cadastrados
(com nome, matrícula, cargo, departamento e e-mail distintos).

| # | Passo | Resultado esperado |
|---|---|---|
| 2.1 | Abrir `Menu → Colaboradores` (`/custodians`) | Campo de pesquisa visível **acima** da tabela, com o placeholder orientativo; lista completa carregada como antes |
| 2.2 | Pesquisar parte do nome (ex.: `Amanda`) | Somente os colaboradores correspondentes; link do nome, cargo, departamento, e-mail, contagem de bens e ações idênticos aos de antes |
| 2.3 | Pesquisar matrícula (ex.: `MAT-1036`) | Colaborador correspondente aparece |
| 2.4 | Pesquisar cargo (`Gerente`) e departamento (`Comercial`) | Correspondentes em cada caso |
| 2.5 | Pesquisar trecho do e-mail (ex.: `amanda.nunes36`) | Colaborador correspondente aparece |
| 2.6 | Pesquisar `AMANDA` / `Amanda` / `amanda` | Resultados equivalentes (caixa ignorada) |
| 2.7 | Pesquisar termo inexistente (ex.: `zzz-inexistente`) | Mensagem "Nenhum colaborador encontrado." — sem erro |
| 2.8 | Limpar o campo e submeter | Lista completa retorna |
| 2.9 | Clicar no nome de um resultado | Detalhes do colaborador abrem normalmente (CA-010) |
| 2.10 | Usar "Ver Bens" / editar em um resultado | Comportamento existente preservado |
| 2.11 | Comparar URL | Busca refletida em `?search=...` (possível favoritar/compartilhar) |

## 3. Verificação de não-regressão (spot-check)

- Tela de **bens** continua pesquisando normalmente (nada mudou lá).
- API REST `GET /api/v1/custodians` responde igual (sem `search` adicionado).
- Usuário **sem** `colaboradores.visualizar` continua bloqueado na tela.

## 4. Checklist de conformidade (Constitution) — para a entrega

- [ ] Escopo: apenas service + rota da listagem + template + testes + docs (plan §9/§10)
- [ ] Comportamento existente preservado (suíte no estado conhecido; tela sem busca = atual)
- [ ] Regra de filtro na camada de serviço; sem duplicação em rota/template/JS
- [ ] Banco: nenhum DDL; apenas SELECT com filtro
- [ ] Permissão `colaboradores.visualizar` intacta (RN-002)
- [ ] Documentação atualizada na mesma tarefa (artigo de ajuda + §12.4)
