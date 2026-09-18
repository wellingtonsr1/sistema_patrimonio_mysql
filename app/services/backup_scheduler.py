"""Agendador de backup automático e política de retenção — feature 020.

Arquitetura (research R1/R4/R5/R6):
- THREAD agendadora daemon interna ao processo (uvicorn único — R1); loop de
  verificação a cada 30 s via `stop_event.wait(30)`; dependências injetáveis
  para testes (`clock`).
- Disparo executa em WORKER THREAD com SESSÕES PRÓPRIAS E CURTAS (R4 — lição
  da 019): nunca retém conexão além do ponto de uso.
- Guardas em camadas (contract §4): (1) `_AUTO_RUNNING` — sobreposição de
  automáticos é DESCARTADA com log; (2) `restore_in_progress()` — disparo
  durante restore é ADIADO para o próximo ciclo; (3) guarda existente do
  `generate_backup` (defesa em profundidade).
- Catch-up determinístico (R5): UMA execução de recuperação por start quando
  o ciclo corrente não tem sucesso; janela precisa em research R5 (daily =
  dia calendário Recife; weekly = semana iniciando 00:00 local no weekday).
- Retenção GFS (R6, contract §5): somente AUTOMATICO elegível; âncoras
  semanal ISO/mensal determinísticas; guarda do último backup válido;
  motivos de preservação em `preservados` do evento resumo (F4); resultado
  COMPLETA/PARCIAL/FALHA (PARCIAL nunca é "concluída" — §32).

Fuso (R11): `BACKUP_AUTO_TIME` é America/Recife; conversões EXCLUSIVAMENTE
via `app/utils/time_utils` (`local_to_utc`/`utc_to_recife`) — sem segunda
política de timezone. Persistência e comparação sempre em UTC.
"""

import logging
import threading
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional

from app.config import (
    BACKUP_AUTO_ENABLED,
    BACKUP_AUTO_SCHEDULE,
    BACKUP_AUTO_TIME,
    BACKUP_AUTO_WEEKDAY,
    BACKUP_RETENTION_DAILY_DAYS,
    BACKUP_RETENTION_KEEP_PRE_RESTORE,
    BACKUP_RETENTION_MONTHLY_MONTHS,
    BACKUP_RETENTION_WEEKLY_WEEKS,
)
from app.database import SessionLocal
from app.models.backup_record import BackupRecord
from app.services import backup_service
from app.services.audit_service import (
    ACTION_BACKUP_AUTO_FAILED,
    ACTION_BACKUP_AUTO_SUCCESS,
    ACTION_BACKUP_REMOVED_RETENTION,
    ACTION_RETENTION_EXECUTED,
    ACTION_RETENTION_FAILED,
    RESULT_FAILURE,
    RESULT_SUCCESS,
    write_audit,
)
from app.services.backup_service import (
    BACKUP_TYPE_AUTOMATICO,
    BackupError,
    get_backup_path,
)
from app.utils.time_utils import now_utc, utc_to_recife

logger = logging.getLogger(__name__)

# Intervalo de verificação do loop agendador (segundos — R1)
_TICK_SECONDS = 30

# Atraso do catch-up após o start (segundos — R5)
_CATCHUP_DELAY_SECONDS = 60

# Motivos de preservação (contract §5 — F4)
_MOTIVO_ULTIMO_VALIDO = "ULTIMO_BACKUP_VALIDO"
_MOTIVO_ANCORA_SEMANAL = "ANCORA_SEMANAL"
_MOTIVO_ANCORA_MENSAL = "ANCORA_MENSAL"
_MOTIVO_INTEGRIDADE = "INTEGRIDADE_NAO_OK"

# Faixas de retenção para `removed_reason`/evento (contract §5)
_FAIXA_DIARIA = "RETENCAO_DIARIA"
_FAIXA_MENSAL = "RETENCAO_MENSAL"


# ============================================================================
# Configuração efetiva — normalização/validação no serviço (contract §1)
# ============================================================================

def _effective_schedule() -> str:
    if BACKUP_AUTO_SCHEDULE in ("daily", "weekly"):
        return BACKUP_AUTO_SCHEDULE
    logger.warning(
        "BACKUP_AUTO_SCHEDULE inválido (%r) — usando default 'daily'.",
        BACKUP_AUTO_SCHEDULE,
    )
    return "daily"


def _effective_time() -> tuple:
    """Retorna (hora, minuto) do horário configurado; inválido → (2, 0) + log."""
    raw = (BACKUP_AUTO_TIME or "").strip()
    parts = raw.split(":")
    if len(parts) == 2:
        try:
            hour, minute = int(parts[0]), int(parts[1])
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return hour, minute
        except ValueError:
            pass
    logger.warning(
        "BACKUP_AUTO_TIME inválido (%r) — usando default '02:00'.", BACKUP_AUTO_TIME
    )
    return 2, 0


def _effective_weekday() -> int:
    if 0 <= BACKUP_AUTO_WEEKDAY <= 6:
        return BACKUP_AUTO_WEEKDAY
    logger.warning(
        "BACKUP_AUTO_WEEKDAY inválido (%r) — usando default 0 (domingo).",
        BACKUP_AUTO_WEEKDAY,
    )
    return 0


def _effective_int(value: int, default: int, name: str) -> int:
    """Retenção ≥ 1 (0/negativo provocaria exclusão imediata — FR-035/A9)."""
    if isinstance(value, int) and value >= 1:
        return value
    logger.warning("%s inválido (%r) — usando default %s.", name, value, default)
    return default


# ============================================================================
# Próxima execução e catch-up (R5/R11 — determinísticos)
# ============================================================================

def _local_py_weekday(local_date) -> int:
    """weekday() no vocabulário da config: 0=domingo .. 6=sábado."""
    return (local_date.weekday() + 1) % 7


def _next_run_utc(now: datetime) -> datetime:
    """Próxima ocorrência FUTURA do horário configurado (UTC — determinística).

    Horário configurado é America/Recife → convertido via `local_to_utc`.
    """
    from app.utils.time_utils import local_to_utc

    hour, minute = _effective_time()
    schedule = _effective_schedule()
    now_local = utc_to_recife(now)

    if schedule == "weekly":
        weekday_target = _effective_weekday()
        for offset in range(0, 8):
            candidate_date = (now_local + timedelta(days=offset)).date()
            if _local_py_weekday(candidate_date) != weekday_target:
                continue
            candidate_utc = local_to_utc(
                datetime(candidate_date.year, candidate_date.month,
                         candidate_date.day, hour, minute)
            )
            if candidate_utc > now:
                return candidate_utc
        return now + timedelta(days=7)  # fallback teórico

    # daily: próxima ocorrência do HH:MM local estritamente futura
    candidate_local = now_local.replace(hour=hour, minute=minute,
                                        second=0, microsecond=0)
    candidate_utc = local_to_utc(candidate_local)
    if candidate_utc <= now:
        candidate_utc = local_to_utc(candidate_local + timedelta(days=1))
    return candidate_utc


def _cycle_window_utc(now: datetime) -> tuple:
    """Janela do CICLO CORRENTE em UTC (research R5 — definição precisa).

    - daily: dia calendário local (Recife) corrente, de 00:00 local;
    - weekly: semana de agendamento iniciando 00:00 local do WEEKDAY
      configurado (NÃO é a semana ISO).

    Retorna (inicio_utc, agora).
    """
    from app.utils.time_utils import local_to_utc

    now_local = utc_to_recife(now)
    if _effective_schedule() == "weekly":
        weekday_target = _effective_weekday()
        days_since_target = (_local_py_weekday(now_local.date()) - weekday_target) % 7
        window_start_local = (now_local - timedelta(days=days_since_target)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    else:
        window_start_local = now_local.replace(hour=0, minute=0, second=0,
                                               microsecond=0)
    return local_to_utc(window_start_local), now


def _cycle_has_success(now: datetime, db) -> bool:
    """Ciclo corrente já tem BackupRecord(AUTOMATICO/SUCCESS)? (R5)"""
    start_utc, now_now = _cycle_window_utc(now)
    return (
        db.query(BackupRecord)
        .filter(
            BackupRecord.backup_type == BACKUP_TYPE_AUTOMATICO,
            BackupRecord.status == "SUCCESS",
            BackupRecord.timestamp >= start_utc,
            BackupRecord.timestamp <= now_now,
        )
        .count()
        > 0
    )


def _should_catch_up(now: datetime, db) -> bool:
    """True só se o horário do ciclo corrente já passou SEM sucesso (R5)."""
    hour, minute = _effective_time()
    now_local = utc_to_recife(now)
    if _effective_schedule() == "weekly":
        scheduled_today = _local_py_weekday(now_local.date()) == _effective_weekday()
    else:
        scheduled_today = True
    time_passed = (now_local.hour, now_local.minute) >= (hour, minute)
    return scheduled_today and time_passed and not _cycle_has_success(now, db)


# ============================================================================
# Estado em memória do processo (uvicorn único — R1/R4; crash-safe como a 019)
# ============================================================================

_AUTO_RUNNING = False
_AUTO_LOCK = threading.Lock()
_stop_event: Optional[threading.Event] = None
_scheduler_thread: Optional[threading.Thread] = None
_catchup_done = False
_last_result: Optional[Dict] = None

# Sobrescrevível nos testes (research R12)
_clock: Callable[[], datetime] = now_utc


def scheduler_status() -> Dict:
    """Estado do agendador para o monitoramento (contract §4 — sem segredos)."""
    now = _clock()
    hour, minute = _effective_time()
    status = {
        "enabled": bool(BACKUP_AUTO_ENABLED),
        "schedule": _effective_schedule(),
        "time_local": f"{hour:02d}:{minute:02d}",
        "weekday": _effective_weekday(),
        "running": False,
        "next_run_local": None,
        "last_result": None,
        "last_finished_at": None,
    }
    with _AUTO_LOCK:
        status["running"] = _AUTO_RUNNING
        if _last_result is not None:
            status["last_result"] = dict(_last_result)
    if status["enabled"] and not status["running"]:
        next_run = _next_run_utc(now)
        status["next_run_local"] = utc_to_recife(next_run)
    return status


def retention_monitoring_summary(db=None) -> Dict:
    """Indicadores de monitoramento (FR-032; data-model §1 — sem segredos).

    Consultas derivadas de backup_records + evento BACKUP_RETENCAO_EXECUTADA
    (fonte única da última retenção). Usa a sessão do chamador quando fornecida
    (request/worker com sessão); senão abre sessão própria e curta. Nunca
    lança — indicador ausente = None.
    """
    import json as _json

    summary: Dict = {
        "last_auto": None,        # {filename, timestamp, status}
        "last_valid": None,       # {filename, timestamp, backup_type}
        "last_failure": None,     # {filename, timestamp, error_description}
        "valid_count": 0,         # SUCCESS com arquivo presente no disco
        "removed_count": 0,       # removed_at IS NOT NULL
        "last_retention": None,   # {timestamp, result, description}
    }
    own_session = db is None
    if own_session:
        try:
            db = SessionLocal()
        except Exception:
            logger.exception("Monitoramento: falha ao abrir sessão.")
            return summary
    try:
        last_auto = (
            db.query(BackupRecord)
            .filter(BackupRecord.backup_type == BACKUP_TYPE_AUTOMATICO)
            .order_by(BackupRecord.timestamp.desc(), BackupRecord.id.desc())
            .first()
        )
        if last_auto is not None:
            summary["last_auto"] = {
                "filename": last_auto.filename,
                "timestamp": last_auto.timestamp,
                "status": last_auto.status,
            }

        removed_count = (
            db.query(BackupRecord)
            .filter(BackupRecord.removed_at.isnot(None))
            .count()
        )
        records = (
            db.query(BackupRecord)
            .order_by(BackupRecord.timestamp.desc(), BackupRecord.id.desc())
            .all()
        )
        for r in records:
            if summary["last_failure"] is None and r.status == "FAILURE":
                summary["last_failure"] = {
                    "filename": r.filename,
                    "timestamp": r.timestamp,
                    "error_description": r.error_description,
                }
            if r.status == "SUCCESS" and summary["last_valid"] is None:
                try:
                    if get_backup_path(r.filename).is_file():
                        summary["last_valid"] = {
                            "filename": r.filename,
                            "timestamp": r.timestamp,
                            "backup_type": r.backup_type,
                        }
                except FileNotFoundError:
                    pass
            if r.status == "SUCCESS" and r.removed_at is None:
                try:
                    if get_backup_path(r.filename).is_file():
                        summary["valid_count"] += 1
                except FileNotFoundError:
                    pass
        summary["removed_count"] = removed_count

        # Última retenção: fonte única = evento de auditoria existente
        from app.models.audit_log import AuditLog

        ev = (
            db.query(AuditLog)
            .filter(AuditLog.action == ACTION_RETENTION_EXECUTED)
            .order_by(AuditLog.timestamp.desc(), AuditLog.id.desc())
            .first()
        )
        if ev is not None:
            entry = {"timestamp": ev.timestamp, "description": ev.description}
            try:
                nd = _json.loads(ev.new_data) if ev.new_data else {}
                entry["result"] = nd.get("resultado")
                entry["removidos"] = nd.get("removidos")
            except (TypeError, ValueError):
                entry["result"] = None
                entry["removidos"] = None
            summary["last_retention"] = entry
    except Exception:
        logger.exception("Monitoramento: falha ao apurar indicadores.")
    finally:
        if own_session:
            try:
                db.close()
            except Exception:
                pass
    return summary


# ============================================================================
# Auditoria do worker — sessão PRÓPRIA e curta (R4; padrão _worker_audit 019)
# ============================================================================

def _worker_audit(*, action: str, result: str, description: str,
                  resource_ref: Optional[str] = None,
                  new_data: Optional[Dict] = None) -> None:
    """Evento de auditoria do worker com sessão própria. Ator None = sistema."""
    db = SessionLocal()
    try:
        write_audit(
            db,
            user=None,
            action=action,
            module="Backup",
            resource="backup",
            resource_ref=resource_ref,
            result=result,
            description=description,
            new_data=new_data,
        )
    finally:
        db.close()


# ============================================================================
# Execução do ciclo automático (contract §4 — ordem invariável)
# ============================================================================

def _run_scheduled_backup() -> Optional[Dict]:
    """Ciclo completo do disparo automático (síncrono; o chamador decide thread).

    Guardas (contract §4): (1) já em execução → descarta (log, sem evento);
    (2) restore em andamento → adia (log, sem evento). Retorna resumo ou None.
    """
    global _AUTO_RUNNING, _last_result

    # Guarda 1: sobreposição de automáticos — descartar (FR-010/Teste M)
    with _AUTO_LOCK:
        if _AUTO_RUNNING:
            logger.warning(
                "Backup automático descartado: já existe uma execução em andamento."
            )
            return None
        _AUTO_RUNNING = True
    try:
        # Guarda 2: restore em andamento — adiar (FR-011)
        if backup_service.restore_in_progress():
            logger.warning(
                "Backup automático adiado: restauração em andamento — "
                "executa no próximo ciclo."
            )
            return None

        # Geração via serviço EXISTENTE (FR-001) — sessão própria e curta
        db = SessionLocal()
        try:
            result = backup_service.BackupService.generate_backup(
                db, None, None, backup_type=BACKUP_TYPE_AUTOMATICO
            )
        finally:
            db.close()

        _worker_audit(
            action=ACTION_BACKUP_AUTO_SUCCESS,
            result=RESULT_SUCCESS,
            description="Backup automático gerado com sucesso (sistema).",
            resource_ref=result["filename"],
            new_data={
                "arquivo": result["filename"],
                "tamanho_bytes": result["size_bytes"],
                "sha256": result["sha256"],
            },
        )

        summary = {"ok": True, "filename": result["filename"]}
        _apply_retention_after_cycle()
        _last_result = {"ok": True, "filename": result["filename"]}
        return summary
    except BackupError as exc:
        description = f"Backup automático falhou: {exc}"
        logger.error("%s", description)
        _record_auto_failure(description)
        summary = {"ok": False, "error": description}
        # FR-021: falha do backup NÃO dispara limpeza agressiva — a retenção
        # mantém TODAS as guardas (nada é removido se reduzir válidos).
        _apply_retention_after_cycle()
        _last_result = {"ok": False, "error": description}
        return summary
    except Exception as exc:  # crash-safety: nenhuma exceção escapa (019)
        description = "Backup automático não concluído por erro inesperado."
        logger.exception("Falha inesperada no ciclo automático: %s", exc)
        _record_auto_failure(description)
        summary = {"ok": False, "error": description}
        _apply_retention_after_cycle()
        _last_result = {"ok": False, "error": description}
        return summary
    finally:
        with _AUTO_LOCK:
            _AUTO_RUNNING = False


def _record_auto_failure(description: str) -> None:
    """Evento de auditoria da falha do automático (ator None = sistema)."""
    try:
        _worker_audit(
            action=ACTION_BACKUP_AUTO_FAILED,
            result=RESULT_FAILURE,
            description=description,
        )
    except Exception:  # auditoria nunca quebra o ciclo
        logger.exception("Falha ao auditar erro do backup automático.")


# ============================================================================
# RETENÇÃO GFS (contract §5 — research R6; data-model §3)
# ============================================================================

def _count_valid_backups_on_disk() -> int:
    """Backups válidos presentes no disco (todos os tipos, gzip legível).

    Conservador (F7): inclui legados sem registro — se está no disco, casa a
    regex e o gzip é legível, conta como cópia válida.
    """
    listing = backup_service.BackupService.list_backups()
    return sum(1 for b in listing if b.get("integrity") == "OK")


def _weeks_between(since: datetime, now: datetime) -> int:
    """Semanas completas entre `since` e `now` (segunda como início — ISO)."""
    return (now.date() - since.date()).days // 7


def _is_anchor_semanal(record: BackupRecord, candidates: List[BackupRecord],
                       weeks_limit: int, now: datetime) -> bool:
    """Âncora semanal: automático MAIS RECENTE da semana ISO dentro do limite."""
    if _weeks_between(record.timestamp, now) >= weeks_limit:
        return False
    record_week = record.timestamp.isocalendar()[:2]
    same_week = [r for r in candidates
                 if r.timestamp.isocalendar()[:2] == record_week]
    return record.id == max(same_week, key=lambda r: r.timestamp).id


def _is_anchor_mensal(record: BackupRecord, candidates: List[BackupRecord],
                      months_limit: int, now: datetime) -> bool:
    """Âncora mensal: automático MAIS RECENTE do mês-calendário dentro do limite."""
    month_age = (now.year - record.timestamp.year) * 12 + (
        now.month - record.timestamp.month
    )
    if month_age >= months_limit:
        return False
    same_month = [r for r in candidates
                  if (r.timestamp.year, r.timestamp.month)
                  == (record.timestamp.year, record.timestamp.month)]
    return record.id == max(same_month, key=lambda r: r.timestamp).id


def _pre_restore_candidates(db) -> List[BackupRecord]:
    """Pré-restauração presentes no disco, mais recentes primeiro (FR-025)."""
    records = (
        db.query(BackupRecord)
        .filter(BackupRecord.backup_type == "PRE_RESTAURACAO")
        .order_by(BackupRecord.timestamp.desc())
        .all()
    )
    on_disk = []
    for r in records:
        try:
            if get_backup_path(r.filename).is_file():
                on_disk.append(r)
        except FileNotFoundError:
            continue
    return on_disk


def _try_unlink_and_mark(record: BackupRecord, path, now: datetime,
                         summary: Dict, faixa: str, motivo_new_data: Dict,
                         preservados: Dict[str, str]) -> bool:
    """Remove o arquivo, marca o registro e audita (comum às faixas).

    Retorna True se removido; False em falha (registrada — §32) ou preservado.
    """
    try:
        path.unlink()
    except OSError as exc:
        summary["falhas"] += 1
        logger.error(
            "Retenção: falha ao remover %s (tipo=%s): %s",
            record.filename, type(exc).__name__, exc,
        )
        try:
            _worker_audit(
                action=ACTION_BACKUP_REMOVED_RETENTION,
                result=RESULT_FAILURE,
                resource_ref=record.filename,
                description=f"Falha na remoção do arquivo pela retenção (sistema): {faixa}.",
            )
        except Exception:
            logger.exception("Falha ao auditar erro de remoção da retenção.")
        return False

    # Registro histórico PRESERVADO (§20/§33): marca a remoção
    record.removed_at = now
    record.removed_reason = faixa
    try:
        _worker_audit(
            action=ACTION_BACKUP_REMOVED_RETENTION,
            result=RESULT_SUCCESS,
            resource_ref=record.filename,
            description="Backup removido pela retenção (sistema).",
            new_data=motivo_new_data,
        )
    except Exception:
        logger.exception("Falha ao auditar remoção da retenção.")
    summary["removidos"] += 1
    return True


def _apply_retention(db) -> Dict:
    """Política de retenção GFS (contract §5; data-model §3).

    Universo: BackupRecord(AUTOMATICO/SUCCESS, removed_at IS NULL) com arquivo
    presente. Seleção determinística: janela diária + âncoras semanal ISO/
    mensal + integridade OK + guarda do último backup válido. Remoção física
    EXCLUSIVAMENTE via `get_backup_path` (regex + diretório oficial — §31).
    """
    daily_days = _effective_int(BACKUP_RETENTION_DAILY_DAYS, 30, "BACKUP_RETENTION_DAILY_DAYS")
    weekly_weeks = _effective_int(BACKUP_RETENTION_WEEKLY_WEEKS, 12, "BACKUP_RETENTION_WEEKLY_WEEKS")
    monthly_months = _effective_int(BACKUP_RETENTION_MONTHLY_MONTHS, 12, "BACKUP_RETENTION_MONTHLY_MONTHS")
    keep_pre_restore = max(0, BACKUP_RETENTION_KEEP_PRE_RESTORE)

    now = _clock()
    daily_deadline = now - timedelta(days=daily_days)
    summary: Dict = {
        "candidatos": 0,
        "removidos": 0,
        "falhas": 0,
        "resultado": "COMPLETA",
        "preservados": {},
    }
    preservados: Dict[str, str] = summary["preservados"]

    try:
        records = (
            db.query(BackupRecord)
            .filter(
                BackupRecord.backup_type == BACKUP_TYPE_AUTOMATICO,
                BackupRecord.status == "SUCCESS",
                BackupRecord.removed_at.is_(None),
                BackupRecord.timestamp < daily_deadline,
            )
            .order_by(BackupRecord.timestamp.asc())  # mais antigo primeiro (§32)
            .all()
        )

        # Só consideram-se candidatos com arquivo presente no disco
        candidates: List[BackupRecord] = []
        for r in records:
            try:
                if get_backup_path(r.filename).is_file():
                    candidates.append(r)
            except FileNotFoundError:
                continue  # órfão: registro sem arquivo — nada a fazer

        summary["candidatos"] = len(candidates)

        for record in candidates:
            try:
                path = get_backup_path(record.filename)
            except FileNotFoundError:
                continue

            # Integridade (016): NUNCA remove sem gzip legível integral
            ok_integrity, _ = backup_service.BackupService._gzip_read_status(path)
            if not ok_integrity:
                preservados[record.filename] = _MOTIVO_INTEGRIDADE
                continue

            # Âncoras GFS determinísticas (data-model §3)
            if _is_anchor_semanal(record, candidates, weekly_weeks, now):
                preservados[record.filename] = _MOTIVO_ANCORA_SEMANAL
                continue
            if _is_anchor_mensal(record, candidates, monthly_months, now):
                preservados[record.filename] = _MOTIVO_ANCORA_MENSAL
                continue

            # Guarda do último backup válido (§28): contando TODOS os válidos
            # no disco (incl. manuais, pré-restauração e legados — F7). O
            # candidato ainda está no disco neste momento, portanto a guarda
            # bloqueia somente quando ele é o ÚLTIMO (remoção deixaria 0).
            if _count_valid_backups_on_disk() <= 1:
                preservados[record.filename] = _MOTIVO_ULTIMO_VALIDO
                continue

            removed = _try_unlink_and_mark(
                record, path, now, summary, _FAIXA_DIARIA,
                {"motivo": "expirado", "faixa": _FAIXA_DIARIA}, preservados,
            )

        # Pré-restauração com política explícita (FR-025): default preserva
        # TODOS; KEEP_PRE_RESTORE=N>0 preserva os N mais recentes.
        if keep_pre_restore > 0:
            pre_records = _pre_restore_candidates(db)
            for record in pre_records[keep_pre_restore:]:
                try:
                    path = get_backup_path(record.filename)
                except FileNotFoundError:
                    continue
                ok_integrity, _ = backup_service.BackupService._gzip_read_status(path)
                if not ok_integrity:
                    preservados[record.filename] = _MOTIVO_INTEGRIDADE
                    continue
                if _count_valid_backups_on_disk() <= 1:
                    preservados[record.filename] = _MOTIVO_ULTIMO_VALIDO
                    continue
                _try_unlink_and_mark(
                    record, path, now, summary, _FAIXA_MENSAL,
                    {"motivo": "política KEEP_PRE_RESTORE", "faixa": "PRE_RESTORE"},
                    preservados,
                )

        # Resultado consolidado (§32): PARCIAL nunca é "concluída"
        if summary["falhas"] > 0 and summary["removidos"] > 0:
            summary["resultado"] = "PARCIAL"
        elif summary["falhas"] > 0:
            summary["resultado"] = "FALHA"
        else:
            summary["resultado"] = "COMPLETA"

        try:
            _worker_audit(
                action=ACTION_RETENTION_EXECUTED,
                result=RESULT_SUCCESS,
                description=(
                    f"Retenção executada: {summary['removidos']} removido(s), "
                    f"{summary['falhas']} falha(s) de remoção, "
                    f"{len(preservados)} preservado(s) — resultado {summary['resultado']}."
                ),
                new_data={
                    "candidatos": summary["candidatos"],
                    "removidos": summary["removidos"],
                    "falhas": summary["falhas"],
                    "resultado": summary["resultado"],
                    "preservados": preservados,
                },
            )
        except Exception:
            logger.exception("Falha ao auditar resumo da retenção.")
        db.commit()  # persiste removed_at/reason (marcações do ciclo)
        return summary
    except Exception as exc:  # erro inesperado do ciclo de retenção
        try:
            db.rollback()
        except Exception:
            logger.exception("Falha ao reverter transação da retenção.")
        logger.exception("Falha inesperada no ciclo de retenção: %s", exc)
        try:
            _worker_audit(
                action=ACTION_RETENTION_FAILED,
                result=RESULT_FAILURE,
                description="Retenção de backups não concluída por erro inesperado (sistema).",
            )
        except Exception:  # auditoria nunca quebra o finally
            logger.exception("Falha ao auditar erro da retenção.")
        summary["resultado"] = "FALHA"
        return summary


def _apply_retention_after_cycle() -> None:
    """Executa a retenção após o ciclo (A8), isolando erros do resumo."""
    try:
        db = SessionLocal()
        try:
            _apply_retention(db)
        finally:
            db.close()
    except Exception:
        logger.exception("Falha inesperada ao executar retenção pós-ciclo.")


# ============================================================================
# Thread agendadora (R1) — start/stop idempotentes via lifespan (contract §8)
# ============================================================================

def _scheduler_loop(stop: threading.Event) -> None:
    """Loop de verificação: dispara o worker no horário configurado (R1/R5)."""
    global _catchup_done
    hour, minute = _effective_time()
    logger.info(
        "Agendador de backup automático iniciado (enabled=%s, schedule=%s, time=%02d:%02d).",
        BACKUP_AUTO_ENABLED, _effective_schedule(), hour, minute,
    )
    while not stop.is_set():
        try:
            now = _clock()

            # Catch-up determinístico (R5): avaliado UMA vez por start
            if not _catchup_done:
                _catchup_done = True
                if BACKUP_AUTO_ENABLED:
                    db = SessionLocal()
                    try:
                        needs_catchup = _should_catch_up(now, db)
                    finally:
                        db.close()
                    if needs_catchup:
                        logger.info(
                            "Catch-up do backup automático agendado para %d s após o start.",
                            _CATCHUP_DELAY_SECONDS,
                        )
                        if stop.wait(timeout=_CATCHUP_DELAY_SECONDS):
                            break
                        threading.Thread(
                            target=_run_scheduled_backup,
                            name="backup-auto-catchup-020",
                            daemon=True,
                        ).start()

            if BACKUP_AUTO_ENABLED:
                next_run = _next_run_utc(_clock())
                if _clock() >= next_run:
                    threading.Thread(
                        target=_run_scheduled_backup,
                        name="backup-auto-worker-020",
                        daemon=True,
                    ).start()
        except Exception:  # o loop NUNCA morre por exceção (crash-safety)
            logger.exception("Erro no loop do agendador de backup (ciclo segue).")
        stop.wait(timeout=_TICK_SECONDS)
    logger.info("Agendador de backup automático encerrado.")


def start_scheduler(clock: Optional[Callable[[], datetime]] = None) -> None:
    """Inicia a thread agendadora (idempotente — contract §8)."""
    global _stop_event, _scheduler_thread, _clock
    if clock is not None:
        _clock = clock
    with _AUTO_LOCK:
        if _scheduler_thread is not None and _scheduler_thread.is_alive():
            return
        _stop_event = threading.Event()
        _scheduler_thread = threading.Thread(
            target=_scheduler_loop,
            args=(_stop_event,),
            name="backup-scheduler-020",
            daemon=True,
        )
        _scheduler_thread.start()


def stop_scheduler() -> None:
    """Encerra a thread agendadora (idempotente — contract §8)."""
    global _stop_event, _scheduler_thread
    if _stop_event is not None:
        _stop_event.set()
    if _scheduler_thread is not None:
        _scheduler_thread.join(timeout=5.0)
    _stop_event = None
    _scheduler_thread = None
