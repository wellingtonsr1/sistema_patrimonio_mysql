from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr


class CustodianBase(BaseModel):
    registration_code: str
    name: str
    email: str
    cpf: Optional[str] = None
    role: str
    department: str
    is_active: bool = True


class CustodianCreate(BaseModel):
    """Criação de colaborador.

    Feature 010: `registration_code` é opcional — quando não informado (ou
    vazio), o service gera automaticamente um identificador provisório
    `PROV-000001` (prefixo exclusivo do sistema; não pode ser digitado).
    """

    registration_code: Optional[str] = None
    name: str
    email: str
    cpf: Optional[str] = None
    role: str
    department: str
    is_active: bool = True


class CustodianUpdate(BaseModel):
    registration_code: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    cpf: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    is_active: Optional[bool] = None


class CustodianRead(CustodianBase):
    id: int
    created_at: datetime
    active_assets_count: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)
