"""Configuração operacional do Backup Automático e da Retenção (feature 021).

Fonte ÚNICA de verdade em runtime (spec FR-006/FR-007): a configuração EFETIVA
é resolvida por campo com a precedência

    valor persistido (tela, quando definido)
      → variável de ambiente (app/config.py — bootstrap/fallback)
        → default da Feature 020

Seguindo o precedente existente de configuração persistente do sistema
(ad_service.get_ad_settings/_effective_settings — singleton + fallback env).
Service ESPECÍFICO de backup: não é um serviço genérico de configuração
(briefing §31). A lógica de agendamento/retenção continua no backup_scheduler
(020) — este módulo é apenas a ORIGEM dos valores.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app import config
from app.models.backup_config import BackupConfig
from app.utils.time_utils import now_utc

logger = logging.getLogger(__name__)

# Defaults da Feature 020 (fonte final da precedência — nunca alterados aqui)
_DEFAULT_AUTO_ENABLED = False
_DEFAULT_SCHEDULE = "daily"
_DEFAULT_TIME = "02:00"
_DEFAULT_WEEKDAY = 0
_DEFAULT_RETENTION_DAILY_DAYS = 30
_DEFAULT_RETENTION_WEEKLY_WEEKS = 12
_DEFAULT_RETENTION_MONTHLY_MONTHS = 12
_DEFAULT_KEEP_PRE_RESTORE = 0

_SCHEDULES_VALIDOS = ("daily", "weekly")


@dataclass(frozen=True)
class EffectiveBackupConfig:
    """Snapshot imutável da configuração efetiva (consumo por ciclo/tela)."""

    auto_enabled: bool
    schedule: str
    time: str
    weekday: int
    retention_daily_days: int
    retention_weekly_weeks: int
    retention_monthly_months: int
    keep_pre_restore: int
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None


def get_backup_config(db: Session) -> BackupConfig:
    """Retorna a linha singleton id=1, criando-a (lazy) se ausente.

    Campos operacionais ficam None = "não definido": a configuração efetiva
    nesse estado é exatamente os defaults da Feature 020 (com fallback env) —
    o agendador nunca fica em estado indefinido (spec FR-008).
    """
    settings = db.query(BackupConfig).filter(BackupConfig.id == 1).first()
    if settings is None:
        settings = BackupConfig(id=1, auto_enabled=False)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


def _env_bool(value: Optional[bool]) -> bool:
    return bool(value)


def _env_time_valid(time_str: str) -> bool:
    parts = time_str.split(":")
    if len(parts) != 2:
        return False
    try:
        hour, minute = int(parts[0]), int(parts[1])
    except ValueError:
        return False
    return 0 <= hour <= 23 and 0 <= minute <= 59


def _first_defined(*values):
    """Primeiro valor "definido" (não None). None se todos indefinidos."""
    for value in values:
        if value is not None:
            return value
    return None


def get_effective_config(db: Session) -> EffectiveBackupConfig:
    """Resolve a configuração efetiva (precedência única — spec FR-007).

    Por campo: persistido (definido) → env (config.py) → default da 020.
    Env inválida é tratada como ausente (cai no default; log técnico) — nunca
    levanta. Retorna snapshot imutável para consumo consistente por ciclo
    (agendador/tela/retenção leem sempre a MESMA configuração — FR-010).
    """
    row = get_backup_config(db)

    # --- frequência ---
    schedule = _first_defined(row.schedule, config.BACKUP_AUTO_SCHEDULE)
    if schedule not in _SCHEDULES_VALIDOS:
        if schedule is not None:
            logger.warning(
                "Configuração de backup: frequência inválida (%r) — usando default.",
                schedule,
            )
        schedule = _DEFAULT_SCHEDULE

    # --- horário (env inválida = ausente) ---
    time_value = _first_defined(row.time, config.BACKUP_AUTO_TIME)
    if time_value is None or not _env_time_valid(time_value):
        if time_value is not None:
            logger.warning(
                "Configuração de backup: horário inválido (%r) — usando default.",
                time_value,
            )
        time_value = _DEFAULT_TIME

    # --- dia da semana ---
    weekday = _first_defined(row.weekday, config.BACKUP_AUTO_WEEKDAY)
    if weekday is None or not 0 <= int(weekday) <= 6:
        if weekday is not None:
            logger.warning(
                "Configuração de backup: dia da semana inválido (%r) — usando default.",
                weekday,
            )
        weekday = _DEFAULT_WEEKDAY
    weekday = int(weekday)

    # --- retenção (env inválida/não positiva = default) ---
    def _effective_int(persisted, env_value, default, name):
        value = _first_defined(persisted, env_value)
        if value is None:
            return default
        try:
            value = int(value)
        except (TypeError, ValueError):
            value = default
        if value < (0 if name == "keep" else 1):
            logger.warning(
                "Configuração de backup: %s fora de faixa (%r) — usando default.",
                name, value,
            )
            return default
        return value

    retention_daily = _effective_int(
        row.retention_daily_days, config.BACKUP_RETENTION_DAILY_DAYS,
        _DEFAULT_RETENTION_DAILY_DAYS, "retention_daily_days",
    )
    retention_weekly = _effective_int(
        row.retention_weekly_weeks, config.BACKUP_RETENTION_WEEKLY_WEEKS,
        _DEFAULT_RETENTION_WEEKLY_WEEKS, "retention_weekly_weeks",
    )
    retention_monthly = _effective_int(
        row.retention_monthly_months, config.BACKUP_RETENTION_MONTHLY_MONTHS,
        _DEFAULT_RETENTION_MONTHLY_MONTHS, "retention_monthly_months",
    )
    keep_pre_restore = _effective_int(
        row.keep_pre_restore, config.BACKUP_RETENTION_KEEP_PRE_RESTORE,
        _DEFAULT_KEEP_PRE_RESTORE, "keep",
    )

    return EffectiveBackupConfig(
        auto_enabled=_env_bool(row.auto_enabled),
        schedule=schedule,
        time=time_value,
        weekday=weekday,
        retention_daily_days=retention_daily,
        retention_weekly_weeks=retention_weekly,
        retention_monthly_months=retention_monthly,
        keep_pre_restore=keep_pre_restore,
        updated_at=row.updated_at,
        updated_by=row.updated_by,
    )


def save_backup_config(
    db: Session,
    actor,
    *,
    auto_enabled: bool,
    schedule: str,
    time: str,
    weekday: int,
    retention_daily_days: int,
    retention_weekly_weeks: int,
    retention_monthly_months: int,
    keep_pre_restore: int,
) -> EffectiveBackupConfig:
    """Valida e persiste a configuração (spec FR-014/FR-015; research R5/R6).

    Valida TODOS os campos ANTES de qualquer escrita — qualquer violação levanta
    ValueError e nada é persistido (estado vigente intacto). Em sucesso: aplica
    na linha singleton com commit ÚNICO (atômico — última escrita válida
    prevalece), registra rastreio e retorna a efetiva resultante. Auditoria é
    responsabilidade da rota (padrão do POST do AD — contract §1).
    """
    # --- validação completa antes de escrever (FR-014/FR-015) ---
    if schedule not in _SCHEDULES_VALIDOS:
        raise ValueError("Frequência inválida: use 'daily' (diário) ou 'weekly' (semanal).")
    if not isinstance(time, str) or not _env_time_valid(time):
        raise ValueError("Horário inválido: informe HH:MM válido (00:00–23:59).")
    try:
        weekday = int(weekday)
    except (TypeError, ValueError):
        raise ValueError("Dia da semana inválido: informe um valor entre 0 (domingo) e 6 (sábado).")
    if not 0 <= weekday <= 6:
        raise ValueError("Dia da semana inválido: informe um valor entre 0 (domingo) e 6 (sábado).")
    for name, value in (
        ("retenção diária", retention_daily_days),
        ("retenção semanal", retention_weekly_weeks),
        ("retenção mensal", retention_monthly_months),
    ):
        try:
            value = int(value)
        except (TypeError, ValueError):
            raise ValueError(f"{name.capitalize()} inválida: informe um número inteiro ≥ 1.")
        if value < 1:
            raise ValueError(f"{name.capitalize()} inválida: informe um valor ≥ 1.")
    try:
        keep_pre_restore = int(keep_pre_restore)
    except (TypeError, ValueError):
        raise ValueError("Pré-restauração inválida: informe um número inteiro ≥ 0.")
    if keep_pre_restore < 0:
        raise ValueError("Pré-restauração inválida: informe 0 (preservar todos) ou N ≥ 1.")

    # --- persistência (commit único — atômico) ---
    row = get_backup_config(db)
    row.auto_enabled = bool(auto_enabled)
    row.schedule = schedule
    row.time = time
    row.weekday = weekday
    row.retention_daily_days = int(retention_daily_days)
    row.retention_weekly_weeks = int(retention_weekly_weeks)
    row.retention_monthly_months = int(retention_monthly_months)
    row.keep_pre_restore = int(keep_pre_restore)
    row.updated_by = getattr(actor, "username", None)
    row.updated_at = now_utc()
    db.commit()
    db.refresh(row)

    return get_effective_config(db)
