"""Central de Integrações (feature 032) — camada de gerenciamento e observabilidade.

Consome um CATÁLOGO DECLARATIVO de integrações (plan D1) e deriva o estado de
cada uma a partir das fontes existentes — NUNCA executa a lógica de negócio
das integrações (spec §2/§8):

- E-mail  (030): notification_service + email_provider + email_config
- 1Doc    (031): onedoc_service + onedoc_client [PENDING C-1..C-4] + ONEDOC_*
- AD     (novo): ad_service + ad_settings
- GLPI         : integração PREVISTA — nada implementado (nada inventado)

Diretrizes:
- Painel/detalhe NÃO fazem I/O externo (NFR-004) — verificação externa só no
  POST de teste, delegada aos mecanismos vigentes de cada integração;
- `record_execution` é BEST-EFFORT: registrar histórico NUNCA afeta a
  integração (plan D6 — mesma disciplina dos hooks pós-commit);
- Nenhum segredo sai daqui sem máscara (FR-017/SC-003).
"""

import logging
import re
from datetime import timedelta
from typing import Callable, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app import config
from app.models.ad_settings import ADSettings
from app.models.backup_external_config import BackupExternalConfig
from app.models.backup_external_record import BackupExternalRecord
from app.models.backup_record import BackupRecord
from app.models.integration_execution import (
    OP_CONNECTION_TEST,
    OP_INTERNAL_CHECK,
    RESULT_FAILURE,
    RESULT_SUCCESS,
    IntegrationExecution,
)
from app.models.notification import EmailConfig, Notification
from app.models.onedoc_integration import OneDocIntegration
from app.utils.time_utils import now_utc, utc_to_recife

logger = logging.getLogger(__name__)

# ============================================================================
# VOCABULÁRIO PADRONIZADO DE STATUS (spec §7)
# ============================================================================

STATUS_NAO_CONFIGURADA = "NAO_CONFIGURADA"
STATUS_PENDENTE = "PENDENTE"
STATUS_DESABILITADA = "DESABILITADA"
STATUS_ATIVA = "ATIVA"
STATUS_COM_ERRO = "COM_ERRO"
STATUS_INDISPONIVEL = "INDISPONIVEL"
STATUS_INATIVA = "INATIVA"

STATUS_LABELS: Dict[str, str] = {
    STATUS_NAO_CONFIGURADA: "Não Configurada",
    STATUS_PENDENTE: "Pendente de Configuração",
    STATUS_DESABILITADA: "Desabilitada",
    STATUS_ATIVA: "Ativa",
    STATUS_COM_ERRO: "Com Erro",
    STATUS_INDISPONIVEL: "Indisponível",
    STATUS_INATIVA: "Inativa",
}

# Feature 047 — estado intermediário de saúde (amarelo): configurado com
# ressalva (ex.: espaço de armazenamento limitado, backup atrasado). Aditivo:
# nenhum status existente muda de significado (plan R1).
STATUS_ATENCAO = "ATENCAO"
STATUS_LABELS[STATUS_ATENCAO] = "Atenção"

# Janela de "falhas recentes" (decisão P-4): 24 horas, explícita na interface.
FAILURE_WINDOW_HOURS = 24


# ============================================================================
# HELPERS
# ============================================================================

def mask_secret(value: Optional[str]) -> str:
    """Indica presença de segredo SEM revelar o valor (FR-016/FR-017).

    - vazio/None → "" (não configurado);
    - configurado (>= 8 chars) → "************" + últimos 4 chars;
    - configurado curto (< 8 chars) → apenas asteriscos (nada revelável).
    """
    value = (value or "").strip()
    if not value:
        return ""
    if len(value) < 8:
        return "************"
    return "************" + value[-4:]


def _sanitize_detail(message: Optional[str]) -> Optional[str]:
    """Sanitiza o texto gravado em `detail` (defesa em profundidade — NFR-002).

    Remove ocorrências de credenciais do ambiente e padrões token=/Bearer
    (precedente onedoc_service._sanitize_error_message). Trunca a 2000 chars.
    """
    if not message:
        return None
    message = str(message)
    for secret in (
        config.SMTP_PASSWORD,
        config.SMTP_USERNAME,
        config.ONEDOC_API_TOKEN,
        config.AD_BIND_PASSWORD,
    ):
        if secret and secret in message:
            message = message.replace(secret, "***")
    message = re.sub(r"(?i)(token\s*[=:]\s*)\S+", r"\1***", message)
    message = re.sub(r"(?i)(bearer\s+)\S+", r"\1***", message)
    message = re.sub(r"(?i)(password|senha|passwd)\s*[=:]\s*\S+", r"\1=***", message)
    return message[:2000] or None


# ============================================================================
# DERIVAÇÃO DE STATUS POR INTEGRAÇÃO (spec §7 — precedência; plan D7)
# ============================================================================

def _email_status_fn(db: Session) -> dict:
    """E-mail (030): SMTP em ambiente + singleton email_config + notificações."""
    detail: Dict[str, object] = {}

    if not config.SMTP_HOST:
        return {"status": STATUS_NAO_CONFIGURADA, "detail": detail}

    eff = EmailConfig  # leitura pura (nunca cria singleton — padrão 030)
    row = db.query(eff).filter(eff.id == 1).first()
    enabled = bool(row and row.notifications_enabled)
    if not enabled:
        return {"status": STATUS_DESABILITADA, "detail": detail}

    # Estado de verificação/verificação externa recente: teste de conexão
    last_test = (
        db.query(IntegrationExecution)
        .filter(
            IntegrationExecution.integration_key == "email",
            IntegrationExecution.operation == OP_CONNECTION_TEST,
        )
        .order_by(IntegrationExecution.created_at.desc())
        .first()
    )
    if last_test is not None and last_test.result == RESULT_FAILURE:
        # INDISPONÍVEL somente para indisponibilidade explícita registrada
        if "indisponível" in (last_test.detail or "").lower() or "indisponivel" in (last_test.detail or "").lower():
            return {"status": STATUS_INDISPONIVEL, "detail": detail}
        return {"status": STATUS_COM_ERRO, "detail": detail}

    # Execuções recentes (envios)
    last_send = (
        db.query(IntegrationExecution)
        .filter(
            IntegrationExecution.integration_key == "email",
            IntegrationExecution.operation == "SEND_EMAIL",
        )
        .order_by(IntegrationExecution.created_at.desc())
        .first()
    )
    if last_send is not None and last_send.result == RESULT_FAILURE:
        return {"status": STATUS_COM_ERRO, "detail": detail}
    if last_send is not None:
        return {"status": STATUS_ATIVA, "detail": detail}

    # Habilitada, com SMTP, sem nenhuma execução registrada
    has_any_notification = db.query(Notification.id).first() is not None
    if not has_any_notification:
        return {"status": STATUS_INATIVA, "detail": detail}
    return {"status": STATUS_ATIVA, "detail": detail}


def _onedoc_status_fn(db: Session) -> dict:
    """1Doc (031): contrato aguardando fornecedor → PENDENTE com precedência.

    Enquanto [PENDING C-1..C-4] não for resolvido (ONEDOC_ENABLED=false e
    integração sem operação real), a Central representa o bloqueio externo —
    a integração nunca operou (spec FR-026 / Seção 18).
    """
    detail: Dict[str, object] = {
        "pendencia": "Aguardando confirmação do contrato da API pelo fornecedor 1Doc (C-1..C-4)."
    }
    if not config.ONEDOC_ENABLED:
        return {"status": STATUS_PENDENTE, "detail": detail}
    # Contrato confirmado no ambiente e habilitado: deriva pelas execuções
    last = (
        db.query(IntegrationExecution)
        .filter(IntegrationExecution.integration_key == "onedoc")
        .order_by(IntegrationExecution.created_at.desc())
        .first()
    )
    if last is None:
        return {"status": STATUS_INATIVA, "detail": detail}
    if last.result == RESULT_FAILURE:
        return {"status": STATUS_COM_ERRO, "detail": detail}
    return {"status": STATUS_ATIVA, "detail": detail}


def _ad_status_fn(db: Session) -> dict:
    """AD: singleton ad_settings + resultado do teste de conexão mais recente."""
    detail: Dict[str, object] = {}
    settings = db.query(ADSettings).filter(ADSettings.id == 1).first()
    enabled = bool(settings and settings.enabled) or bool(config.AD_SERVER and config.AD_BASE_DN)
    if not enabled:
        return {"status": STATUS_DESABILITADA, "detail": detail}
    if settings is not None and (not settings.server or not settings.base_dn) and not config.AD_SERVER:
        return {"status": STATUS_NAO_CONFIGURADA, "detail": detail}

    last_test = (
        db.query(IntegrationExecution)
        .filter(
            IntegrationExecution.integration_key == "ad",
            IntegrationExecution.operation == OP_CONNECTION_TEST,
        )
        .order_by(IntegrationExecution.created_at.desc())
        .first()
    )
    if last_test is not None and last_test.result == RESULT_FAILURE:
        if "indisponível" in (last_test.detail or "").lower() or "indisponivel" in (last_test.detail or "").lower():
            return {"status": STATUS_INDISPONIVEL, "detail": detail}
        return {"status": STATUS_COM_ERRO, "detail": detail}
    return {"status": STATUS_ATIVA, "detail": detail}


def _glpi_status_fn(db: Session) -> dict:
    """GLPI: integração prevista — NÃO CONFIGURADA fixa (spec FR-027/§18)."""
    return {"status": STATUS_NAO_CONFIGURADA, "detail": {"pendencia": "Integração prevista — aguarda investigação da instalação real (spec §18)."}}


# ============================================================================
# COMPONENTES DE SAÚDE DO SISTEMA (feature 047 — status_fn derivadas das
# fontes existentes; SEM I/O externo, SEM conexões novas, SEM threads —
# plan R5/R6; spec FR-007..FR-012)
# ============================================================================

def _safe(fn):
    """Isolamento por componente (R6/SC-007): exceção na coleta → COM_ERRO
    com mensagem sanitizada; o painel inteiro nunca quebra por um card."""
    def wrapper(db: Session) -> dict:
        try:
            return fn(db)
        except Exception as exc:  # noqa: BLE001 — isolamento deliberado
            logger.warning("Falha ao derivar status do componente: %s", exc)
            return {"status": STATUS_COM_ERRO,
                    "detail": {"summary": [("Erro", "Não foi possível verificar este componente")]}}
    return wrapper


def _app_status_fn(db: Session) -> dict:
    """Aplicação: o carregamento da página comprova a operação (FR-007).
    Reapresenta o conceito do /health existente sem reexecutar verificação."""
    summary = [("Estado", "Respondendo"),
               ("Verificação de infra", "/health (endpoint existente)")]
    return {"status": STATUS_ATIVA, "detail": {"summary": summary}}


@_safe
def _database_status_fn(db: Session) -> dict:
    """Banco: consulta simples na SESSÃO da request (mesma conexão/config do
    app — nenhuma conexão nova; FR-008). Apenas estado, sem latência (clarify
    2026-09-26). Mesmo padrão do /health existente (SELECT 1)."""
    from sqlalchemy import text
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        return {"status": STATUS_COM_ERRO,
                "detail": {"summary": [("Consulta", "Falhou")]}}
    return {"status": STATUS_ATIVA,
            "detail": {"summary": [("Consulta", "OK")]}}


@_safe
def _storage_status_fn(db: Session) -> dict:
    """Armazenamento (FR-009): existência dos diretórios relevantes + espaço
    livre pelo mecanismo padrão da plataforma; regra do clarify (2026-09-26):
    ATENÇÃO quando o espaço livre fica abaixo do tamanho do último backup
    válido; FALHA sem espaço para escrita/diretório ausente. Nenhum arquivo
    de teste é gravado ao abrir a página. Fontes: config.BACKUP_DIR e, quando
    habilitado, o destino externo da 045 (plan R7/P-2)."""
    import shutil
    from pathlib import Path

    from app.config import BACKUP_DIR

    dirs = []
    if BACKUP_DIR:
        dirs.append(("Backups locais", Path(BACKUP_DIR)))
    cfg = db.query(BackupExternalConfig).filter(BackupExternalConfig.id == 1).first()
    if cfg and cfg.enabled and cfg.dest_path:
        dirs.append(("Destino externo", Path(cfg.dest_path)))
    if not dirs:
        return {"status": STATUS_NAO_CONFIGURADA,
                "detail": {"summary": [("Diretórios", "Nenhum configurado")]}}

    # referência = tamanho do último backup válido não removido (plan R7)
    last_valid = (
        db.query(BackupRecord)
        .filter(BackupRecord.status == "SUCCESS", BackupRecord.removed_at.is_(None))
        .order_by(BackupRecord.timestamp.desc())
        .first()
    )
    ref_size = last_valid.size_bytes if last_valid and last_valid.size_bytes else None

    worst = STATUS_ATIVA
    free_total = None
    for label, path in dirs:
        if not path.exists():
            return {"status": STATUS_COM_ERRO,
                    "detail": {"summary": [(label, "Diretório ausente")]}}
        try:
            usage = shutil.disk_usage(path)
        except OSError:
            return {"status": STATUS_COM_ERRO,
                    "detail": {"summary": [(label, "Sem acesso ao diretório")]}}
        free_total = usage.free if free_total is None else min(free_total, usage.free)
        if ref_size and usage.free < ref_size:
            worst = STATUS_ATENCAO

    def _fmt_gb(v):
        return f"{v / (1024 ** 3):.1f} GB" if v else "—"

    summary = [("Livre", _fmt_gb(free_total)),
               ("Último backup", _fmt_gb(ref_size) if ref_size else "sem referência")]
    return {"status": worst, "detail": {"summary": summary}}


@_safe
def _backup_local_status_fn(db: Session) -> dict:
    """Backup Local (FR-010): deriva do resumo de monitoramento existente e
    do regime do agendador — regra do clarify (2026-09-26): agendador ATIVO →
    ATENÇÃO quando o ciclo esperado passa sem backup novo (folga de 1 ciclo)
    e FALHA sem nenhum backup válido; regime manual → sem alerta por
    atualidade (espelha a última falha registrada)."""
    from app.services.backup_scheduler import (
        retention_monitoring_summary,
        scheduler_status,
    )

    sched = scheduler_status()
    summary = retention_monitoring_summary(db)
    is_auto = bool(sched.get("enabled"))

    last_valid = summary.get("last_valid") or {}
    last_failure = summary.get("last_failure") or {}
    valid_count = summary.get("valid_count") or 0

    if is_auto:
        if valid_count == 0 and not last_valid:
            status = STATUS_COM_ERRO
        else:
            expected_hours = _expected_cycle_hours(sched)
            last_ts = last_valid.get("timestamp")
            age_h = ((now_utc() - last_ts).total_seconds() / 3600) if last_ts else None
            status = (STATUS_ATENCAO
                      if age_h is not None and age_h > expected_hours * 2
                      else STATUS_ATIVA)
    else:
        status = STATUS_COM_ERRO if last_failure else STATUS_ATIVA

    def _fmt(dt):
        return utc_to_recife(dt).strftime("%d/%m %H:%M") if dt else "—"

    detail_summary = [
        ("Último válido", f"{_fmt(last_valid.get('timestamp'))}" if last_valid else "—"),
        ("Válidos no disco", str(valid_count)),
        ("Última falha", f"{_fmt(last_failure.get('timestamp'))}" if last_failure else "—"),
    ]
    return {"status": status, "detail": {"summary": detail_summary}}


def _expected_cycle_hours(sched: dict) -> int:
    """Ciclo esperado do agendamento (24h diário; 168h semanal) — plan R7.
    Folga de 1 ciclo aplicada pelo chamador (2× o ciclo)."""
    return 168 if (sched.get("schedule") == "weekly") else 24


@_safe
def _backup_externo_status_fn(db: Session) -> dict:
    """Backup Externo (FR-011): config da 045 + registros de cópia já
    persistidos. Nenhuma cópia e nenhum teste ao abrir a página; teste ativo
    = ação explícita reutilizando test_destination (plan R4)."""
    cfg = db.query(BackupExternalConfig).filter(BackupExternalConfig.id == 1).first()
    if cfg is None:
        return {"status": STATUS_NAO_CONFIGURADA,
                "detail": {"summary": [("Configuração", "Não configurada")]}}
    if not cfg.enabled:
        return {"status": STATUS_DESABILITADA,
                "detail": {"summary": [("Cópia externa", "Desabilitada")]}}

    last = (
        db.query(BackupExternalRecord)
        .order_by(BackupExternalRecord.copied_at.desc())
        .first()
    )
    dest = (cfg.dest_path or "")
    if len(dest) > 40:
        dest = dest[:37] + "..."
    summary = [("Habilitado", "Sim"),
               ("Destino", dest or "—"),
               ("Última cópia", utc_to_recife(last.copied_at).strftime("%d/%m %H:%M") if last else "—")]
    if last is None:
        return {"status": STATUS_INATIVA, "detail": {"summary": summary}}
    if last.status == "FAILURE":
        return {"status": STATUS_COM_ERRO, "detail": {"summary": summary}}
    return {"status": STATUS_ATIVA, "detail": {"summary": summary}}


@_safe
def _scheduler_status_fn(db: Session) -> dict:
    """Agendador (FR-012): leitura direta de scheduler_status() existente —
    nenhum thread novo; desabilitado ≠ falha (edge case da spec)."""
    from app.services.backup_scheduler import scheduler_status

    st = scheduler_status()
    if not st.get("enabled"):
        return {"status": STATUS_DESABILITADA,
                "detail": {"summary": [("Backup automático", "Desabilitado")]}}
    last = st.get("last_result") or {}
    summary = [
        ("Agendamento", f"{st.get('schedule') or '—'} {st.get('time_local') or ''}".strip()),
        ("Próximo backup", str(st.get("next_run_local") or "—")),
        ("Último resultado", str(last.get("result") or "—")),
    ]
    if str(last.get("result", "")).upper() == "FAILURE":
        return {"status": STATUS_COM_ERRO, "detail": {"summary": summary}}
    return {"status": STATUS_ATIVA, "detail": {"summary": summary}}


# ============================================================================
# CATÁLOGO DECLARATIVO (plan D1 — extensibilidade SC-007: nova integração =
# nova entrada aqui, sem alteração estrutural da Central)
# ============================================================================

INTEGRATIONS: List[dict] = [
    # === Componentes de saúde do sistema (feature 047 — P-1/P-3: ordem do
    # mock do pedido; R2: label_by_status; R7: capacidades) ===
    {
        "key": "app",
        "name": "Aplicação",
        "description": "Aplicação SisPatrimônio Pro operacional.",
        "purpose": "Comprovar que o sistema responde.",
        "supports_test": False,
        "supports_reprocess": False,
        "supports_enable_disable": False,
        "config_route": None,
        "config_permission": None,
        "label_by_status": {STATUS_ATIVA: "Operacional"},
        "status_fn": _app_status_fn,
    },
    {
        "key": "database",
        "name": "Banco de Dados",
        "description": "Banco de dados de produção acessível pela conexão do próprio sistema.",
        "purpose": "Comprovar a conectividade com o banco sem criar conexão nova.",
        "supports_test": False,
        "supports_reprocess": False,
        "supports_enable_disable": False,
        "config_route": None,
        "config_permission": None,
        "label_by_status": {STATUS_ATIVA: "Conectado", STATUS_COM_ERRO: "Falha"},
        "status_fn": _database_status_fn,
    },
    {
        "key": "storage",
        "name": "Armazenamento",
        "description": "Espaço e disponibilidade dos diretórios de backup.",
        "purpose": "Identificar falta de espaço antes que comprometa os backups.",
        "supports_test": False,
        "supports_reprocess": False,
        "supports_enable_disable": False,
        "config_route": "/admin/backups",
        "config_permission": None,
        "label_by_status": {STATUS_ATIVA: "OK", STATUS_ATENCAO: "Espaço limitado",
                            STATUS_COM_ERRO: "Falha"},
        "status_fn": _storage_status_fn,
    },
    {
        "key": "ad",
        "name": "Active Directory",
        "description": "Autenticação híbrida local + AD/LDAP (tela Integração AD).",
        "purpose": "Autenticar identidades do domínio; autorização permanece no RBAC interno.",
        "supports_test": True,
        "supports_reprocess": False,
        "supports_enable_disable": True,
        "config_route": "/admin/ad",
        "config_permission": None,  # guarda própria: usuarios.editar + perfis.editar
        "status_fn": _ad_status_fn,
    },
    {
        "key": "email",
        "name": "E-mail",
        "description": "Notificação por e-mail de movimentações patrimoniais (feature 030).",
        "purpose": "Avisar o setor de Patrimônio sobre movimentações concluídas.",
        "supports_test": True,
        "supports_reprocess": False,
        "supports_enable_disable": True,
        "config_route": "/admin/notificacoes",
        "config_permission": "notificacoes.gerenciar",
        "status_fn": _email_status_fn,
    },
    {
        "key": "glpi",
        "name": "GLPI",
        "description": "Integração prevista com o GLPI (sincronização futura de equipamentos).",
        "purpose": "Preparada para sincronização com equipamentos já vinculados (sem criação automática).",
        "supports_test": False,
        "supports_reprocess": False,
        "supports_enable_disable": False,
        "config_route": None,
        "config_permission": None,
        "status_fn": _glpi_status_fn,
    },
    {
        "key": "backup_local",
        "name": "Backup Local",
        "description": "Backups no diretório local, com retenção e histórico (features 015/016/020).",
        "purpose": "Comprovar que há backups válidos recentes no regime vigente.",
        "supports_test": False,
        "supports_reprocess": False,
        "supports_enable_disable": False,
        "config_route": "/admin/backups",
        "config_permission": None,
        "label_by_status": {STATUS_ATIVA: "OK", STATUS_ATENCAO: "Sem backup recente",
                            STATUS_COM_ERRO: "Falha"},
        "status_fn": _backup_local_status_fn,
    },
    {
        "key": "backup_externo",
        "name": "Backup Externo",
        "description": "Cópia dos backups válidos para o destino externo (feature 045).",
        "purpose": "Comprovar a cópia externa sem gerar backup nem testar destino ao abrir a página.",
        "supports_test": True,
        "test_label": "Testar destino",
        "supports_reprocess": False,
        "supports_enable_disable": True,
        "config_route": "/admin/backups",
        "config_permission": None,
        "label_by_status": {STATUS_ATIVA: "OK", STATUS_COM_ERRO: "Falha"},
        "status_fn": _backup_externo_status_fn,
    },
    {
        "key": "scheduler",
        "name": "Agendador de Backup",
        "description": "Agendador do backup automático existente (feature 021/026).",
        "purpose": "Comprovar que o backup automático está ativo e agendado.",
        "supports_test": False,
        "supports_reprocess": False,
        "supports_enable_disable": False,
        "config_route": "/admin/backups",
        "config_permission": None,
        "label_by_status": {STATUS_ATIVA: "Ativo", STATUS_DESABILITADA: "Desabilitado",
                            STATUS_COM_ERRO: "Falha"},
        "status_fn": _scheduler_status_fn,
    },
    {
        "key": "onedoc",
        "name": "1Doc",
        "description": "Comunicação automática de movimentações no processo 1Doc (feature 031).",
        "purpose": "Registrar a movimentação no processo administrativo 1Doc já existente.",
        "supports_test": True,
        "supports_reprocess": True,
        "supports_enable_disable": False,
        "config_route": "/admin/integracao-1doc",
        "config_permission": "integracao1doc.reprocessar",
        "status_fn": _onedoc_status_fn,
    },
]


def get_integration(key: str) -> Optional[dict]:
    """Retorna a entrada do catálogo pela key, ou None."""
    for item in INTEGRATIONS:
        if item["key"] == key:
            return item
    return None


# ============================================================================
# AGREGAÇÕES DE EXECUÇÕES
# ============================================================================

def _window_start(hours: int = FAILURE_WINDOW_HOURS):
    return now_utc() - timedelta(hours=hours)


def _execution_counters(db: Session, key: str) -> dict:
    """Contadores por integração a partir do histórico unificado.

    - falhas_24h: janela fixa de 24h explícita no card (P-4);
    - pendentes: PENDING nas tabelas de integração (fonte de verdade do estado).
    """
    window = _window_start()
    total = (
        db.query(func.count(IntegrationExecution.id))
        .filter(IntegrationExecution.integration_key == key)
        .scalar()
        or 0
    )
    failures = (
        db.query(func.count(IntegrationExecution.id))
        .filter(
            IntegrationExecution.integration_key == key,
            IntegrationExecution.result == RESULT_FAILURE,
        )
        .scalar()
        or 0
    )
    failures_24h = (
        db.query(func.count(IntegrationExecution.id))
        .filter(
            IntegrationExecution.integration_key == key,
            IntegrationExecution.result == RESULT_FAILURE,
            IntegrationExecution.created_at >= window,
        )
        .scalar()
        or 0
    )
    last_execution = (
        db.query(IntegrationExecution)
        .filter(IntegrationExecution.integration_key == key)
        .order_by(IntegrationExecution.created_at.desc())
        .first()
    )
    last_success = (
        db.query(IntegrationExecution)
        .filter(
            IntegrationExecution.integration_key == key,
            IntegrationExecution.result == RESULT_SUCCESS,
        )
        .order_by(IntegrationExecution.created_at.desc())
        .first()
    )
    return {
        "total": total,
        "failures": failures,
        "failures_24h": failures_24h,
        "last_execution": last_execution,
        "last_success": last_success,
    }


def _pending_count(db: Session, key: str) -> int:
    """Operações pendentes (fonte de verdade = tabelas de integração)."""
    if key == "email":
        return (
            db.query(func.count(Notification.id))
            .filter(Notification.status == "PENDING")
            .scalar()
            or 0
        )
    if key == "onedoc":
        return (
            db.query(func.count(OneDocIntegration.id))
            .filter(OneDocIntegration.status == "PENDING")
            .scalar()
            or 0
        )
    return 0


# ============================================================================
# PAINEL / DETALHE / HISTÓRICO / PROPAGAÇÃO
# ============================================================================

def get_panel(db: Session) -> List[dict]:
    """Cards do painel — derivação SEM I/O externo (NFR-004)."""
    cards: List[dict] = []
    for item in INTEGRATIONS:
        try:
            derived = item["status_fn"](db)
        except Exception:  # noqa: BLE001 — cinto e suspensório (plan R6/SC-007):
            # mesmo com status_fn protegidas, uma exceção aqui NUNCA derruba
            # o painel inteiro; o card afetado entra em erro isolado.
            logger.exception("Falha ao derivar status de %s.", item["key"])
            derived = {"status": STATUS_COM_ERRO,
                       "detail": {"summary": [("Erro", "Não foi possível verificar este componente")]}}
        counters = _execution_counters(db, item["key"])
        cards.append(
            {
                "key": item["key"],
                "name": item["name"],
                "description": item["description"],
                "status": derived["status"],
                # Feature 047 (R2): rótulo específico por componente com
                # fallback no vocabulário global.
                "status_label": (item.get("label_by_status") or {}).get(
                    derived["status"], STATUS_LABELS.get(derived["status"], derived["status"])
                ),
                "status_detail": derived.get("detail") or {},
                # Feature 047 (R4/E2): rótulo do botão de teste (backup_externo
                # exibe "Testar destino"); fallback = "Testar conexão".
                "test_label": item.get("test_label") or "Testar conexão",
                "last_execution_at": counters["last_execution"].created_at if counters["last_execution"] else None,
                "last_success_at": counters["last_success"].created_at if counters["last_success"] else None,
                "failures_24h": counters["failures_24h"],
                "pending": _pending_count(db, item["key"]),
                "supports_test": item["supports_test"],
                "supports_reprocess": item["supports_reprocess"],
                "supports_enable_disable": item["supports_enable_disable"],
                "config_route": item["config_route"],
            }
        )
    return cards


def get_detail(db: Session, key: str) -> Optional[dict]:
    """Diagnóstico da integração (FR-008/FR-009) — sem I/O externo."""
    item = get_integration(key)
    if item is None:
        return None
    derived = item["status_fn"](db)
    counters = _execution_counters(db, key)
    detail = {
        "key": key,
        "name": item["name"],
        "description": item["description"],
        "purpose": item["purpose"],
        "status": derived["status"],
        "status_label": (item.get("label_by_status") or {}).get(
            derived["status"], STATUS_LABELS.get(derived["status"], derived["status"])
        ),
        "status_detail": derived.get("detail") or {},
        "test_label": item.get("test_label") or "Testar conexão",
        "total": counters["total"],
        "failures": counters["failures"],
        "failures_24h": counters["failures_24h"],
        "pending": _pending_count(db, key),
        "last_execution": counters["last_execution"],
        "last_success": counters["last_success"],
        "supports_test": item["supports_test"],
        "supports_reprocess": item["supports_reprocess"],
        "supports_enable_disable": item["supports_enable_disable"],
        "config_route": item["config_route"],
        "config_permission": item["config_permission"],
        "config_summary": _config_summary(key),
    }
    return detail


def _config_summary(key: str) -> dict:
    """Configuração relevante com segredos MASCARADOS (FR-016/FR-017)."""
    if key == "email":
        return {
            "host": config.SMTP_HOST or "—",
            "port": config.SMTP_PORT,
            "use_tls": config.SMTP_USE_TLS,
            "from": config.SMTP_FROM or config.SMTP_USERNAME or "—",
            "password_configured": mask_secret(config.SMTP_PASSWORD),
        }
    if key == "onedoc":
        return {
            "enabled": config.ONEDOC_ENABLED,
            "url": config.ONEDOC_API_URL or "—",
            "token_configured": mask_secret(config.ONEDOC_API_TOKEN),
            "connect_timeout": config.ONEDOC_CONNECT_TIMEOUT,
            "read_timeout": config.ONEDOC_READ_TIMEOUT,
        }
    if key == "ad":
        return {
            "server": config.AD_SERVER or "—",
            "port": config.AD_PORT,
            "use_ssl": config.AD_USE_SSL,
            "base_dn": config.AD_BASE_DN or "—",
        }
    return {}


def get_history(
    db: Session,
    key: str,
    *,
    status: Optional[str] = None,
    operation: Optional[str] = None,
    days: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
    user: Optional[str] = None,
) -> dict:
    """Histórico paginado com filtros (FR-019): período, status, operação,
    usuário (opcional — execuções automáticas aparecem quando não filtrado)."""
    query = db.query(IntegrationExecution).filter(IntegrationExecution.integration_key == key)
    if status:
        query = query.filter(IntegrationExecution.result == status)
    if operation:
        query = query.filter(IntegrationExecution.operation == operation)
    if days:
        query = query.filter(
            IntegrationExecution.created_at >= now_utc() - timedelta(days=days)
        )
    if user:
        query = query.filter(IntegrationExecution.username == user)
    total = query.count()
    page_size = max(1, min(page_size, 100))
    page = max(1, page)
    rows = (
        query.order_by(IntegrationExecution.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "rows": rows,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if page_size else 1,
    }


def get_movement_propagation(db: Session, movement_id: int) -> dict:
    """Propagação por movimentação (FR-023) — SOMENTE LEITURA, sem lógica
    patrimonial: lê os registros de integração já existentes."""
    notification = db.query(Notification).filter(Notification.movement_id == movement_id).first()
    onedoc = db.query(OneDocIntegration).filter(OneDocIntegration.movement_id == movement_id).first()
    return {
        "movement_id": movement_id,
        "email": {
            "status": notification.status if notification else None,
            "attempt_count": notification.attempt_count if notification else 0,
            "sent_at": notification.sent_at if notification else None,
            "error": notification.error_message if notification else None,
        },
        "onedoc": {
            "status": onedoc.status if onedoc else None,
            "process_number": onedoc.process_number if onedoc else None,
            "attempt_count": onedoc.attempt_count if onedoc else 0,
            "error": onedoc.last_error if onedoc else None,
        },
        "glpi": None,  # integração prevista — sempre "não aplicável" nesta versão
    }


# ============================================================================
# TESTE DE CONEXÃO (delegação — plan D8) e GRAVAÇÃO (plan D6)
# ============================================================================

def run_test(db: Session, key: str, *, user=None, ip_address: Optional[str] = None) -> tuple:
    """Executa o teste da integração de forma SEGURA e NÃO DESTRUTIVA (FR-011).

    - email  → email_provider.check_connection (conexão+auth, SEM envio — P-6);
    - onedoc → verificação INTERNA de configuração (nenhuma chamada externa
      enquanto o contrato [PENDING C-1..C-4] não é confirmado);
    - ad/glp → não suportado pela Central (AD mantém teste próprio com guarda
      vigente; GLPI não configurada) — o chamador (rota) conduz.
    Grava execution + auditoria; nunca levanta ao chamador além do esperado.
    """
    import time

    from app.services.audit_service import (
        ACTION_CENTRAL_TESTE_FALHA,
        ACTION_CENTRAL_TESTE_SUCESSO,
        RESULT_FAILURE,
        RESULT_SUCCESS,
        write_audit,
    )

    item = get_integration(key)
    if item is None or not item["supports_test"]:
        return False, "Teste não suportado para esta integração."

    start = time.monotonic()
    if key == "email":
        from app.services.email_provider import check_connection

        ok, message, latency_ms = check_connection()
    elif key == "onedoc":
        ok, message = _onedoc_internal_check()
        latency_ms = int((time.monotonic() - start) * 1000)
    elif key == "backup_externo":
        # Feature 047 (plan R4/E2): reuso INTEGRAL da função existente da 045
        # (arquivo temporário → grava → lê → valida → remove). Nenhum backup
        # é gerado e nenhum arquivo de teste fica no destino.
        from app.services.external_backup_service import test_destination

        cfg = db.query(BackupExternalConfig).filter(BackupExternalConfig.id == 1).first()
        if cfg is None or not (cfg.dest_path or "").strip():
            ok, message = False, "Destino externo não configurado."
        else:
            ok, message = test_destination(cfg.dest_path)
        latency_ms = int((time.monotonic() - start) * 1000)
    else:
        return False, "Teste não suportado para esta integração."

    duration_ms = latency_ms if key == "email" else int((time.monotonic() - start) * 1000)
    result = RESULT_SUCCESS if ok else RESULT_FAILURE

    record_execution(
        db,
        key,
        OP_CONNECTION_TEST if key == "email" else OP_INTERNAL_CHECK,
        result,
        duration_ms=duration_ms,
        user=user,
        detail=None if ok else message,
    )
    try:
        write_audit(
            db,
            user=user,
            action=ACTION_CENTRAL_TESTE_SUCESSO if ok else ACTION_CENTRAL_TESTE_FALHA,
            module="central_integracoes",
            resource="integration",
            resource_ref=key,
            ip_address=ip_address,
            result=result,
            description=message,
        )
    except Exception:  # best-effort — auditoria nunca bloqueia a resposta
        logger.exception("Falha ao auditar teste de integração (%s).", key)

    return ok, message


def _onedoc_internal_check() -> tuple:
    """Verificação interna do 1Doc — NENHUMA chamada externa (plan D8/P-3).

    Enquanto o contrato [PENDING C-1..C-4] não é confirmado pelo fornecedor,
    o teste valida apenas a configuração local (URL/token presentes).
    """
    if not config.ONEDOC_API_URL and not config.ONEDOC_API_TOKEN:
        return False, "Integração 1Doc não configurada (ONEDOC_API_URL/ONEDOC_API_TOKEN ausentes no ambiente)."
    if not config.ONEDOC_API_URL:
        return False, "Integração 1Doc parcialmente configurada (ONEDOC_API_URL ausente)."
    if not config.ONEDOC_API_TOKEN:
        return False, "Integração 1Doc parcialmente configurada (ONEDOC_API_TOKEN ausente)."
    return True, (
        "Configuração interna verificada. Envio real bloqueado até a confirmação "
        "do contrato da API pelo fornecedor 1Doc."
    )


def record_execution(
    db: Session,
    key: str,
    operation: str,
    result: str,
    *,
    duration_ms: Optional[int] = None,
    user=None,
    movement_id: Optional[int] = None,
    detail: Optional[str] = None,
) -> None:
    """Grava uma execução no histórico unificado — BEST-EFFORT (plan D6).

    NUNCA levanta: falha de observabilidade não pode afetar a integração
    (mesmo espírito dos hooks pós-commit 030/031). Credenciais sanitizadas.
    """
    try:
        row = IntegrationExecution(
            integration_key=key,
            operation=operation,
            result=result,
            duration_ms=duration_ms,
            user_id=getattr(user, "id", None),
            username=getattr(user, "username", None),
            movement_id=movement_id,
            detail=_sanitize_detail(detail),
        )
        db.add(row)
        db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        logger.exception(
            "Falha ao registrar execução de integração (%s/%s) — integração preservada.",
            key,
            operation,
        )
