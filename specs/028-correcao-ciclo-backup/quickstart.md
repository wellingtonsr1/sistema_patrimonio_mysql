# Quickstart: Validação da Correção do Ciclo de Backup (028)

Protocolo de validação de ponta a ponta. Executar após o `/speckit-implement`.

## 1. Pré-requisitos

- Ambiente do projeto ativo (Python 3.10+; dependências instaladas).
- Baseline pré-028 medida em 2026-09-18: **543 passed / 1 failed** (`test_anti_regressao_default_desativado_no_codigo_real` — falha pré-existente, defasada; não é desta feature).
- MariaDB acessível via `DATABASE_URL` para a validação manual (a suíte usa SQLite em memória).
- Usuário com permissões `backup.gerenciar` e `backup.restaurar`.

## 2. Suíte automatizada (obrigatória)

```bash
python -m pytest tests/ -q
```

Esperado: **543 + novos verdes / 1 failed** (a mesma falha pré-existente; nenhuma nova falha).

Módulos em destaque:

```bash
python -m pytest tests/test_backup_restore.py -q      # US1 + US3
python -m pytest tests/test_backup_automatico.py -q    # US2
```

## 3. Cenários automatizados cobertos (referência rápida)

| Story | Cenário-chave (definição de sucesso) |
|---|---|
| US1 | Restore concluído → arquivos presentes no disco mantêm tipo (MANUAL/AUTOMATICO/PRE_RESTAURACAO); pré-restauração do próprio ciclo permanece PRE_RESTAURACAO; sem fallback para MANUAL |
| US2 | Horário devido → 1 AUTOMATICO/SUCCESS no ciclo; tick seguinte → 0 duplicados; semanal → só no dia configurado; catch-up ≤ 1 execução; desabilitado → nada dispara; restore em andamento → adiado |
| US3 | Restore em andamento → GET `/admin/backups` responde (não-503) para usuário autorizado; POSTs continuam 503; após término → tela normal |

## 4. Validação manual no Windows (MariaDB real — obrigatória antes do fechamento)

1. **Reinicie o servidor** (obrigatório: o scheduler correto só vale após restart).
2. **US2 — disparo por horário**: deixe o backup automático habilitado com horário a poucos minutos à frente; confirme na tela de Backups: 1 novo backup AUTOMÁTICO, "Próxima execução" passando a apontar para o próximo ciclo, e **nenhum segundo backup** 30–90 s depois.
3. **US1 — tipos após restore**: gere um backup MANUAL; restaure um backup válido pelo botão **Restaurar** (confirme o modal); após a conclusão, confira a coluna Tipo: MANUAL continua MANUAL e o backup de segurança aparece como PRÉ-RESTAURAÇÃO (nenhum "—" novo para arquivos presentes).
4. **US3 — acompanhamento**: durante uma restauração (ciclo ~30–60 s), permaneça na tela de Backups: ela deve exibir o banner de fase (polling) em vez de 503; tente **Gerar backup** durante o ciclo → deve permanecer bloqueado; após o término, a tela volta ao normal e o modo de manutenção é encerrado sozinho.
5. **503 legítimo**: durante um ciclo, acesse outra página administrativa (ex.: `/admin/usuarios`) → deve continuar recebendo a página de manutenção.

## 5. Validação no Linux (produção)

Mesmos passos 2–5. Pré-requisitos de ambiente já validados pela 018/019: `mysqldump`/`mysql` no PATH (ou `MYSQLDUMP_PATH`), fuso do servidor coerente com America/Recife para o carimbo de manutenção.

## 6. Registros

Preencher o **Validation Results** em `tasks.md` (checks permanecem em branco até a execução real).
