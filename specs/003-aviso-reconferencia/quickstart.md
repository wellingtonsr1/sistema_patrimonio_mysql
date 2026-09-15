# Quickstart: Validação da feature 003 — Aviso de sobrescrita na re-conferência

**Feature**: 003-aviso-reconferencia | **Date**: 2026-09-15

Protocolo de validação ponta a ponta. **Pré-requisito**: implementação concluída conforme
[tasks.md](./tasks.md) (gerado por `/speckit-tasks`). Nenhum passo altera backend; os cenários manuais
usam o sistema rodando localmente.

---

## 1. Pré-requisitos

- Ambiente Python do projeto ativo; dependências instaladas.
- Banco acessível via `DATABASE_URL` (ou testes com SQLite in-memory — ver §3).
- Usuário de teste com perfil contendo `inventario.visualizar` + `inventario.conferir`
  (ex.: **Administrador** ou **Patrimônio**).
- Um inventário aberto (`PLANEJADO` ou `EM_ANDAMENTO`) com pelo menos 2 bens esperados.

Sugestão de preparo rápido pelo próprio sistema: criar inventário com escopo por local que contenha
2 bens ativos.

## 2. Cenários manuais (interface)

### Cenário A — Item PENDENTE: nada muda (CA-01)

1. `GET /inventarios/{id}` → na lista de bens esperados, clique no ícone "Registrar conferência" de um
   item **Pendente**.
2. **Esperado**: modal abre direto no formulário; **sem** alerta âmbar; ao clicar em "Registrar
   resultado", o registro acontece **sem** qualquer diálogo de confirmação.

### Cenário B — Item já conferido: alerta com dados (CA-02, CA-03, CA-08)

1. Confira primeiro um item (ex.: "🟢 Encontrado", observação opcional) para gerar histórico.
2. Reabra o modal do mesmo item.
3. **Esperado**: alerta `alert-warning` acima do formulário com:
   - "Já conferido por {seu usuário} em {dd/mm/aaaa hh:mm}";
   - "Resultado anterior: Encontrado";
   - aviso de que um novo registro substituirá o anterior.

### Cenário C — Confirmação e cancelamento (CA-04, CA-05)

1. No modal do item já conferido, selecione outro resultado e clique em "Registrar resultado".
2. **Esperado**: diálogo de confirmação: *"Este item já foi conferido. Registrar um novo resultado vai
   substituir o anterior. Continuar?"*
3. Clique em **Cancelar** → nenhuma requisição (observável na aba Network do devtools), formulário
   permanece aberto com a seleção intacta.
4. Repita e clique em **OK/Continuar** → POST normal, redirecionamento para a página do inventário,
   item exibe o novo resultado com conferente/data atualizados.

### Cenário D — Ausência de dados históricos (CA-08)

Simulação (o caso real — conferente excluído, `SET NULL` — é raro em dev): em banco de teste, torne
`checked_by_name` e `checked_at` nulos num item com resultado ≠ `PENDENTE`; reabra o modal.
**Esperado**: alerta exibe "Resultado anterior: {rótulo}" + aviso de substituição, **sem** os trechos
"por …" e "em …" e **sem** placeholders fictícios.

### Cenário E — Página de conferência em campo (US3)

1. Na ficha de um bem conferido, use o atalho de conferência do inventário aberto
   (`GET /inventarios/{id}/conferir/{asset_id}`).
2. **Esperado**: alerta existente ("Resultado já registrado: …") presente e complementado com
   conferente e data/hora; sem diálogo de confirmação no envio.
3. Repita com um bem **pendente** do mesmo inventário → badge "Pendente de conferência", sem alerta.

### Cenário F — Inventário ENCERRADO (CA-07)

1. Encerre um inventário (todos os itens conferidos) e acesse sua página.
2. **Esperado**: nenhum botão/modal de conferência; alerta de inventário encerrado; página
   `conferir.html` exibe trava e omite o formulário. Um POST direto à rota continua rejeitado pelo
   service (comportamento de fundo inalterado — pode ser conferido no teste de regressão existente).

## 3. Testes automatizados

```bash
# Suíte nova da feature (UI de re-conferência)
pytest tests/test_inventario_reconferencia_ui.py -v

# Regressão direta do módulo (deve permanecer 100% verde, sem modificações)
pytest tests/test_inventario.py -v

# Suíte completa
pytest
```

Casos cobertos pelo novo arquivo (asserções de HTML via TestClient, padrão existente do projeto):

1. Item pendente: modal sem alerta e `<form>` sem `onsubmit`.
2. Item conferido: modal com alerta contendo conferente, data e resultado anterior.
3. Item conferido: formulário com o `onsubmit` de confirmação (texto canônico).
4. Item conferido sem `checked_by_name`/`checked_at`: alerta omite os trechos (nada inventado).
5. `conferir.html`: alerta existente complementado com conferente/data.
6. `conferir.html`: item pendente sem alerta de sobrescrita.
7. Inventário encerrado: nenhum modal/botão de conferência na página.
8. POST de re-conferência continua funcionando via mesma rota (gravação inalterada).

## 4. Critério de sucesso final

- Todos os cenários manuais A–F conforme esperado **e** suíte completa verde.
- `git diff` mostra alterações **apenas** em `detail.html`, `conferir.html` e no novo arquivo de testes
  (+ atualização de documentação prevista no plano) — zero alteração de rotas, services, models, banco,
  permissões ou auditoria.
