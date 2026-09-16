"""Utilitários centrais de data e hora — SisPatrimônio Pro.

Convenção da feature 004 (specs/004-padronizacao-datas-utc):
- Todo timestamp gerado pelo sistema e persistido representa UTC (naive).
- Toda apresentação converte UTC -> America/Recife pelo mecanismo central.
- Valores naive lidos de colunas DATETIME classificadas como timestamp são
  tratados como UTC por contrato da aplicação (FR-018).
- Datas de negócio (purchase_date, warranty_expiry, datas de CSV/formulários)
  não recebem conversão de fuso.

Contrato completo: specs/004-padronizacao-datas-utc/contracts/time-utils-contract.md
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

UTC = ZoneInfo("UTC")
RECIFE = ZoneInfo("America/Recife")


def now_utc() -> datetime:
    """Instante atual em UTC, naive (contrato de persistência da feature 004).

    Uso exclusivo para timestamps persistidos que representam "o agora"
    (FR-001/FR-002). Caminhos fora do escopo (anos de códigos sequenciais,
    depreciação, carimbo local "Gerado em") não devem migrar para cá.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def utc_to_recife(value: datetime | None) -> datetime | None:
    """Converte um timestamp persistido (UTC) para America/Recife (apresentação).

    - None -> None (preserva os guards condicionais dos templates/exports).
    - naive -> tratado como UTC por convenção (FR-018).
    - aware -> respeitado como instante absoluto (astimezone).
    - Fuso nomeado; deslocamento fixo de horas é proibido (FR-005/SC-008).
    - Aplicar uma única vez por fluxo de apresentação (sem dupla conversão).
    """
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(RECIFE)


def local_to_utc(value: datetime) -> datetime:
    """Converte um instante informado em horário local (America/Recife) para UTC naive.

    Uso: filtros de período antes da comparação com colunas persistidas em UTC.
    - naive -> interpretado como America/Recife.
    - aware -> respeitado como instante absoluto (o cliente informou offset).
    - Retorno sempre naive em UTC, para comparar com colunas DATETIME naive.
    """
    if value.tzinfo is None:
        value = value.replace(tzinfo=RECIFE)
    return value.astimezone(UTC).replace(tzinfo=None)


def format_local(value: datetime | None, fmt: str = "%d/%m/%Y %H:%M") -> str:
    """Formata um timestamp persistido (UTC) em horário local (America/Recife).

    Helper para exports em Python (report_service etc.), onde não há filtro Jinja.
    None -> "" (convenção dos exports).
    """
    converted = utc_to_recife(value)
    return "" if converted is None else converted.strftime(fmt)
