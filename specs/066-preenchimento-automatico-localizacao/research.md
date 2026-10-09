# Research — 066-preenchimento-automatico-localizacao

**Data**: 2026-10-09 | **Status**: Todos os unknowns resolvidos (0 NEEDS CLARIFICATION na spec)

## R1 — Onde vive a regra de composição do nome

**Decision**: Helper puro (método estático sem efeitos colaterais) em `LocationService`, ex.: `compose_name(branch, department) -> str`, que aplica `strip()` em cada componente e junta com `" - "`.

**Rationale**: Constitution II/III exigem regra de negócio nos services; a rota web delega ao helper e ao `create` existentes. Fonte única evita divergência entre o que o JS mostra e o que o servidor grava.

**Alternatives considered**:
- Lógica embutida na rota `create_location_form` — regra em rota, viola Constitution III.
- Módulo utilitário novo (`app/utils/…`) — cria módulo sem necessidade; o service já é o local estabelecido e é importado pela rota.
- Regra em `LocationService.create` para TODAS as origens — **descartada na spec §9-B**: quebraria API REST, `seed_demo.py`, CLI e dezenas de testes que criam locais com nome arbitrário (`name="TI", branch="SP"`).

## R2 — Mecanismo de sincronização no navegador

**Decision**: JavaScript vanilla embutido em `<script>` dentro de `locations/form.html`, com `DOMContentLoaded`, listeners `input` nos campos `[name=branch]` e `[name=department]` e escrita em `[name=name]`.

**Rationale**: Padrão da casa — `base.html` (L330), `dashboard.html` (L462) e `inventarios/offline.html` usam scripts inline; **não há middleware de CSP** no projeto (busca por `Content-Security-Policy` = 0 ocorrências), então script inline é permitido. Zero dependências novas.

**Alternatives considered**:
- Arquivo JS estático externo — mais pesado para ~15 linhas e sem precedente nesse form; o template já é autocontido.
- Extensão de JS existente em base.html — tocaria template compartilhado validado por várias features (escopo maior, risco de regressão global).

## R3 — Tratamento do campo `name` no HTML

**Decision**: `readonly` (visível, focável, **enviado no form**), com label indicando preenchimento automático. P2 aprovado pelo responsável em 2026-10-09.

**Rationale**: `disabled` omitiria o campo do POST (mudaria o contrato do form e dependeria 100% do servidor — funcionaria, mas perde feedback visual); `readonly` mantém o valor submetido como nas demais telas da casa (precedente: Operador Responsável da spec 065).

**Alternatives considered**:
- Campo `hidden` — invisível ao usuário, perde transparência (spec AC04).
- Deixar editável — inviabiliza AC01–AC05 (digitação manual volta a divergir).

## R4 — Autoridade no servidor (anti-falsificação)

**Decision**: Em `create_location_form`, o parâmetro passa a `name: Optional[str] = Form(None)`; a rota **ignora** o valor recebido e monta `LocationCreate(name=LocationService.compose_name(branch, department), …)` antes de chamar `LocationService.create`.

**Rationale**: AC05/FR-003 — navegador não é fonte confiável; recompor (e não apenas validar) elimina a classe inteira de payloads adulterados sem ramificação de erro. P1 aprovado: regra vale **somente** nesta rota web; `POST/PUT /api/v1/locations` e importação seguem aceitando `name` explícito (contratos preservados).

**Alternatives considered**:
- Validar `name == compose_name(branch, department)` e rejeitar — mesmo efeito de segurança, mas exige tratamento de erro extra e rejeita o usuário legítimo com JS desativado que enviou valor velho; recompor é mais robusto.
- Assinar/hashear o campo — complexidade desnecessária para formulário interno autenticado.

## R5 — Validação de tamanho (limite da coluna)

**Decision**: Se `len(name) > 100` após composição, a rota redireciona para `/locations/new?error=…` com mensagem amigável (padrão `?error=` já usado para duplicidade), **sem** truncamento silencioso.

**Rationale**: Coluna `Location.name` é `String(100)`; MySQL pode truncar silenciosamente fora de strict mode, o que criaria nome divergente do par de origem. Dados reais: soma máxima atual = 50 chars (folga de 50).

**Alternatives considered**:
- Truncar no servidor — cria nome fora do padrão e esconde o problema (violaria AC03/AC05).
- Validação só no cliente — falharia em requisição manipulada (FR-004 é regra de servidor).

## R6 — Duplicidade e campos incompletos

**Decision**: Sem código novo: duplicidade já é coberta por `name` UNIQUE + `get_by_name` → `ValueError("Já existe um local cadastrado com este nome")` → redirect `?error=` (fluxo atual); campos incompletos ficam bloqueados pelo `required` de `branch`/`department` (HTML) e pelo `Form(...)` obrigatório da rota (servidor).

**Rationale**: A geração automática não cria caminho novo de validação — reaproveita as regras existentes (menor mudança possível). `name` no POST passa a ser opcional apenas porque a rota o ignora; os campos de origem continuam obrigatórios, logo nenhum registro incompleto é possível.

**Alternatives considered**:
- Mensagem de duplicidade customizada citando a composição — melhoria cosmética, escopo extra; a mensagem atual já é compreensível (AC07).

## R7 — Estratégia de testes e regressão

**Decision**: Arquivo novo `tests/test_localizacao_automatica_066.py` espelhando os helpers das suítes 063/064 (`client`, `db_session`, `LocationService.create`), cobrindo: render (AC01–AC04), POST adulterado (AC05), incompletos (AC06), duplicidade (AC07), nome >100 (FR-004), API PUT intocada (AC08). Réguas sem edição: `test_locations_search.py`, `test_movements.py`, `test_department_selection.py`, `test_import_asset_location.py`, `test_import_asset_movements.py`, `test_departamento_destino_062.py`, `test_presentacao_trilha_063.py`, `test_fluxo_global_064.py` + régua completa `python -m pytest`.

**Rationale**: Constitution VIII — suíte existente é a base de regressão; nada é removido ou enfraquecido. Padrão TDD da casa (red→green) aplicável: primeiro o teste de render contra o form atual, depois a implementação.

**Alternatives considered**:
- Estender teste existente de locations — mistura escopos de features; a casa usa arquivo novo por feature (062/063/064).
