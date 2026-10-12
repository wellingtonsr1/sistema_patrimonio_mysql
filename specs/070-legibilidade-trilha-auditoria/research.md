# Research: Legibilidade dos Eventos de Alteração Cadastral na Trilha (Feature 070)

**Método**: somente leitura sobre o código existente; cada decisão cita o arquivo/linha verificado. As decisões PD-1…PD-4 vieram do clarify 2026-10-12 (spec, seção `## Clarifications`).

---

## R1 — Local e forma do helper de resumo (PD-1, clarify)

**Decision**: novo método **somente leitura** em `AssetService` (`app/services/asset_service.py`), no espelho de `AssetService.get_cadastral_history` (L97–149 — que a 067 criou exatamente para preparar dados de apresentação sem tocar em `get_timeline_for_asset`). A rota `view_asset_detail` (`app/web/routers/assets.py` L478–519) aplica o helper aos itens `type == 'audit'` do `timeline` já carregado, enriquecendo cada item com uma chave derivada (ex.: `audit_summary`) **apenas no contexto do template**.

**Rationale**: (a) precedente aprovado e em produção (067); (b) Constitution II/III — lógica de preparação em service, rota delega, template apresenta; (c) o contrato de `GET /api/v1/assets/{id}/timeline` (`app/api/assets_api.py` L78–130) chama `MovementService.get_timeline_for_asset` **diretamente** — nunca passa pela rota web, então a mudança é isolada por construção.

**Alternatives considered**: (a) filtro/global Jinja em `templates_env.py` — descartado: põe lógica de diff no template e cria um segundo ponto de verdade; (b) pós-processamento embutido na rota (sem método de service) — descartado: espalha lógica de apresentação fora do service, contra Constitution III.

## R2 — Fonte única de diff e rótulos (PD-2, clarify)

**Decision**: o helper reutiliza **no lugar** `changed_fields` (importado de `app/services/audit_service.py` L317–330) e o dicionário `_ASSET_FIELD_LABELS` (`app/services/asset_service.py` L73–92, 17 rótulos) — mesmo par usado por `get_cadastral_history`. Nenhuma exportação nova, nenhum módulo compartilhado, **nenhuma duplicação** do dicionário.

**Rationale**: `_ASSET_FIELD_LABELS` já vive no mesmo arquivo do helper; extração para módulo comum seria refatoração sem necessidade (Constitution I — escopo estrito).

**Alternatives considered**: extrair rótulos para módulo compartilhado — registrado como possível higiene futura, fora do escopo.

## R3 — Mecanismo de expansão "Ver detalhes técnicos"

**Decision**: elemento **`<details>` nativo** com `<summary>Ver detalhes técnicos</summary>`, recolhido por padrão (sem atributo `open`) — mesmo mecanismo já usado em `app/web/templates/admin/audit/list.html` L111–118 para exibir `ANTERIOR`/`POSTERIOR` no log de auditoria.

**Rationale**: sem JavaScript novo; operável por teclado e com estado acessível nativo (AC13/FR-011); precedente no próprio projeto; Bootstrap collapse seria dependência de JS sem ganho (a 063 usou padrões nativos pela mesma razão).

**Alternatives considered**: Bootstrap `data-bs-toggle="collapse"` (usado em `imports/_smart_preview.html`) — descartado: exige JS e não traz acessibilidade extra sobre o `<details>` para este caso.

## R4 — Renderização segura dos dados técnicos

**Decision**: manter a renderização atual via filtro `tojson` (Jinja2 **com autoescape ativo** para `.html`), com `indent` maior que o atual `indent=0` para legibilidade, dentro de elemento `<pre>` com `white-space:pre-wrap; word-break:break-word` (quebra de linha sem rolagem horizontal — AC14). Nenhum `|safe`, nenhum `Markup`, nenhum escape manual.

**Rationale**: `tojson` produz JSON escapado para contexto HTML/JS; o autoescape cobre o restante; teste dedicado com payload hostil (`<script>` em `notes`) prova AC10.

**Alternatives considered**: renderizar como texto puro sem `pre` — descartado: perde a estrutura do JSON e a preservação de quebras/aspas exigidas (FR-004.6).

## R5 — Estrutura do cartão: título, resumo e descrição

**Decision** (formato do pedido original, clarify 2026-10-12):
- **Título** (somente quando há diff): um campo → `Alteração cadastral — <rótulo do campo>`; vários → `Alteração cadastral — Dados do equipamento`.
- **Resumo**: lista no padrão visual do painel "Alterações cadastrais" (`detail.html` L238–248) — `rótulo: ~~anterior~~ → **posterior**`, com `—` para valores nulos/ausentes.
- **Descrição** (`item.data.description`): quando o resumo existe, a linha "Descrição: Campos alterados: …" é **suprimida** (informação redundante — a própria `write_change_audit` L289 gera a descrição a partir do mesmo diff); quando NÃO há resumo (fallback), a descrição continua exibida como hoje (AC11 preservado para eventos sem diff).
- Badges (ação/módulo/`resource_ref`), data/hora (`localtime`) e "Registrado por" permanecem inalterados.

**Rationale**: redundância era um dos problemas apontados no spec (§2); suprimir a descrição apenas quando o resumo a substitui mantém 100% da informação em todos os caminhos.

**Alternatives considered**: manter descrição + resumo — descartado: duplicação visual; mudar o texto gerado pela `write_change_audit` — descartado: gravação intocada (FR-008).

## R6 — Casos de fallback (um estado ausente, JSON inválido, sem diff)

**Decision**: três caminhos no cartão:
1. **Dois dicionários válidos** (`prev_data` e `new_data` são `dict`) → resumo com diff + `<details>`.
2. **Exatamente um dicionário válido** → **sem resumo de diff** (não interpretar ausência como alteração — spec §5.2); exibir o estado disponível rotulado ("Estado registrado") dentro do `<details>`, preservando badges/data/usuário e a descrição atual.
3. **Nenhum dicionário válido** (evento sem dados ou JSON inválido já virou `None` em `get_timeline_for_asset` L449–458) → cartão **idêntico ao atual** (descrição + identificação), sem bloco de detalhes.

**Rationale**: `changed_fields` sobre dict vs vazio marcaria **todos** dos campos como "alterados" — artefato proibido pela spec (FR-005/FR-006, edge case "evento com apenas um dos estados").

**Alternatives considered**: diffrar contra `{}` — descartado, inventaria alterações.

## R7 — Tratamento ausente × nulo (PD-4, clarify)

**Decision**: no resumo, `—` neutro para valor `None` **e** para chave ausente em um dos lados; nenhuma marcação de "campo removido/adicionado". A distinção real permanece no JSON original do `<details>`.

**Rationale**: os snapshots vêm de formatos distintos — web `_asset_audit_snapshot` (`assets.py` L52–68) × API `_asset_snapshot` (`assets_api.py` L24–40, 17 campos + datas) × históricos; sinalizar membership exibiria "removido/adicionado" por **artefato de formato**, violando FR-005 e o risco 3 da spec (§10).

**Alternatives considered**: marcador `(sem registro no estado anterior)` quando `chave not in snapshot` — registrado e descartado nesta versão; representação crua do lado afetado — descartada por ruído visual.

## R8 — Congelamento dos contratos (guardas)

**Decision**: nada muda em `MovementService.get_timeline_for_asset` (L410–473) nem no payload de `GET /api/v1/assets/{id}/timeline` (M1–M6 do `contracts/preserved-contracts.md`). As guardas: (a) teste que compara o payload do endpoint antes/depois (mesmas chaves/valores); (b) suíte `test_api.py` intacta; (c) teste de não-mutação: renderizar a página e comparar `AuditLog` byte-a-byte; (d) suítes 063 (`test_presentacao_trilha_063.py`), 064 (`test_fluxo_global_064.py`) e 067 (`test_consulta_edicao_bens_067.py`) verdes sem edição.

**Rationale**: esses contratos são réguas explícitas das Specs 029/063/064/067; regressão aqui é o maior risco da feature (spec §10, riscos 1–2).

## R9 — Estratégia de testes (arquivo novo, padrão da casa)

**Decision**: `tests/test_legibilidade_trilha_070.py` — fixtures `client`/`db_session` (SQLite em memória), massa pequena como `test_presentacao_trilha_063.py`:

- **RED→GREEN (US1)**: edição via `POST /assets/{id}/edit` (padrão de `_form` da 067) → título único com rótulo do campo; lista antes→depois no padrão do painel; campos inalterados ausentes do HTML do resumo; título genérico com vários campos; campo desconhecido (evento gravado com chave fora de `_ASSET_FIELD_LABELS`) exibido pelo nome técnico.
- **Detalhes (US2)**: `<details>` presente e **sem** `open`; JSON completo de antes e depois dentro dele; quebra de linha sem `<pre>` overflow (classe/estilo de wrap presente); payload hostil (`<script>alert(1)</script>` em `notes`) aparece **escapado**; evento com um único estado funciona.
- **Guardas (US3)**: (a) não-mutação de `AuditLog` (byte-a-byte pós-render); (b) payload de `/api/v1/assets/{id}/timeline` idêntico ao de `MovementService.get_timeline_for_asset` sem enriquecimento; (c) cartão de movimentação (Origem/Destino 063) idêntico; (d) painel "Alterações cadastrais" (067) intacto; (e) evento sem diff → descrição atual preservada.
- **Datas**: filtro `localtime` reaproveitado no cartão (regressão coberta por `test_datetime_flows.py` na régua).

**Rationale**: segue o método red→green + guarda verde-verde das Specs 063/064; nenhum teste existente é editado (Constitution VIII).

**Alternatives considered**: testes só de unidade do helper — insuficientes: o comportamento observável é o HTML (spec AC01–AC14).

## R10 — Performance e limites

**Decision**: sem otimização nova. `get_timeline_for_asset` já limita a 50 eventos de auditoria; o helper processa no máximo 50 itens × ~17 chaves por evento — O(ms) por requisição de página. Nenhuma consulta nova, nenhum cache.

**Rationale**: custo desprezível e constante; introduzir cache seria complexidade sem medida (spec §5.2 — sem animações/novos elementos; Constitution I).

## R11 — Documentação / ajuda central (Constitution XI)

**Decision**: nenhuma atualização de documentação obrigatória nesta feature. Verificado: nenhum artigo da central de ajuda (`/ajuda`) descreve o formato dos cartões de auditoria da trilha (mesma verificação da Spec 063 §16). A implementação reconfirma isso; se um artigo for encontrado à época, a atualização vira tarefa explícita.

**Alternatives considered**: atualizar README/docs preventivamente — descartado: documentar mudança sem artigo prévio seria ruído (a 063 chegou à mesma conclusão).
