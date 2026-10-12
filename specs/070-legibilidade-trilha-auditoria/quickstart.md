# Quickstart — Validação da Feature 070

Guia de validação ponta a ponta. Comandos executados da **raiz do repositório**. Não contém implementação — só cenários, comandos e resultados esperados (detalhes em `contracts/` e `data-model.md`).

## 0. Pré-requisitos

- Ambiente do projeto instalado (`.venv` com `requirements.txt`; ver `README.md`).
- Suíte existente verde antes de começar (baseline): `python -m pytest tests/ -q`.
- Cenário de dados: usuário com permissões `patrimonio.visualizar` + `patrimonio.editar` (padrão da suíte).

## 1. Testes automatizados (fonte primária de verdade)

```bash
# Arquivo novo da feature (red→green + guardas)
python -m pytest tests/test_legibilidade_trilha_070.py -q

# Régua de regressão — contratos congelados (devem passar SEM edição)
python -m pytest tests/test_api.py tests/test_movements.py tests/test_datetime_flows.py -q
python -m pytest tests/test_presentacao_trilha_063.py tests/test_fluxo_global_064.py tests/test_consulta_edicao_bens_067.py -q

# Suíte completa (Constitution VIII)
python -m pytest tests/ -q
```

**Esperado**: 100% passed; nenhum arquivo de teste existente modificado (`git status` limpo fora dos arquivos da feature).

## 2. Smoke visual (comportamento observável)

1. Autenticar e abrir `/assets` → criar ou escolher um bem.
2. Editar o cadastro em `/assets/{id}/edit` alterando **um** campo (ex.: nome: `Notebook X` → `Notebook Y`) e salvar.
3. Abrir `/assets/{id}` e localizar o evento na **Trilha de Fluxo & Movimentações**:
   - **Antes (atual)**: `Descrição: Campos alterados: name` + dois JSONs completos lado a lado.
   - **Esperado (feature)**: título `Alteração cadastral — Nome do bem`; linha no padrão do painel: `Nome do bem: ~~Notebook X~~ → **Notebook Y**`; **sem** JSON como conteúdo principal; controle `Ver detalhes técnicos` **recolhido**.
4. Expandir "Ver detalhes técnicos": JSON original **Antes** e **Depois** completos, distinguíveis, com quebra de linha (sem rolagem horizontal).
5. Editar **vários** campos de uma vez → título `Alteração cadastral — Dados do equipamento` e todos os campos alterados listados; campos inalterados ausentes.
6. Conferir preservação: painel "Alterações cadastrais" acima idêntico; cartões de movimentação (Origem → Destino) idênticos; data/hora no fuso local; "Registrado por" correto.

## 3. Guardas de integridade (executar após o smoke)

```bash
# (a) Nenhum registro alterado — conferir direto no banco de teste/prova:
python -m pytest tests/test_legibilidade_trilha_070.py -q -k nao_mutacao

# (b) Payload da API idêntico:
python -m pytest tests/test_legibilidade_trilha_070.py -q -k payload_api
```

**Esperado**: ambas verdes — `audit_logs` byte-a-byte e payload `/api/v1/assets/{id}/timeline` com as mesmas chaves/valores de antes.

## 4. Cenários de borda obrigatórios (cobertos no arquivo de testes)

| Cenário | Esperado |
|---|---|
| Evento histórico com JSON inválido em `previous_data` | Cartão idêntico ao atual (fallback), sem erro 500 |
| Evento com apenas um estado (ex.: só `new_data`) | Sem resumo de diff; estado disponível nos detalhes |
| Valor nulo / chave ausente | `—` dos dois lados; distinção apenas no JSON original |
| `<script>` em `notes` (payload hostil) | Texto escapado, sem execução |
| Campo desconhecido (chave fora de `_ASSET_FIELD_LABELS`) | Exibido pelo nome técnico; cartão não quebra |
| Texto longo / acentos / aspas | Quebra de linha; conteúdo preservado |

## 5. Rollback

A feature não toca banco nem gravação: remover/evitar os 3 arquivos alterados (service, rota, template) restaura o comportamento atual por completo.
