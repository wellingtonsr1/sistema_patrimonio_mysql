"""
Serviço de importação em massa de equipamentos via CSV.

Colunas esperadas (mínimo: tombamento, equipamento, categoria):
  - tombamento   (obrigatório) → tag
  - equipamento  (obrigatório) → name
  - categoria    (obrigatório) → category (nome amigável, valor técnico ou rótulo)
  - marca        (opcional)    → brand
  - modelo       (opcional)    → model
  - serie        (opcional)    → serial_number
  - nota_fiscal  (opcional)    → invoice_number
  - fornecedor   (opcional)    → supplier
  - valor        (opcional)    → purchase_value
  - data_aquisicao (opcional)  → purchase_date (DD/MM/AAAA ou AAAA-MM-DD)
  - condicao     (opcional)    → condition (valor técnico ou rótulo)
  - notas        (opcional)    → notes

O CSV pode conter colunas adicionais — elas são ignoradas.
A separação pode ser ; (padrão BR) ou , — detectado automaticamente.
"""

import csv
import io
import unicodedata
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from sqlalchemy.orm import Session

from app.utils.time_utils import now_utc
from app.models.enums import AssetCategory, AssetCondition, AssetStatus
from app.models.asset import Asset
from app.models.movement import Movement
from app.models.custodian import Custodian
from app.models.enums import MovementType
from app.schemas.asset import AssetCreate
from app.schemas.movement import MovementCreate
from app.services.location_service import LocationService
from app.services.movement_service import MovementService


# Mapeamento de nomes amigáveis → valores do enum AssetCategory
CATEGORY_MAP = {
    "notebook": AssetCategory.NOTEBOOK,
    "laptop": AssetCategory.NOTEBOOK,
    "notebooks": AssetCategory.NOTEBOOK,
    "desktop": AssetCategory.DESKTOP,
    "computador": AssetCategory.DESKTOP,
    "micro": AssetCategory.DESKTOP,
    "monitor": AssetCategory.MONITOR,
    "monitores": AssetCategory.MONITOR,
    "servidor": AssetCategory.SERVER,
    "server": AssetCategory.SERVER,
    "rede": AssetCategory.NETWORKING,
    "rede e conectividade": AssetCategory.NETWORKING,
    "switch": AssetCategory.NETWORKING,
    "roteador": AssetCategory.NETWORKING,
    "router": AssetCategory.NETWORKING,
    "impressora": AssetCategory.PRINTER,
    "printer": AssetCategory.PRINTER,
    "smartphone": AssetCategory.SMARTPHONE,
    "tablet": AssetCategory.SMARTPHONE,
    "celular": AssetCategory.SMARTPHONE,
    "celulares": AssetCategory.SMARTPHONE,
    "smartphone/tablet": AssetCategory.SMARTPHONE,
    "mobiliario": AssetCategory.FURNITURE,
    "móvel": AssetCategory.FURNITURE,
    "moveis": AssetCategory.FURNITURE,
    "mesa": AssetCategory.FURNITURE,
    "cadeira": AssetCategory.FURNITURE,
    "armário": AssetCategory.FURNITURE,
    "veiculo": AssetCategory.VEHICLE,
    "veículo": AssetCategory.VEHICLE,
    "carro": AssetCategory.VEHICLE,
    "equipamento": AssetCategory.EQUIPMENT,
    "equipamento geral": AssetCategory.EQUIPMENT,
    "equipamento_geral": AssetCategory.EQUIPMENT,
    "outros": AssetCategory.OTHER,
    "outro": AssetCategory.OTHER,
    "other": AssetCategory.OTHER,
}

CONDITION_MAP = {
    "novo": AssetCondition.NEW,
    "new": AssetCondition.NEW,
    "excelente": AssetCondition.EXCELLENT,
    "excellent": AssetCondition.EXCELLENT,
    "bom": AssetCondition.GOOD,
    "good": AssetCondition.GOOD,
    "regular": AssetCondition.FAIR,
    "fair": AssetCondition.FAIR,
    "ruim": AssetCondition.POOR,
    "poor": AssetCondition.POOR,
    "inservivel": AssetCondition.UNSERVICEABLE,
    "inservível": AssetCondition.UNSERVICEABLE,
    "unserviceable": AssetCondition.UNSERVICEABLE,
}


def _detect_delimiter(content: str) -> str:
    """Detecta o delimitador do CSV (pode ser ; ou ,)."""
    first_lines = content.split("\n")[:5]
    semicolons = sum(line.count(";") for line in first_lines)
    commas = sum(line.count(",") for line in first_lines)
    if semicolons > commas:
        return ";"
    return ","


def _parse_date(date_str: str) -> Optional[datetime]:
    """Tenta interpretar data em vários formatos."""
    date_str = date_str.strip()
    if not date_str:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def _parse_float(value: str) -> float:
    """Interpreta valor numérico brasileiro (1.234,56 → 1234.56)."""
    value = value.strip()
    if not value:
        return 0.0
    # Remove caracteres não numéricos exceto . , -
    cleaned = value.replace("R$", "").replace(" ", "").strip()
    # Se tem vírgula como separador decimal (padrão BR)
    if "," in cleaned and "." in cleaned:
        # 1.234,56 → remove pontos, troca vírgula por ponto
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _fold(text: str) -> str:
    """Minúsculas e sem acentos, para comparar textos livres com rótulos."""
    folded = unicodedata.normalize("NFKD", (text or "").strip().lower())
    return "".join(ch for ch in folded if not unicodedata.combining(ch))


def _normalize_category(raw: str) -> AssetCategory:
    """Converte texto livre para o enum AssetCategory.

    Aceita o nome amigável ("notebook"), o valor técnico
    ("REDE_E_CONECTIVIDADE") e o rótulo exibido na interface
    ("Rede e Conectividade"), garantindo que um CSV exportado pelo próprio
    sistema possa ser reimportado sem ajustes manuais.
    """
    key = raw.strip().lower()
    if key in CATEGORY_MAP:
        return CATEGORY_MAP[key]
    # Tenta encontrar por substring
    for k, v in CATEGORY_MAP.items():
        if k in key or key in k:
            return v
    # Tenta pelo valor técnico ou pelo rótulo de interface do enum
    folded_key = _fold(raw)
    for cat in AssetCategory:
        if folded_key in (_fold(cat.value), _fold(cat.label)):
            return cat
    return AssetCategory.OTHER


def _normalize_condition(raw: str) -> AssetCondition:
    """Converte texto livre para o enum AssetCondition (valor técnico ou rótulo)."""
    key = raw.strip().lower()
    if key in CONDITION_MAP:
        return CONDITION_MAP[key]
    folded_key = _fold(raw)
    for cond in AssetCondition:
        if folded_key in (_fold(cond.value), _fold(cond.label)):
            return cond
    return AssetCondition.NEW


def _validate_row(row: Dict[str, str], row_num: int) -> List[str]:
    """Valida uma linha do CSV e retorna lista de erros (vazia = OK)."""
    errors = []
    if not row.get("tombamento", "").strip():
        errors.append(f"Linha {row_num}: tombamento é obrigatório")
    if not row.get("equipamento", "").strip():
        errors.append(f"Linha {row_num}: equipamento é obrigatório")
    if not row.get("categoria", "").strip():
        errors.append(f"Linha {row_num}: categoria é obrigatória")
    return errors


# Mapeamento de nomes alternativos de colunas → nome canônico
# nota: para localização, o parser não confia no alias porque a
# normalização do nome da coluna deve preservar o valor exato (incluindo
# acentuação) para a resolução via LocationService. O alias abaixo é
# meramente indicativo.
COLUMN_ALIASES = {
    # tombamento
    "tombamento": "tombamento",
    "tag": "tombamento",
    "patrimonio": "tombamento",
    "patrimônio": "tombamento",
    "cod_patrimonio": "tombamento",
    "codigo": "tombamento",
    "n_tombamento": "tombamento",
    "nº_tombamento": "tombamento",
    # equipamento
    "equipamento": "equipamento",
    "nome": "equipamento",
    "descricao": "equipamento",
    "descrição": "equipamento",
    "nome_do_equipamento": "equipamento",
    "nome_equipamento": "equipamento",
    # categoria
    "categoria": "categoria",
    "category": "categoria",
    "tipo": "categoria",
    # marca
    "marca": "marca",
    "brand": "marca",
    "fabricante": "marca",
    # modelo
    "modelo": "modelo",
    "model": "modelo",
    "versao": "modelo",
    "versão": "modelo",
    # serie
    "serie": "serie",
    "série": "serie",
    "serial": "serie",
    "serial_number": "serie",
    "n_serie": "serie",
    "nº_serie": "serie",
    "num_serie": "serie",
    "numero_serie": "serie",
    "número_de_série": "serie",
    "nº_de_série": "serie",
    "nº_série": "serie",
    "num_série": "serie",
    "número_série": "serie",
    "s_n": "serie",
    "sn": "serie",
    # nota_fiscal
    "nota_fiscal": "nota_fiscal",
    "nf": "nota_fiscal",
    "n_nota": "nota_fiscal",
    "nº_nota": "nota_fiscal",
    "invoice": "nota_fiscal",
    "nf_e": "nota_fiscal",
    # fornecedor
    "fornecedor": "fornecedor",
    "supplier": "fornecedor",
    "vendor": "fornecedor",
    # valor
    "valor": "valor",
    "preco": "valor",
    "preço": "valor",
    "purchase_value": "valor",
    "value": "valor",
    "valor_aquisicao": "valor",
    "valor_aquisição": "valor",
    # data_aquisicao
    "data_aquisicao": "data_aquisicao",
    "data_aquisição": "data_aquisicao",
    "data": "data_aquisicao",
    "purchase_date": "data_aquisicao",
    "data_compra": "data_aquisicao",
    "aquisicao": "data_aquisicao",
    "aquisição": "data_aquisicao",
    # condicao
    "condicao": "condicao",
    "condição": "condicao",
    "condition": "condicao",
    "estado": "condicao",
    # notas
    "notas": "notas",
    "obs": "notas",
    "observacoes": "notas",
    "observações": "notas",
    "notes": "notas",
    "observacao": "notas",
    "observação": "notas",
    # localização
    # localização (ordem preferida: nomes mais usados em primeiro)
    "localizacao": "localizacao",
    "localização": "localizacao",
    "localization": "localizacao",
    "location": "localizacao",
    "local": "localizacao",
    "locations": "localizacao",
    # custodiante/colaborador (Feature 029 — resolvido pelo cadastro de
    # colaboradores; normalizado para a chave canônica "custodiante")
    "custodiante": "custodiante",
    "custodian": "custodiante",
    "colaborador": "custodiante",
    "responsavel": "custodiante",
    "responsável": "custodiante",
}


def _normalize_column_name(raw: str) -> str:
    """Normaliza nome da coluna usando aliases para nome canônico."""
    # Passo 1: lowercase + espaços para underscores (preservando acentos e º)
    key = raw.strip().lower().replace(" ", "_")
    # Tenta alias direto (com acentos)
    if key in COLUMN_ALIASES:
        return COLUMN_ALIASES[key]
    # Passo 2: Remove º e acentos
    key = key.replace("º", "")
    key = key.replace("é", "e").replace("á", "a").replace("ã", "a").replace("õ", "o")
    key = key.replace("ú", "u").replace("í", "i").replace("ó", "o").replace("ô", "o")
    key = key.replace("ê", "e").replace("â", "a").replace("ç", "c").replace("ü", "u")
    if key in COLUMN_ALIASES:
        return COLUMN_ALIASES[key]
    return key


def parse_csv(content: str) -> Tuple[List[Dict[str, str]], List[str]]:
    """
    Faz o parse do conteúdo CSV e retorna (rows, errors).
    Cada row é um dict com as chaves normalizadas.
    """
    delimiter = _detect_delimiter(content)
    reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)

    # Normalizar nomes das colunas usando aliases
    fieldnames = reader.fieldnames or []
    normalized_fields = {}
    for f in fieldnames:
        normalized_fields[f] = _normalize_column_name(f)

    rows = []
    errors = []

    for i, row in enumerate(reader, start=2):  # linha 1 = header
        normalized = {}
        for orig_key, value in row.items():
            norm_key = normalized_fields.get(orig_key, _normalize_column_name(orig_key))
            normalized[norm_key] = (value or "").strip()

        row_errors = _validate_row(normalized, i)
        errors.extend(row_errors)

        if not row_errors:
            rows.append(normalized)

    return rows, errors


def preview_import(rows: List[Dict[str, str]], db: Session) -> Dict:
    """
    Gera uma pré-visualização da importação, verificando duplicatas.
    Retorna dict com 'previews' (lista) e 'summary' (dict).
    """
    previews = []
    duplicates = 0

    for row in rows:
        tag = row["tombamento"].strip().upper()
        existing = db.query(Asset).filter(Asset.tag == tag).first()
        is_dup = existing is not None

        if is_dup:
            duplicates += 1

        previews.append({
            "tag": tag,
            "name": row.get("equipamento", "").strip(),
            "category": row.get("categoria", "").strip(),
            "brand": row.get("marca", ""),
            "model": row.get("modelo", ""),
            "serial_number": row.get("serie", ""),
            "existing_asset_id": existing.id if existing else None,
            "is_duplicate": is_dup,
        })

    return {
        "previews": previews,
        "total": len(rows),
        "duplicates": duplicates,
        "new_items": len(rows) - duplicates,
    }


def _resolver_custodiante(db: Session, nome_raw: str) -> Optional[Custodian]:
    """
    Feature 029 — Resolve a coluna de custodiante pelo cadastro existente.

    Precedência: matrícula (registration_code, identificador oficial único)
    quando o valor corresponde a uma matrícula; senão nome exato (ilike) com
    order_by(Custodian.id) para primeira ocorrência determinística em nomes
    duplicados. NUNCA cria colaborador.
    """
    nome = nome_raw.strip()
    if not nome:
        return None
    by_code = db.query(Custodian).filter(Custodian.registration_code == nome).first()
    if by_code:
        return by_code
    return (
        db.query(Custodian)
        .filter(Custodian.name.ilike(nome))
        .order_by(Custodian.id.asc())
        .first()
    )


def execute_import(
    rows: List[Dict[str, str]],
    db: Session,
    skip_duplicates: bool = True,
    operator_name: Optional[str] = None,
) -> Dict:
    """
    Executa a importação em massa.
    Retorna dict com 'imported', 'skipped', 'errors'.

    Feature 029 — o estado do bem e o histórico patrimonial derivam da mesma
    operação de domínio: a entrada segue o padrão do cadastro manual
    (ENTRADA_AQUISICAO com snapshots reais) e a custódia informada no CSV é
    aplicada exclusivamente via MovementService.create_movement (matriz
    existente, tipos existentes, termo sequencial padrão). O operador das
    movimentações é o usuário autenticado que executou a importação
    (operator_name; fallback de compatibilidade: "Importação CSV").
    Unidade transacional por linha: commit por linha; erro de linha não deixa
    estado parcial e não impede as demais linhas.
    """
    operator = (operator_name or "Importação CSV").strip() or "Importação CSV"
    imported = 0
    skipped = 0
    errors = []

    for i, row in enumerate(rows, start=2):
        try:
            tag = row["tombamento"].strip().upper()
            name = row["equipamento"].strip()
            category = _normalize_category(row.get("categoria", ""))
            brand = row.get("marca", "").strip() or None
            model = row.get("modelo", "").strip() or None
            serial_number = row.get("serie", "").strip() or None
            invoice_number = row.get("nota_fiscal", "").strip() or None
            supplier = row.get("fornecedor", "").strip() or None
            purchase_value = _parse_float(row.get("valor", "0"))
            purchase_date = _parse_date(row.get("data_aquisicao", ""))
            condition = _normalize_condition(row.get("condicao", ""))
            notes = row.get("notas", "").strip() or None
            
            # Resolver localização via coluna localização (alias)
            location = None
            location_name = None
            location_id = None
            location_snapshot = None
            loc_raw = (
                row.get("localizacao")
                or row.get("localization")
                or ""
            )
            loc_raw = loc_raw.strip()
            if loc_raw:
                location_name = loc_raw
                location = LocationService.get_by_name(db, loc_raw)
                if location:
                    location_name = location.name
                    location_id = location.id
                    # Feature 029 — snapshot no formato canônico usado pelo
                    # motor de movimentações e pelo cadastro manual
                    # ("filial - departamento (nome)"), para o Fluxo exibir
                    # o mesmo local sempre da mesma forma
                    location_snapshot = (
                        f"{location.branch} - {location.department} ({location.name})"
                    )
                else:
                    errors.append(
                        f"Linha {i}: local '{loc_raw}' não encontrado no cadastro de locais"
                    )
                    db.rollback()
                    continue

            # Feature 029 — resolver custodiante pela coluna Custodiante
            # (nome/matrícula do cadastro; vazio ou só espaços = ausência)
            custodiante = None
            custodiante_id = None
            cust_raw = (row.get("custodiante") or "").strip()
            if cust_raw:
                custodiante = _resolver_custodiante(db, cust_raw)
                if custodiante:
                    custodiante_id = custodiante.id
                else:
                    errors.append(
                        f"Linha {i}: colaborador '{cust_raw}' não encontrado no cadastro de colaboradores"
                    )
                    db.rollback()
                    continue

            # Verificar duplicata
            existing = db.query(Asset).filter(Asset.tag == tag).first()
            if existing and skip_duplicates:
                skipped += 1
                continue

            if existing and not skip_duplicates:
                # Atualizar existente
                if serial_number:
                    serial_owner = db.query(Asset).filter(
                        Asset.serial_number == serial_number,
                        Asset.id != existing.id
                    ).first()
                    if serial_owner:
                        errors.append(
                            f"Linha {i}: número de série '{serial_number}' já cadastrado para o tombamento "
                            f"'{serial_owner.tag}'"
                        )
                        continue
                existing.name = name
                existing.category = category
                existing.brand = brand
                existing.model = model
                if serial_number:
                    existing.serial_number = serial_number
                if invoice_number:
                    existing.invoice_number = invoice_number
                if supplier:
                    existing.supplier = supplier
                if purchase_value:
                    existing.purchase_value = purchase_value
                if purchase_date:
                    existing.purchase_date = purchase_date
                existing.condition = condition
                if notes:
                    existing.notes = notes
                db.flush()

                # Feature 029 — reimportação: aplicar custódia somente quando
                # há mudança efetiva, via motor de movimentações (matriz
                # centralizada em MovementService). CSV sem custodiante =
                # manter custódia atual (devolução é operação manual).
                m_type = MovementService.resolve_movement_type(
                    existing.location_id,
                    existing.custodian_id,
                    location_id,
                    custodiante_id,
                )
                if m_type is not None:
                    MovementService.create_movement(
                        db,
                        MovementCreate(
                            asset_id=existing.id,
                            movement_type=m_type,
                            destination_location_id=location_id,
                            destination_custodian_id=custodiante_id,
                            reason=(
                                f"Movimentação derivada da reimportação CSV (linha {i})"
                            ),
                            operator_name=operator,
                            generate_term=(m_type == MovementType.ALLOCATION),
                        ),
                    )
                db.commit()
                imported += 1
                continue

            # Verificar duplicata de serial_number antes de criar
            if serial_number:
                serial_existing = db.query(Asset).filter(
                    Asset.serial_number == serial_number
                ).first()
                if serial_existing and skip_duplicates:
                    skipped += 1
                    continue
                if serial_existing and not skip_duplicates:
                    errors.append(
                        f"Linha {i}: número de série '{serial_number}' já cadastrado para o tombamento "
                        f"'{serial_existing.tag}'"
                    )
                    continue

            # Criar novo asset — status inicial sempre disponível: a custódia
            # do CSV, quando informada, é aplicada pelo motor de movimentações
            # logo após a entrada (Feature 029 — nunca fabricada aqui)
            asset = Asset(
                tag=tag,
                name=name,
                category=category,
                brand=brand,
                model=model,
                serial_number=serial_number,
                purchase_date=purchase_date or datetime.now(),
                purchase_value=purchase_value,
                invoice_number=invoice_number,
                supplier=supplier,
                condition=condition,
                status=AssetStatus.AVAILABLE,
                notes=notes,
                location_id=location_id,
            )
            db.add(asset)
            db.flush()

            # Registrar movimentação de entrada — mesmo padrão do cadastro
            # manual (AssetService.create): snapshots reais de origem/destino,
            # operador informado e termo TR-INIC (a entrada não é cautela)
            movement = Movement(
                asset_id=asset.id,
                movement_type=MovementType.ACQUISITION,
                timestamp=now_utc(),
                origin_location_name="Fornecedor / Entrada Inicial",
                origin_custodian_name="Almoxarifado Geral",
                destination_location_name=location_snapshot or "Estoque Central",
                destination_location_id=location_id,
                destination_custodian_name=None,
                destination_custodian_id=None,
                previous_status=None,
                new_status=AssetStatus.AVAILABLE,
                previous_condition=None,
                new_condition=condition,
                reason=(
                    f"Tombamento inicial e incorporação ao patrimônio via "
                    f"importação CSV (linha {i})"
                ),
                operator_name=operator,
                term_code=f"TR-INIC-{datetime.now().year}-{asset.id:04d}",
                notes="Registro automático de cadastro inicial do bem (importação CSV).",
            )
            db.add(movement)

            # Feature 029 — custódia do CSV aplicada exclusivamente pelo motor
            # de movimentações (alocação/cautela com termo sequencial padrão)
            if custodiante_id:
                MovementService.create_movement(
                    db,
                    MovementCreate(
                        asset_id=asset.id,
                        movement_type=MovementType.ALLOCATION,
                        destination_location_id=location_id,
                        destination_custodian_id=custodiante_id,
                        reason=(
                            f"Entrega/cautela derivada da importação CSV (linha {i})"
                        ),
                        operator_name=operator,
                        generate_term=True,
                    ),
                )
            else:
                # Bem novo sem custodiante: fecha a unidade da linha aqui
                # (com custodiante, create_movement já fez o commit da linha)
                db.commit()
            imported += 1

        except Exception as e:
            db.rollback()
            errors.append(f"Linha {i}: {str(e)}")
            continue

    return {
        "imported": imported,
        "skipped": skipped,
        "errors": errors,
        "total_processed": imported + skipped + len(errors),
    }
