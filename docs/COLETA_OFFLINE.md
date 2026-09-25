# Coleta Offline de Inventário — Guia de uso

> Feature 033 (inventário offline PWA). Referências técnicas: `specs/033-inventario-offline-pwa/` · `specs/035-conferencia-offline-layout/`

## O que é

A coleta offline permite fazer a conferência física dos bens **sem conexão com a internet** (galpão sem sinal, rede instável), usando celular ou tablet. As coletas ficam guardadas **no próprio dispositivo** (IndexedDB) e são enviadas ao servidor quando a conexão volta. O dispositivo **nunca é fonte de verdade**: tudo é revalidado pelo servidor na sincronização.

---

## Passo 1 — Preparar a coleta (precisa estar online)

1. Entre no inventário (status **Planejado** ou **Em andamento**).
2. Clique em **"Preparar coleta offline"** (requer permissão `inventario.conferir`).
3. O dispositivo recebe um **pacote** com apenas o essencial de cada item: tombamento, descrição, número de série, **local esperado** e a URL do QR. Nada de usuários, permissões ou credenciais.

> O pacote é uma "fotografia" do snapshot do inventário. Se o inventário for re-preparado ou encerrado, o pacote antigo fica inválido.

## Passo 2 — Coletar em campo (funciona sem internet)

Abra a coleta offline (botão/link da preparação, ou `/inventarios/{id}/offline`). A tela tem:

- **Painel de contadores**: Conferidas · Restantes · Divergências locais · Bens não previstos
- **Indicador de conexão** no topo (Online · status / **OFFLINE**) — verificação real por ping, não apenas o sinal do Wi‑Fi
- **Campo de pesquisa** por tombamento ou descrição (filtra a lista)
- **Botão flutuante "Ler QR"** (canto inferior direito) — sempre acessível durante a rolagem

### As 3 formas de coletar um item

| Forma | Como |
|---|---|
| **Câmera (recomendada)** | Toque no **"Ler QR"** e aponte para a etiqueta do bem |
| **Pesquisa** | Digite o tombamento/descrição → toque em **"Conferir"** na linha do bem |
| **Digitação de emergência** | Se a câmera não funcionar, o leitor oferece digitar a **URL do QR, o número do bem ou o tombamento** |

Em todos os casos abre o **mesmo formulário de conferência** do fluxo online.

### Os 4 resultados possíveis

1. 🟢 **Encontrado** — o bem está no local esperado. *Nenhum dado adicional é pedido.*
2. 🟡 **Encontrado em local diferente** — o bem apareceu em outro lugar. **Informe o nome do local onde ele foi encontrado** (campo livre — digite exatamente o nome; o **servidor valida** na sincronização: se o local não existir no cadastro, a coleta é rejeitada com `local_inexistente`).
3. 🔴 **Não encontrado** — o bem não está lá. Nada adicional.
4. ⚠️ **Sem identificação** — o bem está lá mas não pôde ser identificado (etiqueta ilegível, sem QR).

Cada coleta entra na **fila local** com estado *pendente de sync* — você pode continuar coletando normalmente, sem esperar rede.

### Bem NÃO PREVISTO (fora da lista)

Se escanear um QR de bem que **não está no pacote** (esquecido no local, transferido sem registro), o sistema registra uma **ocorrência local "não previsto"** — ela vai para o contador e é sincronizada como item não previsto do inventário.

> Por **tombamento digitado** o sistema não identifica bens fora do pacote, pois não há como validar offline — para não previstos, use a leitura do **QR** (câmera).

## Passo 3 — Sincronizar (de volta à rede)

O indicador no topo mostra quando está **Online**. Toque em **"Sincronizar agora"**. O servidor processa cada coleta e classifica em 4 destinos:

| Resultado | Significado | O que fazer |
|---|---|---|
| ✅ **Aceitas** | Gravadas no inventário oficial | Nada — viram resultado da conferência |
| 🔁 **Duplicadas** | Coleta já recebida antes (reenvio ou resultado igual) | Nada — idempotência, não duplica |
| ⚠️ **Conflitos** | Resultado **divergente** do que já consta no item | **Decidir** — veja seção A |
| ❌ **Rejeitadas** | Não pôde ser gravada (motivo informado) | Corrigir e re-coletar — veja seção B |

O servidor **nunca sobrescreve silenciosamente** um resultado divergente — é isso que protege a comprovação do inventário.

---

## Divergências e como resolver cada uma

### A) Conflito de resultado (CONFLICT)

**Quando acontece:** a coleta offline diz **ENCONTRADO**, mas o item já consta no sistema como **LOCAL_DIFERENTE/NAO_ENCONTRADO** (ou vice-versa) — típico quando alguém conferiu o mesmo bem pelo fluxo online enquanto a coleta offline esperava sincronização.

**Como resolver:** na **tela do inventário** (web), um card amarelo **"Conflitos offline"** lista cada caso com: bem, resultado offline vs. item atual, dispositivo e hora. Para cada conflito escolha:

- **KEEP (Manter atual)** — mantém o resultado que **já está no sistema** (ex.: o conferente online viu primeiro); a coleta offline é arquivada como *reconciliada* sem aplicar.
- **APPLY (Aplicar a coleta offline)** — grava o resultado trazido do campo **pelo mesmo mecanismo oficial** (`record_check`), com todas as validações. Só funciona com o inventário **aberto**; encerrado, apenas KEEP é possível.

A decisão é auditada (quem reconciliou, quando, o que escolheu).

### B) Coletas rejeitadas (REJECTED) — motivos e solução

| Motivo | O que aconteceu | Como resolver |
|---|---|---|
| `inventario_encerrado` | Inventário foi encerrado antes do sync | Abrir novo inventário incluindo o bem, se aplicável |
| `snapshot_mismatch` | O pacote do dispositivo é **antigo** (inventário re-preparado/alterado) | Conecte-se e **re-prepare a coleta offline**; re-colete o que faltar |
| `resultado_invalido` | Resultado declarado inválido | Re-coletar o item |
| `local_inexistente` | O nome do local digitado (divergência) **não existe** no cadastro | Corrigir o cadastro de locais OU re-coletar digitando o nome exato do local cadastrado |
| `responsavel_inexistente` | Responsável informado não existe no cadastro | Idem — corrigir cadastro ou re-coletar |
| `asset_fora_do_snapshot` | Bem não pertence ao inventário do pacote | Foi registrado como não previsto ou pertence a outro inventário — verificar |
| `local_nao_resolvido` | Divergência sem local informado | Re-coletar informando o local encontrado |

Coletas rejeitadas **não são perdidas**: ficam registradas com o motivo (rastreabilidade), mas não alteram o inventário.

### C) Divergências "normais" (LOCAL_DIFERENTE / NAO_ENCONTRADO)

Não são erros: são **resultados válidos** que o inventário registra para tratamento posterior. **O inventário nunca altera o cadastro** — o bem encontrado em local diferente deve ser regularizado depois por **Fluxo & Movimentação** (transferência), e o não encontrado vira busca física/apuração. A ata comprobatória final traz tudo consolidado.

---

## Dicas práticas

- **Encerramento**: exige todos os bens esperados conferidos — sincronize tudo antes de encerrar. Depois de encerrado, itens travam e coletas novas são rejeitadas.
- **"Encerrar coleta neste dispositivo"** (botão do card de sincronização): apaga do aparelho o pacote e as coletas **já sincronizadas** — use ao devolver o dispositivo. Coletas pendentes/conflitantes são preservadas.
- **Atualização da tela**: o sistema usa cache do navegador (Service Worker). Se o layout parecer antigo, abra a página **com internet** e recarregue — a nova versão assume sozinha.
- **Sessão expirada**: a coleta continua funcionando offline; a sessão só é validada na sincronização.
