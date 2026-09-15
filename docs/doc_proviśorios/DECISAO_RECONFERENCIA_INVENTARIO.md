# DECISÃO DE DESIGN — RE-CONFERÊNCIA DE ITENS DO INVENTÁRIO

**Sistema:** SisPatrimônio Pro
**Data:** 14/09/2026
**Pergunta avaliada:** *A re-conferência (sobrescrita do resultado enquanto o inventário está aberto) está adequada, ou seria melhor bloquear a edição dos itens já conferidos?*

---

## Comportamento atual vs. bloquear re-conferências

O desenho atual — **editável enquanto aberto, imutável após o encerramento** — é fundamentalmente o modelo certo. Não se deve bloquear a edição dos itens já conferidos de imediato. Mas há duas salvaguardas baratas que valem a pena acrescentar.

### Por que bloquear é a escolha errada

- **A realidade de campo exige correção.** Durante uma conferência com centenas ou milhares de itens, resultados errados acontecem o tempo todo: um rádio marcado errado, um local "encontrado" equivocado, um erro de digitação na observação. Se a re-conferência fosse bloqueada, os operadores bateriam num muro e passariam a exigir recursos de cancelamento/reabertura — o que seria muito pior para a integridade das evidências do que uma sobrescrita controlada.
- **O limite de imutabilidade já existe no lugar certo.** O "registro oficial" é a ata *encerrada*. O encerramento trava tudo (`ValueError` no service + travas nos dois templates). É aí que a imutabilidade probatória pertence: rascunhos são provisórios, o inventário encerrado é a prova.
- **A sobrescrita não é cega.** Toda gravação carimba `checked_by_name` + `checked_at` e gera uma entrada de auditoria com o novo resultado — o valor anterior é recuperável de `audit_logs.new_data`/`previous_data`.

### O que o desenho atual ainda não tem (o risco real)

1. **Sobrescrita silenciosa entre conferentes.** O conferente A registra ENCONTRADO; o conferente B depois sobrescreve com LOCAL_DIFERENTE sem jamais ver o resultado de A. Nada na tela diz "isto já foi conferido por X". Para um módulo que se apresenta como *comprobatório*, esse é o ponto fraco.
2. **O histórico existe, mas não é exposto.** A página de detalhe mostra só o último resultado; o anterior fica enterrado na trilha de auditoria.

### Meio-termo recomendado (em ordem de valor/esforço)

1. **Confirmação na sobrescrita** — quando o item não estiver mais PENDENTE, mostrar "Já conferido por {nome} em {data/hora} — você está atualizando este resultado" antes do POST. Barato, elimina o risco de sobrescrita acidental. (Observação: o `conferir.html` já exibe um alerta informativo de que existe resultado registrado — estender esse aviso aos modais do `detail.html` cobriria os dois caminhos.)
2. **Tornar a mudança visível** — após uma re-conferência, marcar o item como "atualizado" (a informação já está na trilha de auditoria; falta apenas exibi-la).
3. **Somente se os requisitos probatórios crescerem**: versionar as conferências — uma tabela de histórico por item (`resultado`, conferente, data/hora, observação), em que a entrada mais recente é a vigente. Assim nada é sobrescrito, nem em rascunho. É o "melhor dos dois mundos", mas adiciona complexidade de schema e UI — justificável apenas se a organização precisar do histórico completo de re-conferências no banco para contestações.

---

## Comparação dos cenários

| Cenário | Agilidade em campo | Integridade da evidência | Custo | Veredito |
|---|---|---|---|---|
| 1. Como está hoje | ✅ Total | ⚠️ Sobrescrita silenciosa é possível | Zero | Aceitável, mas com risco evitável |
| 2. Bloquear já conferidos | ❌ Operador trava; vai exigir cancelar/reabrir | ✅ | Baixo | **Pior opção** — troca nuance pequena por paralisia real |
| 3. **Liberdade + confirmação + aviso do conferente anterior** | ✅ Total | ✅ Ninguém sobrescreve sem saber | **Baixo** (ajuste de template) | **Melhor cenário** |
| 4. Histórico versionado completo | ✅ Total | ✅✅ Nada é perdido nem em rascunho | Alto (nova tabela, schema, UI) | Só vale se houver exigência real de contestações judiciais/administrativas |

---

## DECISÃO FINAL (14/09/2026)

**Cenário 3 adotado: re-conferência permitida (liberdade) + confirmação explícita de sobrescrita + aviso do conferente anterior, mantendo o travamento no encerramento.**

O comportamento de fundo atual (editável enquanto aberto, imutável após encerrado) permanece como regra de negócio; o que muda é apenas a **camada de segurança na sobrescrita**:

1. Nos **modais de conferência do `detail.html`** (mantendo o alerta que o `conferir.html` já exibe): quando `item.status != PENDENTE`, mostrar *"Já conferido por {checked_by_name} em {checked_at} — registrar novo resultado vai substituir este"*.
2. Opcionalmente, marcar na listagem os itens re-conferidos como "atualizado" (informação já disponível na trilha de auditoria).

**Por que o histórico versionado (cenário 4) fica descartado por ora:** a prova definitiva já está garantida pelos dois mecanismos que existem hoje — o **travamento no encerramento** (a ata fechada é imutável) e a **trilha de auditoria** (cada sobrescrita grava antes/depois com usuário e IP em `audit_logs`). O versionamento duplicaria essa proteção no banco ao custo de nova tabela, alteração de schema, UI adicional e complexidade de manutenção, sem atender a nenhuma exigência atual. Ele permanece documentado como opção a reavaliar **somente se** a organização passar a precisar do histórico completo de re-conferências para contestações judiciais/administrativas.

**Síntese:** é a mudança de melhor custo-benefício — algumas dezenas de linhas de template, zero alteração de regra de negócio, zero risco de regressão — e o módulo passa a se comportar de fato como *comprobatório* também no momento da sobrescrita.

---

## Veredito

**Como está, a regra é boa e operacionalmente correta; não bloquear a re-conferência — confirmá-la e expô-la.** Bloquear trocaria uma nuance pequena de rastreabilidade por paralisia operacional real, enquanto o travamento no encerramento já garante a integridade do registro final.

---

## Referência cruzada

- Auditoria completa da funcionalidade: `docs/AUDITORIA_FUNCIONALIDADE_INVENTARIO.md`
- Regras de negócio do módulo: `docs/REGRAS_DE_NEGOCIO_INVENTARIO.md` (seção 4 — regra da re-conferência)
