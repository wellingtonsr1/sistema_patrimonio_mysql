# Validação: Central de Integrações — Saúde do Sistema e das Integrações (047)

**Data**: 2026-09-26 · **Branch**: `047-saude-central-integracoes`

## 1. Suíte de testes

| Momento | Comando | Resultado |
|---|---|---|
| Baseline (T001) | `.venv/bin/python -m pytest tests/ -q` | **748 passed** |
| Novos testes primeiro (T004/TDD) | `.venv/bin/python -m pytest tests/test_central_saude.py -q` | FALHAVAM (status_fn inexistentes) — confirmado antes da implementação |
| Pós-implementação (T008/T011) | `pytest tests/test_central_saude.py tests/test_central_integracoes.py -q` | **70 passed** (27 novos + 43 da 032) |
| Completo pós-alteração (T016) | `.venv/bin/python -m pytest tests/ -q` | **775 passed** |

## 2. Cenários do quickstart (A–M)

- **A — Central acessível**: `test_painel_renderiza_10_cards_na_ordem` (ordem exata do catálogo) + `test_catalogo_tem_10_chaves_e_labels` ✓. Sem subpágina "Visão geral" ✓.
- **B — Banco**: `test_database_status_conectado` (ATIVA/"Conectado", consulta "OK") + `test_database_status_falha` (COM_ERRO sem quebrar) ✓. Sem conexão nova (sessão da request) ✓. Sem latência (clarify) ✓.
- **C/D — GLPI/1Doc honestos**: `test_glpi_nao_configurada_e_onedoc_pendente` ✓ — GLPI "Não Configurada" sem botão de teste; 1Doc PENDENTE/INATIVA.
- **E/F — Backup externo**: `test_backup_externo_ok_com_copia_sucesso` (ATIVA/"OK") · `test_backup_externo_com_erro_por_ultima_copia_falha` (COM_ERRO) · `test_backup_externo_desabilitado_e_nao_configurado` (DESABILITADA/NAO_CONFIGURADA) ✓. Nenhuma cópia nem teste ao abrir a página ✓.
- **G/H — AD/E-mail**: comportamento da 032 preservado (`test_central_integracoes.py` 43 passed); AD mantém teste na tela própria com guarda vigente ✓.
- **I — Agendador**: `test_scheduler_ativo_e_desabilitado` + `test_scheduler_com_ultimo_resultado_erro` (ATIVO/DESABILITADO distinto de falha/COM_ERRO com último resultado de erro) ✓. Nenhum thread novo ✓.
- **Backup Local (clarify)**: OK com válido recente · ATENÇÃO com ciclo perdido (48h > 2× ciclo diário) · COM_ERRO sem válido com agendador ativo · regime manual sem alerta por atualidade (90 dias sem alerta; espelha última falha) ✓.
- **Armazenamento (clarify)**: OK com espaço livre ≥ referência · ATENÇÃO quando livre < `size_bytes` do último backup válido · COM_ERRO com diretório ausente · OK sem backup de referência (nota no card) ✓. Nenhum arquivo de teste gravado ao abrir a página ✓.
- **J/K — Responsividade/temas**: grid `col-12 col-md-6 col-xl-4` (3/2/1 colunas — Bootstrap vigente); badge ATENÇÃO `bg-warning text-dark` (amarelo existente, mesmo do INDISPONÍVEL); nenhum CSS novo ✓.
- **L — RBAC**: `test_painel_403_sem_permissao` (403 no painel e no detalhe sem `integracoes.visualizar`) + `test_painel_200_com_visualizar` (com a permissão, 200 em ambos) ✓. Nenhuma permissão nova criada ✓.
- **M — Regressão**: **775 passed** (748 + 27) ✓.

## 3. Comprovação consulta ≠ teste (SC-002)

`test_get_panel_nao_executa_testes_caros`: durante o `GET /admin/integracoes`, chamadas a `BackupService.generate_backup`, `test_destination`, `email_provider.check_connection` e `ad_ldap.test_connection` = **0** (monkeypatch com guarda que falharia em qualquer chamada) ✓.

## 4. Isolamento por componente (SC-007)

`test_isolamento_um_card_nao_derruba_o_painel`: status_fn do Armazenamento forçada a levantar exceção → painel responde 200, demais cards renderizam e o card afetado exibe "Erro: Não foi possível verificar este componente" (dupla proteção: wrapper `_safe` + try/except no `get_panel` — plan R6) ✓.

## 5. Segurança (SC-003/SC-004)

- `test_painel_nao_exibe_segredos`: com `SMTP_PASSWORD`/`ONEDOC_API_TOKEN`/`AD_BIND_PASSWORD` injetados via monkeypatch, nenhum valor aparece no HTML ✓.
- `test_get_nao_gera_eventos_de_auditoria`: GETs repetidos criam 0 registros em `IntegrationExecution` e 0 em `audit_logs` (só testes manuais registram — US3.4) ✓.
- Mensagens de erro passam por `_sanitize_detail` (mecanismo da 032) ✓.

## 6. Teste do destino externo pela Central (US2)

- `test_run_test_backup_externo_sucesso`: destino válido (tmp_path) → sucesso, **nenhum arquivo deixado no destino** ✓.
- `test_run_test_backup_externo_destino_invalido`: destino inexistente → falha com mensagem amigável, aplicação de pé ✓.
- `test_run_test_componentes_sem_mecanismo`: app/database/storage/backup_local/scheduler → "Teste não suportado" (sem botão no painel) ✓.
- Mecanismo reutilizado: `external_backup_service.test_destination` (045) — zero linhas alteradas nele ✓.
- Páginas de detalhe das 10 keys → 200 (verificação manual T011) ✓.

## 7. Escopo do diff (T016 — coerência com o plan)

Alterados: `app/services/integration_center_service.py` (catálogo + 6 status_fn + dispatcher + STATUS_ATENCAO), `app/web/templates/admin/integracoes/list.html` (grid/badge/summary/rótulo de teste), `app/services/help_article_032.py` (ajuda), `tests/test_central_saude.py` (novo), specs/047 (documentação).

**Zero linhas alteradas** (R5): `app/main.py` (`/health`), `backup_service.py`, `backup_scheduler.py`, `external_backup_service.py`, `ad_service.py`/`ad_ldap.py`, `email_provider.py`/`notification_service.py`, `onedoc_*`, `permission_service.py`, `admin_routes.py`. Zero tabelas/colunas novas (SC-009).

## 8. Limitações

- GLPI permanece "Não Configurada" até a implementação da integração (spec própria) — os cenários C/D com cliente real ficam para essa futura feature.
- 1Doc permanece "Pendente de Configuração" aguardando o fornecedor (bloqueio da 031).
- A validação de responsividade foi feita por inspeção das classes Bootstrap (comportamento padrão do framework já validado nas features 036–046) e não por screenshots.
