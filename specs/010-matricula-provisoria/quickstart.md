# Quickstart: Validação do Identificador Provisório de Colaborador (feature 010)

Protocolo de validação de ponta a ponta. Executar após o `/speckit-implement`.

## 1. Pré-requisitos

- Ambiente do projeto ativo (Python 3.10+; dependências instaladas).
- Baseline executada antes da edição: **281 passed / 1 failed** (lockout defasado conhecido).
- Aplicação executável localmente (`python run.py`; banco via `DATABASE_URL`) com usuário com permissões `colaboradores.criar` e `colaboradores.editar` (e um segundo usuário sem elas para o teste de permissão, se desejar).

## 2. Validação automatizada (TDD + não-regressão)

```bash
# Arquivo novo da feature — deve estar 100% verde
python -m pytest tests/test_custodian_provisional.py -q

# Suíte completa — patamar da baseline + testes novos, nenhum failure novo
python -m pytest tests/ -q --tb=no
```

Esperado: testes novos verdes; suíte com **nenhum failure novo** além do lockout defasado; `test_help.py` verde (docs da ajuda atualizadas).

## 3. Validação manual (navegador)

Login com usuário autorizado (`colaboradores.criar`/`colaboradores.editar`).

| # | Passo | Resultado esperado |
|---|---|---|
| 3.1 | Colaboradores → Novo Colaborador: preencher nome, e-mail, cargo, departamento **deixando a Matrícula em branco**; salvar | Colaborador criado com matrícula `PROV-000001` (ou próximo sequencial) e marcação **"provisória"** visível na listagem/detalhes |
| 3.2 | Repetir o cadastro sem matrícula | Novo colaborador recebe o **próximo** número (`PROV-000002`) — nunca repetido |
| 3.3 | Tentar cadastrar digitando manualmente `PROV-000999` | Rejeitado com mensagem no padrão do sistema (sem gravar) |
| 3.4 | Pesquisar por `PROV-000001` (ou `PROV`) | Colaborador provisório encontrado (pesquisa 006) |
| 3.5 | Movimentar um bem: Alocação/Cautela para o colaborador provisório | Movimentação registrada normalmente (nenhum bloqueio por ser provisório); histórico exibe o colaborador com sua identificação |
| 3.6 | Emitir o termo de responsabilidade/cautela | Termo gerado normalmente, com a identificação do colaborador e a marcação de provisória |
| 3.7 | No cadastro do colaborador provisório, editar e informar a matrícula oficial (ex.: `123456`) | Substituição aceita; o **mesmo** colaborador exibe `123456` sem marcação de provisória; bens custodiados permanecem vinculados; nenhum colaborador novo foi criado |
| 3.8 | Consultar o histórico de movimentações anteriores à substituição | Snapshots antigos permanecem como gravados na época (imutáveis); novo termo emitido agora exibe a matrícula oficial |
| 3.9 | Abrir um colaborador com matrícula oficial para edição | Matrícula **readonly** (comportamento atual preservado — a edição de matrícula só existe para `PROV-*`) |
| 3.10 | Conferir a ajuda embutida (`/ajuda` → artigo de colaboradores) | Documenta o identificador provisório (quando é gerado, como aparece, como substituir) |

## 4. Validação via API (opcional, com sessão)

```bash
# Criar sem matrícula → 201 com PROV-* no registration_code
curl -b cookies.txt -X POST http://localhost:8000/api/v1/custodians \
  -H "Content-Type: application/json" \
  -d '{"name":"Fulano Provisorio","email":"fulano.prov@empresa.local","role":"Técnico","department":"TI"}'

# Tentar fabricar PROV-* → 400
curl -b cookies.txt -X POST http://localhost:8000/api/v1/custodians \
  -H "Content-Type: application/json" \
  -d '{"registration_code":"PROV-000123","name":"X","email":"x1@empresa.local","role":"T","department":"D"}'
```

## 5. Escopo de arquivos (fechamento)

```bash
git status --porcelain
```

Esperado (além de itens pré-existentes fora da feature): **somente** os arquivos do plan §Source Code — `app/schemas/custodian.py`, `app/services/custodian_service.py`, `app/web/routes.py`, templates de colaboradores/bens/movimentações (marcação), `tests/test_custodian_provisional.py` (novo), `app/services/help_service.py`, `README.md` + artefatos de `specs/010-matricula-provisoria/`. **Zero** models/migrations, `ad_service.py`, `custodian_import_service.py`, autenticação, RBAC.

**Critério de pronto**: §2 verde no patamar da baseline + testes novos verdes + §3/§4 sem falhas + §5 confirmado.
