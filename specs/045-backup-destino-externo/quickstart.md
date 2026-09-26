# Quickstart: Destino Externo para Backups (045)

Guia de validação ponta a ponta. Referências: [contract](contracts/contrato-backup-externo.md) · [data-model](data-model.md) · [spec](spec.md)

## Pré-requisitos

- Ambiente de dev (`python run.py`); usuário **admin** com `backup.gerenciar` (RBAC existente).
- **Destino externo de teste**: um diretório local (`tmp_path` no pytest; ex.: `/tmp/destino-externo-teste`) — comportamento de pasta idêntico ao NAS montado (C-4/Assumptions). NAS real só no aceite de produção.
- Suíte: `python -m pytest tests/ -q` verde antes e depois (regressão §37).

## Como exercitar

- **Testes automatizados**: `python -m pytest tests/test_backup_externo.py -v` — cenários A–L (quickstart automatizado; C-17).
- **Manual (dev)**: Administração → Backups → Configurações de Backup: fieldset "Backup externo" → marcar Ativado, informar destino, "Testar destino", salvar; card "Gerar backup" → flash local+externo; histórico com coluna "Externo"; card "Destino externo".

## Cenários do pedido (§36) — mapeamento teste ↔ cenário

| Cenário | Verificação essencial | Onde |
|---|---|---|
| A — manual sem externo | comportamento atual preservado; zero I/O no destino | `test_externo_desabilitado_manual_somente_local` |
| B — automático sem externo | idem no ciclo automático | `test_externo_desabilitado_automatico_somente_local` |
| C — manual com externo | local OK → externo OK; mesmo nome; sha256 igual; registro+auditoria | `test_manual_com_externo_copia_validada` |
| D — automático com externo | idem no ciclo automático (dump único) | `test_automatico_com_externo_copia_validada` |
| E — externo indisponível | local preservado; app íntegra; falha registrada + auditada | `test_destino_indisponivel_local_preservado` |
| F — sem permissão de escrita | local OK; externo FALHA (motivo) | `test_destino_sem_permissao` |
| G — integridade | hash divergente → cópia inválida + falha | `test_hash_divergente_copia_invalida` |
| H — duplicidade | repetição não cria cópias/registros duplicados | `test_sem_duplicidade_de_registro_e_copia` |
| I — restauração | pré-restauração e restore intocados; externo não quebra fluxo | `test_restore_e_pre_restauracao_intactos` |
| J — retenção | retenção existente sem exclusões indevidas; destino nunca varrido | `test_retencao_nao_toca_destino` |
| K — reinicialização | config persiste; scheduler/destino íntegros | `test_config_persiste_apos_reinicializacao` |
| L — desativado novamente | manual/auto voltam a somente local | `test_desativado_volta_somente_local` |

Extras: RBAC (403 sem `backup.gerenciar` em configurar/testar), "Testar destino" (§24 — cria/lê/remove temporário, sem backup) e `test_zero_segredos_em_logs` (evidência automatizada do SC-007: `caplog` nos cenários E/F/G sem padrões de senha/token/segredo).

## Registro

- Resultado de cada cenário + suíte completa em `specs/045-backup-destino-externo/validacao.md` (SC-009), incluindo o **relatório final obrigatório** (§43 do pedido): arquivos alterados/novos, configuração, fluxos manual/automático, integridade, falhas, auditoria, testes e limitações reais (NAS não existe em dev — teste com diretório local; segredos estruturalmente ausentes).
