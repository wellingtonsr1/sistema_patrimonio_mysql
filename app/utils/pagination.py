"""Paginação web central — SisPatrimônio Pro (feature 068).

Contrato: specs/068-paginacao-listas-e-relatorios-integros/contracts/
web-list-pagination-contract.md (helper de página, FR-002).

Convenção da casa (research R2): o vocabulário de `page_meta` espelha
`IntegrationCenterService.get_history` (pages/total/start/end/has_prev/has_next),
com `page_size` padrão de **200** (P3).

Invariantes da spec 068 (data-model §4):
- **FR-002**: `page` ausente, vazio, não numérica, <= 0 ou além do fim
  resulta em página válida (1 ou última) — nunca em erro.
- **I3**: filtro antes da página — o `total` é sempre do filtro completo;
  o recorte (`offset_for`) acontece depois.
- **I5**: nada aqui altera comportamento de quem não o utiliza.

Somente-leitura: não há escrita de estado algum (Constitution IX não se aplica).
"""

DEFAULT_PAGE_SIZE = 200

__all__ = ["DEFAULT_PAGE_SIZE", "parse_page", "offset_for", "page_meta"]


def parse_page(raw) -> int:
    """Normaliza o parâmetro de query `page` para um inteiro >= 1 (FR-002).

    Regras (spec §1.4 — *Edge Cases*):
    - `None`, string vazia ou só espaços -> 1;
    - não numérico (`abc`), float, bool ou qualquer outro tipo -> 1;
    - inteiro <= 0 -> 1;
    - strings numéricas válidas -> valor convertido (`"3"` -> 3).

    O recorte além do fim (`> pages`) é resolvido por `page_meta`, que
    "puxa" a página para a última válida (FR-002/SC-002).
    """
    if raw is None or isinstance(raw, bool):
        return 1
    if isinstance(raw, int):
        return raw if raw >= 1 else 1
    if isinstance(raw, str):
        text = raw.strip()
        if not text.lstrip("-").isdigit():
            return 1
        try:
            value = int(text)
        except ValueError:
            return 1
        return value if value >= 1 else 1
    return 1


def offset_for(page, page_size: int = DEFAULT_PAGE_SIZE) -> int:
    """`offset` SQL para a página normalizada (>= 1) com `page_size` válido.

    `page_size` <= 0 ou não numérico é tratado como `DEFAULT_PAGE_SIZE`
    para nunca gerar consulta sem limite acidental. Uso nos services:
    `query.offset(offset_for(page)).limit(page_size)` (FR-001).
    """
    safe_size = page_size if isinstance(page_size, int) and not isinstance(page_size, bool) and page_size > 0 else DEFAULT_PAGE_SIZE
    return (parse_page(page) - 1) * safe_size


def page_meta(total, page, page_size: int = DEFAULT_PAGE_SIZE) -> dict:
    """Contexto de página para templates/rotas (vocabulário de `get_history`).

    Retorna `{page, page_size, pages, total, start, end, has_prev, has_next}`.

    - `total` e `page_size` são normalizados para valores seguros (>= 0 / >= 1).
    - `pages` tem mínimo 1 (estado vazio: "Nenhum registro encontrado",
      sem controle de página — FR-006).
    - Página além do fim é recortada para a **última válida** (FR-002).
    - `start`/`end` são o intervalo exibido ("Mostrando X–Y de Z", FR-004);
      com total 0 ambos são 0.
    """
    safe_total = total if isinstance(total, int) and not isinstance(total, bool) and total > 0 else 0
    safe_size = page_size if isinstance(page_size, int) and not isinstance(page_size, bool) and page_size > 0 else DEFAULT_PAGE_SIZE

    pages = max(1, (safe_total + safe_size - 1) // safe_size)
    current = parse_page(page)
    current = min(current, pages)

    start = (current - 1) * safe_size + 1 if safe_total else 0
    end = min(current * safe_size, safe_total)

    return {
        "page": current,
        "page_size": safe_size,
        "pages": pages,
        "total": safe_total,
        "start": start,
        "end": end,
        "has_prev": current > 1,
        "has_next": current < pages,
    }
