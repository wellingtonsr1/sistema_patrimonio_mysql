# Contract — CSS de impressão dos relatórios (feature 013)

**Feature**: 013-impressao-relatorios | **Data**: 2026-09-17

Contrato do **novo bloco `@media print`** a ser adicionado ao **final** de `app/web/static/css/style.css` (após o bloco de Etiquetas). Nenhuma regra existente é editada; todas as regras novas estão ancoradas na classe de escopo `.report-print`.

---

## 1. Marcação (templates — única alteração permitida)

Nos 3 templates (`reports/movements_report.html`, `reports/custodians_report.html`, `reports/inventory.html`), a única alteração é no container do relatório:

```html
<!-- antes -->
<div class="card p-4">
<!-- depois -->
<div class="card p-4 report-print">
```

Nenhuma outra linha dos templates é tocada: dados, colunas, badges, condicionais e o botão `window.print()` permanecem idênticos.

## 2. Regras do novo bloco (contrato de implementação)

Ordem e intenção de cada regra (seletores sempre ancorados em `.report-print`):

| # | Regra | Intenção | Origem |
|---|---|---|---|
| C1 | `@page { margin: 10mm; }` — **sem `size`**: tamanho e orientação ficam selecionáveis no diálogo de impressão (A4 retrato como padrão do sistema, paisagem liberada — decisão do usuário 2026-09-17); o layout fluido (C3) se adapta à orientação escolhida | Margens determinísticas sem travar a orientação | R6 (revista) |
| C2 | `.report-print { page-break-inside: auto !important; break-inside: auto !important; }` | O card volta a poder atravessar páginas (revoga herança indesejada do `.card { avoid }` global neste escopo) | R1/R3 |
| C3 | `.report-print table { page-break-inside: auto !important; break-inside: auto !important; width: 100% !important; table-layout: auto !important; }` | **Causa raiz**: tabela deixa de ser bloco inquebrável (fim da página em branco) e colunas dimensionam por conteúdo (fim do espremimento) | R1/R4 |
| C4 | `.report-print thead { display: table-header-group !important; }` | Cabeçalho das colunas repete em todas as páginas | R3 |
| C5 | `.report-print tr { page-break-inside: avoid; break-inside: avoid; }` | Linha indivisível entre páginas | R3 |
| C6 | `.report-print .table-responsive { overflow: visible !important; min-width: 0 !important; }` | Contêiner de rolagem vira contêiner estático de largura integral | R4 |
| C7 | `.report-print td, .report-print th { white-space: normal !important; overflow-wrap: anywhere; max-width: none !important; }` | Revoga `text-nowrap` e `max-width` inline; textos longos quebram em vez de estourar/cortar | R5 (remediado A3 — `word-break: break-word` é valor obsoleto; `overflow-wrap: anywhere` cobre os navegadores-alvo) |
| C8 | `.report-print .truncate-2 { display: block !important; overflow: visible !important; -webkit-line-clamp: unset; }` | Motivo completo impresso (sem clamp de tela) | R5 |
| C9 | `.report-print { font-size: 8.5pt; } .report-print table { font-size: 8.5pt; }` | Escala compacta para 8–10 colunas em A4 retrato | R7 |
| C10 | `.report-print .badge, .report-print .status-pill { border: 1px solid #d1d5db; }` | Contraste em impressão P&B e com tema escuro ativo — **cores semânticas preservadas** (verde/vermelho dos status continuam visíveis em impressão colorida; a borda é o fallback natural em P&B) | R7 (remediado A1 — monocromatismo não era requisito do briefing) |

Notas de integridade:

- **Nenhuma regra global é editada** — C2/C3/C6/C7/C8 sobrecarregam por especificidade (`.report-print` + `!important`) apenas dentro do escopo das 3 páginas.
- **Etiquetas/Termo intocados**: os seletores novos não casam com `#labels-print-area`, `.label-card`, `.term-paper` ou `.term-container`.
- **Tema escuro**: o bloco PRINT II (paleta clara) permanece; C10 apenas reforça legibilidade.
- **Tela**: todas as regras estão dentro de `@media print` — zero efeito no layout de tela.

## 3. Resultado esperado (aceitação)

| Sintoma atual | Mecanismo | Resultado |
|---|---|---|
| 1ª página em branco | C3 (tabela quebrável) | Conteúdo inicia na página 1 |
| Colunas truncadas | C3+C4+C6+C7 | Largura integral, colunas por conteúdo, texto quebra |
| Motivo omitido | C8 | Texto completo |
| Linha cortada ao meio | C5 | Quebra entre linhas |
| Cabeçalho não repete | C4 | Repete em cada página |
| Papel instável | C1 | A4 fixo |

## 4. Traçabilidade spec → contrato

| Requisito | Regra(s) |
|---|---|
| FR-001/AC-01, AC-02 (sem página em branco) | C2, C3 |
| FR-002/AC-03 (limites A4) | C1, C3, C6, C7 |
| FR-003/AC-04 (nada truncado) | C7, C8 |
| FR-004/AC-05 (continuação + cabeçalho) | C3, C4 |
| FR-005/AC-06 (linha íntegra) | C5 |
| FR-006/AC-07 (dados idênticos) | §1 (única alteração de marcação) |
| FR-007/AC-08 (Etiquetas/Termo intocados) | §2 notas de integridade |
| FR-008 (sem bloco fantasma) | C2, C3 |
| FR-009 (contêiner estático/largura integral) | C6, C7 |
| FR-010 (clamp/nowrap desligados) | C7, C8 |
| FR-011 (quebra por unidade + A4) | C1, C3, C5 |
| FR-012 (CSS dedicado, sem editar existentes) | §2 notas de integridade |
