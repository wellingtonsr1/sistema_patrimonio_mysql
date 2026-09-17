# Contract: Identificador Provisório de Colaborador (feature 010)

Contratos dos caminhos de escrita/leitura afetados. Tudo o que não está listado aqui permanece **byte-idêntico** ao comportamento atual.

## 1. Web — `POST /custodians/new` (criação; permissão `colaboradores.criar`)

| Aspecto | Contrato |
|---|---|
| Campo `registration_code` | Passa a ser **opcional** (`Optional[str] = Form(None)`). Enviado vazio/ausente/espaços → o service gera `PROV-%06d` automaticamente; enviado com valor oficial → comportamento atual (unicidade validada) |
| Valor `PROV-*` digitado | **Rejeitado** — redirect `303` para `/custodians/new?error=...` com mensagem no padrão atual de erros de validação (mesmo mecanismo de "Matrícula já cadastrada") |
| Sucesso | Redirect ao fluxo atual de criação bem-sucedida; auditoria de criação existente registra o colaborador com o `PROV-*` gerado no `resource_ref` |
| Demais campos | Inalterados (`name`, `email`, `cpf`, `role`, `department` — mesmas validações atuais) |

## 2. Web — `POST /custodians/{id}/edit` (edição; permissão `colaboradores.editar`)

| Aspecto | Contrato |
|---|---|
| Matrícula atual `PROV-*` | Formulário exibe o campo **editável** (com a marcação de provisória); o POST passa a aceitar `registration_code` opcional **somente neste caso**; novo valor oficial valida unicidade ("Matrícula já cadastrada" em caso de colisão — erro existente) e a alteração é auditada (before/after pelo mecanismo existente do caminho) |
| Matrícula atual oficial | **Inalterado**: campo readonly, POST não recebe/aplica matrícula — comportamento atual preservado |
| Novo valor `PROV-*` digitado | Rejeitado (anti-fabricação) — mesmo tratamento da criação |
| Demais campos | Inalterados |

## 3. API — `POST /api/v1/custodians` (criação; `colaboradores.criar`)

| Aspecto | Contrato |
|---|---|
| Body sem `registration_code` (ou `"")` | `201 Created`; o colaborador é criado com `PROV-*` gerado pelo sistema; resposta `CustodianRead` contém o identificador gerado |
| Body com `registration_code: "PROV-000123"` | `400` — anti-fabricação (detail no padrão atual dos erros de validação de colaborador) |
| Body com matrícula oficial | Comportamento atual (201 / 400 por duplicidade) — inalterado |
| Demais validações | E-mail duplicado → 400 "E-mail já cadastrado" (atual) |

## 4. API — `PUT /api/v1/custodians/{id}` (edição; `colaboradores.editar`)

| Aspecto | Contrato |
|---|---|
| `registration_code` informado com atual `PROV-*` | Comportamento novo da feature: substituição pela oficial (mesmo registro), unicidade validada; auditada (before/after — mecanismo existente) |
| `registration_code: "PROV-*"` como novo valor | `400` — anti-fabricação |
| `registration_code` oficial→oficial | Comportamento **atual** da API (validação de unicidade; preservado conforme spec FR-010/edge cases) |
| Sem `registration_code` no body | Comportamento atual (campo opcional do `CustodianUpdate`; nada é alterado) |

## 5. Leitura/exibição (contrato de apresentação)

| Superfície | Contrato |
|---|---|
| `CustodianRead` (API) | `registration_code` devolve o valor vigente (`PROV-*` ou oficial) — campo não muda de nome nem de tipo; consumidores decidem a apresentação |
| Templates de exibição da matrícula viva (colaboradores list/detail/form, `movements/new.html`, `assets/detail|list|form.html`, `movements/term.html`) | Quando o colaborador é `PROV-*`, a exibição inclui a marcação **"provisória"** (badge do padrão visual atual) junto ao código — nunca apresentando `PROV-*` como matrícula oficial |
| Snapshots históricos (`Movement`, ata de inventário) | Permanecem exatamente como gravados na época — **nenhuma reescrita** |
| Pesquisa de colaboradores (006) | Termo `PROV-`/parcial encontra colaboradores provisórios (o campo já é alvo da pesquisa combinada) — sem mudança de contrato |

## 6. Regras de não regressão (verificáveis por teste)

1. Cadastro com matrícula oficial informada (web e API) → idêntico ao atual.
2. Duplicidade de matrícula oficial → mesmo erro atual ("Matrícula já cadastrada").
3. Duplicidade de e-mail → mesmo erro atual.
4. Importação CSV de colaboradores → matrícula continua **obrigatória**; fluxo intocado.
5. Casamento AD (`registration_code == username AD`) → intocado.
6. Movimentações, inventário, termos (estrutura), relatórios, RBAC, permissões → intocados.
7. Suíte existente → patamar atual (281 passed / 1 failed conhecido), nenhum teste editado.
