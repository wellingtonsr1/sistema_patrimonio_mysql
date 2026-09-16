# Quickstart: Validação da Pesquisa de Locais (feature 007)

Protocolo de validação de ponta a ponta. Executar após o `/speckit-implement`; os cenários manuais (§3) confirmam os critérios de UX (SC-001) que testes automatizados não medem.

## 1. Pré-requisitos

- Ambiente do projeto ativo; banco configurado via `DATABASE_URL` (MariaDB — Constitution VII; SQLite só na suíte de testes).
- Usuário com permissão `locais.visualizar` para os cenários manuais.
- Alguns locais cadastrados (idealmente com nomes no formato real, ex.: "IPMJP – Acessoria de Controle Interno", "IPMJP – Acessoria de Gabinete").

## 2. Validação automatizada

```bash
# Suíte da feature (deve estar 100% verde)
python -m pytest tests/test_locations_search.py -q

# Suíte completa (baseline: 245 passed / 1 failed conhecido — lockout defasado; a feature não pode alterar esse patamar além dos testes novos)
python -m pytest tests/ -q --tb=no
```

Esperado: todos os testes novos de `test_locations_search.py` passando; suíte completa no patamar baseline + testes novos; **nenhum teste existente quebrado**.

## 3. Cenários manuais (navegador)

Login como usuário com `locais.visualizar` e abrir **Locais & Departamentos** (`/locations`).

| # | Passo | Resultado esperado |
|---|---|---|
| 3.1 | Abrir a tela | Card de filtros separado (fora do card da tabela) com campo de pesquisa + **Filtrar** (com ícone de funil) + **Limpar** (somente texto, sem ícone); tabela com as 7 colunas atuais |
| 3.2 | Pesquisar `Controle` | Somente locais cujo Nome / Identificação contém "Controle" (ex.: "IPMJP – Acessoria de Controle Interno"); campo continua preenchido; URL contém `?search=Controle` |
| 3.3 | Pesquisar `CONTROLE` / `controle` | Resultados idênticos aos de 3.2 (case-insensitive) |
| 3.4 | Pesquisar `IPMJP` | Todos os locais do exemplo (sigla presente no nome) |
| 3.5 | Pesquisar `Gabinete` | "IPMJP – Acessoria de Gabinete" aparece (parcial, qualquer posição) |
| 3.6 | Pesquisar termo que existe só no Departamento/Filial (ex.: nome do departamento de um local cujo *nome* não o contém) | **Nenhum resultado** — confirma alvo exclusivo no Nome / Identificação |
| 3.7 | Pesquisar termo inexistente (`zzz-xxx`) | Banner/estado: **"Nenhum local encontrado."** — sem erro, HTTP 200 |
| 3.8 | Digitar termo com espaços nas pontas (`  Controle  `) | Pesquisa considera `Controle` (aparado) |
| 3.9 | Limpar o campo e clicar em Filtrar (ou clicar em **Limpar**) | Lista completa volta, na ordenação atual |
| 3.10 | Em um resultado, clicar **Ver Bens** | Navega para `/assets?location_id=<id>` como antes; contagem de bens do card bate com a listagem completa |
| 3.11 | F5 na URL com `?search=...` | Resultado recarrega idêntico (GET compartilhável) |
| 3.12 | (Opcional) Usuário sem `locais.visualizar` | Acesso segue bloqueado (403), com ou sem `search` |

## 4. Spot-checks de não regressão (contrato §5)

1. `GET /locations` sem `search` — tela idêntica ao comportamento pré-feature (dados, ordem, contagens).
2. `GET /api/v1/locations` — resposta inalterada (API não expõe `search`).
3. Formulários e seletores que usam locais (bens, movimentações, inventário) — sem mudança de comportamento.

## 5. Checklist Constitution (resumo pós-implementação)

- [ ] Escopo: somente service/rota/template/testes/docs previstos
- [ ] Regra do filtro no service (não na rota/template)
- [ ] Zero DDL; MariaDB no manual, SQLite só nos testes
- [ ] Nenhum teste existente alterado; suíte verde
- [ ] Docs na mesma tarefa (ajuda embutida + §12.4 do doc de arquitetura)
- [ ] Nenhuma permissão nova; gate `locais.visualizar` intacto

**Critério de pronto (spec §DoD)**: §2 verde + §3 sem falhas + §4 sem divergências.
