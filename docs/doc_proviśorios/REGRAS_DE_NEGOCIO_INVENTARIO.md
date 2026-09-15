# REGRAS DE NEGÓCIO — FUNCIONALIDADE "INVENTÁRIO"

**Sistema:** SisPatrimônio Pro
**Base da documentação:** inspeção do código-fonte (`app/services/inventario_service.py`, `app/models/inventario.py`, rotas e templates) — nada aqui é especulação; cada regra está implementada e, em sua maioria, coberta por testes (`tests/test_inventario.py`).
**Data:** 14/09/2026

---

## 1. A regra de ouro — o inventário nunca toca no cadastro

A regra central (declarada nos docstrings do service, garantida no código e coberta por testes de regressão): **o resultado da conferência NUNCA altera o bem**.

- `record_check` e `register_unlisted_asset` nunca escrevem em `assets.location_id`, `custodian_id` ou `status`.
- Uma divergência é apenas **registrada**; corrigi-la é trabalho dos fluxos próprios (movimentação, edição via API REST `PUT /api/v1/assets/{id}`).
- Evidência: docstring do service ("NUNCA altera Asset.location_id / custodian_id / status") e testes `test_record_check_found_starts_inventory` e `test_record_check_wrong_location_requires_different_location`.

## 2. Snapshot da expectativa

- A lista de esperados é gerada **uma única vez, na criação** e é prova imutável: `expected_location_id/name` e `expected_custodian_name` capturam o estado do cadastro naquele momento (imune a movimentações posteriores — testado por `test_scope_snapshot_survives_later_asset_move`).
- Escopo = todos os bens com `status != BAIXADO`, opcionalmente filtrados por local e/ou setor; a combinação de filtros é congelada como texto em `scope_filters`.
- Bens cadastrados **após** a criação não entram na lista de esperados (só podem aparecer como "não previstos").

## 3. Ciclo de vida

- Fluxo de status: `PLANEJADO → EM_ANDAMENTO → ENCERRADO`.
- A passagem para "em andamento" acontece de forma formal (botão "Iniciar" → `started_at`) ou **implicitamente na primeira conferência/ocorrência de não previsto registrada**.

## 4. Regras de conferência

- Cada item tem exatamente um resultado vigente: `ENCONTRADO`, `LOCAL_DIFERENTE`, `NAO_ENCONTRADO`, `SEM_IDENTIFICACAO` (estado inicial: `PENDENTE`).
- Todo registro carimba **quem e quando**: `checked_by_id/name` (snapshot do username) + `checked_at`.
- A re-conferência é permitida enquanto o inventário estiver aberto (sobrescreve o resultado; o histórico só existe na trilha de auditoria).
- Validações por resultado:
  - `LOCAL_DIFERENTE` **exige** um local encontrado **diferente** do esperado (o service rejeita local igual ou ausente com `ValueError`).
  - `ENCONTRADO` assume o local esperado se nenhum for informado.
  - `NAO_ENCONTRADO` limpa o local encontrado.
- Inventário encerrado → nenhuma conferência é aceita (`ValueError` no service, reforçado nos dois templates).

## 5. Bens não previstos

- Um bem que existe no cadastro mas está fora da lista esperada é registrado como ocorrência (`nao_previsto=True`), com local encontrado e observação.
- Não há duplicidade: `UNIQUE(inventario_id, asset_id)` no banco + guard no service.
- Um bem que **não existe no cadastro não pode ser registrado** — o sistema não tem fluxo de "encontrado sem cadastro" (lacuna documentada na auditoria, caso D).
- O status do item não previsto é gravado como `SEM_IDENTIFICACAO` (sobrecarga semântica apontada na auditoria).

## 6. Encerramento

- Só é permitido quando **zero itens esperados estão PENDENTES** (itens "não encontrados" podem existir — contam como conferidos).
- Irreversível: grava `closed_at`, `closed_by_name`, `closure_notes` e **trava** todas as conferências seguintes.
- Não existe cancelamento nem reabertura de inventário encerrado.

## 7. Comprovação e rastreabilidade

- As pessoas são gravadas como snapshots (`created_by_name`, `closed_by_name`, `checked_by_name`), para que a prova sobreviva à exclusão do usuário (`ondelete="SET NULL"` nas FKs).
- Toda operação de escrita gera registro em `audit_logs` com ação `INVENTARIO`: criação, início formal, cada conferência, cada ocorrência nova de não previsto, encerramento.
- O resultado pode ser exportado como "ata" formal (CSV/PDF/Excel) com bloco de comprovação (quem criou, iniciou, encerrou).
- Cada item guarda conferente, data/hora, local encontrado e observação — exibidos na tela, nas atas e na timeline da ficha do bem.

## 8. Acesso

- Quatro permissões (deny-by-default, verificadas no servidor em todas as rotas):
  - `inventario.visualizar` — consultar inventários e resultados;
  - `inventario.criar` — criar inventário e gerar a lista esperada;
  - `inventario.conferir` — registrar resultados de conferência;
  - `inventario.encerrar` — encerrar e consolidar.
- Perfis padrão: **Administrador** e **Patrimônio** têm as 4; **Auditor** só visualiza; os demais perfis não têm nenhuma.
- Não há restrição por local/unidade — o escopo é decisão de quem cria o inventário, não do RBAC.

---

## Síntese em uma frase

**O inventário é um instrumento de conferência que não altera o cadastro e produz evidências** — congela o que era esperado, registra o que foi fisicamente encontrado (incluindo divergências), trava ao terminar e deixa a correção do bem para os fluxos dedicados.

---

## Referência cruzada

- Auditoria completa da funcionalidade: `docs/AUDITORIA_FUNCIONALIDADE_INVENTARIO.md`
