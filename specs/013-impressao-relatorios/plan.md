# Implementation Plan: Correção da Impressão A4 dos Relatórios

**Branch**: `013-impressao-relatorios` | **Date**: 2026-09-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/013-impressao-relatorios/spec.md`

## Summary

Corrigir **exclusivamente a apresentação de impressão** dos três relatórios (Trilha de Auditoria & Fluxo, Relação de Colaboradores e Relatório Contábil-Físico), que hoje geram primeira página em branco, truncamento lateral e quebras degradadas em A4. A causa é 100% de CSS: o `<body style="padding-top: 90px">` inline de `base.html` (não neutralizado na impressão), `py-4` no `<main>`, `table-layout: fixed` dentro de `.table-responsive`, `.truncate-2`/`text-nowrap` ocultando conteúdo no papel e `.card { page-break-inside: avoid }` forçando o card inteiro numa página. A abordagem — aprendida do bloco de Etiquetas (referência funcional) — é um **novo bloco `@media print` dedicado aos relatórios**, adicionado ao final de `style.css` sem editar regras existentes, com `@page { size: A4 }`, neutralização dos espaçamentos herdados, largura integral sem espremimento, liberação dos mecanismos de corte de tela, `thead { display: table-header-group }` e `tr { break-inside: avoid }`. Zero alteração em consultas, permissões, filtros, dados, `base.html`, Etiquetas ou Termo.

## Technical Context

**Language/Version**: Python 3.10+ (backend intocado nesta feature); HTML5/CSS3 (área da correção)

**Primary Dependencies**: Bootstrap 5 (classes `page-header`, `card`, `table`, `table-responsive`), Jinja2, tema claro/escuro próprio com CSS variables

**Storage**: N/A (nenhuma consulta, modelo ou banco é tocado)

**Testing**: pytest (suíte existente como guarda de não-regressão funcional); validação de impressão é manual/visual na pré-visualização do navegador (Chrome/Chromium e Firefox), pois pytest não renderiza layout

**Target Platform**: Navegadores desktop Chrome/Chromium e Firefox — diálogo de impressão A4 (função `window.print()` já existente nos templates)

**Project Type**: Monolítico web (`app/web` com templates Jinja2 + CSS estático)

**Performance Goals**: N/A (impressão de página já renderizada; sem impacto de tempo de resposta)

**Constraints**: Nenhuma regra `@media print` existente pode ser editada (Termo e Etiquetas); o CSS novo não pode depender de `:has()` (compatibilidade Firefox); nenhuma mudança visual em tela (somente impressão)

**Scale/Scope**: 3 templates de relatório + 1 arquivo CSS (novo bloco no final); zero mudança em rota, service, model, schema ou teste existente

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação pré-design | Avaliação pós-design |
|---|---|---|
| I. Preservação e evolução incremental | ✅ Correção restrita à apresentação; nada reescrito | ✅ **Re-verificado**: novo bloco CSS aditivo + (se necessário) classe de escopo nos 3 templates; nenhum arquivo fora do escopo |
| II. Arquitetura em camadas | ✅ Nenhuma regra de negócio envolvida | ✅ Confirmado — zero Python alterado |
| III. Regras nos services | ✅ N/A (nenhuma regra nova de negócio) | ✅ Confirmado |
| IV/V. Integridade patrimonial/inventário | ✅ N/A (impressão não altera dados) | ✅ Confirmado — dados exibidos idênticos |
| VI. Segurança (auth/RBAC/AD) | ✅ Permissões e rotas intocadas | ✅ Confirmado |
| VII. Banco de dados | ✅ Zero DDL | ✅ Confirmado |
| VIII. Testes como não-regressão | ✅ Suíte como guarda; validação de impressão manual | ✅ Confirmado — nenhum teste editado; arquivo novo de testes só se houver comportamento pytest-verificável |
| IX. Auditoria | ✅ N/A | ✅ Confirmado |
| X. Interface consistente | ✅ Bootstrap e padrões visuais preservados em tela; impressão segue a boa prática das Etiquetas | ✅ Confirmado — tema escuro na impressão continua forçando paleta clara (bloco PRINT II intacto) |
| XI. Documentação fiel | ⚠️ A verificar: docs podem citar impressão dos relatórios | ✅ Re-verificado na Fase 1 (R8): README/docs/ajuda não documentam comportamento de impressão dos 3 relatórios → nenhuma atualização obrigatória; se a implementação alterar algo visível documentado, atualiza na mesma tarefa |
| XII. Especificação e validação | ✅ Fluxo Spec Kit em curso; validação manual definida no quickstart | ✅ Confirmado |

**GATE: PASS** (pré e pós-design) — nenhuma violação.

## Project Structure

### Documentation (this feature)

```text
specs/013-impressao-relatorios/
├── plan.md              # This file
├── research.md          # Phase 0 output — decisões verificadas no código
├── css-contract.md      # Phase 1 output — contrato do novo bloco @media print (no lugar de contracts/)
├── quickstart.md        # Phase 1 output — roteiro de validação de impressão
└── tasks.md             # Phase 2 output (/speckit-tasks — não criado aqui)
```

### Source Code (repository root)

```text
app/web/
├── static/css/style.css                # ALTERADO: novo bloco @media print dos relatórios (final do arquivo)
└── templates/reports/
    ├── movements_report.html            # ALTERÁVEL (só se necessário): classe de escopo no container
    ├── custodians_report.html           # ALTERÁVEL (só se necessário): idem
    └── inventory.html                   # ALTERÁVEL (só se necessário): idem

# INTOCADOS (garantias da feature):
app/web/templates/base.html             # neutralização do padding inline é via CSS, não editando o shell
app/web/templates/assets/labels.html    # referência funcional — sem alteração
app/web/templates/movements/term.html   # Termo — sem alteração
# Regras @media print existentes (linhas ~896, ~1476, ~1588 de style.css): sem edição
```

**Structure Decision**: correção concentrada em **um arquivo CSS** (novo bloco aditivo no final de `style.css`), ancorada por seletor de escopo das páginas de relatório; templates de relatório recebem apenas uma classe de escopo se o CSS puro não conseguir endereçar as páginas (decisão R2). Nenhum outro diretório é tocado.

## Complexity Tracking

> Nenhuma violação de Constitution — tabela não utilizada.
