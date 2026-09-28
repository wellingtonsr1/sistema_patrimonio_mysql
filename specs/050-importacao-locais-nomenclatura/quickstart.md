# Quickstart — Feature 050 (validação ponta a ponta)

Referências: [contract](contracts/ui-contract-importacao-locais.md) · [data-model](data-model.md) · [spec](spec.md)

## Pré-requisitos

- Ambiente de dev (`python run.py`) com usuário `locais.criar` (admin serve).
- Baseline conhecido (plan R7): 842 passed / 5 failed (3 do domínio de locais, corrigidos pela 050; 2 de backup fora de escopo).

## Cenários de validação

### V1 — Contrato oficial importa ponta a ponta (SC-001)

CSV `Localização;Unidade Administrativa;Departamento` → `/locations/import`:
1. Mapeamento sugerido correto (3 colunas → Localização/Unidade Administrativa/Departamento) com rótulos oficiais.
2. Prévia classificando registros; confirmação grava; relatório final sem erros.
3. Banco: local criado com name/branch/department corretos.

### V2 — Compatibilidade legada (SC-002)

CSV `Nome;Filial;Departamento` (e `localização`/`unidade`/`sede`/`empresa`/`setor`) → importação OK, idêntica ao comportamento atual. Nenhum alias legado removido.

### V3 — Mensagens oficiais (FR-012)

CSV com linha faltando Unidade Administrativa → mensagem `Linha N: Unidade Administrativa é obrigatória` (na prévia tradicional e na inteligente).

### V4 — Export oficial + round-trip (FR-026/027)

`GET /api/v1/reports/locations/csv` → header `Localização;Unidade Administrativa;Departamento;Prédio;Andar;Sala;Gestor`. Reimportar o arquivo baixado (sem edição) → duplicados corretos, nada criado (reanálise), SC-004 satisfeito.

### V5 — Não-vazamento (SC-006)

- `git diff --stat` confinado aos arquivos do §4 do contract.
- Parciais `imports/_mapping_step.html`/`_smart_preview.html` intocados.
- Mapeamento de equipamentos/colaboradores segue funcionando (rótulos próprios inalterados).

### V6 — Regressão completa (SC-005)

Suíte: 842+3 testes do domínio verdes; 2 failures de backup permanecem como baseline externo (documentados em validacao.md).

## Ambientes

Desktop 1440 (tela de importação, tema dark/light), e verificação de textos via render (`strings` do HTML) — feature não visual, foco em textos/fluxo.

## Resultado esperado

CSV oficial → importação ponta a ponta sem erro; CSV legado → intacto; export → oficial e reimportável; mensagens → terminologia oficial; zero alteração fora do domínio de locais.
