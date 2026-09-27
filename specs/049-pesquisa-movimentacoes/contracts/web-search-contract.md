# Contract: Pesquisa no Fluxo Global de Movimentações (`GET /movements`)

**Feature**: 049-pesquisa-movimentacoes  
**Base**: Extensão da rota web existente `list_movements_view` em `app/web/routes.py`.  

---

## 1. Interface HTTP

```text
GET /movements                                          -> listagem padrão dos 200 registros mais recentes
GET /movements?search=<termo>                           -> listagem filtrada por termo de pesquisa
GET /movements?search=<termo>&movement_type=<tipo>      -> listagem filtrada por termo E tipo (cumulativo)
GET /movements?movement_type=<tipo>                     -> listagem filtrada apenas por tipo (comportamento atual)
```

### Parâmetros de Requisição (Query String)

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `search` | string | Não | Termo de pesquisa textual livre informado pelo usuário. Espaços nas extremidades são ignorados (`strip()`). Vazio = pesquisa desativada. |
| `movement_type` | string | Não | Filtro existente por tipo de movimentação (`ENTRADA_AQUISICAO`, `ALOCACAO_CAUTELA`, etc.). |
| `asset_id` | integer | Não | Filtro existente por ID específico de equipamento. |

### Guarda de Segurança (RBAC)

- Exige usuário autenticado na sessão web.
- Exige permissão explícita `movimentacao.visualizar`.
- Usuários não autorizados recebem HTTP 403 / redirecionamento apropriado.

---

## 2. Comportamentos de Saída e Estados de Tela

| Cenário de Entrada | Resposta HTTP | Renderização em Tela |
|---|---|---|
| `search` vazio ou ausente | HTTP 200 | Tabela padrão com até 200 registros mais recentes ordenados decrescentemente por data. |
| `search` com correspondências encontradas | HTTP 200 | Tabela contendo apenas os registros compatíveis (até 200 itens). O campo de pesquisa é mantido preenchido com o termo pesquisado (`value="{{ search }}"`). Contador exibe a quantidade de registros encontrados. |
| `search` com correspondências + `movement_type` | HTTP 200 | Tabela contendo apenas registros que atendem **ambos** os critérios. Ambos os campos permanecem preenchidos no formulário. |
| `search` sem nenhuma correspondência | HTTP 200 | Bloco `.empty-state` com mensagem contextualizada: *"Nenhuma movimentação encontrada para a pesquisa informada."*, texto orientativo e botão de ação para limpar a pesquisa. |
| Banco de dados sem nenhuma movimentação (sem busca) | HTTP 200 | Estado vazio padrão atual: *"Nenhuma movimentação encontrada. Ajuste os filtros ou registre uma nova movimentação."*. |

---

## 3. Especificação do Componente Visual (UI)

O formulário de filtros em `app/web/templates/movements/list.html` deve manter o layout responsivo Bootstrap 5:

```html
<form method="get" action="/movements" class="row g-3 align-items-end">
    <!-- Campo de Pesquisa -->
    <div class="col-12 col-md-6 col-lg-5">
        <label class="form-label small fw-semibold">Pesquisar</label>
        <div class="input-group">
            <span class="input-group-text bg-white border-end-0 text-muted"><i class="bi bi-search"></i></span>
            <input type="text" name="search" class="form-control border-start-0 ps-0"
                   placeholder="Pesquisar por tombamento, equipamento, colaborador, local, termo..."
                   value="{{ search }}">
        </div>
    </div>

    <!-- Dropdown de Tipo de Movimentação -->
    <div class="col-12 col-md-4 col-lg-4">
        <label class="form-label small fw-semibold">Tipo de Movimentação</label>
        <select name="movement_type" class="form-select">
            <option value="">Todos os Tipos</option>
            {% for mt in movement_types %}
            <option value="{{ mt.value }}" {% if selected_type == mt.value %}selected{% endif %}>{{ mt.label }}</option>
            {% endfor %}
        </select>
    </div>

    <!-- Botões de Ação -->
    <div class="col-12 col-md-2 col-lg-3 d-flex gap-2">
        <button type="submit" class="btn btn-primary"><i class="bi bi-funnel me-1"></i> Filtrar</button>
        <a href="/movements" class="btn btn-ghost">Limpar</a>
    </div>
</form>
```

---

## 4. Regras de Não-Regressão

1. Chamadas a `/movements` sem o parâmetro `search` produzem resposta visual e lógica idêntica à versão anterior.
2. A listagem preserva todas as 9 colunas da tabela (`Data/Hora`, `Tombamento`, `Equipamento`, `Tipo`, `Origem`, `Destino`, `Motivo`, `Operador`, `Ações`) e a largura responsiva definida na Feature 039 (`.mov-lista-table`).
3. As ações de linha (ver bem `/assets/{id}` e imprimir termo `/movements/{id}/term`) continuam funcionando normalmente.
4. Nenhuma operação de escrita é acionada por requisições GET.
