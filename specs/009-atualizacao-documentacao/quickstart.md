# Quickstart: Validação da Atualização Documental (feature 009)

Protocolo de validação de ponta a ponta. Executar após o `/speckit-implement`.

## 1. Pré-requisitos

- Ambiente do projeto ativo (Python 3.10+; dependências instaladas).
- Suíte de referência executada **antes** da edição (baseline: **281 passed / 1 failed** — lockout defasado conhecido).
- Aplicação executável localmente para abrir a `/ajuda` no navegador (banco configurado via `DATABASE_URL`).

## 2. Validação automatizada (não-regressão)

```bash
# Suíte completa — deve permanecer no patamar da baseline (nenhum teste novo, nenhum teste editado)
python3 -m pytest tests/ -q --tb=no

# Foco da ajuda — deve estar 100% verde
python3 -m pytest tests/test_help.py -q
```

Esperado: **281 passed / 1 failed** (a mesma falha pré-existente de lockout); `test_help.py` verde.

## 3. Validação manual (navegador)

Login com usuário que tenha acesso à ajuda; abrir **`/ajuda`**.

| # | Passo | Resultado esperado |
|---|---|---|
| 3.1 | Abrir o artigo "Como exportar os dados em CSV" | Texto menciona **locais** entre as exportações (botão na tela de Locais, arquivo `locais.csv`, conjunto completo, sem colunas de interface, permissão de exportação) |
| 3.2 | Abrir o artigo "Como cadastrar locais e departamentos" | Pesquisa de locais (007) e exportação de locais (008) documentadas, coerentes com a tela real |
| 3.3 | Abrir o artigo "Como cadastrar colaboradores (custodiantes)" | Pesquisa de colaboradores (006) conforme comportamento real (termo único: matrícula/nome/cargo/departamento/e-mail) |
| 3.4 | Usar a pesquisa da central de ajuda (ex.: "exportar", "locais") | Artigos alterados aparecem nos resultados (keywords coerentes) |
| 3.5 | Percorrer os demais artigos alterados | Nenhum passo descreve botão/campo/fluxo inexistente; formatação, ícones e estrutura idênticos ao padrão |
| 3.6 | Verificar que nenhuma credencial/IP real aparece nos textos | Exemplos usam placeholders fictícios |

## 4. Validação do README (revisão de consistência)

| # | Verificação | Resultado esperado |
|---|---|---|
| 4.1 | Contagem de testes citada vs. `pytest` executado | Coerentes (e o texto explica como obter o número atual) |
| 4.2 | Padrões `APP_HOST`/`APP_PORT` citados vs. `app/config.py` | Idênticos |
| 4.3 | Tabela de endpoints protegidos | Inclui `GET /api/v1/reports/locations/csv` (`relatorios.exportar`) |
| 4.4 | Seção "Instalação em uma máquina nova" | Cobre os 11 pontos (pré-requisitos → validação), sem comando inventado; `DATABASE_URL` obrigatória; 3 caminhos reais de primeiro admin (env, `/setup`, CLI); zero credenciais reais |
| 4.5 | Seguir o guia de instalação em máquina/ambiente limpo (quando possível) | Sistema sobe com `python run.py`, banco estruturado automaticamente, login do admin criado funciona |
| 4.6 | Funcionalidades listadas | Incluem 006/007/008 e Etiquetas em lote; nada inexistente listado |

## 5. Escopo de arquivos (fechamento)

```bash
git status --porcelain
```

Esperado (além de itens pré-existentes fora da feature): **somente** `app/services/help_service.py` e `README.md` modificados + artefatos de `specs/009-atualizacao-documentacao/`. Nenhum arquivo de código, teste, template ou config alterado.

**Critério de pronto**: §2 verde no patamar da baseline + §3/§4 sem falhas + §5 confirmado.
