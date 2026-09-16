# Quickstart: Validação da Exportação CSV de Locais (feature 008)

Protocolo de validação de ponta a ponta. Executar após o `/speckit-implement`; os cenários manuais (§3) confirmam a experiência real de download e abertura no Excel (SC-002).

## 1. Pré-requisitos

- Ambiente do projeto ativo; banco configurado via `DATABASE_URL` (MariaDB — Constitution VII; SQLite só na suíte de testes).
- Dois usuários de teste: um **com** `relatorios.exportar` (ex.: Administrador) e um **sem** (ex.: perfil Técnico — padrão de `test_rbac.py`).
- Alguns locais cadastrados (idealmente com nomes contendo acentos, `;` e/ou aspas para o teste de escapamento).

## 2. Validação automatizada

```bash
# Suíte da feature (deve estar 100% verde)
python -m pytest tests/test_locations_export.py -q

# Suíte completa (baseline: 264 passed / 1 failed conhecido — lockout defasado; a feature soma testes sem alterar o patamar)
python -m pytest tests/ -q --tb=no
```

Esperado: todos os testes novos passando; suíte completa = baseline + testes novos; **nenhum teste existente quebrado**.

## 3. Cenários manuais (navegador)

Login com usuário que tenha `locais.visualizar` **e** `relatorios.exportar`; abrir **Locais & Departamentos** (`/locations`).

| # | Passo | Resultado esperado |
|---|---|---|
| 3.1 | Observar o cabeçalho da tela | Botão **"Exportar CSV"** visível, com ícone de upload e estilo idêntico ao das telas de Colaboradores/Movimentações/Dashboard, à esquerda dos botões de Importar/Cadastrar |
| 3.2 | Clicar em "Exportar CSV" | Download inicia imediatamente; arquivo salvo como **`locais.csv`** |
| 3.3 | Abrir o arquivo em editor de texto | 1ª linha: `nome;filial;departamento;predio;andar;sala;gestor`; separador `;`; sem colunas "Ações" ou "Bens" |
| 3.4 | Comparar com a tabela | Um linha por local, mesmos dados, **mesma ordem** da listagem (filial, departamento, nome); campos vazios em branco |
| 3.5 | Abrir o arquivo no Excel | Acentos exibidos corretamente (UTF-8 BOM); colunas separadas por `;` |
| 3.6 | Local com `;` ou aspas no nome | Valor escapado no CSV; abre como uma célula única no Excel |
| 3.7 | Voltar à tela e usar a pesquisa (007) | Tela continua funcionando normalmente; a exportação não é afetada por filtros ativos |
| 3.8 | Exportar novamente após criação de um novo local | Novo local aparece no CSV (sempre exporta todos) |
| 3.9 | Login com usuário **sem** `relatorios.exportar` | Botão **não aparece** na tela; acesso direto a `/api/v1/reports/locations/csv` → **403** |
| 3.10 | (Opcional) Sem sessão (URL anônima) | Acesso direto ao endpoint → **401** |
| 3.11 | Verificar os dados após exportações repetidas | Nada criado/alterado/excluído — contagem de locais inalterada |

## 4. Spot-checks de não regressão (contrato §5)

1. Telas de Colaboradores/Movimentações/Dashboard: botões "Exportar CSV" e downloads existentes funcionam como antes.
2. `GET /api/v1/reports/custodians/csv` e `/api/v1/reports/inventory/csv` inalterados.
3. Tela de Locais: pesquisa (feature 007), tabela, contagem de bens e ações idênticos ao estado pós-007.

## 5. Checklist Constitution (resumo pós-implementação)

- [ ] Escopo: somente report_service.py, reports_api.py, locations/list.html, testes novos, docs previstos
- [ ] Geração CSV no ReportService (não na rota); sem nova forma de gerar CSV
- [ ] Zero DDL; MariaDB no manual, SQLite só nos testes
- [ ] Nenhum teste existente alterado; suíte verde
- [ ] Nenhuma permissão nova; gates `relatorios.exportar` (endpoint + botão) e `locais.visualizar` (tela) intactos
- [ ] Docs na mesma tarefa (ajuda embutida + §12.5 do doc de arquitetura)

**Critério de pronto (spec §DoD)**: §2 verde + §3 sem falhas + §4 sem divergências.
