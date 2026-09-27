"""
Feature 048 — Importação Inteligente: camada transversal compartilhada.

Contém apenas o que os três importadores (Equipamentos/Colaboradores/Locais)
compartilham de fato (R2):
  1) analyze_columns — análise de cabeçalho/colunas/registros sobre os
     COLUMN_ALIASES existentes de cada service (R1 — os aliases são a
     inteligência de mapeamento já vigente; nada é inventado);
  2) classify_rows — classificação por registro (casca sobre _validate_row e
     verificações existentes de cada service — R3);
  3) detecção de duplicidade interna ao arquivo (chave natural por entidade).

Regras específicas de entidade (obrigatoriedade, normalização de categoria,
movimentações) permanecem nos services de cada importador. Nenhuma
persistência: toda a camada vive em memória (data-model §2). A leitura segue
o mecanismo vigente (_detect_delimiter de cada service + csv.DictReader; o
decode utf-8-sig permanece na rota, como hoje).
"""

import csv
import io
import unicodedata
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.services.import_service import (
    COLUMN_ALIASES as ASSET_ALIASES,
    _detect_delimiter as _asset_detect_delimiter,
    _normalize_column_name as _asset_normalize_column_name,
)
from app.services.custodian_import_service import (
    COLUMN_ALIASES as CUSTODIAN_ALIASES,
    _detect_delimiter as _custodian_detect_delimiter,
    _normalize_column_name as _custodian_normalize_column_name,
)
from app.services.location_import_service import (
    COLUMN_ALIASES as LOCATION_ALIASES,
    _detect_delimiter as _location_detect_delimiter,
    _normalize_column_name as _location_normalize_column_name,
)

# kinds suportados pela camada (os três importadores existentes)
_KINDS = ("assets", "custodians", "locations")

# Tabelas de aliases por kind — consumidas (não duplicadas) dos services.
_KIND_ALIASES = {
    "assets": ASSET_ALIASES,
    "custodians": CUSTODIAN_ALIASES,
    "locations": LOCATION_ALIASES,
}

# Normalizadores de coluna por kind — os mesmos usados pelos parsers.
_KIND_NORMALIZERS = {
    "assets": _asset_normalize_column_name,
    "custodians": _custodian_normalize_column_name,
    "locations": _location_normalize_column_name,
}

_KIND_DETECT_DELIMITER = {
    "assets": _asset_detect_delimiter,
    "custodians": _custodian_detect_delimiter,
    "locations": _location_detect_delimiter,
}

# Campos canônicos obrigatórios por entidade (F3) — exigidos para avançar do
# passo de mapeamento (contrato §3: "avançar exige mapeamento válido").
# Equipamentos: tombamento, equipamento, categoria (local/responsável opcionais)
# Colaboradores: name, email, role, department (matrícula opcional — 014)
# Locais: name, branch, department
REQUIRED_FIELDS = {
    "assets": ("tombamento", "equipamento", "categoria"),
    "custodians": ("name", "email", "role", "department"),
    "locations": ("name", "branch", "department"),
}

# Rótulos amigáveis dos campos canônicos (exibição no passo de mapeamento)
FIELD_LABELS = {
    "assets": {
        "tombamento": "Tombamento",
        "equipamento": "Equipamento",
        "categoria": "Categoria",
        "marca": "Marca",
        "modelo": "Modelo",
        "serie": "Número de série",
        "nota_fiscal": "Nota fiscal",
        "fornecedor": "Fornecedor",
        "valor": "Valor",
        "data_aquisicao": "Data de aquisição",
        "condicao": "Condição",
        "notas": "Notas",
        "localizacao": "Localização",
        "custodiante": "Custodiante (responsável)",
    },
    "custodians": {
        "registration_code": "Matrícula",
        "name": "Nome",
        "email": "E-mail",
        "cpf": "CPF",
        "role": "Cargo",
        "department": "Setor",
        "is_active": "Ativo",
    },
    "locations": {
        "name": "Nome do local",
        "branch": "Filial",
        "department": "Departamento",
        "building": "Prédio",
        "floor": "Andar",
        "room": "Sala",
        "manager_name": "Gestor",
        "description": "Descrição",
    },
}


def _detect_delimiter(content: str, kind: str) -> str:
    """Delimitador detectado pelo mecanismo existente do service do kind."""
    return _KIND_DETECT_DELIMITER[kind](content)


def _raw_key(raw: str) -> str:
    """Chave bruta de comparação de colunas (apresentação): caixa, espaços,
    hifen e acentos normalizados — SEM resolver o alias (o normalizador dos
    services já devolve o campo canônico; aqui precisamos da chave anterior
    a essa resolução para detectar colisões entre aliases do mesmo kind)."""
    key = (raw or "").strip().lower().replace(" ", "_").replace("-", "_")
    folded = unicodedata.normalize("NFKD", key)
    return "".join(ch for ch in folded if not unicodedata.combining(ch))


def analyze_columns(content: str, kind: str) -> Dict:
    """Analisa o CSV (somente leitura) e sugere o campo de cada coluna (R1).

    A sugestão usa apenas os COLUMN_ALIASES do kind selecionado (A1: a união
    das tabelas acontece aqui na camada — consumidas dos services sem
    duplicar; a análise de UM arquivo usa apenas a tabela do importador
    escolhido). Cada coluna recebe:
      - confidence "auto": alias único do kind para o campo;
      - confidence "ambigua": a reversão alias→campo devolve 2+ campos
        canônicos do MESMO kind (colisão na tabela — ex.: 'descricao' em
        locais → name e description). Nunca é escolhida silenciosamente
        (FR-003); candidates lista os campos;
      - confidence "desconhecida": sem alias no kind (FR-005).

    Guardas R6 (parse_errors, sem exceção ao usuário): arquivo vazio, só BOM,
    sem registros (só cabeçalho) e sem cabeçalho utilizável.

    Retorna dict ColumnAnalysis (data-model §2.1):
      header, suggestions, total_rows, parse_errors, delimiter
    """
    if kind not in _KINDS:
        raise ValueError(f"kind inválido: {kind!r}")

    parse_errors: List[str] = []

    # Guarda R6: arquivo vazio ou só BOM (o decode utf-8-sig da rota já remove
    # o BOM quando presente; aqui sobra apenas vazio)
    if not (content or "").strip():
        return {
            "header": [],
            "suggestions": [],
            "total_rows": 0,
            "parse_errors": ["Arquivo vazio: nenhum conteúdo para analisar."],
            "delimiter": ",",
        }

    delimiter = _detect_delimiter(content, kind)

    try:
        reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
        fieldnames = list(reader.fieldnames or [])
    except csv.Error as e:
        return {
            "header": [],
            "suggestions": [],
            "total_rows": 0,
            "parse_errors": [f"CSV corrompido ou mal formatado: {e}"],
            "delimiter": delimiter,
        }

    header = [f for f in fieldnames if f is not None]

    # Guarda R6: sem cabeçalho utilizável (todas as colunas vazias)
    if not any(str(f).strip() for f in header):
        return {
            "header": header,
            "suggestions": [],
            "total_rows": 0,
            "parse_errors": ["Cabeçalho não encontrado: a primeira linha não contém nomes de colunas."],
            "delimiter": delimiter,
        }

    # Sugestão por coluna, a partir dos aliases do kind (A1)
    aliases = _KIND_ALIASES[kind]
    normalizer = _KIND_NORMALIZERS[kind]
    all_fields = set(aliases.values())

    # Reversão alias→campo por chave bruta: quantos campos distintos do kind
    # têm aliases que caem na mesma chave bruta da coluna? (A1/FR-003)
    raw_map: Dict[str, set] = {}
    for alias_key, field in aliases.items():
        raw_map.setdefault(_raw_key(alias_key), set()).add(field)

    suggestions: List[Dict] = []
    for original in header:
        column = str(original)
        rk = _raw_key(column)
        colliding = raw_map.get(rk, set())

        if len(colliding) > 1:
            # Colisão real: 2+ campos canônicos do mesmo kind reivindicam a
            # mesma chave bruta (ex.: variantes com/sem acento apontando para
            # campos diferentes) — nunca escolhida silenciosamente (FR-003)
            suggestions.append({
                "column": column,
                "field": None,
                "confidence": "ambigua",
                "candidates": sorted(colliding),
            })
            continue

        if colliding:
            suggestions.append({
                "column": column,
                "field": next(iter(colliding)),
                "confidence": "auto",
                "candidates": [],
            })
            continue

        # Sem match pela chave bruta: usa o normalizador do service (fallback
        # de acentos/º já vigente). Conhecido só se cair num campo canônico.
        field = normalizer(column)
        if field in all_fields:
            suggestions.append({
                "column": column,
                "field": field,
                "confidence": "auto",
                "candidates": [],
            })
        else:
            suggestions.append({
                "column": column,
                "field": None,
                "confidence": "desconhecida",
                "candidates": [],
            })

    # Contagem de registros (a análise lê apenas a estrutura — validação de
    # linha permanece no parse/classificação dos services)
    total_rows = 0
    try:
        for _ in reader:
            total_rows += 1
    except csv.Error as e:
        parse_errors.append(f"CSV corrompido durante a leitura: {e}")

    # Guarda R6: sem registros de dados (só cabeçalho)
    if total_rows == 0:
        parse_errors.append(
            "O arquivo contém apenas o cabeçalho: nenhum registro para importar."
        )

    return {
        "header": header,
        "suggestions": suggestions,
        "total_rows": total_rows,
        "parse_errors": parse_errors,
        "delimiter": delimiter,
    }


# ============================================================
# Classificação por registro (R3) — casca sobre o que existe
# ============================================================

from app.services.import_service import (
    _validate_row as _asset_validate_row,
    _resolver_custodiante,
)
from app.services.custodian_import_service import (
    _validate_row as _custodian_validate_row,
    _find_by_registration_code,
    _find_by_email,
)
from app.services.location_import_service import (
    _validate_row as _location_validate_row,
    _find_existing_location,
)
from app.models.asset import Asset
from app.services.location_service import LocationService


def _fold(text: str) -> str:
    """Minúsculas sem acentos — mesmo critério de comparação dos services (R7)."""
    folded = unicodedata.normalize("NFKD", (text or "").strip().lower())
    return "".join(ch for ch in folded if not unicodedata.combining(ch))


def _natural_key(row: dict, kind: str) -> Optional[str]:
    """Chave natural da duplicidade interna ao arquivo (data-model §3):
    Equipamentos: tombamento (upper); Colaboradores: matrícula ou e-mail;
    Locais: nome normalizado."""
    if kind == "assets":
        tag = (row.get("tombamento") or "").strip().upper()
        return tag or None
    if kind == "custodians":
        reg = (row.get("registration_code") or "").strip().upper()
        if reg:
            return f"MAT:{reg}"
        email = (row.get("email") or "").strip().lower()
        return f"MAIL:{email}" if email else None
    if kind == "locations":
        name = _fold(row.get("name") or "")
        return name or None
    return None


def _identify(row: dict, kind: str) -> str:
    """Identificador legível da linha para a tabela de preview (contrato §4)."""
    if kind == "assets":
        return (row.get("tombamento") or "").strip() or "—"
    if kind == "custodians":
        return (row.get("name") or "").strip() or "—"
    return (row.get("name") or "").strip() or "—"


def _classify_asset_row(row: dict, row_num: int, db: Session,
                        seen: Dict[str, int]) -> Dict:
    """Classificação de uma linha de equipamento pelas regras reais (F3–F6):
    _validate_row → IGNORADO/ERRO → DUPLICADO (interno/banco/serial) →
    relacionamentos (local rejeita; custodiante vira NAO_ENCONTRADO) →
    VALIDO/AVISO (opcionais ausentes não bloqueiam)."""
    problems: List[str] = []

    if not any((v or "").strip() for v in row.values()):
        return {"row_num": row_num, "status": "IGNORADO",
                "problems": ["Linha em branco"], "identify": "—",
                "internal_dup_of": None}

    row_errors = _asset_validate_row(row, row_num)
    if row_errors:
        return {"row_num": row_num, "status": "ERRO",
                "problems": [e.split(": ", 1)[-1] for e in row_errors],
                "identify": _identify(row, "assets"), "internal_dup_of": None}

    key = _natural_key(row, "assets")
    if key in seen:
        return {"row_num": row_num, "status": "DUPLICADO",
                "problems": [f"Tombamento repetido no próprio arquivo (linha {seen[key]})"],
                "identify": _identify(row, "assets"), "internal_dup_of": seen[key]}
    seen[key] = row_num

    tag = (row.get("tombamento") or "").strip().upper()
    existing = db.query(Asset).filter(Asset.tag == tag).first()
    if existing:
        return {"row_num": row_num, "status": "DUPLICADO",
                "problems": [f"Tombamento já existe no cadastro: {existing.tag}"],
                "identify": tag, "internal_dup_of": None}

    serial = (row.get("serie") or "").strip()
    if serial:
        serial_owner = db.query(Asset).filter(Asset.serial_number == serial).first()
        if serial_owner:
            return {"row_num": row_num, "status": "DUPLICADO",
                    "problems": [
                        f"Número de série já cadastrado para o tombamento '{serial_owner.tag}'"],
                    "identify": tag, "internal_dup_of": None}

    loc_raw = (row.get("localizacao") or "").strip()
    if loc_raw and LocationService.get_by_name(db, loc_raw) is None:
        # Regra atual preservada (F6/G): local inexistente rejeita a linha
        return {"row_num": row_num, "status": "ERRO",
                "problems": [f"Local '{loc_raw}' não encontrado no cadastro de locais"],
                "identify": tag, "internal_dup_of": None}

    cust_raw = (row.get("custodiante") or "").strip()
    if cust_raw and _resolver_custodiante(db, cust_raw) is None:
        return {"row_num": row_num, "status": "NAO_ENCONTRADO",
                "problems": [f"Responsável não encontrado: {cust_raw}"],
                "identify": tag, "internal_dup_of": None}

    if not loc_raw:
        problems.append("Local não informado")  # AVISO informacional (F3) — sem valor fabricado (SC-004)
    if not cust_raw:
        problems.append("Responsável não informado")

    status = "AVISO" if problems else "VALIDO"
    return {"row_num": row_num, "status": status, "problems": problems,
            "identify": tag, "internal_dup_of": None}


def _classify_custodian_row(row: dict, row_num: int, db: Session,
                            seen: Dict[str, int]) -> Dict:
    """Classificação de colaborador (F3/014): _validate_row → IGNORADO/ERRO →
    DUPLICADO interno (matrícula/e-mail) e banco → VALIDO; matrícula ausente
    é AVISO informacional (provisória PROV-%06d é regra vigente da 014)."""
    if not any((v or "").strip() for v in row.values()):
        return {"row_num": row_num, "status": "IGNORADO",
                "problems": ["Linha em branco"], "identify": "—",
                "internal_dup_of": None}

    row_errors = _custodian_validate_row(row, row_num)
    if row_errors:
        return {"row_num": row_num, "status": "ERRO",
                "problems": [e.split(": ", 1)[-1] for e in row_errors],
                "identify": _identify(row, "custodians"), "internal_dup_of": None}

    key = _natural_key(row, "custodians")
    if key and key in seen:
        return {"row_num": row_num, "status": "DUPLICADO",
                "problems": [f"Repetido no próprio arquivo (linha {seen[key]})"],
                "identify": _identify(row, "custodians"), "internal_dup_of": seen[key]}
    if key:
        seen[key] = row_num

    reg = (row.get("registration_code") or "").strip()
    email = (row.get("email") or "").strip()
    existing = (_find_by_registration_code(db, reg) if reg else None) or (
        _find_by_email(db, email) if email else None
    )
    if existing:
        if reg and existing.registration_code == reg.upper():
            motivo = f"Matrícula já cadastrada: {existing.registration_code}"
        else:
            motivo = f"E-mail já cadastrado: {existing.email}"
        return {"row_num": row_num, "status": "DUPLICADO",
                "problems": [motivo],
                "identify": _identify(row, "custodians"), "internal_dup_of": None}

    problems: List[str] = []
    if not reg:
        problems.append("Matrícula não informada — será gerada matrícula provisória")
    status = "AVISO" if problems else "VALIDO"
    return {"row_num": row_num, "status": status, "problems": problems,
            "identify": _identify(row, "custodians"), "internal_dup_of": None}


def _classify_location_row(row: dict, row_num: int, db: Session,
                           seen: Dict[str, int]) -> Dict:
    """Classificação de local (F3/F5): _validate_row → IGNORADO/ERRO →
    DUPLICADO interno (nome normalizado) e banco (get_by_name) → VALIDO."""
    if not any((v or "").strip() for v in row.values()):
        return {"row_num": row_num, "status": "IGNORADO",
                "problems": ["Linha em branco"], "identify": "—",
                "internal_dup_of": None}

    row_errors = _location_validate_row(row, row_num)
    if row_errors:
        return {"row_num": row_num, "status": "ERRO",
                "problems": [e.split(": ", 1)[-1] for e in row_errors],
                "identify": _identify(row, "locations"), "internal_dup_of": None}

    key = _natural_key(row, "locations")
    if key and key in seen:
        return {"row_num": row_num, "status": "DUPLICADO",
                "problems": [f"Nome repetido no próprio arquivo (linha {seen[key]})"],
                "identify": _identify(row, "locations"), "internal_dup_of": seen[key]}
    if key:
        seen[key] = row_num

    name = (row.get("name") or "").strip()
    existing = _find_existing_location(db, name)
    if existing:
        return {"row_num": row_num, "status": "DUPLICADO",
                "problems": [f"Já existe local com o nome '{existing.name}'"],
                "identify": name, "internal_dup_of": None}

    return {"row_num": row_num, "status": "VALIDO", "problems": [],
            "identify": name, "internal_dup_of": None}


_CLASSIFIERS = {
    "assets": _classify_asset_row,
    "custodians": _classify_custodian_row,
    "locations": _classify_location_row,
}


def classify_rows(rows: List[Dict], db: Session, kind: str) -> Dict:
    """Classifica cada registro individualmente (R3/FR-007) — nunca rejeição
    em bloco (SC-002). Cada linha recebe VALIDO/AVISO/DUPLICADO/ERRO/
    NAO_ENCONTRADO/IGNORADO + motivos legíveis, derivados das validações e
    verificações existentes de cada service (nenhuma regra reescrita).

    rows: [{"row_num": int, "resolved": dict}] renormalizadas pelo mapeamento.
    Retorna PreviewSmart (data-model §2.3): rows, summary, needs_resolution.
    Somente leitura — nenhuma escrita no banco (SC-001)."""
    classifier = _CLASSIFIERS[kind]
    seen: Dict[str, int] = {}
    classified: List[Dict] = []

    for item in rows:
        row_num = item["row_num"]
        resolved = item["resolved"]
        entry = classifier(resolved, row_num, db, seen)
        entry["resolved_values"] = resolved
        classified.append(entry)

    summary = {
        "total": len(classified),
        "validos": sum(1 for r in classified if r["status"] == "VALIDO"),
        "avisos": sum(1 for r in classified if r["status"] == "AVISO"),
        "duplicados": sum(1 for r in classified if r["status"] == "DUPLICADO"),
        "erros": sum(1 for r in classified if r["status"] == "ERRO"),
        "nao_encontrados": sum(1 for r in classified if r["status"] == "NAO_ENCONTRADO"),
        "ignorados": sum(1 for r in classified if r["status"] == "IGNORADO"),
    }
    needs_resolution = [
        r["row_num"] for r in classified if r["status"] == "NAO_ENCONTRADO"
    ]
    return {
        "rows": classified,
        "summary": summary,
        "needs_resolution": needs_resolution,
        "kind": kind,
    }


def search_custodian_candidates(db: Session, term: str, limit: int = 10) -> List[dict]:
    """R4 (resolução interativa): candidatos de colaborador para "Atribuir a…"
    na preview — reutiliza a mesma comparação ilike da pesquisa existente
    (nenhum mecanismo novo; nunca cria colaborador)."""
    from app.models.custodian import Custodian

    term = (term or "").strip()
    if not term:
        return []
    results = (
        db.query(Custodian)
        .filter(
            Custodian.name.ilike(f"%{term}%")
            | Custodian.registration_code.ilike(f"%{term}%")
        )
        .order_by(Custodian.id.asc())
        .limit(limit)
        .all()
    )
    return [
        {"id": c.id, "name": c.name, "registration_code": c.registration_code}
        for c in results
    ]


def apply_resolutions(rows: List[Dict], resolutions: Dict,
                      db: Session) -> List[Dict]:
    """R4/§5: aplica as decisões da preview ANTES do execute_* (nenhuma
    mudança nos execute_* — o service recebe o lote como se o CSV tivesse
    chegado daquele jeito).

    rows são as linhas classificadas da preview (status + resolved_values).
      ERRO/IGNORADO            → nunca gravados (FR-014)
      NAO_ENCONTRADO + skip    → linha removida
      NAO_ENCONTRADO sem ação  → removida (sem escolha silenciosa)
      NAO_ENCONTRADO + sem_custodia → custodiante vazio
      NAO_ENCONTRADO + assign:<id>  → custodiante = colaborador escolhido
      VALIDO/AVISO/DUPLICADO   → seguem no lote (duplicados: regra
                                 skip_duplicates vigente no execute_*)
    Retorna o lote (lista de dicts canônicos) pronto para o execute_*.
    """
    from app.models.custodian import Custodian

    lote: List[Dict] = []
    for item in rows:
        status = item.get("status")
        resolved = dict(item.get("resolved_values") or item.get("resolved") or {})
        row_num = item.get("row_num")

        if status in ("ERRO", "IGNORADO"):
            continue

        if status == "NAO_ENCONTRADO":
            action = (resolutions or {}).get(row_num)
            if action is None:
                action = (resolutions or {}).get(str(row_num))
            if action in (None, "skip"):
                continue
            if action == "sem_custodia":
                resolved["custodiante"] = ""
            elif isinstance(action, str) and action.startswith("assign:"):
                custodian_id = action.split(":", 1)[1]
                custodian = db.query(Custodian).filter(Custodian.id == custodian_id).first()
                if custodian:
                    # valor do cadastro escolhido — a gravação segue o caminho
                    # existente (_resolver_custodiante) no execute_import
                    resolved["custodiante"] = custodian.name
                else:
                    continue
        else:
            action = (resolutions or {}).get(row_num) or (resolutions or {}).get(str(row_num))
            if action == "skip":
                continue

        lote.append(resolved)
    return lote


def classify_summary_counts(rows: List[Dict]) -> Dict[str, int]:
    """Contagens por classificação de um payload de preview (para a auditoria
    do confirm — FR-022, sem segredos)."""
    counts: Dict[str, int] = {}
    for item in rows:
        status = item.get("status", "VALIDO")
        counts[status] = counts.get(status, 0) + 1
    return counts
