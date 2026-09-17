"""DepartmentService — fonte oficial de Departamentos/Setores (Feature 012).

A fonte oficial é a lista **derivada ao vivo** dos valores distintos de
`Location.department` (nenhuma tabela nova, nenhum seed — ZERO DDL; research
R1/R8 do plano). Novos valores oficiais surgem do fluxo existente de cadastro/
edição de locais; este service apenas lê e valida.

Escopo da validação (research R6/R7): `ensure_official` é invocado
exclusivamente pelos handlers web `create_custodian_form`/`update_custodian_form`
quando o formulário envia o marcador `department_source=official`. Caminhos
legados (API REST, importação CSV, chamadas diretas ao service) permanecem
inalterados (FR-012). `CustodianService` não é tocado — recebe o valor já
canonizado pela rota.

A fonte não possui conceito ativo/inativo; a regra condicional FR-015 da spec
é inoperante nesta feature (research R9).
"""
from typing import List

from sqlalchemy.orm import Session

from app.models.location import Location

MSG_OBRIGATORIO = "Departamento/Setor é obrigatório"
MSG_INVALIDO = "Departamento/Setor inválido — selecione um registro da lista oficial"


class DepartmentService:
    @staticmethod
    def list_official(db: Session) -> List[str]:
        """Retorna a lista oficial: valores distintos de `locations.department`,
        não nulos e com trim não vazio, ordenados alfabeticamente
        (case-insensitive). Derivada ao vivo a cada chamada — sem cache/seed."""
        valores = (
            db.query(Location.department)
            .filter(Location.department.isnot(None))
            .distinct()
            .all()
        )
        limpos = {d[0].strip() for d in valores if d[0] and d[0].strip()}
        return sorted(limpos, key=str.casefold)

    @staticmethod
    def ensure_official(db: Session, department: str) -> str:
        """Valida o valor submetido contra a lista oficial e devolve a forma
        canônica (o valor exato vigente na lista).

        Regras (contract service §1.2):
        1. Normaliza a entrada (trim).
        2. Vazio → ValueError de obrigatoriedade (FR-003/AC-03).
        3. Correspondência case-insensitive contra `list_official` — quando
           exatamente um oficial casa (ignorando caixa), devolve sua forma
           canônica (ex.: "SUPORTE" → "Setor de Suporte").
        4. Sem correspondência, ou ambiguidade (dois oficiais diferindo só por
           caixa) sem correspondência exata → ValueError de seleção inválida
           (FR-004/AC-02/AC-04) — força seleção explícita da lista.
        """
        valor = (department or "").strip()
        if not valor:
            raise ValueError(MSG_OBRIGATORIO)

        oficiais = DepartmentService.list_official(db)

        # Correspondência exata (após trim) tem prioridade — resolve a
        # ambiguidade de caixa quando o usuário submete a forma vigente.
        if valor in oficiais:
            return valor

        correspondentes = [o for o in oficiais if o.casefold() == valor.casefold()]
        if len(correspondentes) == 1:
            return correspondentes[0]

        raise ValueError(MSG_INVALIDO)
