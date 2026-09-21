# Backup Automático — por que não testar vários disparos no mesmo ciclo

**Data**: 21/09/2026 · **Relacionada**: feature 028 (correção do ciclo de backup/restauração/agendamento)

Este documento explica por que o backup automático dispara **apenas 1× por ciclo** — e por que "testar vários disparos" não é um caminho operacional, mas a própria funcionalidade funcionando.

---

## 1. É a regra de negócio aprovada — o mecanismo foi desenhado para isso

A feature 028 define: **dispara 1× por ciclo** (diário = dia calendário local; semanal = semana iniciando no dia configurado). Duas barreiras independentes impedem o segundo disparo:

1. **Critério de execução devida** — o tick do agendador (a cada 30 s) só dispara quando **as duas condições** são verdadeiras:
   - o horário agendado do ciclo corrente **já venceu**; **e**
   - **não existe** backup `AUTOMATICO` / `SUCCESS` no ciclo corrente.

   Depois do primeiro sucesso do dia, a segunda condição vira falsa — não importa quantos ticks passem ou quantas vezes o horário seja alterado na configuração.

2. **Marca de ciclo em memória** (`_attempted_cycle_keys`) — mesmo que algo mude no banco, cada ciclo só é **tentado** 1× por execução do scheduler. Isso também evita que uma falha gere nova tentativa a cada 30 s (sem "retry em rajada") e que catch-up + disparo normal executem duas vezes o mesmo ciclo.

Isso não é limitação técnica — é exatamente o comportamento especificado para evitar a **tempestade de backups** (08:16 → backup, 08:16:30 → outro, 08:17 → outro...). **Testar vários disparos exigiria remover as guardas** — ou seja, desligar em teste a única coisa que protege a produção do problema que motivou a regra.

---

## 2. O que "vários disparos" destruiria na prática

| Impacto | Consequência |
|---|---|
| **Disco** | cada backup é um dump completo (`.sql.gz`) — N disparos = N× espaço consumido |
| **Servidor/Banco** | cada um é um `mysqldump --single-transaction`: I/O, CPU e leitura de todas as tabelas — em rajada, degrada o sistema em produção |
| **Retenção GFS** | a política preserva o automático mais recente de cada semana/mês; duplicados de teste podem desancorar backups "bons" e causar remoção indevida |
| **Auditoria e listagem** | eventos e registros falsos poluem a trilha de auditoria e a tela, embaralhando o histórico real |
| **Semântica do "Último automático"** | o card da tela e o critério do ciclo deixam de refletir a realidade operacional |

---

## 3. O teste único já cobre 100% do mecanismo

Não existe comportamento novo que um segundo disparo revelaria — o caminho é **um só**:

- ✅ **leitura da config efetiva** — provado em produção real: restart das 12:29 leu `enabled=True, daily, 12:28` da linha persistida;
- ✅ **critério de devida + catch-up** — provado ao vivo: disparo às 12:26 (horário vencido sem sucesso no ciclo) e às 12:50 (ciclo reaberto artificialmente);
- ✅ **marca de ciclo / anti-duplicação** — provado: tick seguinte (30 s+) sem novo backup;
- ✅ **geração, integridade, auditoria e retenção** — evento `BACKUP_AUTOMATICO_SUCESSO` emitido e retenção executada após o ciclo.

A **não-duplicação é o segundo teste** — e ele só tem significado justamente porque o disparo não se repete.

---

## 4. Preciso validar a geração várias vezes? Existe caminho certo para isso

| Necessidade | Caminho correto |
|---|---|
| **Testar o dump/validação/download à vontade** | Botão **"Gerar backup agora"** (manual) — ilimitado, não passa pelo agendador, não contamina a semântica do ciclo |
| **Re-testar o disparo** do agendador | Reabrir o ciclo (artifício pontual: marcar o registro do ciclo como `FAILURE` direto no banco **com revert imediato**) — use com parcimônia; não é rotina operacional |
| **Prova final de produção** | Ciclo natural — deixar o sistema disparar no horário configurado no dia seguinte, sem nenhum artifício |

---

## 5. E se eu mudar o horário depois de salvo?

A mudança é aplicada **na hora, sem reinício** (o scheduler relê a configuração efetiva a cada tick de 30 s). Mas o **disparo** segue a mesma regra do ciclo:

| Situação ao corrigir | O que acontece |
|---|---|
| Errou **para mais tarde**, ciclo de hoje **já cumprido** | Hoje **não dispara de novo** (anti-duplicação); amanhã dispara 1× no horário corrigido |
| Corrigiu **antes do ciclo cumprir** e o horário novo **já passou** | Dispara em até 30 s (catch-up de execução devida) |
| **Dia da semana errado (semanal)** | Dia ainda vem nesta semana → dispara nele; dia já passou e a janela da semana não tem SUCCESS → catch-up em até 30 s |

O card **"Próxima execução"** na tela de Backups é o sinal visual de que a correção foi aplicada.

---

## Resumo

> O automático é um **disjuntor de ciclo**, não um botão de repetição — dispara quando o ciclo está pendente e silencia quando cumprido.

"Testar vários disparos" não é proibição arbitrária: é a própria funcionalidade funcionando. Cada tentativa extra seria ou **ignorada** (guardas) ou um **backup redundante com custo real** (se as guardas fossem retiradas).

*Prova de campo (21/09/2026, MariaDB real): reabertura do ciclo → 1 disparo às 12:50:39 + `BACKUP_AUTOMATICO_SUCESSO` + zero duplicação no tick seguinte. Registro do teste revertido ao status real.*
