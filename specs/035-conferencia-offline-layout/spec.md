# Feature Specification: Conferência Offline — responsividade e padronização visual da shell

**Feature Branch**: `035-conferencia-offline-layout`

**Created**: 2026-09-24

**Status**: Draft

**Input**: Corrigir o layout da página de **Conferência Offline** (shell PWA da feature 033, rota `/inventarios/{id}/offline`) para que a interface seja totalmente responsiva e mantenha o mesmo padrão visual e estrutural das demais telas do sistema. Pontos exigidos: (1) identificação "SisPatrimônio Pro" abaixo da logo do IPMJP; (2) área principal com a mesma largura/container das demais páginas; (3) barra de pesquisa + botão "Ler QR" no mesmo grid/largura da tabela; (4) cabeçalhos da tabela alinhados com os dados; (5) rolagem horizontal restrita à tabela em telas pequenas; (6) reorganização natural em celulares; (7) grid Bootstrap existente, sem posicionamento absoluto nem larguras fixas; (8) espaçamentos padronizados; (9) modo claro e escuro; (10) PWA/offline intocado. A alteração é exclusivamente de layout — nenhuma regra de negócio, dado ou funcionamento offline muda.

## Estado atual analisado (fatos do repositório — leitura prévia)

| Fato verificado | Relevância |
|---|---|
| A shell é `app/web/templates/inventarios/offline.html` (rota `GET /inventarios/{inventario_id}/offline`), página **autônoma** (não estende `base.html`), com Bootstrap 5.3.3 + Bootstrap Icons **locais** (vendors self-hosted para funcionar offline) | Superfície única a corrigir; não pode passar a depender de CDN/base com navegação administrativa |
| O commit `30d051e` ("UX: reorganiza a barra superior da shell de coleta offline") colocou o título "SisPatrimônio PRO" **lado a lado** com o código do inventário na mesma linha do bloco central (`.offbar-line1`), com a logo à esquerda | É o posicionamento que esta spec **substitui**: nome deve voltar a ficar **abaixo** da logo (empilhado), como na navbar principal do sistema |
| A navbar principal do sistema (`base.html`/`style.css`, `.app-navbar`/`.navbar-brand`) usa logo + marca empilhados verticalmente; o comentário do template offline registra que o empilhado era "o mesmo padrão do .navbar-brand do style.css" antes do commit `30d051e` | Padrão visual de referência a restaurar — reutilizar o padrão existente, não inventar outro |
| A área principal da shell usa `<main class="container-fluid py-4 px-lg-4 mx-auto" style="max-width: 92%;">`; as páginas do sistema usam `<main class="container-fluid py-4 px-lg-5 mx-auto" style="max-width:90%;">` (base.html) | Larguras quase iguais mas **não idênticas** — spec exige adotar o mesmo padrão das demais telas |
| A barra de pesquisa (`#buscaItem`) + botão "Ler QR" (`#btnLerQR`) e a tabela (`table-responsive`) já estão dentro do **mesmo card** (`card p-4 mb-4`), com a pesquisa em `d-flex gap-2 mb-3` | Estrutura base já correta; problemas residuais são de largura/overflow em telas estreitas |
| O `<body>` da shell tem `overflow-x: hidden` (proteção global contra transbordo) e a tabela usa `table-responsive` (rolagem restrita à tabela) | Comportamento exigido já parcialmente presente — verificar e preservar, não regredir |
| O template tem media queries próprias: ≥992px (contadores 1×4, main 92%), ≥768px (main 92%), ≤767.98px (main 100%, header compacto), ≤575.98px (botões full-width) | Responsividade existente a preservar/ajustar cirurgicamente; regra de largura unificada com o sistema é o alvo |
| Tema claro/escuro via `data-theme`/`data-bs-theme` + `localStorage('sispatrim-theme')` + toggle próprio da shell (`#darkToggle`), cores por variáveis CSS (`--color-primary`, `--c-text`, `--amber`) | Identidade de tema a preservar; nenhum estilo que funcione só em um tema |
| O SW cacheia esta rota **cache-first** (navegação) e os estáticos da allowlist; `CACHE_VERSION` "inventario-offline-v24" | Mudança de layout na shell/estáticos cacheados exige **bump do CACHE_VERSION** para propagar aos dispositivos (único toque admissível no SW) |
| Constitution X (interface consistente, nenhuma alteração de UI que quebre fluxos), I (escopo cirúrgico), VIII (suíte verde) | Restringem a implementação |

## Clarifications

### Session 2026-09-24

- Q: Em telas pequenas (celular/tablet vertical), a área principal deve usar exatamente a mesma largura das demais páginas (90% centralizado) ou continuar aproveitando 100% da largura com padding reduzido? → A: **Padrão + exceção mobile** — 90% centralizado a partir de 768px (mesmo padrão das demais telas); abaixo disso mantém 100% + padding reduzido, comportamento mobile atual da shell (decisão C-1).
- Q: O botão "Ler QR" deve ganhar destaque como ação primária (preenchido) ou permanecer com o estilo de contorno atual? → A: **Manter contorno** — o botão permanece no estilo atual (`btn-outline-primary`); a correção garante apenas alinhamento, dimensão e não-corte, sem mudança de hierarquia visual (decisão C-2).
- Q: Em telas estreitas, com a marca empilhada, o código do inventário e o indicador de conexão devem permanecer na mesma linha da marca ou quebrar para uma segunda linha do cabeçalho? → A: **Quebra em telas estreitas** — a partir de 768px o cabeçalho fica em linha única (marca | código+status | tema); em ≤767px código e status passam a uma segunda linha do próprio cabeçalho, sem esconder nenhum elemento (decisão C-3).
- Q: (Ajuste pós-feedback, 2026-09-24) No celular a quebra para a segunda linha colocou o código/status abaixo da logo — indesejado. Como fica o cabeçalho ≤767px? → A: **C-4 (supera C-3)** — código e indicador de conexão permanecem NA MESMA LINHA da marca empilhada em todas as larguras; quando falta espaço encolhem com ellipsis (sem quebrar para baixo e sem esconder elementos).
- Q: (Ajuste pós-feedback, 2026-09-24) Onde o botão "Ler QR" deve ficar, já que abre a câmera e não depende da busca? → A: **C-6** — vira botão flutuante (FAB) fixo no canto inferior-direito, sempre acessível (ação principal de campo); o campo de busca ocupa a linha inteira do card.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Identificação da shell: nome abaixo da logo (Priority: P1)

O coletador abre a Conferência Offline (via "Preparar coleta offline" ou URL direta) em qualquer dispositivo. Na barra superior, a marca aparece empilhada — logo do IPMJP acima, "SisPatrimônio Pro" abaixo — dentro da mesma área de identificação, igual à navbar principal do sistema. O código do inventário e o indicador de conexão permanecem visíveis ao lado, sem sobreposição.

**Why this priority**: é a correção de identidade visual que motivou a feature — o posicionamento lateral atual (commit `30d051e`) destoa de todas as demais telas.

**Independent Test**: abrir a shell em desktop e em celular e observar a barra superior: logo empilhada com o nome abaixo dela, sem quebra em telas pequenas. Não requer pacote nem coleta.

**Acceptance Scenarios**:

1. **Given** a shell aberta em desktop, **When** a barra superior é renderizada, **Then** "SisPatrimônio Pro" aparece abaixo da logo do IPMJP, dentro da mesma área de identificação.
2. **Given** a shell aberta em celular (≈320–430px), **When** a barra superior é renderizada, **Then** a identificação empilhada permanece legível e alinhada, sem cortar a logo nem o nome, e o código do inventário/indicador de conexão ocupam a segunda linha do cabeçalho (decisão C-3).
3. **Given** a shell aberta, **When** o código do inventário e o indicador de conexão são exibidos, **Then** nenhum elemento da barra sobrepõe ou espreme a identificação.

---

### User Story 2 - Largura e container padronizados com as demais telas (Priority: P1)

Todos os blocos da página (alerta informativo, painel de contadores, card de sincronização, card de pesquisa+tabela, modal e demais elementos) compartilham o mesmo container e a mesma largura máxima usados pelas páginas principais do sistema — a Conferência Offline não parece uma página "solta" com largura própria.

**Why this priority**: largura inconsistente é a principal causa visual da página parecer "fora do padrão"; unifica margem lateral, largura máxima, espaçamento e alinhamento.

**Independent Test**: comparar a shell com qualquer página do sistema (ex.: listagem de inventários) na mesma janela: as bordas esquerdas/direitas do conteúdo coincidem; nenhum bloco ultrapassa o container.

**Acceptance Scenarios**:

1. **Given** a shell aberta em desktop, **When** comparada com uma página principal do sistema na mesma largura de janela, **Then** o conteúdo usa o mesmo container, mesma largura máxima e mesmas margens laterais.
2. **Given** qualquer bloco da página (tabela, contadores, sincronização, mensagens), **When** medido horizontalmente, **Then** nenhum elemento tem largura independente que ultrapasse o container principal.
3. **Given** a página em qualquer resolução da faixa 320–1920px, **When** renderizada, **Then** não existe rolagem horizontal da página inteira.

---

### User Story 3 - Pesquisa, botão "Ler QR" e tabela alinhados no mesmo grid (Priority: P1)

A barra de pesquisa e o botão "Ler QR" ocupam exatamente a mesma largura horizontal da tabela abaixo deles; os cabeçalhos (Tombamento, Descrição, Local esperado, Estado local, Ações) alinham com seus dados; nada transborda o card.

**Why this priority**: é o alinhamento fino entre os blocos superiores e a tabela que elimina o efeito de "colunas começando em posições diferentes".

**Independent Test**: inspecionar as bordas do card de pesquisa+tabela: campo de pesquisa + botão formam uma linha que coincide com a largura da tabela; cabeçalhos e células da mesma coluna alinham verticalmente.

**Acceptance Scenarios**:

1. **Given** o card de pesquisa aberto em qualquer largura de tela, **When** a linha de pesquisa + "Ler QR" é renderizada, **Then** ela ocupa exatamente a mesma largura disponível da tabela do card (mesmo container, mesmas bordas).
2. **Given** a tabela com registros, **When** os cabeçalhos são exibidos, **Then** cada cabeçalho alinha com os dados da sua coluna (nenhum deslocamento horizontal).
3. **Given** conteúdo longo (descrição ou local extenso), **When** a linha é renderizada, **Then** a célula quebra o texto de forma controlada sem empurrar as colunas vizinhas nem gerar transbordo da página.

---

### User Story 4 - Responsividade em telas pequenas com rolagem restrita à tabela (Priority: P2)

Em celulares e telas estreitas, a interface se reorganiza naturalmente: a identificação permanece empilhada, pesquisa e botão podem reorganizar verticalmente, e a tabela ganha rolagem horizontal **própria** (restrita à sua área), sem quebrar a página inteira. O botão "Ler QR" nunca sai da tela, é cortado ou sobrepõe a pesquisa.

**Why this priority**: protege o uso em campo (celular/tablet é o dispositivo principal da coleta offline), mas depende das stories P1 estarem corretas.

**Independent Test**: abrir a shell em viewport de 320px: nenhuma rolagem horizontal da página; a tabela rola dentro do próprio bloco; pesquisa e botão acessíveis e íntegros.

**Acceptance Scenarios**:

1. **Given** viewport estreita (≈320–430px), **When** a página é renderizada, **Then** a rolagem horizontal, quando necessária, fica restrita à área da tabela — a página inteira não transborda.
2. **Given** viewport estreita, **When** a linha de pesquisa + botão é renderizada, **Then** o botão "Ler QR" permanece integralmente visível (reorganização vertical permitida) e não sobrepõe o campo.
3. **Given** tabela com muitos registros ou textos longos, **When** rolada horizontalmente dentro do próprio bloco, **Then** as demais áreas da página (contadores, sincronização, cabeçalho) permanecem fixas e íntegras.
4. **Given** orientação retrato ou paisagem em tablet/celular, **When** a página é girada, **Then** o layout se reorganiza sem quebras.

---

### User Story 5 - Coerência de tema e funcionamento preservados (Priority: P2)

A página corrigida funciona identicamente no modo claro e no modo escuro, e **todo** o funcionamento offline permanece inalterado: preparação de pacote, coleta por QR/tombamento, fila no IndexedDB, sincronização, indicadores e contadores.

**Why this priority**: garantia de não regressão — a mudança é só de apresentação; qualquer alteração funcional ou de tema é falha da feature.

**Independent Test**: alternar tema na shell (claro/escuro) e executar o ciclo coletar → sincronizar: contraste correto nos dois temas e comportamento funcional idêntico ao atual; suíte pytest existente permanece verde.

**Acceptance Scenarios**:

1. **Given** o modo escuro ativo, **When** a página é renderizada, **Then** texto, cabeçalhos, campos, botões, tabela, estados, bordas e fundo mantêm contraste adequado — sem cores fixas que funcionem só em um tema.
2. **Given** o modo claro ativo, **When** a página é renderizada, **Then** o mesmo conjunto de elementos mantém contraste adequado.
3. **Given** coleta offline executada após a mudança (coletar item, gerar pendência, sincronizar), **When** comparada com o comportamento atual, **Then** nenhum passo funcional muda (mesmo modal, mesmos campos, mesmos estados, mesma fila).
4. **Given** a suíte pytest existente, **When** executada após a mudança, **Then** permanece 100% verde (nenhum teste funcional alterado).

---

### Edge Cases

- Tabela com **poucos** registros (1–5 linhas): blocos inferiores não "flutuam" desalinhados; card mantém proporção.
- Tabela com **muitos** registros (1.000 itens — limite do pacote): rolagem vertical da página e horizontal da tabela permanecem independentes e fluidas.
- Descrição/local esperado **muito longos** (sem espaços, ex.: códigos longos): quebra controlada na célula, sem empurrar colunas nem transbordar o card.
- Celular **muito estreito (320px)** com orientação paisagem: nada fica cortado; rolagem continua restrita à tabela.
- **Sem pacote** no dispositivo (mensagem "Sem pacote neste dispositivo?"): mensagens e estados respeitam o mesmo container.
- Alerta de **divergência/erro** (`#avisoPacote`) visível: mesma largura do restante do card.
- **Modal de conferência** em telas pequenas (já com margem `.5rem` em ≤575.98px): permanece integralmente visível após o ajuste do layout externo.
- Dispositivo com **cache antigo do SW**: após o bump da versão de cache, a próxima visita online carrega o novo layout (sem exigir limpeza manual).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A barra superior da Conferência Offline MUST apresentar a identificação empilhada — logo do IPMJP acima, "SisPatrimônio Pro" abaixo — dentro da mesma área de identificação, seguindo o padrão visual da navbar principal do sistema.
- **FR-002**: A identificação empilhada MUST permanecer legível e alinhada em todas as larguras de tela (320px a 1920px) e nas orientações retrato e paisagem. O cabeçalho fica em linha única em todas as larguras (marca empilhada | código + status | tema); em ≤767px, quando faltar espaço, o código e o indicador encolhem com ellipsis — nunca ficam abaixo da logo nem são escondidos (decisão C-4, supera C-3).
- **FR-003**: A imagem da logo existente MUST permanecer a mesma (nenhuma troca de arquivo, tamanho-base 32px preservado, adaptação em telas pequenas mantida).
- **FR-004**: A área principal da página MUST usar o mesmo container, mesma largura máxima e mesmas margens laterais das páginas principais do sistema (padrão `container-fluid` centralizado do `base.html`) a partir de 768px; em telas ≤767px mantém o aproveitamento de 100% da largura com padding reduzido (comportamento mobile atual da shell — decisão C-1). Nenhuma largura específica nova é criada para a Conferência Offline.
- **FR-005**: A barra de pesquisa e a tabela (com seus elementos abaixo: mensagens, estados, avisos, dicas) MUST ocupar exatamente a mesma largura disponível do container do card — nenhuma coluna ou bloco começa/termina em posição diferente do bloco superior. O botão "Ler QR" é ação independente da busca e vive como botão flutuante (FAB) fixo no canto inferior-direito, fora do fluxo do card (decisão C-6).
- **FR-006**: Os cabeçalhos da tabela (Tombamento, Descrição, Local esperado, Estado local, Ações) MUST permanecer alinhados verticalmente com os dados das respectivas colunas.
- **FR-007**: Em telas estreitas, qualquer rolagem horizontal MUST ficar restrita à área da tabela; a página inteira MUST NOT transbordar horizontalmente.
- **FR-008**: O botão "Ler QR" (FAB — decisão C-6) MUST permanecer integralmente visível e acessível em qualquer largura de viewport e durante toda a rolagem — nunca cortado, fora da tela ou sobreposto por conteúdo (em telas pequenas apresenta apenas o ícone; abaixo do modal/backdrop do Bootstrap).
- **FR-009**: O layout MUST usar o grid e os utilitários Bootstrap já adotados pelo projeto; posicionamento absoluto (`position: absolute` com offsets) e larguras fixas desnecessárias (`width: 900px` etc.) MUST NOT ser introduzidos para elementos estruturais (preferir `width/max-width/min-width` fluidos quando necessário).
- **FR-010**: Os espaçamentos verticais/horizontais entre cabeçalho → pesquisa → tabela → conteúdo MUST ser padronizados com as classes de espaçamento Bootstrap já usadas pelo sistema (`mt-*`, `mb-*`, `gap-*` etc.), sem espaços excessivos nem elementos colados.
- **FR-011**: A página MUST funcionar nos modos claro e escuro usando as variáveis/classes de tema existentes — nenhuma cor específica de um único tema; contraste adequado preservado para texto, cabeçalhos, campos, botões, tabela, estados, bordas e fundo.
- **FR-012**: Nenhuma lógica funcional MUST ser alterada: preparação de pacote, coleta (QR/tombamento/modal), IndexedDB, fila de sincronização, reconciliação, indicadores de conexão, contadores e regras de inventário permanecem exatamente como estão.
- **FR-013**: Nenhum model, banco de dados, rota, permissão ou API MUST ser alterado; a mudança é restrita a HTML/template, CSS/classes e estrutura de containers/grid.
- **FR-014**: O Service Worker MUST ter apenas a versão de cache atualizada (`CACHE_VERSION`) para propagar o novo layout da shell aos dispositivos — nenhuma outra alteração de comportamento de cache, allowlist ou sincronização é permitida.
- **FR-015**: A suíte de testes existente MUST permanecer 100% verde após a mudança.
- **FR-016**: A correção MUST ser cirúrgica: reutilizar classes/componentes/CSS existentes antes de criar qualquer classe nova; não substituir todo o CSS da página sem necessidade.

### Key Entities *(include if feature involves data)*

- Não há entidades de dados novas ou alteradas — a feature é exclusivamente de apresentação. As estruturas existentes (pacote offline, coletas no IndexedDB, fila de sincronização) permanecem intocadas.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em 100% das larguras de teste (320, 375, 390, 430, 768, 1024, 1280, 1366, 1440 e 1920px), a página renderiza sem rolagem horizontal da página inteira (rolagem restrita à tabela quando houver).
- **SC-002**: "SisPatrimônio Pro" aparece abaixo da logo em 100% das larguras/orientações testadas, sem corte ou sobreposição.
- **SC-003**: As bordas do bloco pesquisa+"Ler QR" coincidem com as bordas da tabela em 100% dos tamanhos testados (mesmo container, mesmo alinhamento de colunas com seus dados).
- **SC-004**: Modo claro e modo escuro passam com contraste adequado em todos os elementos listados (inspeção visual em todos os tamanhos de teste).
- **SC-005**: Suíte pytest completa permanece 100% verde (nenhum teste funcional alterado) e o ciclo coletar → sincronizar é executado sem diferença de comportamento.
- **SC-006**: Nenhuma regra de negócio, dado, rota ou permissão alterada (`git status` confirma que apenas o template/CSS da shell e o `CACHE_VERSION` do SW mudam — além dos artefatos da spec).

## Assumptions

- A shell permanece página autônoma (sem `base.html`): a navbar completa do sistema não pode ser usada porque traria navegação administrativa proibida offline (FR-030 da 033) e dependências que o SW não cacheia — a padronização é do **padrão visual** (empilhamento da marca, container, largura, espaçamentos), não da estrutura de navegação.
- O padrão de container/largura de referência é o do `base.html` atual (`container-fluid` centralizado, `max-width: 90%` em desktop com padding lateral equivalente); a shell adota exatamente esse padrão a partir de 768px (decisão C-1; hoje usa 92% — diferença a eliminar) e mantém o comportamento mobile atual abaixo disso.
- Testes automatizados de layout não são exigidos além da suíte existente: a validação é visual/inspeção (checklist V1–V4 no quickstart), pois não há infraestrutura de teste de UI no projeto.
- A propagação do novo layout a dispositivos com cache exige bump do `CACHE_VERSION` do SW (arquivos estáticos cacheados: `style.css` com querystring de versão e a própria shell em navegação cache-first) — único toque admissível no SW.
- Nenhum teste pytest existente asserta o posicionamento visual atual da shell, de modo que a mudança de layout não deve exigir alteração em testes.

## Restrições de implementação (Constitution)

- **X (Interface Consistente)**: a correção segue os templates, componentes e convenções existentes; nenhuma alteração de UI pode quebrar o fluxo de coleta offline existente.
- **I (Evolução Incremental/escopo)**: alteração cirúrgica no template/CSS da shell + bump do SW; nenhuma refatoração não relacionada, mesmo que problemas em outros arquivos sejam encontrados no caminho.
- **XII (Validação)**: suíte verde + validação visual documentada antes de considerar concluída.
