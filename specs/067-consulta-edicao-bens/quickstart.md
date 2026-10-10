# Quickstart — Validação da 067-consulta-edicao-bens

Guia executável para provar a feature de ponta a ponta **após a implementação**. Contrato do fluxo em [contracts/web-asset-edit-contract.md](contracts/web-asset-edit-contract.md); o que permanece intacto em [contracts/asset-edit-preserved-contracts.md](contracts/asset-edit-preserved-contracts.md); regras e campos em [data-model.md](data-model.md).

> ✅ **Estado atual: implementada e validada (2026-10-10).** Resultado da execução: `tests/test_consulta_edicao_bens_067.py` **21 passed**, manifesto de rotas **1 passed**, réguas de regressão **201 passed**, suíte completa **1005 passed / 2 skipped** (baseline 979). Registro detalhado em [validacao.md](validacao.md) — inclusive a ressalva de que os cenários de navegador (§2–§4) não foram executados neste ambiente e a decisão registrada de o histórico cadastral considerar apenas `ALTERACAO`.

## Pré-requisitos

- Dependências do projeto instaladas no ambiente do repositório (`.venv`).
- Suíte rodando sem `DATABASE_URL` de produção (SQLite in-memory por `tests/conftest.py`, padrão da casa).
- Pendências **P1–P5** da spec §14 aprovadas pelo responsável.
- Implementação aplicada nos arquivos da spec §11 (detalhe + edição + service + manifesto + docs).

## 1. Validação automatizada (obrigatória)

```bash
# Suíte nova da feature (AC01–AC15)
.venv/bin/python -m pytest tests/test_consulta_edicao_bens_067.py -v
```

Esperado: **todos passed** — consulta completa, campos vazios omitidos, 403/404, edição atualizando o mesmo registro, série duplicada rejeitada, limites/valor negativo rejeitados, campos protegidos ignorados, auditoria before/after, "nada mudou" sem gravação, falha sem estado parcial, operador autenticado na movimentação de condição, histórico separado e vazio sem erro.

```bash
# Manifesto de rotas (feature 051) — as rotas novas precisam estar registradas
.venv/bin/python -m pytest tests/test_route_inventory.py -v
```

Esperado: **passed** (manifesto atualizado com `GET`/`POST /assets/{asset_id}/edit`).

```bash
# Réguas de regressão (sem editar nenhum teste existente)
.venv/bin/python -m pytest tests/test_assets.py tests/test_api.py tests/test_rbac.py \
  tests/test_import_asset_location.py tests/test_import_asset_movements.py \
  tests/test_movements.py tests/test_localizacao_automatica_066.py \
  tests/test_presentacao_trilha_063.py tests/test_fluxo_global_064.py -v
```

Esperado: **0 falhas novas** em relação ao baseline registrado no Setup.

```bash
# Régua completa
.venv/bin/python -m pytest
```

Esperado: mesmo patamar do baseline (nenhuma regressão; falhas ambientais pré-existentes, se houver, devem ser exatamente as mesmas já documentadas em `specs/063/validacao.md`).

## 2. Validação manual no navegador (recomendada)

**Consulta (US1)**
1. Subir o app (`.venv/bin/python run.py`) em ambiente de demonstração.
2. Login com perfil **Técnico de TI** (somente `patrimonio.visualizar`) → abrir **Bens** → "Ver Detalhes" de um bem completo.
3. Conferir: tombamento, nome, categoria, situação, condição, marca, modelo, nº de série, especificações, data/valor de aquisição, NF, fornecedor, garantia, **observações** e **última atualização**; localização com unidade/departamento e responsável atual.
4. Abrir um bem **sem** especificações/observações → os campos aparecem como não informados, sem dado fictício.
5. Conferir que a ação **"Editar bem" não aparece** para esse perfil (e que forçar a URL `/assets/{id}/edit` responde 403 amigável).

**Edição (US2)** — repetir com perfil **Patrimônio** (ou Gestor de TI)
6. Abrir o detalhe → **Editar bem** visível → alterar **nome**, **marca**, **modelo**, **nº de série** e **especificações** → salvar.
7. Conferir que o **mesmo bem** (mesmo tombamento/URL) exibe os novos valores e que a **contagem de bens não mudou** (nenhum duplicado).
8. Tentar salvar o **nº de série de outro bem** → mensagem de duplicidade; nada muda.
9. Tentar **valor de aquisição negativo** e **texto acima do limite** → mensagem clara; nada é gravado.
10. Salvar **sem alterar nada** → aviso de que nada mudou; **nenhum** evento novo no histórico.
11. Alterar a **condição** → salvar → conferir no histórico de movimentações que a `ATUALIZACAO_ESTADO` registra **o seu usuário** (não "Sistema").
12. Abrir o mesmo bem em **duas abas**, salvar na primeira e depois na segunda → a segunda deve **avisar conflito** (nada sobrescrito em silêncio) *(P3)*.
13. Bem com situação **Baixado** → conferir o comportamento decidido em P4 (bloqueio, por padrão).
14. Conferir que **localização, unidade, departamento, responsável e situação** não aparecem como campos editáveis no formulário.

**Histórico (US3)**
15. Após as edições acima, conferir o **Histórico de alterações cadastrais** com campo → de → para, autor e data.
16. Conferir que alterações cadastrais e movimentações aparecem **separadas**.
17. Abrir o detalhe de um bem **sem** alterações → estado vazio claro, sem erro.

**Responsividade (AC14)**
18. Reduzir a janela para **360 px** (breakpoints `sm`/`md`): detalhe e formulário de edição continuam utilizáveis, sem sobreposição (SC-010/AC14 — T028).

## 3. Verificação de integridade (somente leitura)

```bash
# Contagens antes/depois de uma edição manual (SEM escrita): bens, movimentações e itens de inventário
.venv/bin/python -c "import os;from dotenv import load_dotenv;load_dotenv();\
from sqlalchemy import create_engine,text;\
c=create_engine(os.getenv('DATABASE_URL')).connect();\
print('assets:',c.execute(text('SELECT COUNT(*) FROM assets')).scalar());\
print('movements:',c.execute(text('SELECT COUNT(*) FROM movements')).scalar());\
print('inventario_itens:',c.execute(text('SELECT COUNT(*) FROM inventario_itens')).scalar())"
```

Esperado: `assets` inalterado após edições (a edição não cria bem); `movements` inalterado, exceto **+1** por mudança de condição; `inventario_itens` inalterado.

```bash
# Auditoria da edição (1 evento ALTERACAO por salvamento efetivo, com before/after)
.venv/bin/python -c "import os;from dotenv import load_dotenv;load_dotenv();\
from sqlalchemy import create_engine,text;\
c=create_engine(os.getenv('DATABASE_URL')).connect();\
r=c.execute(text(\"SELECT timestamp,username,action,resource,resource_id,description FROM audit_logs WHERE module='Patrimônio' AND resource='Asset' AND action='ALTERACAO' ORDER BY id DESC LIMIT 5\"));\
[print(x) for x in r]"
```

Esperado: um evento por salvamento efetivo, com o **usuário autenticado** e a descrição listando os campos alterados.

## 4. Verificação do contrato da API (preservado)

```bash
# PUT da API continua aceitando o payload atual (nada de 422 novo)
.venv/bin/python -m pytest tests/test_api.py -k asset -v
```

Esperado: passed. O contrato de `PUT /api/v1/assets/{id}` segue o documentado em [contracts/asset-edit-preserved-contracts.md](contracts/asset-edit-preserved-contracts.md) §1.

## 5. Critério de pronto

- [ ] Suíte nova verde (AC01–AC15) · [ ] `test_route_inventory.py` verde com manifesto atualizado
- [ ] Réguas de regressão e régua completa sem regressões em relação ao baseline
- [ ] Cenários manuais 2.1–2.18 passam (incluindo P3/P4 conforme decisão)
- [ ] Contagens de `assets`/`movements`/`inventario_itens` conforme o §3 (nenhum dado histórico reescrito)
- [ ] Nenhum evento de auditoria órfão; um evento por edição efetiva
- [ ] `docs/ARQUITETURA_E_MANUTENCAO.md` e central de ajuda atualizados (Constitution XI)
- [ ] `git diff` limitado aos arquivos da spec §11 — **zero DDL, zero migração, zero dependência nova**
