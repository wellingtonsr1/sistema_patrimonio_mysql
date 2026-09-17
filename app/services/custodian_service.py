from typing import List, Optional
import re
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from app.models.custodian import Custodian
from app.models.asset import Asset
from app.models.enums import AssetStatus
from app.schemas.custodian import CustodianCreate, CustodianUpdate

# Feature 010 — Identificador provisório de colaborador:
# prefixo EXCLUSIVO do sistema (nunca digitado pelo usuário) + 6 dígitos.
_PROV_PREFIX = "PROV-"
_PROV_RE = re.compile(r"^PROV-\d{6}$")
_PROV_FABRICATED_RE = re.compile(r"^PROV-", re.IGNORECASE)  # qualquer valor com o prefixo


class CustodianService:
    @staticmethod
    def is_provisional(registration_code: Optional[str]) -> bool:
        """Feature 010: o prefixo PROV- é o marcador da condição provisória.

        A geração do sistema sempre produz o formato estrito PROV-%06d, mas a
        verificação é pelo PREFIXO (case-insensitive): um valor com o prefixo
        que não esteja bem-formado continua provisório — nunca é tratado como
        matrícula oficial — e permanece substituível pela oficial."""
        return bool(registration_code) and bool(
            _PROV_FABRICATED_RE.match(registration_code.strip())
        )

    @staticmethod
    def _next_provisional_code(db: Session) -> str:
        """Gera o próximo PROV-%06d (padrão do precedente InventarioService.next_code):
        maior PROV- BEM-FORMADO existente + 1. A constraint UNIQUE de
        registration_code é a garantia final contra duplicidade (inclusive em
        cadastros simultâneos). Valores com prefixo malformados (legado/fabricados)
        são ignorados na contagem para não quebrar a conversão numérica."""
        candidates = (
            db.query(Custodian.registration_code)
            .filter(Custodian.registration_code.like(f"{_PROV_PREFIX}%"))
            .all()
        )
        nums = [
            int(row[0][len(_PROV_PREFIX):])
            for row in candidates
            if _PROV_RE.match(row[0] or "")
        ]
        seq = max(nums) + 1 if nums else 1
        return f"{_PROV_PREFIX}{seq:06d}"

    @staticmethod
    def create(db: Session, data: CustodianCreate) -> Custodian:
        # Feature 010: matrícula não informada → gera identificador provisório.
        provided_code = (data.registration_code or "").strip() or None
        if provided_code and _PROV_FABRICATED_RE.match(provided_code):
            # Anti-fabricação: o usuário não pode escolher NENHUM valor iniciado
            # por PROV- (inclusive malformados como PROV-0000 ou prov-123).
            raise ValueError(
                "O identificador provisório é gerado automaticamente pelo sistema "
                "— não informe valores iniciados por PROV-."
            )
        registration_code = provided_code
        if registration_code is None:
            # Erros específicos de validação vencem o loop de retentativa.
            if db.query(Custodian).filter(Custodian.email == data.email).first():
                raise ValueError("E-mail já cadastrado")
            from sqlalchemy.exc import IntegrityError

            # Loop curto de retentativa: colisão concorrente dispara a UNIQUE;
            # faz rollback, regenera o próximo número e tenta novamente.
            for _attempt in range(5):
                code = CustodianService._next_provisional_code(db)
                if CustodianService.get_by_registration_code(db, code):
                    continue  # colisão determinística (ex.: PROV- pré-existente)
                try:
                    return CustodianService._insert(db, data, code)
                except IntegrityError:
                    db.rollback()  # colisão concorrente da UNIQUE → regenera
                    continue
            raise ValueError("Não foi possível gerar o identificador provisório. Tente novamente.")
        return CustodianService._create_with_code(db, data, registration_code)

    @staticmethod
    def _insert(db: Session, data: CustodianCreate, registration_code: str) -> Custodian:
        custodian = Custodian(
            registration_code=registration_code,
            name=data.name,
            email=data.email,
            cpf=data.cpf,
            role=data.role,
            department=data.department,
            is_active=data.is_active,
        )
        db.add(custodian)
        db.commit()
        db.refresh(custodian)
        return custodian

    @staticmethod
    def _create_with_code(db: Session, data: CustodianCreate, registration_code: str) -> Custodian:
        if CustodianService.get_by_registration_code(db, registration_code):
            raise ValueError("Matrícula já cadastrada")
        if db.query(Custodian).filter(Custodian.email == data.email).first():
            raise ValueError("E-mail já cadastrado")

        custodian = Custodian(
            registration_code=registration_code,
            name=data.name,
            email=data.email,
            cpf=data.cpf,
            role=data.role,
            department=data.department,
            is_active=data.is_active,
        )
        db.add(custodian)
        db.commit()
        db.refresh(custodian)
        return custodian

    @staticmethod
    def get_all(db: Session, active_only: bool = False, search: Optional[str] = None) -> List[Custodian]:
        """Lista colaboradores, opcionalmente filtrada por termo de pesquisa.

        Feature 006: `search` é combinado (matrícula, nome, cargo, departamento,
        e-mail), com correspondência parcial e sem diferenciar maiúsculas de
        minúsculas (padrão da pesquisa de bens em asset_service.get_all).
        Sem termo (None/vazio), a consulta permanece idêntica à anterior —
        retrocompatível com API REST e demais chamadores.
        """
        query = db.query(Custodian)
        if active_only:
            query = query.filter(Custodian.is_active == True)

        termo = (search or "").strip()
        if termo:
            filtro = f"%{termo}%"
            query = query.filter(or_(
                Custodian.registration_code.ilike(filtro),
                Custodian.name.ilike(filtro),
                Custodian.role.ilike(filtro),
                Custodian.department.ilike(filtro),
                Custodian.email.ilike(filtro),
            ))

        return query.order_by(Custodian.name).all()

    @staticmethod
    def get_by_id(db: Session, custodian_id: int) -> Optional[Custodian]:
        return db.query(Custodian).filter(Custodian.id == custodian_id).first()

    @staticmethod
    def get_by_registration_code(db: Session, code: str) -> Optional[Custodian]:
        return db.query(Custodian).filter(Custodian.registration_code == code).first()

    @staticmethod
    def update(db: Session, custodian_id: int, data: CustodianUpdate) -> Optional[Custodian]:
        custodian = CustodianService.get_by_id(db, custodian_id)
        if not custodian:
            return None

        if data.registration_code is not None:
            new_code = (data.registration_code or "").strip()
            if not new_code:
                pass  # vazio/espacos = sem alteração
            # Anti-fabricação: PROV-* nunca pode ser um valor digitado
            # (inclusive malformados como PROV-0000 ou prov-123).
            elif _PROV_FABRICATED_RE.match(new_code):
                raise ValueError(
                    "O identificador provisório é gerado automaticamente pelo sistema "
                    "— não informe valores iniciados por PROV-."
                )
            elif new_code != custodian.registration_code:
                # Substituição (feature 010): provisório → oficial, ou oficial → oficial
                # pela API (comportamento atual, validação de unicidade mantida).
                if CustodianService.get_by_registration_code(db, new_code):
                    raise ValueError("Matrícula já cadastrada")
                custodian.registration_code = new_code
        if data.email is not None and data.email != custodian.email:
            if db.query(Custodian).filter(Custodian.email == data.email).first():
                raise ValueError("E-mail já cadastrado")

        for key, value in data.model_dump(exclude_unset=True).items():
            if key == "registration_code":
                continue  # já tratado acima (feature 010)
            setattr(custodian, key, value)

        db.commit()
        db.refresh(custodian)
        return custodian

    @staticmethod
    def get_assigned_assets(db: Session, custodian_id: int) -> List[Asset]:
        """Retorna os equipamentos atualmente sob posse/custódia do colaborador"""
        return db.query(Asset).filter(
            Asset.custodian_id == custodian_id,
            Asset.status != AssetStatus.WRITTEN_OFF
        ).all()

    @staticmethod
    def count_assigned_assets(db: Session, custodian_id: int) -> int:
        return db.query(func.count(Asset.id)).filter(
            Asset.custodian_id == custodian_id,
            Asset.status != AssetStatus.WRITTEN_OFF
        ).scalar() or 0
