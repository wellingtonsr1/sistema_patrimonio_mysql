# UI Contract — Cartão de Evento de Alteração Cadastral na Trilha (Feature 070)

**Alcance**: somente o ramo `{% if item.type == 'audit' %}` do loop da trilha em `app/web/templates/assets/detail.html` (~L285–321). **Fora do contrato**: cartões de movimentação (063/064), painel "Alterações cadastrais" (067), "Custódia & Localização Atual", ficha técnica, QR Code, demais templates e a API.

---

## 1. Estrutura do cartão (caminho com resumo — dois estados + diff)

Mantém-se inalterado o cabeçalho atual: badges (`action_label(item.data.action)`, módulo, `resource_ref`) + data/hora (`(item.timestamp | localtime).strftime('%d/%m/%Y %H:%M')`) e o rodapé "Registrado por". Entre eles:

```html
<div class="fw-semibold small mb-1" style="color:var(--c-text);">
    {{ item.audit_summary.titulo }}          {# ex.: "Alteração cadastral — Nome do bem" #}
</div>
<ul class="list-unstyled mb-0 small">        {# resumo — mesmo padrão visual do painel 067 (L238–248) #}
    {% for m in item.audit_summary.mudancas %}
    <li class="text-muted">
        {{ m.label }}:
        <span class="text-decoration-line-through">{{ m.before if m.before is not none else '—' }}</span>
        <i class="bi bi-arrow-right mx-1"></i>
        <strong style="color:var(--c-text);">{{ m.after if m.after is not none else '—' }}</strong>
    </li>
    {% endfor %}
</ul>
<details class="mt-1">                        {# recolhido por padrão: SEM atributo open #}
    <summary class="small text-muted">Ver detalhes técnicos</summary>
    {% if item.prev_data %}                   {# estados originais preservados e distinguíveis #}
    <div class="small text-muted mt-1">Antes:</div>
    <pre class="small mb-2" style="white-space:pre-wrap;word-break:break-word;">{{ item.prev_data | tojson(indent=2) }}</pre>
    {% endif %}
    {% if item.new_data %}
    <div class="small text-muted mt-1">Depois:</div>
    <pre class="small mb-0" style="white-space:pre-wrap;word-break:break-word;">{{ item.new_data | tojson(indent=2) }}</pre>
    {% endif %}
</details>
```

## 2. Regras de renderização

| # | Regra |
|---|---|
| M1 | `titulo`: um campo alterado → `Alteração cadastral — <label>`; ≥2 → `Alteração cadastral — Dados do equipamento`; **sem título quando não há diff** |
| M2 | Resumo lista **somente** campos do diff (`item.audit_summary.mudancas`), ordenados por rótulo; inalterados não aparecem |
| M3 | `None` (nulo ou ausente) renderiza `—` nos dois lados; valores exibem-se inteiros (sem truncamento); textos longos quebram linha via `pre-wrap` |
| M4 | A linha `<strong>Descrição:</strong> {{ item.data.description ... }}` atual é exibida **apenas** quando `audit_summary` não existe ou não tem diff (caminhos de fallback) — nunca junto do resumo |
| M5 | `<details>` **sem** `open` por padrão; `<summary>` com texto acessível "Ver detalhes técnicos"; operável por teclado pelo comportamento nativo (AC13) |
| M6 | JSON exibido via `tojson` + autoescape (nunca `|safe`); `<script>` etc. aparecem como **texto** (AC10); o conteúdo nunca é interpretado |
| M7 | `<pre style="white-space:pre-wrap;word-break:break-word">` garante quebra sem rolagem horizontal da página (AC14) |
| M8 | Estilos reaproveitados do painel 067 e do tema atual — **zero CSS/JS novo** obrigatório (sem animações novas) |
| M9 | Escopo do diff de template: somente dentro do ramo `{% if item.type == 'audit' %}` — uma linha alterada fora desse ramo é fora do contrato |

## 3. Caminhos de fallback (contrato por cenário)

| Cenário | Cartão renderizado |
|---|---|
| Diff disponível (dois dicts) | Seção 1 completa |
| Diff vazio (dois dicts iguais) | Badges + descrição atual + `<details>` com os dois estados |
| Um único estado dict | Badges + descrição atual + `<details>` com o estado disponível (rótulo "Antes:"/"Depois:" conforme o lado) |
| Nenhum dict (JSON inválido/ausente) | **Idêntico ao atual** — badges + `Descrição:` + "Registrado por"; sem `<details>` |

## 4. Fora do contrato

- Cartões de movimentação (Origem/Destino padrão 063/064, motivo, operador, termo) — byte-a-byte.
- Painel "Alterações cadastrais" (`id="historico-cadastral"`) — byte-a-byte.
- `GET /api/v1/assets/{id}/timeline` e `MovementService.get_timeline_for_asset` — ver `preserved-contracts.md`.
- `/admin/audit`, relatórios, exportações, demais telas.
