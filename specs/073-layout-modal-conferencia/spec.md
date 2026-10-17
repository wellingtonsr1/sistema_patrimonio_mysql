# Feature Specification: Correção de Layout, Espaçamento e Dimensionamento do Modal de Conferência Patrimonial

**Feature Branch**: `073-layout-modal-conferencia`  
**Created**: 2026-10-17  
**Status**: Draft (Aguardando aprovação da especificação)  
**Input**: User description: "Crie uma SPEC para corrigir o dimensionamento, o espaçamento interno e o posicionamento dos elementos do modal de registro de resultado da conferência patrimonial do SisPatrimônio Pro."

---

## 1. Contexto e Descrição do Problema

### 1.1 Contexto de Uso
No SisPatrimônio Pro, a tela de detalhes do inventário (`/inventarios/{id}`) lista todos os bens esperados no escopo planejado. Para cada item com conferência pendente ou já realizada, o operador que possui a permissão `inventario.conferir` pode abrir a janela modal de registro de resultado da conferência clicando no botão de ação da tabela ("Registrar conferência", ícone `bi-check2-square`).

O modal apresenta:
- Identificação do bem (tombamento/tag e nome);
- Localização cadastrada / esperada do bem;
- Alerta informativo caso o item já tenha sido conferido anteriormente;
- Grupo de opções de resultado da conferência em formato de cartões de rádio ("🟢 Encontrado", "🟡 Encontrado em local diferente", "🔴 Não encontrado", "⚠️ Sem identificação");
- Campo de seleção suspensa (dropdown/select) "Local onde foi encontrado (para local diferente)";
- Campo de texto em múltiplas linhas (textarea) "Observação";
- Rodapé de ações contendo os botões "Cancelar" e "Registrar resultado".

### 1.2 Problemas Observados
1. **Campo de localização alternativa encostado nas bordas**: O elemento `<select>` do campo "Local onde foi encontrado (para local diferente)" estende-se por toda a largura do modal de ponta a ponta, sem respeitar o padding lateral interno da janela.
2. **Campo de observação sem espaçamento interno**: O elemento `<textarea>` de "Observação" apresenta a mesma anomalia, encostando diretamente nos limites laterais da janela sem margem interna.
3. **Instabilidade do dropdown (abre e fecha imediatamente)**: Ao clicar no dropdown de seleção de locais, o menu suspenso abre e fecha instantaneamente (ou sofre perda imediata de foco), impedindo o operador de selecionar a localização com conforto.
4. **Desalinhamento e extravasamento dos botões de ação**: Os botões "Cancelar" e "Registrar resultado" situam-se fora da hierarquia visual adequada do contêiner modal ou ultrapassam o limite inferior visível.
5. **Dimensionamento inadequado em relação à altura da janela**: Quando a janela do navegador possui altura vertical reduzida (telas de laptops ou navegadores com barras de favoritos/ferramentas expandidas), o conteúdo do modal ultrapassa a área útil inferior da tela sem uma rolagem interna controlada, dificultando o acesso aos botões do rodapé.

---

## 2. Análise da Causa Raiz e Diagnóstico Técnico

### 2.1 Mapeamento dos Arquivos Responsáveis
- **Template HTML**: [`app/web/templates/inventarios/detail.html`](file:///home/wellington/IA/sistema_patrimonio_mysql/app/web/templates/inventarios/detail.html#L407-L476) (linhas 407–476: estrutura do loop `{% for item in expected_itens %}` e do modal `#modalConferir{{ item.id }}`).
- **Template Base / Layout**: [`app/web/templates/base.html`](file:///home/wellington/IA/sistema_patrimonio_mysql/app/web/templates/base.html) (inclusão do Bootstrap 5.3.3 CSS e JS).
- **Folha de Estilos**: [`app/web/static/css/style.css`](file:///home/wellington/IA/sistema_patrimonio_mysql/app/web/static/css/style.css#L518-L525) (estilos de `.result-option` e tokens de cor).
- **Scripts**: [`app/web/static/vendor/js/bootstrap.bundle.min.js`](file:///home/wellington/IA/sistema_patrimonio_mysql/app/web/static/vendor/js/bootstrap.bundle.min.js) (Bootstrap 5.3.3 Modal e FocusTrap).

### 2.2 Diagnóstico da Causa Real
A inspeção detalhada do código-fonte e do histórico de commits (`commit 18c7c5608dfe4d129507fab465fbf0c18cbe94f0`, implementação da Spec 069 de acessibilidade) revelou múltiplos defeitos estruturais e de fechamento de tags HTML dentro de `detail.html`:

```html
<!-- Trecho atual com anomalias em detail.html (L431-L474) -->
<label class="form-label fw-semibold">Resultado da conferência <span class="text-danger">*</span></label>
<label class="form-label fw-semibold">Resultado da conferência <span class="text-danger">*</span></label> <!-- DUPLICADO -->
<fieldset class="d-grid gap-2 mb-3" style="border:0;padding:0;margin:0;">
    <legend class="visually-hidden">Resultado da conferência</legend>
    <label class="d-block border rounded p-2 result-option" style="cursor:pointer;">...</label>
    <label class="d-block border rounded p-2 result-option" style="cursor:pointer;">...</label>
    <label class="d-block border rounded p-2 result-option" style="cursor:pointer;">...</label>
    <label class="d-block border rounded p-2 result-option" style="cursor:pointer;">...</label>
</div> <!-- ANOMALIA CRÍTICA 1: </div> residual que fecha antecipadamente <div class="modal-body">! -->
</fieldset>
<div class="mb-2">
    <label class="form-label fw-semibold small" for="modalloc-{{ item.id }}">...</label>
    <select name="found_location_id" id="modalloc-{{ item.id }}" class="form-select form-select-sm">...</select>
</div>
<div>
    <label class="form-label fw-semibold small" for="modalobs-{{ item.id }}">...</label>
    <textarea name="observation" id="modalobs-{{ item.id }}" class="form-control form-control-sm" ...></textarea>
</div>
</div> <!-- ANOMALIA CRÍTICA 2: </div> que fecha antecipadamente <div class="modal-content">! -->
<div class="modal-footer"> <!-- ANOMALIA CRÍTICA 3: ejetado para fora de modal-content -->
    <button type="button" class="btn btn-ghost" data-bs-dismiss="modal">Cancelar</button>
    <button type="submit" class="btn btn-primary">Registrar resultado</button>
</div>
</form>
</div>
</div>
</div> <!-- ANOMALIA CRÍTICA 4: fecha elemento pai da página (<main>), corrompendo o documento! -->
```

#### Efeitos em Cadeia da Falha:
1. **Perda de Padding nos Campos**: O `</div>` órfão na linha 451 fecha antecipadamente o `<div class="modal-body">`. Como consequência direta, o wrapper do select (`<div class="mb-2">`) e o wrapper do textarea (`<div>`) são renderizados fora de `.modal-body`. No Bootstrap 5, o padding padrão (`var(--bs-modal-padding) = 1rem / 1.5rem`) é aplicado exclusivamente à classe `.modal-body`. Estando fora dela, os controles com classe `.form-select` e `.form-control` (`width: 100%`) expandem-se até a borda externa da janela modal.
2. **Ejeção do Rodapé (`.modal-footer`)**: O `</div>` na linha 466 (que originalmente pretendia fechar `modal-body`) acaba fechando precocemente o contêiner `.modal-content`. Com isso, `.modal-footer` é cuspido para fora de `.modal-content`, ficando desalinhado no `.modal-dialog` e potencialmente fora da tag `<form>` após a reconstrução da árvore DOM pelo navegador.
3. **Corrupção Global do DOM por Multiplicação de `</div>` Órfãos**: Como o loop `{% for item in expected_itens %}` renderiza até 20 ou 50 itens por página, cada item injetava um `</div>` a mais no final. O primeiro modal fechava `<main id="conteudo-principal">`; os subsequentes fechavam `<body>` e `<html>`, fazendo com que os modais seguintes fossem posicionados fora do `<body>`.
4. **Comportamento "Abre e Fecha" do Dropdown**: Com o `<select>` posicionado fora de `.modal-body` e o modal renderizado em um DOM quebrado fora de seu contexto normal, o mecanismo de contenção de foco do Bootstrap 5 (`FocusTrap` acionado via `tabindex="-1"` e listener `focusin.bs.focustrap`) interpreta a abertura do menu pop-up nativo do sistema operacional / navegador como perda de foco do contêiner modal. O listener `_handleFocusin` força o foco de volta para o primeiro elemento focável do modal (`.btn-close`), emitindo um evento `blur` no `<select>` que colapsa imediatamente suas opções.
5. **Falta de Rolagem Responsiva**: O modal não utiliza a classe padrão do Bootstrap 5 `.modal-dialog-scrollable`, nem define contenção de altura para viewports compactos.

---

## 3. Objetivos e Escopo

### 3.1 Objetivo
Corrigir a estrutura de marcação e as classes de contenção do modal de conferência patrimonial, garantindo:
- Enclausuramento correto de todos os campos de formulário dentro de `<div class="modal-body">`;
- Fechamento íntegro e alinhado de `<div class="modal-content">`, mantendo `<div class="modal-footer">` adequadamente encapsulado dentro do formulário;
- Espaçamento interno (padding) lateral e vertical padronizado e uniforme;
- Estabilidade total do campo `<select>`, permitindo que o usuário clique, veja a lista de opções e selecione o local sem fechamento prematuro;
- Comportamento responsivo com rolagem vertical interna quando a altura da viewport for insuficiente, preservando cabeçalho e rodapé sempre visíveis.

### 3.2 Escopo Incluído
- Template `app/web/templates/inventarios/detail.html`:
  - Correção das tags de abertura e fechamento de `form`, `modal-header`, `modal-body` e `modal-footer` dentro de `#modalConferir{{ item.id }}`;
  - Eliminação da duplicação do rótulo de resultado da conferência;
  - Preservação intacta da semântica de acessibilidade introduzida pela Spec 069 (`<fieldset>`, `<legend class="visually-hidden">`, labels associados com `for="modalloc-..."` e `for="modalobs-..."`);
  - Aplicação de `.modal-dialog-scrollable` e/ou regras de dimensionamento vertical responsivo padrão do Bootstrap 5.
- Folha de estilos `app/web/static/css/style.css`:
  - Apenas intervenções mínimas estritamente necessárias se as classes nativas do Bootstrap não suprirem o confinamento em resoluções atípicas.

### 3.3 Escopo Não Incluído (Restrições)
- Nenhuma alteração em rotas backend (`app/web/routers/inventario.py`), controllers ou APIs;
- Nenhuma alteração nas regras de negócio ou serviços (`InventarioService`, `MovementService`);
- Nenhuma alteração no esquema de banco de dados, migrações ou modelos SQLAlchemy;
- Nenhuma alteração em permissões RBAC (`inventario.conferir`, etc.);
- Nenhuma alteração nos demais modais do sistema (`modalEncerrar`, modal de backup, etc.), preservando o Princípio Constitucional I (Preservação do Sistema Existente e Evolução Incremental).

---

## 4. Requisitos Funcionais e Visuais

- **RF01 — Limites internos**: Todos os elementos visíveis do modal (título, tag, alertas, opções de rádio, dropdown de locais, caixa de texto de observação e botões de ação) DEVEM permanecer confinados dentro dos limites gráficos do modal, com zero transbordo ou corte.
- **RF02 — Espaçamento uniforme dos campos**: O contêiner de conteúdo do modal DEVE aplicar espaçamento interno (padding) padronizado nas laterais e na base (mínimo de `1rem` / 16px), afastando os controles das bordas do modal.
- **RF03 — Dimensionamento do dropdown de localização**: O campo "Local onde foi encontrado (para local diferente)" (`<select>`) DEVE respeitar rigorosamente a largura disponível interna do `modal-body`, mantendo alinhamento visual com as opções de rádio acima e com o campo de observação abaixo.
- **RF04 — Dimensionamento do campo de observação**: O elemento `<textarea>` de "Observação" DEVE preencher a largura disponível da área de conteúdo respeitando as margens e paddings internos, sem ultrapassar o contêiner.
- **RF05 — Estabilidade do dropdown**: Ao clicar no `<select>` de localização alternativa, o menu suspenso de opções DEVE permanecer aberto de forma estável até que o usuário selecione uma opção ou clique fora deliberadamente, sem fechar de forma abrupta ou involuntária.
- **RF06 — Rodapé e botões**: A área de rodapé (`.modal-footer`) DEVE estar devidamente posicionada dentro da estrutura do modal e do formulário, contendo os botões "Cancelar" e "Registrar resultado" perfeitamente visíveis, com espaçamento entre si e alinhados à direita.
- **RF07 — Altura responsiva**: O modal DEVE se adaptar à altura disponível da viewport (`window.innerHeight`), garantindo que o modal nunca seja cortado na borda inferior da tela.
- **RF08 — Rolagem vertical controlada**: Caso o conteúdo completo do modal exceda a altura útil da tela, o corpo do modal (`.modal-body`) DEVE permitir rolagem vertical suave (`overflow-y: auto`), mantendo o cabeçalho (`.modal-header`) e os botões de ação (`.modal-footer`) fixos e visíveis.
- **RF09 — Integridade visual**: O modal DEVE preservar a identidade visual existente do SisPatrimônio Pro em ambos os temas (claro e escuro), incluindo as cores institucionais, fontes Plus Jakarta Sans, ícones Bootstrap Icons, bordas `--c-border` e estilos dos botões `.btn-ghost` e `.btn-primary`.
- **RF10 — Compatibilidade responsiva**: O layout DEVE permanecer coeso e legível tanto em resoluções de desktop (1920x1080, 1366x768) quanto em janelas compactas ou tablets (largura >= 320px), sem geração de rolagem horizontal (`overflow-x: hidden`).
- **RF11 — Preservação funcional do formulário**: O formulário DEVE manter intactos seu método (`POST`), ação (`/inventarios/{{ inv.id }}/conferir/{{ item.id }}`), confirmação via `onsubmit` quando re-conferido, nomes de campos (`result`, `found_location_id`, `observation`) e opções de resultado (`ENCONTRADO`, `LOCAL_DIFERENTE`, `NAO_ENCONTRADO`, `SEM_IDENTIFICACAO`).
- **RF12 — Acessibilidade e conformidade**: A correção DEVE manter conformidade com a Spec 069: grupo de rádios envolto em `<fieldset>` com `<legend class="visually-hidden">`, campos com rótulos vinculados por `for` e `id`, ausência de IDs duplicados por página e foco navegável por teclado sem armadilhas indevidas.

---

## 5. Diretrizes Técnicas

1. **Correção Estrutural Canônica**: Utilizar a hierarquia formal do componente Modal do Bootstrap 5.3:
   ```html
   <div class="modal fade" id="modalConferir{{ item.id }}" tabindex="-1" aria-hidden="true" aria-labelledby="modalLabel{{ item.id }}">
       <div class="modal-dialog modal-dialog-centered modal-dialog-scrollable">
           <div class="modal-content">
               <form method="post" action="/inventarios/{{ inv.id }}/conferir/{{ item.id }}" ...>
                   <div class="modal-header">...</div>
                   <div class="modal-body">
                       <!-- Todo o conteúdo do formulário fica aqui dentro -->
                   </div>
                   <div class="modal-footer">
                       <!-- Botões de ação aqui dentro -->
                   </div>
               </form>
           </div>
       </div>
   </div>
   ```
2. **Uso de `.modal-dialog-scrollable`**: A classe padrão do Bootstrap `.modal-dialog-scrollable` adiciona `overflow-y: auto` no `.modal-body` e fixa o cabeçalho e rodapé nas extremidades do modal, resolvendo simultaneamente o dimensionamento vertical em telas baixas sem necessidade de CSS customizado frágil.
3. **Eliminação do `</div>` Espúrio e do Rótulo Duplicado**:
   - Remover a tag `</div>` que precedia `</fieldset>` na linha 451.
   - Remover o `<label>` redundante da linha 432.
   - Garantir que cada tag aberta possua exatamente uma tag de fechamento correspondente dentro do loop `item`, mantendo o balanço de tags estritamente neutro.
4. **Semântica e Foco**:
   - Manter o `id="modalloc-{{ item.id }}"` e o `for="modalloc-{{ item.id }}"` para atender às regras do `test_acessibilidade_estatica_069.py`.
   - Manter `id="modalobs-{{ item.id }}"` e `for="modalobs-{{ item.id }}"`.
5. **Zero Dependências Novas**: Não adicionar bibliotecas externas de seleção (como Select2, Choices.js ou TomSelect). O componente `<select>` nativo com estilo `.form-select` do Bootstrap atende integralmente à especificação quando a árvore DOM está íntegra.

---

## 6. User Scenarios & Acceptance Testing

### User Story 1 - Conferência com Espaçamento Íntegro em Desktop (Priority: P1)
Como conferente de inventário patrimonial, desejo abrir o modal de conferência de um bem esperado e visualizar todos os campos organizados com espaçamento uniforme para registrar o resultado de forma clara e confortável.

- **Why this priority**: É o fluxo operacional principal de validação física do acervo.
- **Independent Test**: Acessar `/inventarios/{id}`, clicar no ícone de conferência de um item, verificar que o dropdown de local e o campo de observação possuem margem lateral de no mínimo 1rem em relação às bordas da janela modal e que os botões de ação estão perfeitamente visíveis no rodapé.
- **Acceptance Scenarios**:
  1. **Given** um inventário aberto e um bem pendente de conferência, **When** o usuário clica no botão "Registrar conferência", **Then** a janela modal abre centralizada, com padding uniforme em torno de todos os campos e sem encostar nas bordas.
  2. **Given** o modal de conferência aberto, **When** o usuário inspeciona o campo de observação, **Then** a caixa de texto respeita a largura interna do corpo do modal.

---

### User Story 2 - Interação Estável com o Dropdown de Local Alternativo (Priority: P1)
Como conferente patrimonial, desejo clicar no seletor de "Local onde foi encontrado" e navegar pelas opções disponíveis sem que a lista se feche inesperadamente, permitindo apontar a localização correta do bem.

- **Why this priority**: A divergência de localização é uma das ocorrências mais frequentes no processo de inventário.
- **Independent Test**: Abrir o modal de conferência, selecionar a opção "🟡 Encontrado em local diferente", clicar no dropdown de locais, navegar pelas opções com o mouse ou teclado e selecionar um local diferente do esperado.
- **Acceptance Scenarios**:
  1. **Given** o modal de conferência aberto, **When** o usuário clica no elemento `<select>` de locais, **Then** o dropdown de opções abre normalmente e permanece aberto até a seleção.
  2. **Given** o dropdown de locais aberto, **When** o usuário escolhe um local e clica nele, **Then** o valor selecionado é mantido no campo e o foco permanece sob controle do usuário.

---

### User Story 3 - Visualização Responsiva em Telas com Altura Reduzida (Priority: P2)
Como conferente utilizando um notebook com tela de 1366x768 ou resolução compacta, desejo visualizar o modal sem que os botões de ação fiquem cortados ou inacessíveis além da margem inferior da tela.

- **Why this priority**: Conferências em campo frequentemente utilizam notebooks e telas de resolução limitada.
- **Independent Test**: Reduzir a altura da janela do navegador para 600px, abrir o modal de conferência e verificar que o cabeçalho e os botões de ação permanecem visíveis, permitindo rolar o conteúdo interno do formulário.
- **Acceptance Scenarios**:
  1. **Given** uma janela de navegador com altura vertical reduzida (<= 600px), **When** o usuário aciona o modal de conferência, **Then** o cabeçalho e os botões "Cancelar" e "Registrar resultado" permanecem visíveis na tela, e o corpo do modal apresenta barra de rolagem vertical para acessar todos os campos.
  2. **Given** o modal em modo rolagem, **When** o usuário preenche a observação e clica em "Registrar resultado", **Then** o formulário é enviado com sucesso e a conferência é gravada.

---

### Edge Cases
- **Item já conferido anteriormente**: O modal exibe um alerta `alert-warning` detalhando quem conferiu e em qual data. O alerta deve ficar devidamente contido no `.modal-body` com padding regular, sem empurrar os botões para fora da tela.
- **Lista extensa de locais no sistema**: Quando existirem dezenas de locais cadastrados, a lista de opções do `<select>` não deve quebrar o layout do modal nem estender a largura do contêiner.
- **Múltiplos modais renderizados na mesma página**: Como a listagem pode conter vários bens, cada modal gerado no loop deve manter seu balanço de tags independente, garantindo que o fechamento de um modal não interfira no layout da tabela ou dos demais modais.
- **Tentativa de envio sem selecionar resultado**: O atributo `required` no radio `ENCONTRADO` deve disparar a validação nativa do navegador de forma visível ao operador.

---

## 7. Critérios de Aceitação Verificáveis

- **CA01 — Limites internos garantidos**: Todos os campos (identificação, rádio, select, textarea e botões) permanecem estritamente dentro dos limites visuais do modal.
- **CA02 — Espaçamento interno padronizado**: Os campos de localização alternativa e de observação possuem espaçamento interno (padding) lateral de pelo menos 1rem (16px), não tocando as bordas do modal.
- **CA03 — Visibilidade integral dos botões**: Os botões "Cancelar" e "Registrar resultado" ficam completamente visíveis no rodapé do modal em qualquer resolução compatível.
- **CA04 — Rolagem vertical em telas baixas**: Em alturas de janela reduzidas (<= 600px), o corpo do formulário rola verticalmente sem esconder permanentemente os botões ou o cabeçalho.
- **CA05 — Ausência de rolagem horizontal**: Não ocorre barra de rolagem horizontal no modal em nenhuma largura suportada (>= 320px).
- **CA06 — Submissão funcional**: O formulário é postado com sucesso para a rota `/inventarios/{id}/conferir/{item_id}` com todos os dados preenchidos.
- **CA07 — Integridade das 4 opções de conferência**: As quatro opções de rádio (`ENCONTRADO`, `LOCAL_DIFERENTE`, `NAO_ENCONTRADO`, `SEM_IDENTIFICACAO`) continuam presentes e selecionáveis.
- **CA08 — Preservação da identidade visual**: As cores, fontes, bordas e botões nos modos claro e escuro mantêm a identidade estabelecida do SisPatrimônio Pro.
- **CA09 — Operações de controle íntegras**: O botão de fechar (`btn-close`), o botão "Cancelar" e o fechamento por clique externo/ESC funcionam normalmente.
- **CA10 — Suíte de testes automatizados verde**: Todos os testes das suítes `test_acessibilidade_estatica_069.py`, `test_inventario.py` e `test_inventario_reconferencia_ui.py` passam sem falhas.
- **CA11 — Ausência de regressão global**: Nenhum outro modal ou tela do sistema sofre impacto visual ou comportamental.

---

## 8. Critérios de Sucesso Mensuráveis

- **SC-001**: 100% dos elementos internos do modal confinadas dentro da área delimitada por padding de `.modal-body`.
- **SC-002**: Zero ocorrências de fechamento involuntário do dropdown ao clicar nele em navegadores padrão (Chrome, Firefox, Edge).
- **SC-003**: Zero tags HTML órfãs ou desbalanceadas na saída de renderização de `app/web/templates/inventarios/detail.html`.
- **SC-004**: 100% de conformidade com os testes automatizados existentes (55/55 testes de inventário e acessibilidade passando).
- **SC-005**: 100% dos botões de ação acessíveis por teclado (Tab e Enter) e visualmente disponíveis sem corte.

---

## 9. Plano de Testes e Regressão

### 9.1 Testes Manuais Obrigatórios
1. **Inspeção em Desktop (1920x1080 / 1440x900)**: Abrir `/inventarios/{id}`, clicar no botão de conferir de um item esperado e verificar o alinhamento e o padding de todos os campos.
2. **Teste de Interação com o Dropdown**: Clicar no seletor de localização alternativa, verificar que as opções abrem, selecionar uma opção com clique do mouse e confirmar que o valor permanece selecionado.
3. **Teste de Navegação por Teclado**: Abrir o modal, usar a tecla `Tab` para navegar entre as opções de rádio, o select de localização, o textarea de observação e os botões de ação; alternar opções com as setas do teclado.
4. **Teste de Janela com Altura Reduzida**: Redimensionar a janela do navegador para 500px de altura vertical, abrir o modal e confirmar que o cabeçalho e rodapé continuam visíveis enquanto a área central rola suavemente.
5. **Teste de Janela Estreita (Mobile/Tablet)**: Redimensionar para largura de 375px e 768px, confirmando a ausência de overflow horizontal.
6. **Teste de Envio de Formulário**: Registrar uma conferência como "Encontrado em local diferente", selecionar um local, preencher a observação e enviar; verificar a persistência correta na listagem de inventário.
7. **Teste de Cancelamento e Fechamento**: Clicar em "Cancelar", no botão "X" e pressionar a tecla `Esc`; verificar que o modal fecha limpo e sem resíduos de backdrop.
8. **Teste no Tema Escuro**: Alternar para o modo escuro (`data-theme="dark"`), abrir o modal e verificar o contraste das bordas e o fundo dos campos.

### 9.2 Testes Automatizados
- Execução de `pytest tests/test_acessibilidade_estatica_069.py` para garantir que:
  - Todo input/select/textarea possui nome acessível (`label[for]`);
  - O grupo de rádios "Resultado da conferência" permanece envolto em `fieldset`/`legend`;
  - Nenhum `id` duplicado é gerado.
- Execução de `pytest tests/test_inventario.py` e `pytest tests/test_inventario_reconferencia_ui.py` para assegurar integridade dos fluxos de conferência.
- Teste de regressão estática do HTML servido: validação via script de parsing para garantir que não restam tags `<div>` desbalanceadas.

---

## 10. Riscos e Medidas de Mitigação

| Risco | Impacto | Mitigação |
|---|---|---|
| Quebra de testes de acessibilidade (Spec 069) ao ajustar tags | Médio | Manter rigorosamente o `<fieldset>` com `<legend class="visually-hidden">Resultado da conferência</legend>` e os atributos `for="modalloc-{{ item.id }}"` intactos. |
| Botões de rodapé submetendo fora do `<form>` | Alto | Assegurar que `<div class="modal-footer">` permaneça estritamente dentro da tag `<form>`, antes de `</form>`. |
| Conflito de estilos ao introduzir classes customizadas desnecessárias | Médio | Utilizar exclusivamente classes padronizadas do Bootstrap 5.3 (`modal-dialog-scrollable`, `modal-body`, `form-select`, `form-control`) sem sobrescritas CSS arbitrárias. |
| Impacto em outros modais | Baixo | As alterações serão isoladas cirurgicamente no modal de conferência em `inventarios/detail.html`. |

---

## 11. Arquivos Candidatos à Alteração

1. **`app/web/templates/inventarios/detail.html`** *(Principal)*:
   - Remover rótulo duplicado na linha 432;
   - Remover `</div>` espúrio na linha 451;
   - Assegurar encapsulamento de `<div class="mb-2">` e `<div>` dentro de `<div class="modal-body">`;
   - Posicionar `<div class="modal-footer">` dentro de `<form>`;
   - Adicionar a classe utilitária responsiva `modal-dialog-scrollable` ao `<div class="modal-dialog">`;
   - Eliminar `</div>` órfão na linha 474 para equilibrar o loop `{% for item in expected_itens %}`.
2. **`app/web/static/css/style.css`** *(Opcional / Se estritamente necessário)*:
   - Somente se for exigido ajuste fino de altura máxima ou padding em regras locais.

---

## 12. Critérios para Considerar a Implementação Concluída

1. O arquivo `detail.html` não possui tags HTML desbalanceadas ou duplicadas no bloco do modal de conferência.
2. Os campos de seleção e de observação respeitam o padding interno padrão do `.modal-body`.
3. O dropdown abre normalmente e não fecha sozinho ao ser clicado.
4. Os botões de ação "Cancelar" e "Registrar resultado" permanecem dentro da moldura do modal e visíveis em qualquer altura de tela suportada.
5. A rolagem vertical interna funciona perfeitamente com a classe `.modal-dialog-scrollable` quando a altura da viewport for reduzida.
6. A suíte completa de testes de inventário e acessibilidade (`test_acessibilidade_estatica_069.py`, `test_inventario.py`, etc.) executa com 100% de sucesso.
7. Nenhuma outra tela do sistema é modificada ou impactada.
