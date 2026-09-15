# Research: Aviso de sobrescrita na re-conferência de inventário

**Feature**: 003-aviso-reconferencia | **Date**: 2026-09-15
**Base**: análise do código-fonte existente (nada aqui é especulação — cada decisão cita evidência).

---

## R1 — A página `conferir.html` deve ter confirmação no envio?

**Decision**: **Não.** A confirmação explícita (`confirm()`) fica apenas nos modais do `detail.html`. Em
`conferir.html`, apenas complementa-se o alerta existente com conferente/data/resultado anterior.

**Rationale**: o briefing define confirmação para "o envio do formulário" no contexto dos **modais** de
`detail.html` ("os modais de conferência existentes em `detail.html` abrem o formulário diretamente…") e
trata `conferir.html` separadamente no item 4 ("Verifique a mensagem já existente… preserve seu
comportamento. Apenas complemente a informação, se necessário"). A página de conferência em campo também
não abre "direto o formulário em branco": o documento de decisão (`docs/doc_proviśorios/DECISAO_RECONFERENCIA_INVENTARIO.md`)
registra que ela "já exibe um alerta informativo de que existe resultado registrado" — o usuário chega ali
já ciente da conferência anterior, o que satisfaz o objetivo de eliminar a sobrescrita silenciosa.
O documento de planejamento (`IMPLEMENTACAO_AVISO_RECONFERENCIA.md`, item 2) confirma a leitura: o
`confirm()` é listado como ajuste do `detail.html`, e o `conferir.html` recebe "~1 linha" de complemento.
**Alternativa considerada**: adicionar `confirm()` também na página — rejeitada por extrapolar o escopo
previsto no briefing (risco de alterar fluxo de campo sem previsão) e por duplicar fricção onde o alerta
já informa.

## R2 — Qual mecanismo de confirmação no envio?

**Decision**: `confirm()` nativo do navegador via atributo `onsubmit` no `<form>` do modal, condicionado
no servidor a `item.status != 'PENDENTE'` (o atributo só é renderizado para itens já conferidos).

**Rationale**:
- **Padrão consolidado no próprio sistema** — 4 precedentes exatos de `confirm()` em português:
  - `app/web/templates/admin/roles/list.html:54` — `onsubmit="return confirm('Excluir o perfil {{ role.name }}?')"`
  - `app/web/templates/admin/users/edit.html:124` — `onclick="return confirm('Bloquear o acesso deste usuário? …')"`
  - `app/web/templates/admin/users/edit.html:154` — `onclick="return confirm('Redefinir a senha deste usuário? …')"`
  - `app/web/templates/admin/ad/settings.html:147` — `onclick="return confirm('Remover o mapeamento…')"`
- **Semântica exata exigida pela spec** (FR-007): `return confirm(...)` cancela o submit (0 requisições,
  formulário preservado) quando o usuário escolhe Cancelar, e permite o POST normal ao confirmar (FR-008) —
  sem interceptar a rota.
- **Zero dependência nova**; funciona nos dois temas e no fluxo atual sem tocar `base.html`.
- O documento de decisão de produto (item 1 da decisão final) prevê exatamente esse formato: mostrar o
  aviso "**antes do POST**".

**Alternativas consideradas**:
- *Modal Bootstrap customizado* — padrão visual mais rico, porém exigiria novo JS de interceptação de
  submit por item (um modal de confirmação por item, ~N itens), aumentando superfície de erro sem
  previsão do briefing; rejeitada por complexidade desnecessária para o mesmo resultado de UX.
- *Diálogo `<dialog>` nativo* — sem precedente no projeto; rejeitada pela mesma razão.

**Forma de renderização**: o `onsubmit` é montado **condicionalmente no Jinja** — para `PENDENTE`, o
`<form>` não recebe o atributo (comportamento idêntico ao atual, CA-01); para itens conferidos, recebe
`onsubmit="return confirm('Este item já foi conferido. Registrar um novo resultado vai substituir o anterior. Continuar?')"`.
Essa condicionalização server-side evita JS que precise descobrir o estado do item em tempo de execução.

## R3 — Quais campos estão disponíveis e como renderizar o alerta sem inventar dados?

**Decision**: o alerta do modal é renderizado quando `item.status.value != 'PENDENTE'`, com blocos
condicionais independentes para `item.checked_by_name` e `item.checked_at` (guards `if` no Jinja). O
resultado anterior é sempre exibível (derivado de `item.status`, campo `NOT NULL` com default).

**Rationale** (verificado no código):
- `app/web/routes.py` (`view_inventario`, linhas ~1838-1889) passa `expected_itens` (objetos
  `InventarioItem`) diretamente ao template — os mesmos objetos usados na listagem, que **já renderiza**
  `item.status`, `item.checked_by_name` e `item.checked_at` (linhas da coluna "Resultado" de
  `detail.html`), inclusive com o guard condicional `{% if item.checked_by_name %}` e o padrão de data
  `item.checked_at.strftime('%d/%m/%Y %H:%M') if item.checked_at`. **Nenhuma variável nova é necessária.**
- `app/models/inventario.py` (`InventarioItem`): `checked_by_name` e `checked_at` são `nullable=True`
  (podem estar ausentes — ex.: `ondelete="SET NULL"` na FK `checked_by_id` quando o usuário é excluído);
  `status` é `NOT NULL` com default `PENDING`. Logo: nome e data **exigem guards**; o resultado, não.
- Modelo do alerta conforme o documento de decisão ("Já conferido por {nome} em {data} — registrar novo
  resultado vai substituir este") + resultado anterior com rótulo legível (`item.status.label`,
  `_LabeledEnum`, mesmo padrão usado no alerta do `conferir.html`).
- Mesmo mecanismo se aplica a `conferir.html`: a rota `conferir_asset_page` já fornece `item` completo ao
  template (linhas ~1965-1994), e o alerta atual não exibe conferente/data apenas por omissão.

**Alternativas consideradas**: solicitar novo campo/endpoint ao backend — proibido pela spec (FR-011) e
desnecessário (dados já disponíveis).

## R4 — Onde exatamente o alerta entra nos modais do `detail.html`?

**Decision**: bloco Jinja inserido no `modal-body` de cada `#modalConferir{{ item.id }}`, imediatamente
**acima do formulário** (antes do bloco "Local cadastrado…"), dentro do loop
`{% for item in expected_itens %}{% if inv.status.value != 'ENCERRADO' and can_conferir %}`.

**Rationale**: verificação literal do template (linhas ~251-311): o `<form>` de conferência vive dentro
do `modal-body`, que hoje começa com o contexto do item ("Local cadastrado: …"); o briefing pede o alerta
"acima do formulário". O loop já garante que os modais só existem para inventário aberto + usuário com
`inventario.conferir` — portanto **nenhum ajuste é necessário** para o cenário ENCERRADO (CA-07): com
inventário encerrado, os modais simplesmente não são renderizados, como hoje. Nos modais, `item` é a
variável do loop, não a da listagem — mesmo objeto, escopo diferente; sem risco de colisão.

**Alternativa considerada**: alerta único fora do loop via JS — rejeitada: exigiria descobrir o estado de
cada item em runtime e alteraria mais código que o bloco condicional por item.
