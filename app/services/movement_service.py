from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from app.utils.time_utils import now_utc, format_local, local_to_utc
from app.models.asset import Asset
from app.models.movement import Movement
from app.models.location import Location
from app.models.custodian import Custodian
from app.models.audit_log import AuditLog
from app.models.enums import MovementType, AssetStatus, AssetCondition
from app.services.audit_service import ACTION_CREATE, ACTION_UPDATE, ACTION_MOVEMENT, ACTION_MAINTENANCE, RESULT_SUCCESS
import json as json_lib
from app.schemas.movement import MovementCreate, MovementFilter
from app.config import COMPANY_NAME, COMPANY_CNPJ, COMPANY_ADDRESS


class MovementService:
    @staticmethod
    def resolve_movement_type(
        current_location_id: Optional[int],
        current_custodian_id: Optional[int],
        dest_location_id: Optional[int],
        dest_custodian_id: Optional[int],
    ) -> Optional[MovementType]:
        """
        Feature 029 — Decide o tipo de movimentação existente a partir da
        diferença entre o estado atual (local/custodiante) e o destino desejado.

        Método PURO: não consulta o banco, não muta estado, não grava nada —
        a execução (validações VAL-002..VAL-008, snapshots, termo, commit)
        continua exclusivamente em create_movement, que permanece a fonte
        das regras (a matriz aqui é apenas consultável/reutilizável).

        Tabela de decisão:
        | local atual × destino | custodiante atual × destino        | resultado          |
        |-----------------------|------------------------------------|--------------------|
        | igual (inclusive None)| igual (inclusive None)             | None               |
        | igual                 | diferente (destino não None)       | ALOCACAO_CAUTELA   |
        | diferente             | igual (não None)                   | TRANSFERENCIA_LOCAL|
        | diferente             | diferente (destino não None)       | ALOCACAO_CAUTELA   |
        | estoque (sem custodiante) → custodiante | qualquer local   | ALOCACAO_CAUTELA   |

        Devolução ao estoque (custodiante → None) NÃO é decidível aqui: é
        operação manual (DEVOLUCAO_ESTOQUE) e não é disparada por carga CSV.
        """
        location_same = (current_location_id or None) == (dest_location_id or None)
        custodian_same = (current_custodian_id or None) == (dest_custodian_id or None)

        if location_same and custodian_same:
            return None  # nenhuma alteração efetiva (semântica VAL-002)
        if dest_custodian_id and not custodian_same:
            # entrega a colaborador (novo ou a partir do estoque) → cautela/termo
            return MovementType.ALLOCATION
        if not dest_custodian_id and not custodian_same:
            # destino sem custodiante com custodiante atual: custódia não é
            # alterável por carga (devolução é manual) — sem movimentação
            return None
        # custódia preservada: só resta mudança de local → transferência
        return MovementType.TRANSFER

    @staticmethod
    def create_movement(
        db: Session,
        data: MovementCreate,
        notify: bool = True,
        operator: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Movement:
        """
        Executa e grava de forma atômica uma nova movimentação de equipamento,
        atualizando o estado atual do bem e registrando a trilha de auditoria completa.

        Feature 030 — parâmetros ADITIVOS (nenhum chamador existente muda):
        - ``notify=True`` (default): após o commit, solicita a notificação por
          e-mail ao serviço de notificação (best-effort — falha NUNCA afeta a
          movimentação nem propaga erro; RN-001/FR-003). O import CSV em lote
          passa ``notify=False`` (RN-002 — lote não notifica).
        - ``operator``/``ip_address``: contexto opcional para chamadas diretas
          ao service (defaults None — nenhum chamador atual é obrigado a passar).
        """
        asset = db.query(Asset).filter(Asset.id == data.asset_id).first()
        if not asset:
            raise ValueError(f"Equipamento com ID {data.asset_id} não encontrado.")

        if asset.status == AssetStatus.WRITTEN_OFF and data.movement_type != MovementType.ACQUISITION:
            raise ValueError("Não é possível movimentar um equipamento que já foi baixado/descartado.")

        # Guardar snapshots da situação anterior
        prev_status = asset.status
        prev_condition = asset.condition
        prev_location_id = asset.location_id
        prev_custodian_id = asset.custodian_id

        prev_location_name = None
        if asset.location:
            prev_location_name = f"{asset.location.branch} - {asset.location.department} ({asset.location.name})"
        
        prev_custodian_name = None
        if asset.custodian:
            prev_custodian_name = f"{asset.custodian.name} ({asset.custodian.registration_code})"

        # Obter referências do novo destino
        new_location = None
        new_location_name = None
        if data.destination_location_id:
            new_location = db.query(Location).filter(Location.id == data.destination_location_id).first()
            if new_location:
                new_location_name = f"{new_location.branch} - {new_location.department} ({new_location.name})"

        new_custodian = None
        new_custodian_name = None
        if data.destination_custodian_id:
            new_custodian = db.query(Custodian).filter(Custodian.id == data.destination_custodian_id).first()
            if new_custodian:
                new_custodian_name = f"{new_custodian.name} ({new_custodian.registration_code})"

        # Determinar novo status e atualizar campos do Ativo conforme o Tipo de Movimentação
        m_type = data.movement_type

        # ===================================================================
        # Feature 005 — Matriz de Movimentação (Local x Responsável)
        # ===================================================================
        # Resolução determinística dos valores efetivos de origem/destino,
        # ANTES de qualquer mutação do Asset (nenhum efeito parcial).
        origin_location_id = prev_location_id
        origin_custodian_id = prev_custodian_id
        effective_dest_location_id = (
            data.destination_location_id
            if (data.destination_location_id and data.destination_location_id > 0)
            else origin_location_id  # "Manter Local Atual" e destino omitido = local atual
        )
        if m_type in (MovementType.RETURN_STOCK, MovementType.WRITE_OFF):
            effective_dest_custodian_id = None
        elif m_type == MovementType.ALLOCATION:
            effective_dest_custodian_id = data.destination_custodian_id
        elif m_type == MovementType.TRANSFER:
            # Transferência não representa mudança de custódia: preserva o atual
            effective_dest_custodian_id = data.destination_custodian_id or origin_custodian_id
        else:
            # Demais tipos (manutenção, estado, aquisição) mantêm regras próprias
            effective_dest_custodian_id = origin_custodian_id

        # NULL + NULL = iguais; NULL x identificado = diferentes (comparação direta)
        is_location_same = (effective_dest_location_id == origin_location_id)
        is_custodian_same = (effective_dest_custodian_id == origin_custodian_id)

        # A matriz se aplica somente a ALOCAÇÃO/CAUTELA e TRANSFERÊNCIA —
        # devolução, baixa/descarte e manutenção possuem fluxos próprios preservados.
        if m_type in (MovementType.ALLOCATION, MovementType.TRANSFER):
            # VAL-005 — transferência sem local de destino informado (campo ausente;
            # verificada antes da matriz por ser erro de preenchimento mais específico)
            if m_type == MovementType.TRANSFER and not data.destination_location_id:
                raise ValueError(
                    "Para transferência de setor é obrigatório selecionar o local de destino."
                )
            # VAL-002 — nenhuma alteração efetiva: bloquear sem gravar nada
            if is_location_same and is_custodian_same:
                raise ValueError(
                    "Nenhuma alteração efetiva detectada. "
                    "O local e o colaborador de destino são idênticos aos atuais."
                )
            # VAL-003 — alocação/cautela exige responsável de destino
            if m_type == MovementType.ALLOCATION and not effective_dest_custodian_id:
                raise ValueError(
                    "Para alocação/cautela é obrigatório selecionar o colaborador de destino."
                )
            # VAL-004 — mudança só de local com o mesmo responsável é Transferência
            if m_type == MovementType.ALLOCATION and not is_location_same and is_custodian_same:
                raise ValueError(
                    "O colaborador informado já é o responsável atual pelo equipamento. "
                    "Para transferir o equipamento mantendo o mesmo responsável, "
                    "utilize Transferência de Setor / Filial."
                )
            # VAL-006 — transferência exige alteração efetiva de local
            if m_type == MovementType.TRANSFER and is_location_same:
                raise ValueError(
                    "Para transferência de setor/filial é obrigatório selecionar um local "
                    "de destino diferente do atual. Para alterar apenas o colaborador "
                    "responsável, utilize Alocação / Cautela."
                )
            # VAL-007 — entrega a novo colaborador deve ser Alocação/Cautela (termo)
            if (
                m_type == MovementType.TRANSFER
                and not is_location_same
                and not is_custodian_same
                and effective_dest_custodian_id is not None
            ):
                raise ValueError(
                    "A entrega do equipamento a um novo colaborador deve ser registrada "
                    "como Alocação / Cautela para emissão do Termo de Responsabilidade."
                )
        elif m_type == MovementType.RETURN_STOCK:
            # VAL-008 — devolução redundante: bem já disponível no estoque, sem
            # responsável e sem alteração efetiva de local
            if origin_custodian_id is None and is_location_same:
                raise ValueError("O equipamento já se encontra no estoque neste local.")

        if m_type == MovementType.ALLOCATION:
            if not data.destination_custodian_id:
                raise ValueError("Para alocação/cautela é obrigatório selecionar o colaborador de destino.")
            new_status = AssetStatus.IN_USE
            asset.custodian_id = data.destination_custodian_id
            if data.destination_location_id:
                asset.location_id = data.destination_location_id

        elif m_type == MovementType.RETURN_STOCK:
            new_status = AssetStatus.AVAILABLE
            asset.custodian_id = None
            if data.destination_location_id:
                asset.location_id = data.destination_location_id

        elif m_type == MovementType.TRANSFER:
            if not data.destination_location_id:
                raise ValueError("Para transferência de setor é obrigatório selecionar o local de destino.")
            asset.location_id = data.destination_location_id
            if data.destination_custodian_id:
                asset.custodian_id = data.destination_custodian_id
            new_status = AssetStatus.IN_USE if asset.custodian_id else AssetStatus.AVAILABLE

        elif m_type == MovementType.MAINTENANCE_OUT:
            new_status = AssetStatus.IN_MAINTENANCE
            if data.destination_location_id:
                asset.location_id = data.destination_location_id

        elif m_type == MovementType.MAINTENANCE_IN:
            new_status = AssetStatus.AVAILABLE
            if data.destination_location_id:
                asset.location_id = data.destination_location_id
            if data.destination_custodian_id:
                asset.custodian_id = data.destination_custodian_id
                new_status = AssetStatus.IN_USE

        elif m_type == MovementType.WRITE_OFF:
            new_status = AssetStatus.WRITTEN_OFF
            asset.custodian_id = None
            if not data.new_condition:
                data.new_condition = AssetCondition.UNSERVICEABLE

        elif m_type == MovementType.STATUS_UPDATE:
            new_status = asset.status
            new_location_name = prev_location_name
            new_custodian_name = prev_custodian_name

        else:
            new_status = asset.status

        # Atualiza status e condição no ativo
        asset.status = new_status
        if data.new_condition:
            asset.condition = data.new_condition
        asset.updated_at = now_utc()

        # Gera termo de responsabilidade sequencial
        term_code = None
        if data.generate_term or m_type in [MovementType.ALLOCATION, MovementType.RETURN_STOCK]:
            count_year = db.query(Movement).filter(
                Movement.movement_type.in_([MovementType.ALLOCATION, MovementType.RETURN_STOCK])
            ).count() + 1
            term_code = f"TR-{datetime.now().year}-{count_year:05d}"

        # Criação do registro imutável no log de fluxo de movimentações
        movement = Movement(
            asset_id=asset.id,
            movement_type=data.movement_type,
            timestamp=now_utc(),
            origin_location_id=prev_location_id,
            origin_location_name=prev_location_name or "Não definido",
            origin_custodian_id=prev_custodian_id,
            origin_custodian_name=prev_custodian_name or "Nenhum / Estoque",
            destination_location_id=data.destination_location_id or prev_location_id,
            destination_location_name=new_location_name or prev_location_name,
            # Feature 005 (T008/T028): o registro histórico reflete a custódia
            # efetiva — transferência que preserva o responsável grava o
            # custodiante real, não NULL.
            destination_custodian_id=(
                None if m_type == MovementType.RETURN_STOCK
                else effective_dest_custodian_id if m_type == MovementType.TRANSFER
                else data.destination_custodian_id
            ),
            destination_custodian_name=(
                "Almoxarifado / Estoque" if m_type == MovementType.RETURN_STOCK
                else (new_custodian_name or prev_custodian_name) if m_type == MovementType.TRANSFER
                else new_custodian_name
            ),
            previous_status=prev_status,
            new_status=new_status,
            previous_condition=prev_condition,
            new_condition=data.new_condition or prev_condition,
            reason=data.reason.strip(),
            operator_name=data.operator_name.strip(),
            term_code=term_code,
            term_signed=False,
            notes=data.notes
        )

        db.add(movement)
        db.commit()
        db.refresh(movement)

        # ====================================================================
        # Feature 030 — notificação por e-mail (pós-commit, best-effort).
        # PONTO DE NÃO-RETORNO: a movimentação JÁ está persistida aqui; qualquer
        # falha no bloco abaixo é capturada e NUNCA propaga (FR-002/FR-003/RN-001).
        # ====================================================================
        if notify:
            try:
                from app.services import notification_service as _ns

                _ns.notify_movement(
                    db,
                    movement,
                    operator=operator,
                    ip_address=ip_address,
                )
            except Exception:  # pragma: no cover — defesa final; nada escapa
                import logging

                logging.getLogger(__name__).exception(
                    "Falha inesperada no hook de notificação (movimentação %s) — movimentação preservada.",
                    movement.id,
                )

        return movement

    @staticmethod
    def get_by_id(db: Session, movement_id: int) -> Optional[Movement]:
        return db.query(Movement).options(
            joinedload(Movement.asset),
            joinedload(Movement.origin_location),
            joinedload(Movement.destination_location),
            joinedload(Movement.origin_custodian),
            joinedload(Movement.destination_custodian)
        ).filter(Movement.id == movement_id).first()

    @staticmethod
    def get_by_uuid(db: Session, movement_uuid: str) -> Optional[Movement]:
        return db.query(Movement).options(
            joinedload(Movement.asset),
            joinedload(Movement.origin_location),
            joinedload(Movement.destination_location),
            joinedload(Movement.origin_custodian),
            joinedload(Movement.destination_custodian)
        ).filter(Movement.movement_uuid == movement_uuid).first()

    @staticmethod
    def get_timeline_for_asset(db: Session, asset_id: int) -> List[Dict[str, Any]]:
        """
        Retorna toda a linha do tempo / histórico do equipamento,
        combinando movimentações E eventos de auditoria relacionados.
        Ordenada cronologicamente (da mais recente para a mais antiga).
        """
        # Movimentações do asset
        movements = db.query(Movement).options(
            joinedload(Movement.origin_location),
            joinedload(Movement.destination_location),
            joinedload(Movement.origin_custodian),
            joinedload(Movement.destination_custodian)
        ).filter(Movement.asset_id == asset_id).all()
        
        # Eventos de auditoria relacionados ao asset (resource = 'Asset' e resource_id = asset_id)
        audit_events = db.query(AuditLog).filter(
            AuditLog.resource == 'Asset',
            AuditLog.resource_id == asset_id
        ).order_by(AuditLog.timestamp.desc()).limit(50).all()
        
        # Combina ambos em uma lista unificada
        timeline = []
        
        # Adiciona movimentações
        for m in movements:
            timeline.append({
                'type': 'movement',
                'timestamp': m.timestamp,
                'data': m
            })
        
        # Adiciona eventos de auditoria relevantes
        for a in audit_events:
            # Evita duplicar eventos que já estão representados como movimentações:
            # - MOVIMENTACAO/MANUTENCAO: o próprio fluxo grava a movimentação equivalente;
            # - CRIACAO do bem: já contada como o movimento inicial ENTRADA_AQUISICAO.
            if a.action in [ACTION_MOVEMENT, ACTION_MAINTENANCE, ACTION_CREATE]:
                continue
            
            # Desserializa os dados anteriores/posteriores se existirem
            prev_data = None
            new_data = None
            if a.previous_data:
                try:
                    prev_data = json_lib.loads(a.previous_data)
                except (json_lib.JSONDecodeError, TypeError):
                    prev_data = None
            if a.new_data:
                try:
                    new_data = json_lib.loads(a.new_data)
                except (json_lib.JSONDecodeError, TypeError):
                    new_data = None
            
            timeline.append({
                'type': 'audit',
                'timestamp': a.timestamp,
                'data': a,
                'prev_data': prev_data,
                'new_data': new_data
            })
        
        # Ordena por timestamp (mais recente primeiro)
        timeline.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return timeline

    @staticmethod
    def get_all_movements(
        db: Session,
        filters: Optional[MovementFilter] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Movement], int]:
        query = db.query(Movement).options(
            joinedload(Movement.asset),
            joinedload(Movement.origin_location),
            joinedload(Movement.destination_location),
            joinedload(Movement.origin_custodian),
            joinedload(Movement.destination_custodian)
        )

        if filters:
            if filters.asset_id:
                query = query.filter(Movement.asset_id == filters.asset_id)
            if filters.movement_type:
                query = query.filter(Movement.movement_type == filters.movement_type)
            if filters.custodian_id:
                query = query.filter(
                    (Movement.origin_custodian_id == filters.custodian_id) |
                    (Movement.destination_custodian_id == filters.custodian_id)
                )
            if filters.location_id:
                query = query.filter(
                    (Movement.origin_location_id == filters.location_id) |
                    (Movement.destination_location_id == filters.location_id)
                )
            # Feature 004: intervalo informado em horário local (America/Recife)
            # é convertido para UTC antes de comparar com Movement.timestamp (UTC).
            # Valor com offset explícito (aware) é respeitado como instante absoluto.
            if filters.start_date:
                query = query.filter(Movement.timestamp >= local_to_utc(filters.start_date))
            if filters.end_date:
                query = query.filter(Movement.timestamp <= local_to_utc(filters.end_date))

        total = query.count()
        items = query.order_by(desc(Movement.timestamp)).offset(skip).limit(limit).all()
        return items, total

    @staticmethod
    def get_term_details(db: Session, movement_id: int) -> Optional[Dict[str, Any]]:
        """
        Estrutura todos os dados necessários para renderização e impressão
        do Termo de Entrega e Responsabilidade (Cautela) ou Devolução.
        """
        movement = MovementService.get_by_id(db, movement_id)
        if not movement:
            return None

        asset = movement.asset
        custodian = movement.destination_custodian or movement.origin_custodian

        return {
            "company": {
                "name": COMPANY_NAME,
                "cnpj": COMPANY_CNPJ,
                "address": COMPANY_ADDRESS,
            },
            "term_code": movement.term_code or f"TR-{movement.timestamp.year}-{movement.id:05d}",
            "movement_type": movement.movement_type.value,
            "date": format_local(movement.timestamp, "%d/%m/%Y às %H:%M"),
            "operator": movement.operator_name,
            "reason": movement.reason,
            "notes": movement.notes or "",
            "asset": {
                "id": asset.id,
                "tag": asset.tag,
                "name": asset.name,
                "brand": asset.brand or "N/A",
                "model": asset.model or "N/A",
                "serial_number": asset.serial_number or "N/A",
                "category": asset.category.value,
                "condition": movement.new_condition.value if movement.new_condition else asset.condition.value,
                "specifications": asset.specifications or "N/A"
            },
            "custodian": {
                "name": custodian.name if custodian else movement.destination_custodian_name or "Almoxarifado / Estoque",
                "registration_code": custodian.registration_code if custodian else "N/A",
                "role": custodian.role if custodian else "N/A",
                "department": custodian.department if custodian else "N/A",
                "email": custodian.email if custodian else "N/A",
                "cpf": custodian.cpf if custodian and custodian.cpf else "N/A"
            },
            "location": {
                "name": movement.destination_location_name or "Almoxarifado / Estoque"
            }
        }
