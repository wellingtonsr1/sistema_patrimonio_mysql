# UI Contract: Comportamento da interface de conferência (modais + página em campo)

**Feature**: 003-aviso-reconferencia | **Date**: 2026-09-15

Contrato de comportamento da camada de apresentação. A rota e o service de gravação **não fazem parte
desta feature** e permanecem intocados; são listados apenas como dependências consumidas.

---

## 1. Modal de conferência (`detail.html`, um por item esperado)

### 1.1 Abertura do modal

| Estado do item | Comportamento obrigatório |
|---|---|
| `status == PENDENTE` | Modal **idêntico ao atual**: formulário direto, sem alerta, sem confirmação, `<form>` sem `onsubmit` |
| `status != PENDENTE` | Alerta visual **acima do formulário** (antes do bloco "Local cadastrado…"), seguido do formulário atual |
| Inventário `ENCERRADO` **ou** usuário sem `inventario.conferir` | Modal não renderizado (condição do loop existente — inalterada) |

### 1.2 Conteúdo obrigatório do alerta (itens ≠ `PENDENTE`)

1. Frase de identificação: "Já conferido por {checked_by_name} em {checked_at}" — **cada trecho
   condicionado à presença do dado**; sem nenhum dos dois, abre direto com o resultado anterior.
2. "Resultado anterior: {status.label}".
3. Aviso explícito: "Registrar um novo resultado **substituirá** o resultado anterior."

Visual: componente `alert alert-warning small` (padrão existente do sistema) com ícone Bootstrap Icons
de advertência — consistente com o alerta informativo já usado em `conferir.html`.

### 1.3 Envio do formulário (itens ≠ `PENDENTE`)

| Ação do usuário | Comportamento obrigatório |
|---|---|
| Confirmar no diálogo | POST normal para `POST /inventarios/{inventario_id}/conferir/{item_id}` (rota e service atuais, sem modificações) |
| Cancelar no diálogo | **0 requisições**, formulário permanece aberto com o preenchido intacto |

Mecanismo: `onsubmit="return confirm('Este item já foi conferido. Registrar um novo resultado vai
substituir o anterior. Continuar?')"` — renderizado **apenas** para itens ≠ `PENDENTE` (condicional
server-side no Jinja; para `PENDENTE` o `<form>` é emitido sem o atributo).

### 1.4 Texto canônico do diálogo

```text
Este item já foi conferido. Registrar um novo resultado vai substituir o anterior. Continuar?
```

(Opções nativas do navegador: OK/Continuar e Cancelar.)

---

## 2. Página de conferência em campo (`conferir.html`)

| Estado do item | Comportamento obrigatório |
|---|---|
| `status == PENDENTE` | Apresentação atual preservada: badge "Pendente de conferência" + local/collaborador esperados |
| `status != PENDENTE` | Alerta existente **preservado** e **complementado** com "Conferido por {checked_by_name} em {checked_at}" (trechos com guard); mantém o resultado e o local encontrado já exibidos |
| Inventário `ENCERRADO` | Alerta de trava e ausência de formulário — inalterado |

**Sem** `confirm()` no envio desta página (decisão R1 do research).

---

## 3. Dependências consumidas (fora de escopo — intocadas)

| Dependência | Contrato consumido |
|---|---|
| `GET /inventarios/{inventario_id}` (`view_inventario`) | Fornece `expected_itens` (objetos `InventarioItem` completos) e `inv` ao `detail.html` |
| `GET /inventarios/{inventario_id}/conferir/{asset_id}` (`conferir_asset_page`) | Fornece `item`, `inv`, `asset` e `all_locations` ao `conferir.html` |
| `POST /inventarios/{inventario_id}/conferir/{item_id}` (`confer_item` → `record_check`) | Recebe `result`, `found_location_id`, `observation`; grava com carimbos de quem/quando + auditoria |
| Permissão `inventario.conferir` | Gate das rotas e da renderização dos modais — inalterada |

## 4. Critérios de conformidade do contrato

O contrato é atendido quando os cenários CA-01..CA-09 da [spec](../spec.md) passam no protocolo de
validação de [quickstart.md](../quickstart.md).
