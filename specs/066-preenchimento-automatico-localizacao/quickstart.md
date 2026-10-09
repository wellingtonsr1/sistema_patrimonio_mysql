# Quickstart — Validação da 066-preenchimento-automatico-localizacao

Guia executável para provar a feature de ponta a ponta. Detalhes de contrato em [contracts/web-location-form-contract.md](contracts/web-location-form-contract.md); entidades em [data-model.md](data-model.md).

## Pré-requisitos

- Dependências do projeto instaladas (ambiente do repositório; **sem** `DATABASE_URL` definida — a suíte usa SQLite in-memory, padrão da casa: `tests/conftest.py`).
- Spec aprovada (2026-10-09) e implementação aplicada nos 3 arquivos de produção da spec §11.

## 1. Validação automatizada (obrigatória)

```bash
# Suite nova da feature (AC01–AC06 + guarda de API)
python -m pytest tests/test_localizacao_automatica_066.py -v
```

Esperado: todos os testes novos **passed** (render da composição, POST adulterado recomposto, incompletos bloqueados, duplicidade, nome >100 chars, API PUT intacta).

```bash
# Réguas de regressão sem edição (AC09/AC12)
python -m pytest tests/test_locations_search.py tests/test_movements.py \
  tests/test_department_selection.py tests/test_import_asset_location.py \
  tests/test_import_asset_movements.py tests/test_departamento_destino_062.py \
  tests/test_presentacao_trilha_063.py tests/test_fluxo_global_064.py -v
```

Esperado: **0 falhas** (nenhum teste existente editado).

```bash
# Régua completa
python -m pytest
```

Esperado: mesmo patamar da última régua da casa (sem regressões novas; failures ambientais pré-existentes, se houver, devem ser os mesmos registrados em `specs/063/validacao.md`).

## 2. Validação manual no navegador (recomendada)

1. Subir o app (`python run.py`) com ambiente de teste/demonstração.
2. Login com usuário de permissão `locais.criar` → **Locais → Cadastrar Novo Local** (`/locations/new`).
3. Digitar somente a Unidade → campo **Localização permanece vazio**; tentar salvar → navegador bloqueia (required).
4. Digitar também o Departamento → Localização mostra `Unidade - Departamento` **a cada tecla**; campo é `readonly` (não editável).
5. Salvar → redireciona para `/locations` com o novo local no padrão; conferir na listagem.
6. Repetir os mesmos dois valores → mensagem "Já existe um local cadastrado com este nome"; **nenhum** registro criado.
7. (Opcional, anti-falsificação) Enviar via `curl` um POST com `name` divergente:
   `curl -X POST …/locations/new -d "name=HACK&branch=UNID TESTE&department=SETOR TESTE"` autenticado → conferir no banco que gravou `UNID TESTE - SETOR TESTE`.

## 3. Verificação de preservação de dados (somente leitura)

```bash
# Contagem e padrão dos nomes antes/depois da implementação (sem escrita)
python -c "import os;from dotenv import load_dotenv;load_dotenv();\
from sqlalchemy import create_engine,text;\
c=create_engine(os.getenv('DATABASE_URL')).connect();\
print('total:',c.execute(text('SELECT COUNT(*) FROM locations')).scalar());\
print('fora do padrao:',c.execute(text(\"SELECT COUNT(*) FROM locations WHERE name<>CONCAT(TRIM(branch),' - ',TRIM(department))\")).scalar())"
```

Esperado: `total` igual ao antes (37 + cadastros novos) e `fora do padrao` = **0** em qualquer momento (nenhum registro antigo alterado — AC10/AC11).

## 4. Critério de pronto

- [ ] Suite nova verde · [ ] Réguas verdes · [ ] Régua completa sem regressões
- [ ] Cenários manuais 2.1–2.6 passam
- [ ] Verificação 3: nenhum registro fora do padrão e nenhum UPDATE executado
- [ ] `docs/ARQUITETURA_E_MANUTENCAO.md` §12.4 atualizado (Constitution XI)
- [ ] `git diff` limitado aos arquivos da spec §11
