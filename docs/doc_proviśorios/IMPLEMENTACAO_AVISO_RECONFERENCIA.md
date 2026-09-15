# IMPLEMENTAÇÃO DO CENÁRIO ESCOLHIDO — AVISO DE SOBRESCRITA NA RE-CONFERÊNCIA

**Sistema:** SisPatrimônio Pro
**Data:** 14/09/2026
**Decisão implementável:** *"Re-conferência permitida + confirmação explícita quando o item já tem resultado + aviso de quem conferiu antes — mantendo o travamento no encerramento"* (ver `docs/DECISAO_RECONFERENCIA_INVENTARIO.md`).

> Documento conceitual/planejamento — **nada foi implementado no código**.

---

## Visão geral

É uma mudança **apenas de interface (templates)**: zero alteração em rotas, service, banco ou permissões. As quatro partes:

### 1. Re-conferência permitida (já funciona hoje — nada muda)
Enquanto o inventário estiver `PLANEJADO` ou `EM_ANDAMENTO`, quem tem `inventario.conferir` pode submeter novo resultado a um item já conferido. O `record_check` continua sobrescrevendo `status`, `found_location_*`, `observation`, `checked_by_id/name` e `checked_at`.

### 2. Confirmação explícita (o que se acrescenta)
Hoje existe uma assimetria: a página `conferir.html` **já avisa** ("Resultado já registrado: … pode ser atualizado abaixo"), mas os **modais do `detail.html` não avisam nada** — abrem direto o formulário em branco. O ajuste é estender o mesmo alerta aos modais e, idealmente, pedir uma confirmação no envio:

- No modal, quando `item.status != 'PENDENTE'`, exibir um alerta âmbar acima do formulário.
- Opcionalmente, um `confirm()` em JavaScript no submit do formulário quando o item já tem resultado: *"Este item já foi conferido. Registrar novo resultado vai substituir o anterior. Continuar?"*

### 3. Aviso de quem conferiu antes (o dado que falta exibir)
O alerta mostra a trilha existente no próprio item (os campos `checked_by_name` e `checked_at` já estão carregados no template):

```text
┌─ Modal: TMB-2026-1141 — Notebook Dell ───────────────┐
│ ⚠️ Já conferido por Maria Souza em 12/09/2026 14:32  │
│    Resultado anterior: 🟢 Encontrado                 │
│    Registrar novo resultado vai SUBSTITUIR este.     │
│                                                      │
│ Resultado da conferência *                           │
│ ( ) 🟢 Encontrado  ( ) 🟡 Local diferente            │
│ ( ) 🔴 Não encontrado  ( ) ⚠️ Sem identificação      │
│ Local onde foi encontrado: [ — ▼ ]                   │
│ Observação: [____________]                           │
│                                                      │
│                    [Cancelar]  [Registrar resultado] │
└──────────────────────────────────────────────────────┘
```

Para itens `PENDENTE`, o modal continua exatamente como hoje (sem alerta).

### 4. Travamento no encerramento (já existe — permanece intacto)
- **Backend**: `record_check` levanta `ValueError("Este inventário está encerrado…")` quando o status é `ENCERRADO` — é a garantia real.
- **Frontend**: com inventário encerrado, os modais nem são renderizados, a página de conferência mostra o alerta de trava e os botões somem.

---

## Fluxo do usuário na prática

```text
Conferente B abre o modal de um item já conferido por A
      ↓
Vê o alerta: "Já conferido por Maria Souza em 12/09 14:32 — Encontrado"
      ↓
Confere no campo e decide:
   ├─ resultado de B é igual → não precisa registrar nada (evita sobrescrita à toa)
   └─ resultado diverge → marca novo resultado → confirm() "vai substituir" → OK
      ↓
POST /inventarios/{id}/conferir/{item_id} (rota e service intactos)
      ↓
Sobrescrita gravada + auditoria com antes/depois (quem, quando, IP)
      ↓
Ata final continua imutável após o encerramento
```

---

## Resumo do esforço

| Item | Onde | Esforço |
|---|---|---|
| Alerta de sobrescrita nos modais | `detail.html` (bloco do `#modalConferir{item.id}`) | ~5 linhas de Jinja |
| Aviso equivalente na página de conferência | `conferir.html` (já existe; só acrescentar conferente/data anteriores, se quiser) | ~1 linha |
| `confirm()` no submit | JS inline do `detail.html` | ~5 linhas |
| Regra de negócio / backend | — | **Nenhuma** |

**Resultado esperado:** o risco de sobrescrita silenciosa desaparece com custo mínimo, e a regra de fundo (liberdade enquanto aberto, prova imutável após encerrado) fica exatamente como decidido.

---

## Referência cruzada

- Decisão de design da re-conferência: `docs/DECISAO_RECONFERENCIA_INVENTARIO.md`
- Regras de negócio do módulo: `docs/REGRAS_DE_NEGOCIO_INVENTARIO.md` (seção 4)
- Auditoria completa da funcionalidade: `docs/AUDITORIA_FUNCIONALIDADE_INVENTARIO.md`
