# Quickstart: Matrícula Opcional na Importação CSV de Colaboradores

**Feature**: 014-matricula-opcional-importacao-csv

## Pré-requisitos

```bash
python3 -m venv .venv && source .venv/bin/activate   # se ainda não ativo
pip install -r requirements.txt
export DATABASE_URL_TEST="sqlite:///:memory:"        # suíte usa SQLite em memória
python3 -m pytest -q                                  # baseline antes de começar
```

> Baseline conhecido: 1 falha pré-existente `tests/test_rbac.py::test_lockout_after_failed_attempts` (RBAC lockout — fora do escopo, registrada desde a feature 012). Não interpretar como regressão desta feature.

## 1. Suíte automatizada

```bash
python3 -m pytest tests/test_custodian_import.py -q      # importador (existentes + novos T1–T8)
python3 -m pytest tests/test_custodian_provisional.py -q # feature 010 intacta (cadastro individual)
python3 -m pytest -q                                     # regressão completa
```

**Esperado**: todos os testes do importador passando, incluindo os 8 cenários do briefing; suíte completa verde exceto a falha pré-existente do baseline.

## 2. Cenários de teste do briefing (T1–T8 → automatizados)

| # | CSV de entrada | Resultado esperado |
|---|---|---|
| T1 | `MAT-1045` informada | colaborador com `MAT-1045`; não é provisória |
| T2 | célula vazia `""` | `PROV-\d{6}` gerada; sem erro de matrícula |
| T3 | só espaços `"   "` | tratada como ausente → `PROV-*` |
| T4 | coluna `matricula` ausente do CSV | importação válida; todos com `PROV-*` |
| T5 | linhas com e sem matrícula | informadas mantêm valor; ausentes recebem `PROV-*` |
| T6 | matrícula já existente no banco | regra atual: skip (ou update, conforme `skip_duplicates`); nunca vira `PROV-*` |
| T7 | várias linhas sem matrícula | cada uma com `PROV-*` distinta |
| T8 | regressão | suíte existente verde |

## 3. Validação manual (web — fluxo completo)

1. Fazer login com usuário com permissão `colaboradores.criar`.
2. Ir em **Colaboradores → Importar CSV**.
3. Conferir a documentação da tela: `matricula` listada como **opcional** com a observação "Se informada, será utilizada. Quando não informada, o sistema gerará automaticamente uma matrícula provisória, seguindo a mesma regra do cadastro individual."
4. Enviar um CSV misto (delimitador `;`):

   ```csv
   nome;email;matricula;cargo;setor
   João Silva;joao.silva@empresa.com;MAT-1045;Analista;TI
   Maria Souza;maria.souza@empresa.com;;Assistente;RH
   Pedro Santos;pedro.santos@empresa.com;MAT-1088;Analista;Patrimônio
   Ana Lima;ana.lima@empresa.com;   ;Coordenadora;Financeiro
   ```

5. **Preview esperado**: 4 registros, nenhum erro de matrícula; Maria e Ana aparecem com matrícula vazia (sem número inventado); duplicatas por e-mail continuam sinalizadas.
6. Confirmar a importação e abrir a lista de Colaboradores.
   - **Esperado**: João = `MAT-1045`; Maria e Ana = `PROV-xxxxxx` **distintas**; Pedro = `MAT-1088`.
7. Repetir com um CSV **sem a coluna `matricula`** (`nome;email;cargo;setor`) — importação válida, todos com `PROV-*` distintos.
8. Repetir com matrícula já cadastrada — **preview/execução** seguem a regra atual de duplicata (skip), sem substituição por provisória.
9. Conferir que os demais campos obrigatórios seguem validados: linha sem nome/e-mail/cargo/setor continua rejeitada, com as mensagens atuais.

## 4. Não-regressão (intocados)

- **Cadastro individual**: criar/editar colaborador com e sem matrícula (feature 010) — comportamento idêntico, inclusive a rejeição de valores informados iniciados por `PROV-`.
- **API REST de colaboradores**: intocada (matrícula opcional desde a feature 010); o endpoint de importação REST (`POST /api/v1/custodians/import/csv`) herda a nova regra pelos services compartilhados — validar cenário misto também por ele (opcional, coberto pelos testes de service).
- **Outros importadores** (equipamentos, locais): intactos.
- **Histórico patrimonial**: a geração de provisória na importação não altera movimentações/termos/inventário/auditoria.

## Definition of Done

- [ ] `python3 -m pytest -q` verde (exceto a falha pré-existente do baseline RBAC).
- [ ] Os 8 cenários T1–T8 automatizados e passando.
- [ ] Validação manual §3 concluída (fluxo web com importação mista).
- [ ] Documentação da tela de importação coerente com o comportamento (§3.3).
- [ ] `git diff` restrito a: `custodian_import_service.py`, fachada em `custodian_service.py`, `import.html` (documentação), `tests/test_custodian_import.py`.
