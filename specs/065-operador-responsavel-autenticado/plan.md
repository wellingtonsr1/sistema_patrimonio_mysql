# Implementation Plan: Operador Responsável Vinculado ao Usuário Autenticado

**Branch**: `065-operador-responsavel-autenticado` | **Date**: 2026-10-09 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/065-operador-responsavel-autenticado/spec.md`

---

## Summary

Esta funcionalidade vincula automaticamente o campo **"Operador Responsável"** do formulário de movimentação patrimonial ao usuário autenticado na sessão atual (`current_user.full_name or current_user.username`). No front-end (Jinja2/Bootstrap), o campo passa a ser exibido com o valor preenchido e marcado como `readonly`. No back-end (FastAPI routers web e REST API), a identidade do operador é determinada e imposta exclusivamente a partir de `request.state.user`, neutralizando qualquer tentativa de manipulação via navegador (anti-spoofing). A alteração é 100% retrocompatível e não exige nenhuma modificação no esquema do banco de dados.

---

## Technical Context

**Language/Version**: Python 3.10+  
**Primary Dependencies**: FastAPI 0.100+, SQLAlchemy 2.0+, Pydantic v2, Jinja2 + Bootstrap 5  
**Storage**: MariaDB / MySQL (PyMySQL) em produção; SQLite em testes  
**Testing**: pytest (+ FastAPI TestClient)  
**Target Platform**: Linux / Windows Web Server  
**Project Type**: Web Application / REST API  
**Performance Goals**: Latência de processamento < 5ms (0 overhead adicional)  
**Constraints**: Nenhuma alteração no esquema do banco de dados (sem migrações); preservação total dos registros históricos de movimentação; cumprimento rigoroso da Constitution v1.0.0.  
**Scale/Scope**: Sistema de Gestão Patrimonial institucional (SisPatrimônio Pro).

---

## Constitution Check

*GATE: Checked against SisPatrimônio Pro Constitution v1.0.0. All items pass.*

- [x] **Princípio I — Preservação do Sistema Existente**: Alteração cirúrgica sem refatorações não relacionadas.
- [x] **Princípio II/III — Arquitetura em Camadas & Services**: Regra de identificação tratada no ponto de entrada de rota e repassada ao `MovementService`.
- [x] **Princípio IV — Integridade Patrimonial**: O motor de movimentações (`MovementService.create_movement`) permanece como a fonte única imutável de movimentações.
- [x] **Princípio VI — Segurança por Padrão & RBAC**: A autoridade para definição do operador é 100% no servidor (`request.state.user`).
- [x] **Princípio VII — Banco de Dados**: Nenhuma alteração estrutural nem migração destrutiva. Coluna `movements.operator_name` (VARCHAR 100) reutilizada.
- [x] **Princípio VIII — Testes como Requisito**: Suíte de testes existente mantida verde e novos testes unitários/integrados adicionados.

---

## Project Structure

### Documentation (this feature)

```text
specs/065-operador-responsavel-autenticado/
├── spec.md              # Especificação de requisitos funcionais e aceitação
├── plan.md              # Este plano de implementação
├── research.md          # Fase 0 - Decisões técnicas e análises de alternativas
├── data-model.md        # Fase 1 - Modelo de dados e contrato do operador
├── quickstart.md        # Fase 1 - Guia prático de execução e validação
├── contracts/           # Fase 1 - Contrato da interface Web e API REST
│   └── movements-api-contract.md
└── checklists/
    └── requirements.md  # Checklist de qualidade da especificação
```

### Source Code (repository root)

```text
app/
├── web/
│   ├── templates/
│   │   └── movements/
│   │       └── new.html          # Template HTML do formulário de movimentação (campo readonly)
│   └── routers/
│       └── movements.py          # Rota web POST /movements/new (extracão de request.state.user)
├── api/
│   └── movements_api.py          # REST API POST /api/v1/movements (sobrescreve operator_name)
└── models/
    └── movement.py               # Modelo SQLAlchemy Movement (operator_name VARCHAR 100)

tests/
└── test_movements.py             # Testes automatizados (preenchimento, persistência e anti-spoofing)
```

**Structure Decision**: Projeto Python/FastAPI em camada única com separação clara entre web, api e services.

---

## Complexity Tracking

*Nenhuma violação constitucional. Tabela de complexidade não requerida.*
