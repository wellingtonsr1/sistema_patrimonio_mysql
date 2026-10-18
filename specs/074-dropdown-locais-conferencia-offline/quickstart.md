# Quickstart — Validação do 074 Dropdown de Locais na Conferência Offline

**Data**: 2026-10-18 | Guia de validação fim-a-fim. Detalhes em [contracts/offline-package-locations-contract.md](./contracts/offline-package-locations-contract.md) e [data-model.md](./data-model.md).

## Pré-requisitos

- Ambiente do projeto com dependências instaladas e banco acessível (`DATABASE_URL`).
- Usuário com permissões `inventario.visualizar` + `inventario.conferir` (ex.: Patrimônio/Administrador).
- Um inventário `EM_ANDAMENTO` com itens gerados e **ao menos 2 locais cadastrados** (cadastre via `/locais` se preciso).

## 1. Automação (obrigatória antes de declarar pronto)

```bash
# Suíte completa — deve permanecer 100% verde (SC-008)
pytest -q

# Cobertura nova da feature 074
pytest -q tests/test_dropdown_locais_offline_074.py
```

Critérios: 0 falhas; nenhum teste existente alterado/enfraquecido; testes novos cobrindo:
1. `POST .../offline/package` devolve `locations` com `id`+`name` completos e ordenados;
2. Pacote antigo (payload sem `locations`) é tratado como lista indisponível;
3. Coleta offline `LOCAL_DIFERENTE` com `found_location_id` é **aceita** no sync e o item fica com o local correto;
4. `found_location_id` inexistente → rejeição `local_inexistente` **sem descartar** a coleta;
5. Coleta antiga só com `found_location_name` continua sincronizando (retrocompat);
6. Página offline sem controles sem nome (regressão acessibilidade 069).

## 2. Validação manual (cenários da spec)

### Cenário A — Carregamento online
1. Abra `/inventarios/{id}` → clique **Preparar coleta offline**.
2. DevTools → IndexedDB → `sispatrimonio_offline` → store `packages` → o record do inventário contém `locations[]` com todos os locais.

### Cenário B — Seleção offline
1. DevTools → Network → **Offline** (ou desative a rede) → abra **Abrir coleta offline**.
2. Clique **Conferir** em um item → marque 🟡 **Encontrado em local diferente**.
3. **Esperado**: campo vira `<select>` com os locais; selecionar funciona sem nenhuma requisição (aba Network sem chamadas).

### Cenário C — Persistência
1. Após registrar a coleta, recarregue a página offline e reabra o item.
2. **Esperado**: painel mostra o item coletado (status LOCAL_DIFERENTE · pendente de sync).

### Cenário D — Sincronização
1. Volte a ficar online → **Sincronizar**.
2. **Esperado**: `4/N` aceitas; no servidor, o item tem `found_location_id` correto e `local_encontrado` exibido na tela do inventário.

### Cenário E — Falha de atualização
1. Com rede, clique **Preparar novamente** com a rede bloqueada após a confirmação.
2. **Esperado**: alerta de falha; o pacote anterior (com `locations`) permanece no IndexedDB e segue utilizável.

### Cenário F — Lista indisponível (pacote antigo)
1. Simule pacote antigo: em DevTools, remova o campo `locations` do record e salve; abra a coleta offline sem rede.
2. Marque 🟡.
3. **Esperado**: mensagem "reconecte e prepare a coleta offline"; registro **bloqueado**; nenhum texto livre; nenhum local inventado.

### Cenário G — Local inválido
1. Online, envie coleta (API) com `found_location_id: 999999`.
2. **Esperado**: rejeição `local_inexistente`; coleta preservada; nada atribuído automaticamente.

### Cenário H — Compatibilidade
1. Coleta antiga só com `found_location_name` válido → sincroniza e resolve o id (nome único).
2. **Esperado**: aceita; nenhum registro descartado.

### Cenário I — Integridade patrimonial
1. Bem com localização cadastral A, encontrado em B (🟡 + dropdown).
2. **Esperado**: cadastro do bem permanece com local A; apenas o registro da conferência carrega B; nenhuma movimentação criada.

### Cenário J — Não regressão
1. Conferência **Online** (modal `detail.html` + `conferir.html`): inalterada.
2. Preparar/re-preparar/encerrar coleta, pendências, conflitos: comportamento anterior preservado.

## 3. Verificações de apoio

```bash
# Bump de cache presente (o shell/JS atualizado chega aos dispositivos)
grep -n 'CACHE_VERSION' app/web/static/js/sw.js   # esperado: inventario-offline-v35

# Conferência Online intacta
grep -n 'all_locations' app/web/templates/inventarios/detail.html app/web/templates/inventarios/conferir.html

# Diff contendo apenas os 5 arquivos previstos em plan.md (SC-009)
git diff --stat
```
