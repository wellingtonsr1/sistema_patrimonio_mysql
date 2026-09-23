"""Conteúdo da comunicação no 1Doc (feature 031 — contracts §5).

Funções PURAS: nenhum acesso a banco, nenhuma chamada HTTP. O modelo é fiel
ao utilizado pelo setor de Patrimônio (spec §9 — P-1/P-2):

    Bom dia! Seguem os dados acerca da movimentação do equipamento:

    | Descrição do Material | Tombamento | Origem | Destino |
    |---|---|---|---|
    | Monitor DELL          | 0008       | Suporte | Desenvolvimento |

Dados EXCLUSIVAMENTE do registro patrimonial oficial (FR-004/FR-005).
Sem link para o SisPatrimônio nesta versão (FR-017).
"""

from datetime import datetime
from typing import Optional

SUBJECT_PREFIX = "[SisPatrimônio Pro] "

TABLE_HEADERS = ("Descrição do Material", "Tombamento", "Origem", "Destino")


def build_subject(tag: str) -> str:
    """Assunto institucional (contracts §5) — distinto do assunto do e-mail 030."""
    return f"{SUBJECT_PREFIX}Movimentação patrimonial - {tag or '-'}"


def build_greeting(now_local: Optional[datetime] = None) -> str:
    """Saudação conforme horário local do envio (P-2): 5-11h manhã, 12-17h tarde, noite."""
    hour = (now_local or datetime.now()).hour
    if 5 <= hour < 12:
        return "Bom dia!"
    if 12 <= hour < 18:
        return "Boa tarde!"
    return "Boa noite!"


def _clean(value: Optional[str]) -> str:
    return (value or "-").strip() or "-"


def build_body_text(
    *,
    asset_name: str,
    asset_tag: str,
    origin_name: Optional[str],
    destination_name: Optional[str],
    now_local: Optional[datetime] = None,
) -> str:
    """Versão texto plano: saudação + tabela alinhada de 4 colunas (P-1)."""
    greeting = build_greeting(now_local)
    row = (
        _clean(asset_name),
        _clean(asset_tag),
        _clean(origin_name),
        _clean(destination_name),
    )

    widths = [
        max(len(TABLE_HEADERS[i]), len(row[i])) for i in range(len(TABLE_HEADERS))
    ]
    line = lambda cells: "| " + " | ".join(  # noqa: E731 — local, legível
        cells[i].ljust(widths[i]) for i in range(len(cells))
    ) + " |"
    separator = "|" + "|".join("-" * (w + 2) for w in widths) + "|"

    return "\n".join(
        [
            greeting,
            "Seguem os dados acerca da movimentação do equipamento:",
            "",
            line(TABLE_HEADERS),
            separator,
            line(row),
        ]
    )


def build_body_html(
    *,
    asset_name: str,
    asset_tag: str,
    origin_name: Optional[str],
    destination_name: Optional[str],
    now_local: Optional[datetime] = None,
) -> str:
    """Versão HTML: saudação + tabela de 4 colunas (formato escolhido pelo
    client conforme C-4 do fornecedor)."""
    greeting = build_greeting(now_local)
    cells = "".join(f"<th>{h}</th>" for h in TABLE_HEADERS)
    values = (_clean(asset_name), _clean(asset_tag), _clean(origin_name), _clean(destination_name))
    row = "".join(f"<td>{v}</td>" for v in values)

    return (
        f"<p>{greeting} Seguem os dados acerca da movimentação do equipamento:</p>"
        "<table border=\"1\" cellpadding=\"4\" cellspacing=\"0\">"
        f"<thead><tr>{cells}</tr></thead>"
        f"<tbody><tr>{row}</tr></tbody>"
        "</table>"
    )
