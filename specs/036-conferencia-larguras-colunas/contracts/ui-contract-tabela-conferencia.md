# Contract de UI: Tabela de Bens Esperados da Conferência (036)

Contrato de apresentação da tabela de bens esperados em `app/web/templates/inventarios/detail.html` — define o que a mudança de larguras **não pode quebrar**. Nenhum contrato de API/dados muda nesta feature (não há endpoints novos).

## §1 Contrato DOM (JS/Bootstrap ↔ template — IDs e atributos funcionais intocados)

Elementos selecionados por identificadores/atributos **não podem ser removidos, renomeados ou perder a função**:

| Identificador | Origem | Função |
|---|---|---|
| `formBuscar` | template/JS | Formulário de busca de bem (POST `/inventarios/{id}/buscar`) |
| `#modalConferir{{ item.id }}` | template | Modal de conferência por item (aberto pelo botão da coluna Conferir) |
| `#modalEncerrar` | template | Modal de encerramento (fora do escopo, mas na mesma página — não tocar) |
| `data-bs-toggle="modal"` / `data-bs-target` | Bootstrap 5.3 | Disparo dos modais pelo botão-ícone |
| `tag-badge`, `badge-soft-gray/green/amber/red` | `style.css` | Visual de tombamento e status (sem alteração de classe) |
| `btn btn-ghost btn-icon` | `style.css` | Botão-ícone da ação de conferir (sem alteração de classe) |
| link `/assets/{{ item.asset.id }}` | template | Navegação para a ficha do bem a partir do tombamento |

## §2 Contrato de conteúdo (FR-011 — nada exibido é removido)

Por linha da tabela, TODOS estes elementos permanecem renderizados como hoje:

1. Tombamento como link com badge.
2. Nome do bem (`small fw-semibold`).
3. Local esperado (ou fallback "Estoque Central").
4. Badge de resultado com o mesmo vocabulário/cores: `Pendente`, `✓ Encontrado`, `⚠ Local diferente[: local]`, `✕ Não encontrado`, `⚠ Sem identificação`.
5. Observação do item (quando existir) — `em`, `.72rem`.
6. Metadados "data • usuário" da conferência (quando existirem) — `.68rem`.
7. Botão de conferir (somente quando `inv.status != 'ENCERRADO'` **e** `can_conferir` — condição Jinja preservada).

## §3 Contrato de comportamento responsivo (FR-008/C-3)

| Viewport | Comportamento exigido |
|---|---|
| Desktop largo (≥1400px) | Proporções de referência visíveis; Bem/Local esperado dominam; linha única nos textos típicos |
| Desktop médio (768–1399px) | Mesmas proporções relativas; sem sobreposição; nomes longos podem quebrar linha |
| Tablet (≥576 e <768px) | Proporções mantidas; `table-responsive` pode rolar horizontalmente **dentro do contêiner da tabela** se inevitável; botão acessível |
| Celular (<576px) | Tabela utilizável; rolagem horizontal restrita ao contêiner; nenhuma coluna invisível/cortada sem rolagem |
| Zoom 80%–200% | Mesmos critérios de legibilidade e ausência de sobreposição (decisão da clarificação Q3) |

## §4 Contrato de não-vazamento de escopo (FR-009/FR-012)

- O CSS novo é **escopado** à tabela-alvo (classe dedicada na `<table>` + seletor no `<style>` embutido): as tabelas dos cards "Conflitos offline" e "coletas offline" NÃO podem herdar nenhuma regra nova.
- Nenhuma regra global (`table { ... }`, `td { ... }` sem escopo) pode ser introduzida.
- Nenhum asset estático alterado → nenhum bump de versão de cache (`style.css?v=` e SW allowlist permanecem como estão — research R8).

## §5 Critérios de violação do contrato

O contrato é violado se, após a alteração:

1. Algum ID/atributo do §1 não funcionar (modal não abre, busca falha, link não navega).
2. Algum item do §2 deixar de renderizar.
3. As tabelas dos cards Conflitos/coletas mudarem de aparência.
4. `style.css` ou `sw.js` forem modificados.
5. A página lançar erro de template (suíte pytest detecta via `test_conferencia_visual.py`/`test_inventario*.py`).
