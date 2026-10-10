import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, desc, and_
from app.utils.time_utils import now_utc
from app.models.asset import Asset
from app.models.audit_log import AuditLog
from app.models.movement import Movement
from app.models.location import Location
from app.models.custodian import Custodian
from app.models.maintenance import Maintenance
from app.models.enums import AssetStatus, AssetCondition, MovementType, MaintenanceStatus
from app.schemas.asset import AssetCreate, AssetUpdate
from app.services.audit_service import ACTION_UPDATE, changed_fields


def _safe_json(raw: Optional[str]) -> Dict[str, Any]:
    """Desserializa `previous_data`/`new_data` da trilha, tolerando valor inválido.

    Mesmo padrão tolerante de `MovementService.get_timeline_for_asset`.
    """
    if not raw:
        return {}
    try:
        dados = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
    return dados if isinstance(dados, dict) else {}


# Feature 067 — limites de coluna validados na edição (data-model V2)
_EDIT_TEXT_LIMITS: Dict[str, int] = {
    "name": 150,
    "brand": 100,
    "model": 100,
    "serial_number": 100,
    "invoice_number": 100,
    "supplier": 150,
}

# Feature 067 — campos de texto opcionais normalizados na edição:
# `strip` e string vazia viram `None` (mesma normalização do cadastro web;
# evita colidir com a unicidade de `serial_number` ao limpar o valor).
_EDIT_OPTIONAL_TEXT = (
    "brand", "model", "serial_number", "invoice_number", "supplier",
    "specifications", "notes",
)

# Feature 067 — campos de data comparados na PRECISÃO DE DIA: o formulário web
# envia `<input type="date">` (sem hora) enquanto a coluna é `DateTime`; sem
# isso, salvar o formulário pré-preenchido contaria como alteração (auditoria
# espúria) e gravaria a data à meia-noite em toda edição.
_EDIT_DATE_FIELDS = ("purchase_date", "warranty_expiry")


class AssetNotEditableError(ValueError):
    """Bem em situação que não permite edição cadastral (feature 067 — P4).

    Subclasse de `ValueError` de propósito: as rotas de API já convertem
    `ValueError` em HTTP 400, preservando o contrato existente.
    """


class AssetEditConflictError(ValueError):
    """Conflito de edição otimista: o bem mudou desde a abertura da tela.

    Feature 067 — P3 (controle otimista por `updated_at`). Subclasse de
    `ValueError` para preservar o mapeamento de erro da API (HTTP 400).
    """


# Feature 067 — rótulos de negócio para o histórico cadastral (FR-016/FR-017).
_ASSET_FIELD_LABELS: Dict[str, str] = {
    "name": "Nome do bem",
    "category": "Categoria",
    "brand": "Marca",
    "model": "Modelo",
    "serial_number": "Nº de Série",
    "specifications": "Especificações Técnicas",
    "purchase_date": "Data de Compra",
    "purchase_value": "Valor de Aquisição",
    "invoice_number": "Nº da Nota Fiscal",
    "supplier": "Fornecedor",
    "warranty_expiry": "Validade da Garantia",
    "condition": "Estado de Conservação",
    "notes": "Observações",
    "tag": "Tombamento",
    "status": "Situação",
    "location_id": "Localização",
    "custodian_id": "Responsável",
}


class AssetService:
    @staticmethod
    def get_cadastral_history(db: Session, asset_id: int, limit: int = 50) -> Dict[str, Any]:
        """Histórico das ALTERAÇÕES CADASTRAIS do bem (feature 067 — FR-016/FR-017).

        Leitura **somente** da trilha de auditoria já existente (`AuditLog` com
        `resource == 'Asset'` e `resource_id == asset_id`) — nenhum mecanismo
        paralelo, nenhuma tabela nova (Constitution IV/VI). O cadastro inicial
        (`CRIACAO`) fica de fora de propósito: ele já é representado pela
        movimentação `ENTRADA_AQUISICAO`, e o §4.5 da spec exige estado vazio
        claro para bens sem alteração cadastral (sem informação enganosa).

        Retorna `{"eventos": [...], "total": int, "truncado": bool}` — `truncado`
        avisa que existem eventos mais antigos que o teto `limit` (FR-016: sem
        truncamento silencioso). As chaves evitam os métodos nativos de `dict`
        (Jinja resolveria `historico.items` como o método `items`).
        """
        query = db.query(AuditLog).filter(
            AuditLog.resource == "Asset",
            AuditLog.resource_id == asset_id,
            AuditLog.action == ACTION_UPDATE,
        )
        total = query.count()
        registros = query.order_by(AuditLog.timestamp.desc(), AuditLog.id.desc()).limit(limit).all()

        items = []
        for registro in registros:
            before = _safe_json(registro.previous_data)
            after = _safe_json(registro.new_data)
            alteracoes = []
            for campo, valores in changed_fields(before, after).items():
                alteracoes.append(
                    {
                        "field": campo,
                        "label": _ASSET_FIELD_LABELS.get(campo, campo),
                        "before": valores.get("de"),
                        "after": valores.get("para"),
                    }
                )
            alteracoes.sort(key=lambda item: item["label"])
            items.append(
                {
                    "id": registro.id,
                    "timestamp": registro.timestamp,
                    "username": registro.username or "Sistema",
                    "description": registro.description,
                    "changes": alteracoes,
                }
            )

        return {"eventos": items, "total": total, "truncado": total > len(items)}

    @staticmethod
    def get_all(
        db: Session,
        search: Optional[str] = None,
        status: Optional[AssetStatus] = None,
        category: Optional[str] = None,
        location_id: Optional[int] = None,
        custodian_id: Optional[int] = None,
        brand: Optional[str] = None,
        model: Optional[str] = None,
        department: Optional[str] = None,
        maintenance_status: Optional[str] = None,
        purchase_date_from: Optional[datetime] = None,
        purchase_date_to: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Asset], int]:
        query = db.query(Asset).options(
            joinedload(Asset.location),
            joinedload(Asset.custodian),
            joinedload(Asset.maintenances)
        )

        if search:
            search_filter = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    # Campos do equipamento
                    Asset.tag.ilike(search_filter),
                    Asset.name.ilike(search_filter),
                    Asset.brand.ilike(search_filter),
                    Asset.model.ilike(search_filter),
                    Asset.serial_number.ilike(search_filter),
                    Asset.invoice_number.ilike(search_filter),
                    # Colaborador relacionado
                    Asset.custodian.has(Custodian.name.ilike(search_filter)),
                    # Localização relacionada (todos os campos)
                    Asset.location.has(
                        or_(
                            Location.name.ilike(search_filter),
                            Location.branch.ilike(search_filter),
                            Location.building.ilike(search_filter),
                            Location.floor.ilike(search_filter),
                            Location.room.ilike(search_filter),
                            Location.department.ilike(search_filter),
                            Location.manager_name.ilike(search_filter),
                            Location.description.ilike(search_filter)
                        )
                    )
                )
            )

        if status:
            query = query.filter(Asset.status == status)

        if category:
            query = query.filter(Asset.category == category)

        if location_id:
            query = query.filter(Asset.location_id == location_id)

        if custodian_id:
            query = query.filter(Asset.custodian_id == custodian_id)

        # Novos filtros avançados
        if brand:
            query = query.filter(Asset.brand.ilike(f"%{brand}%"))

        if model:
            query = query.filter(Asset.model.ilike(f"%{model}%"))

        if department:
            query = query.filter(Asset.location.has(Location.department == department))

        if maintenance_status == "open":
            # Equipamentos com manutenção em andamento
            query = query.filter(Asset.maintenances.any(Maintenance.status == MaintenanceStatus.IN_PROGRESS))
        elif maintenance_status == "closed":
            # Equipamentos sem manutenção aberta (ou com todas finalizadas)
            query = query.filter(
                ~Asset.maintenances.any(Maintenance.status == MaintenanceStatus.IN_PROGRESS)
            )

        if purchase_date_from:
            query = query.filter(Asset.purchase_date >= purchase_date_from)

        if purchase_date_to:
            query = query.filter(Asset.purchase_date <= purchase_date_to)

        total = query.count()
        assets = query.order_by(desc(Asset.created_at)).offset(skip).limit(limit).all()
        return assets, total

    @staticmethod
    def get_by_id(db: Session, asset_id: int) -> Optional[Asset]:
        return db.query(Asset).options(
            joinedload(Asset.location),
            joinedload(Asset.custodian),
            joinedload(Asset.movements),
            joinedload(Asset.maintenances)
        ).filter(Asset.id == asset_id).first()

    @staticmethod
    def get_by_tag(db: Session, tag: str) -> Optional[Asset]:
        return db.query(Asset).options(
            joinedload(Asset.location),
            joinedload(Asset.custodian)
        ).filter(Asset.tag == tag.strip().upper()).first()

    @staticmethod
    def create(db: Session, data: AssetCreate) -> Asset:
        tag = data.tag.strip().upper()
        if AssetService.get_by_tag(db, tag):
            raise ValueError(f"Já existe um equipamento com o tombamento '{tag}'")

        serial_number = data.serial_number.strip() if data.serial_number else None
        if serial_number:
            existing = db.query(Asset).filter(Asset.serial_number == serial_number).first()
            if existing:
                raise ValueError(f"Já existe um equipamento com o número de série '{serial_number}'")

        # Define status inicial baseado na alocação
        initial_status = AssetStatus.IN_USE if data.initial_custodian_id else AssetStatus.AVAILABLE

        asset = Asset(
            tag=tag,
            name=data.name.strip(),
            category=data.category,
            brand=data.brand,
            model=data.model,
            serial_number=serial_number,
            specifications=data.specifications,
            purchase_date=data.purchase_date or datetime.now(),
            purchase_value=data.purchase_value or 0.0,
            invoice_number=data.invoice_number,
            supplier=data.supplier,
            warranty_expiry=data.warranty_expiry,
            condition=data.condition,
            status=initial_status,
            location_id=data.initial_location_id,
            custodian_id=data.initial_custodian_id,
            notes=data.notes
        )
        db.add(asset)
        db.flush()

        # Obter snapshots para a gravação da movimentação inicial de aquisição
        location_name = None
        if data.initial_location_id:
            loc = db.query(Location).filter(Location.id == data.initial_location_id).first()
            if loc:
                location_name = f"{loc.branch} - {loc.department} ({loc.name})"

        custodian_name = None
        if data.initial_custodian_id:
            cust = db.query(Custodian).filter(Custodian.id == data.initial_custodian_id).first()
            if cust:
                custodian_name = f"{cust.name} ({cust.registration_code})"

        # Grava o primeiro registro no fluxo de movimentação (ENTRADA_AQUISICAO)
        initial_movement = Movement(
            asset_id=asset.id,
            movement_type=MovementType.ACQUISITION,
            timestamp=now_utc(),
            origin_location_name="Fornecedor / Entrada Inicial",
            origin_custodian_name="Almoxarifado Geral",
            destination_location_id=data.initial_location_id,
            destination_location_name=location_name or "Estoque Central",
            destination_custodian_id=data.initial_custodian_id,
            destination_custodian_name=custodian_name,
            previous_status=None,
            new_status=initial_status,
            previous_condition=None,
            new_condition=data.condition,
            reason=f"Tombamento inicial e incorporação ao patrimônio (NF: {data.invoice_number or 'N/A'})",
            operator_name=data.initial_operator or "Sistema",
            term_code=f"TR-INIC-{datetime.now().year}-{asset.id:04d}",
            notes="Registro automático de cadastro inicial do bem."
        )
        db.add(initial_movement)
        db.commit()
        db.refresh(asset)
        return asset

    @staticmethod
    def _edit_payload(data: AssetUpdate) -> Dict[str, Any]:
        """Normaliza e valida o payload de edição (feature 067 — V1/V2/V3).

        Fonte única da regra de edição (Constitution III) — aplicada tanto pelo
        fluxo web quanto pela API:

        - campos de texto opcionais: `strip` e vazio -> `None`;
        - `name` presente precisa ser não vazio (V1);
        - limites de coluna com mensagem de negócio, sem truncamento (V2);
        - `purchase_value` presente precisa ser >= 0 (V3).

        Campos não enviados (`exclude_unset`) permanecem intocados.
        """
        payload = data.model_dump(exclude_unset=True)

        for field in _EDIT_OPTIONAL_TEXT:
            value = payload.get(field)
            if isinstance(value, str):
                payload[field] = value.strip() or None

        if "name" in payload:
            name = payload["name"]
            if name is None or not str(name).strip():
                raise ValueError("O nome do equipamento é obrigatório")
            payload["name"] = str(name).strip()

        for field, limit in _EDIT_TEXT_LIMITS.items():
            value = payload.get(field)
            if isinstance(value, str) and len(value) > limit:
                raise ValueError(
                    f"O campo '{field}' excede o limite de {limit} caracteres"
                )

        if "purchase_value" in payload:
            value = payload["purchase_value"]
            if value is not None and value < 0:
                raise ValueError("O valor de aquisição não pode ser negativo")

        return payload

    @staticmethod
    def edit_changes(asset: Asset, data: AssetUpdate) -> Dict[str, Any]:
        """Campos que a edição realmente alteraria (feature 067 — V9).

        Sinal explícito para o chamador distinguir "salvar sem alterações" de
        uma edição efetiva: sem diferença, não há movimentação nem registro de
        auditoria (FR-019/AC11).
        """
        payload = AssetService._edit_payload(data)
        changes: Dict[str, Any] = {}
        for key, value in payload.items():
            atual = getattr(asset, key, None)
            if key in _EDIT_DATE_FIELDS:
                atual = atual.date() if atual else None
                value_cmp = value.date() if value else None
            else:
                value_cmp = value
            if atual != value_cmp:
                changes[key] = value
        return changes

    @staticmethod
    def update(
        db: Session,
        asset_id: int,
        data: AssetUpdate,
        *,
        operator_name: Optional[str] = None,
        change_reason: Optional[str] = None,
        expected_updated_at: Optional[datetime] = None,
        commit: bool = True,
    ) -> Optional[Asset]:
        """Atualiza os dados cadastrais de um bem (feature 067).

        Regras aplicadas aqui (fonte única — Constitution III):

        - V1–V3 (nome obrigatório, limites de coluna, valor >= 0) e
          normalização de texto opcional via `_edit_payload`;
        - V4: unicidade de `serial_number` ignorando o próprio bem;
        - V11: bem `BAIXADO` não é editável por esta via (P4) →
          `AssetNotEditableError`;
        - V10: `expected_updated_at` habilita o controle otimista de edição
          concorrente usado pela tela web (P3) → `AssetEditConflictError`;
        - V8/FR-012: mudança de `condition` grava a movimentação
          `ATUALIZACAO_ESTADO` com o operador autenticado e o motivo informado
          (padrão da feature 065), sem eles o comportamento anterior é mantido.

        `commit=False` permite ao chamador fechar a alteração e o registro de
        auditoria numa única transação (FR-015); o padrão preserva o
        comportamento anterior. As duas novas exceções herdam de `ValueError`
        para manter o mapeamento HTTP 400 da API (contrato preservado).

        `tag`, `status`, `location_id` e `custodian_id` não fazem parte de
        `AssetUpdate` e continuam protegidos (Constitution IV).
        """
        asset = AssetService.get_by_id(db, asset_id)
        if not asset:
            return None

        if asset.status == AssetStatus.WRITTEN_OFF:
            raise AssetNotEditableError(
                "Bem baixado não pode ter o cadastro editado por esta via. "
                "Utilize o procedimento administrativo apropriado."
            )

        if expected_updated_at is not None and asset.updated_at is not None:
            # Precisão de segundo: MariaDB/MySQL armazena DATETIME sem fração.
            if asset.updated_at.replace(microsecond=0) != expected_updated_at.replace(microsecond=0):
                raise AssetEditConflictError(
                    "O bem foi alterado por outro usuário desde que esta tela foi aberta. "
                    "Recarregue e refaça a edição."
                )

        payload = AssetService._edit_payload(data)

        serial_number = payload.get("serial_number")
        if serial_number:
            existing = db.query(Asset).filter(
                Asset.serial_number == serial_number,
                Asset.id != asset_id
            ).first()
            if existing:
                raise ValueError(f"Já existe um equipamento com o número de série '{serial_number}'")

        old_condition = asset.condition

        for key, value in payload.items():
            setattr(asset, key, value)

        new_condition = payload.get("condition")

        # Se houve alteração de condição, grava no fluxo (V8/FR-012)
        if new_condition is not None and new_condition != old_condition:
            movement = Movement(
                asset_id=asset.id,
                movement_type=MovementType.STATUS_UPDATE,
                timestamp=now_utc(),
                origin_location_id=asset.location_id,
                origin_location_name=asset.location.name if asset.location else None,
                origin_custodian_id=asset.custodian_id,
                origin_custodian_name=asset.custodian.name if asset.custodian else None,
                destination_location_id=asset.location_id,
                destination_location_name=asset.location.name if asset.location else None,
                destination_custodian_id=asset.custodian_id,
                destination_custodian_name=asset.custodian.name if asset.custodian else None,
                previous_status=asset.status,
                new_status=asset.status,
                previous_condition=old_condition,
                new_condition=new_condition,
                reason=change_reason or "Vistoria técnica / Atualização de estado de conservação",
                operator_name=operator_name or "Sistema",
                notes=f"Estado de conservação alterado de {old_condition.label} para {new_condition.label}."
            )
            db.add(movement)

        if commit:
            db.commit()
            db.refresh(asset)
        else:
            db.flush()
        return asset

    @staticmethod
    def calculate_depreciation(asset: Asset, annual_rate: float = 0.20) -> dict:
        """
        Calcula a depreciação linear contábil estimada do bem.
        Padrão: 20% ao ano (5 anos de vida útil para equipamentos de TI).
        """
        if not asset.purchase_date or not asset.purchase_value:
            return {
                "initial_value": asset.purchase_value or 0.0,
                "current_value": asset.purchase_value or 0.0,
                "depreciated_amount": 0.0,
                "depreciation_percent": 0.0,
                "age_months": 0
            }

        now = datetime.now()
        months = max(0, (now.year - asset.purchase_date.year) * 12 + (now.month - asset.purchase_date.month))
        monthly_rate = annual_rate / 12.0
        total_depreciation_rate = min(1.0, months * monthly_rate)
        
        depreciated_amount = round(asset.purchase_value * total_depreciation_rate, 2)
        current_value = round(max(0.0, asset.purchase_value - depreciated_amount), 2)
        percent = round(total_depreciation_rate * 100, 1)

        return {
            "initial_value": asset.purchase_value,
            "current_value": current_value,
            "depreciated_amount": depreciated_amount,
            "depreciation_percent": percent,
            "age_months": months
        }
