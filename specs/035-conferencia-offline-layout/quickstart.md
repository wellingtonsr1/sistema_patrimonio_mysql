# Quickstart: Conferência Offline — responsividade e padronização visual (035)

Guia de validação ponta a ponta. Referências: [contract](contracts/ui-shell-offline-contract.md) · [data-model](data-model.md) · [spec](spec.md)

## Pré-requisitos

- Ambiente de dev rodando (`.venv/bin/python run.py`); usuário com `inventario.conferir`.
- Um inventário em `PLANEJADO`/`EM_ANDAMENTO` com itens (mesmo local usado nos testes da 033).
- Suíte de regressão: `.venv/bin/python -m pytest tests/ -q` (deve permanecer 100% verde).

## Como abrir a shell

1. **Inventários** → abrir o inventário → **Preparar coleta offline** (gera o pacote no dispositivo).
2. Acessar `/inventarios/{id}/offline` (desktop: mesma janela; celular: URL direta ou QR).

## Cenários de validação

### V1 — Marca empilhada e cabeçalho (US1/D1/D4)

1. Desktop (≥768px): barra superior mostra **logo acima** e "SisPatrimônio Pro" **abaixo**, centralizados entre si — igual à navbar principal do sistema (comparar com qualquer página logada).
2. Código do inventário e indicador "Online · {status}" visíveis na mesma linha (≥768px).
3. Reduzir para ≤767px: código + indicador passam à segunda linha do cabeçalho; logo/nome permanecem íntegros; toggle de tema acessível.
4. Nenhum elemento é cortado, sobreposto ou escondido em nenhuma largura.

### V2 — Container e largura padronizados (US2/D2)

1. Desktop ≥768px: abrir a shell e uma página qualquer do sistema (ex.: listagem de inventários) na mesma janela — as bordas do conteúdo coincidem (90% centralizado, mesmas margens).
2. Medir os blocos: alerta, contadores, sincronização, pesquisa+tabela — todos terminam na mesma linha vertical (nenhum ultrapassa o container).
3. ≤767px: página aproveita 100% da largura com padding compacto (comportamento mobile atual mantido).

### V3 — Pesquisa, "Ler QR" e tabela alinhados (US3/D3)

1. A linha [pesquisa | Ler QR] ocupa exatamente a largura da tabela abaixo (mesmas bordas do card).
2. Cabeçalhos Tombamento/Descrição/Local esperado/Estado local/Ações alinham com os dados.
3. Pesquisar um termo que zere a lista: mensagem "Nenhum item encontrado" dentro do mesmo container.
4. Digitar descrição/local longo: célula quebra o texto sem empurrar colunas nem transbordar.

### V4 — Telas pequenas, rolagem e tema (US4/US5)

1. Viewport 320px (DevTools device emulation): **nenhuma** rolagem horizontal da página; rolar a tabela horizontalmente dentro do próprio bloco quando necessário.
2. "Ler QR" integralmente visível (pode reorganizar verticalmente com a pesquisa).
3. Alternar tema claro/escuro: contraste correto em texto, cabeçalhos, campos, botões, tabela, estados, bordas e fundo nos dois temas.
4. Girar retrato/paisagem: layout se reorganiza sem quebras.

### V5 — Funcionalidade intocada (US5/FR-012)

1. Coletar um item (Conferir → modal → ENCONTRADO): contador "Conferidas" incrementa; badge do estado atualiza; item vira "Coletado".
2. Gerar divergência (LOCAL_DIFERENTE com local informado): aparece no contador de divergências.
3. "Sincronizar agora" com pendências: coletas gravadas; contadores recalculam.
4. Indicador de conexão alterna Online/OFFLINE (derrubar/reestabelecer servidor).
5. Suíte: `.venv/bin/python -m pytest tests/ -q` → 100% verde.

## Roteiro visual por largura (V1–V4 em cada uma)

```text
320 · 375 · 390 · 430 · 768 · 1024 · 1280 · 1366 · 1440 · 1920 px
(claro/escuro × retrato/paisagem × poucos/muitos registros × textos longos)
```

## Propagação do cache (pós-implementação)

Após o bump do `CACHE_VERSION` (v24 → v25): reabrir a shell **online** em um dispositivo que já usava a coleta offline — o novo layout carrega na próxima visita (o SW detecta o novo worker e ativa o cache novo). Nenhuma limpeza manual de cache é necessária.

## Automação (pytest)

Nenhum teste novo. `tests/test_inventario_offline.py` (34 testes) e a suíte completa validam não-regressão funcional (rota, RBAC, pacote, coleta, sincronização).
