# Contract — Consulta detalhada e edição web de bem (`GET/POST /assets/{asset_id}/edit`)

**Feature**: 067-consulta-edicao-bens | **Data**: 2026-10-10
**Status**: NOVO (fluxo web de edição + complementos da tela de detalhes). Decisões de negócio **P1–P5 aprovadas em 2026-10-10** (spec §14 / Clarifications) e já refletidas neste contrato. Contratos de API, importação, movimentação, inventário e relatórios **preservados** — ver [asset-edit-preserved-contracts.md](asset-edit-preserved-contracts.md).

## 1. Consulta detalhada — `GET /assets/{asset_id}` (rota existente, estendida)

- **Permissão**: `patrimonio.visualizar` (inalterada).
- **Resposta**: `200` com `assets/detail.html` contendo, além do que já existe hoje (hero com tag/nome/situação/categoria/condição, custodía & localização, ficha técnica & dados fiscais, contabilidade/depreciação, QR Code, trilha):
  - **Observações** (`notes`) quando preenchidas;
  - **Última atualização** (`updated_at`);
  - **Histórico de alterações cadastrais** (seção/aba própria, separada das movimentações);
  - **Ação "Editar bem"** visível somente quando `can('patrimonio.editar')` e `status != BAIXADO` (P4 aprovada).
- **Campos vazios**: exibidos como "não informado" ou omitidos — nunca como se estivessem cadastrados.
- **Erros**: `403` sem permissão (página amigável + registro `ACESSO_NEGADO`); `404` para bem inexistente.

## 2. Formulário de edição — `GET /assets/{asset_id}/edit`

- **Permissão**: **`patrimonio.editar`** (`require_permission`, deny by default).
- **Resposta**: `200` com `assets/edit.html`, pré-preenchido com os valores atuais do bem, contendo **apenas** os campos do §3 e um campo oculto com `updated_at` (versão lógica, P3 aprovada).
- **Erros**: `403` sem permissão (nada é carregado/gravado); `404` bem inexistente; bem `BAIXADO` → recusa com mensagem clara (P4 aprovada).

## 3. Entrada do POST (form-urlencoded) — `POST /assets/{asset_id}/edit`

| Campo | Obrigatório | Regra |
|---|---|---|
| `name` | **Sim** | `strip`; ≤ 150 caracteres; não vazio |
| `category` | **Sim** | Valor de `AssetCategory` |
| `brand` | Não | ≤ 100 |
| `model` | Não | ≤ 100 |
| `serial_number` | Não | ≤ 100; **único** (excluindo o próprio bem) |
| `specifications` | Não | Texto livre |
| `purchase_date` | Não | Data válida (`AAAA-MM-DD` no protocolo do form) |
| `purchase_value` | Não (default 0) | **≥ 0** |
| `invoice_number` | Não | ≤ 100 |
| `supplier` | Não | ≤ 150 |
| `warranty_expiry` | Não | Data válida |
| `condition` | Sim (valor atual) | Valor de `AssetCondition`; mudança gera movimentação `ATUALIZACAO_ESTADO` com operador autenticado (P2 aprovada) |
| `notes` | Não | Texto livre |
| `expected_updated_at` | **Sim** (oculto) | Versão lógica para controle de conflito (P3 aprovada) |
| `operator_name` | ❌ não recebido do cliente | O operador é o **usuário autenticado** no servidor (nunca o navegador) |

**Campos que NÃO fazem parte do contrato** (enviados por requisição manipulada são **ignorados**, sem erro que revele implementação): `tag`, `status`, `location_id`, `custodian_id`, `created_at`, `updated_at`, `id`.

### Regra do servidor

```text
1) autoriza            → require_permission("patrimonio.editar")            (403 + ACESSO_NEGADO)
2) carrega o bem       → AssetService.get_by_id(asset_id)                   (404 se ausente)
3) protege             → status == BAIXADO? recusa (P4 aprovada)
4) detecta conflito    → expected_updated_at != asset.updated_at? recusa (P3 aprovada)
5) valida              → V1–V7 de data-model.md (ValueError → mensagem amigável)
6) aplica              → AssetService.update(..., operator_name=<autenticado>, commit=False)
7) audita              → write_change_audit(before, after, commit=False)
8) conclui             → db.commit()   (transação única; rollback total em qualquer exceção)
```

- **Campos alterados** da auditoria são calculados pelo serviço de auditoria a partir do estado **persistido** (before = banco, after = resultado da gravação) — nunca do payload do navegador.
- **Nada mudou**: o sistema informa e **não** grava auditoria nem movimentação.

## 4. Saída do POST

| Situação | Resposta | Efeito |
|---|---|---|
| Sucesso com alterações | `303` → `/assets/{asset_id}?updated=true` | Bem atualizado (**mesmo `id`/`tag`**), 1 evento de auditoria `ALTERACAO` com before/after, `updated_at` novo; 0 bens criados |
| Sucesso com mudança de `condition` | `303` → `/assets/{asset_id}?updated=true` | O acima **+** 1 movimentação `ATUALIZACAO_ESTADO` com operador autenticado |
| Sem alterações efetivas | `303` → `/assets/{asset_id}?unchanged=true` | Nenhuma gravação, nenhuma auditoria, nenhuma movimentação |
| Validação de negócio (nome vazio, limite excedido, valor negativo, série duplicada) | `303` → `/assets/{asset_id}/edit?error=<mensagem>` (padrão `?error=` da casa) | Nada gravado |
| Conflito de edição | `303` → `/assets/{asset_id}/edit?error=…` | Nada gravado; usuário instruído a recarregar |
| Bem `BAIXADO` | `303` → `/assets/{asset_id}?error=…` | Nada gravado |
| Sem permissão | `403` (página amigável) | Nada gravado; `ACESSO_NEGADO` na trilha |
| Bem inexistente | `404` | Nada gravado |
| Falha de gravação/banco | resposta de erro amigável | **Rollback total**: nenhum campo alterado e nenhum evento de auditoria órfão |

Mensagens de erro **não** revelam SQL, stack, nomes de tabela ou qualquer dado sensível (FR-018).

## 5. Histórico cadastral na tela (leitura)

- Fonte: `audit_logs` (`resource='Asset' AND resource_id=<asset_id>`) — **a trilha existente**, sem mecanismo novo.
- Apresentação: campo → valor anterior → valor novo, autor (`username`), data/hora (`localtime`), separado das movimentações.
- Sem eventos: estado vazio claro ("nenhuma alteração cadastral registrada"); o cadastro inicial **não** aparece como alteração (é representado pela movimentação `ENTRADA_AQUISICAO`).
- Nenhuma rota nova de auditoria e nenhuma possibilidade de escrita/exclusão pela tela.

## 6. Front-end (comportamento observável)

- Botão/linha "Editar bem" renderizado apenas com `can('patrimonio.editar')` (a apresentação **não** é a autorização — o backend sempre revalida).
- Formulário responsivo no padrão Bootstrap dos demais formulários; sem redesenho de telas existentes.
- Campos protegidos não aparecem como editáveis; se enviados por manipulação, o servidor os ignora.
