# Phase 1 Data Model: Contraste das Opções de Resultado da Conferência

**Feature**: 011-contraste-conferencia | **Date**: 2026-09-17

## Entidades de dados

**Nenhuma.** A feature é exclusivamente de apresentação visual (spec §Key Entities):

- Nenhum modelo SQLAlchemy é criado, alterado ou consultado.
- Nenhum schema Pydantic é alterado.
- Nenhuma tabela ou coluna é adicionada (zero DDL — Constitution VII).
- Nenhuma persistência ocorre: o formulário de conferência continua gravando pelos mesmos serviços com os mesmos valores.

## "Modelo" aplicável: estrutura visual do componente

Para fins de rastreabilidade, o único "estado" tocado é o atributo `class` dos 8 elementos:

| Elemento | Antes | Depois | Delta |
|---|---|---|---|
| 4× `<label>` em `inventarios/conferir.html` | `d-block border rounded p-2` | `d-block border rounded p-2 result-option` | +1 classe |
| 4× `<label>` em `inventarios/detail.html` (modal) | `d-block border rounded p-2` | `d-block border rounded p-2 result-option` | +1 classe |

Regras que governam a nova classe (definidas no plan §Technical Approach):

- `border: 1px solid var(--c-border) !important` — vence a utilitária `.border` do Bootstrap (ambas `!important`; `style.css` carregado depois).
- A cor resolve pelo tema ativo via mapeamento existente: claro → `#C8C2C0`, escuro → `#3A3335`.
- Nenhum estado (seleção/foco/hover) é redefinido; nada é removido.

## Transições de estado

Não aplicável — nenhum estado de negócio é afetado (o fluxo de conferência é intocado, Constitution V).
