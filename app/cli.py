import argparse
import getpass
import os
import sys
from datetime import datetime
from typing import Callable, Optional
from app.database import SessionLocal, init_db
from app.models.user import User
from app.models.enums import AssetStatus, AssetCondition, AssetCategory, MovementType
from app.schemas.asset import AssetCreate
from app.schemas.movement import MovementCreate
from app.schemas.custodian import CustodianCreate
from app.schemas.location import LocationCreate
from app.services.asset_service import AssetService
from app.services.movement_service import MovementService
from app.services.custodian_service import CustodianService
from app.services.location_service import LocationService
from app.services.dashboard_service import DashboardService
from app.services.auth_service import create_user
from app.services.auth_service import reset_password as _reset_password
from app.services.audit_service import (
    ACTION_PASSWORD_RESET,
    RESULT_FAILURE,
    RESULT_SUCCESS,
    write_audit,
)
from app.services.ad_service import PROVIDER_AD
from app.services.permission_service import assign_role, ensure_default_roles, get_all_roles, get_role_by_name


# Mensagens do contrato do subcomando reset-password (contrato CLI, feature 002)
_MSG_SUCESSO = "Sucesso: senha redefinida para o usuário '{username}'. Sessões ativas foram invalidadas."
_MSG_INEXISTENTE = "Erro: usuário '{username}' não encontrado."
_MSG_AD = (
    "Erro: '{username}' autentica pelo Active Directory. Este comando redefine apenas "
    "a senha local do SisPatrimônio e não altera credenciais do AD."
)
_MSG_ENTRADA = "Erro: entrada de senha indisponível. Operação abortada."
_MSG_CONFEREM = "Erro: as senhas não conferem."
_MSG_GENERICA = "Erro: falha ao atualizar a senha. Tente novamente."
_MSG_AVISO_AUDITORIA = "Atenção: não foi possível registrar o evento de auditoria."


def _get_os_operator() -> Optional[str]:
    """Identifica o operador do sistema operacional (decisão D-2).

    Prioriza SUDO_USER (execução via sudo); fallback para getpass.getuser().
    Qualquer indisponibilidade retorna None sem propagar exceção — a operação
    nunca deve falhar apenas por não conseguir identificar o operador.
    """
    try:
        return os.environ.get("SUDO_USER") or getpass.getuser()
    except Exception:
        return None


def _audit_reset(
    db,
    *,
    username: str,
    result: str,
    description: str,
    resource_id: Optional[int] = None,
) -> None:
    """Grava o evento RESET_SENHA (ator nulo + snapshot do alvo — decisão D-2).

    Best-effort (plan §5.1): uma falha de auditoria NUNCA altera o resultado
    da operação — apenas emite um único aviso genérico, sem detalhes internos.
    """
    operador = _get_os_operator()
    new_data = {"origem": "CLI"}
    if operador:
        new_data["operador_so"] = operador
    try:
        write_audit(
            db,
            user=None,
            username=username,
            action=ACTION_PASSWORD_RESET,
            module="Usuários",
            resource="User",
            resource_id=resource_id,
            resource_ref=username,
            ip_address=None,
            result=result,
            description=description,
            previous_data=None,
            new_data=new_data,
        )
    except Exception:
        print(_MSG_AVISO_AUDITORIA)


def run_reset_password(
    db,
    username: str,
    password_reader: Callable[[str], str] = getpass.getpass,
) -> int:
    """Orquestrador do reset administrativo de senha (feature 002).

    Regras de negócio (política de senha, hash, invalidação de sessões,
    limpeza de lockout) permanecem EXCLUSIVAMENTE em auth_service — este
    orquestrador apenas valida o contexto, coleta a senha oculta e delega.

    Retorna 0 em sucesso e 1 em qualquer erro (plan §5.1: uma falha de
    auditoria APÓS o reset efetivado mantém o retorno 0).
    """
    username = (username or "").strip()

    # 1) Usuário inexistente — recusa antes de qualquer prompt de senha
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        _audit_reset(
            db,
            username=username,
            result=RESULT_FAILURE,
            description=f"Tentativa de redefinição de senha para usuário inexistente '{username}' (origem: CLI).",
        )
        print(_MSG_INEXISTENTE.format(username=username))
        return 1

    # 2) Usuário AD — recusa antes de qualquer prompt; nada do AD é tocado
    if user.auth_provider == PROVIDER_AD:
        _audit_reset(
            db,
            username=username,
            result=RESULT_FAILURE,
            description=f"Tentativa de redefinição de senha do usuário AD '{username}' recusada (origem: CLI).",
        )
        print(_MSG_AD.format(username=username))
        return 1

    # 3) Coleta da senha — exclusivamente por prompt oculto (decisão D-1)
    try:
        senha = password_reader("Nova senha: ")
        confirmacao = password_reader("Confirme a nova senha: ")
    except EOFError:
        _audit_reset(
            db,
            username=username,
            result=RESULT_FAILURE,
            description="Entrada de senha indisponível (EOF) — operação abortada (origem: CLI).",
        )
        print(_MSG_ENTRADA)
        return 1

    if not senha or senha != confirmacao:
        _audit_reset(
            db,
            username=username,
            result=RESULT_FAILURE,
            description="Confirmação de senha divergente ou vazia (origem: CLI).",
        )
        print(_MSG_CONFEREM)
        return 1

    # 4) Escrita da senha + sessões — EXCLUSIVAMENTE pelo service existente
    try:
        _reset_password(db, user, senha)
    except ValueError as e:
        # Política de senha: mensagem original do service (FR-006), sem segredos
        _audit_reset(
            db,
            username=username,
            result=RESULT_FAILURE,
            description=f"Política de senha não atendida (origem: CLI).",
        )
        print(f"Erro: {e}")
        return 1
    except Exception:
        # Falha de banco / erro inesperado: mensagem genérica (FR-013/FR-014)
        _audit_reset(
            db,
            username=username,
            result=RESULT_FAILURE,
            description="Falha na atualização da senha (origem: CLI).",
        )
        print(_MSG_GENERICA)
        return 1

    # 5) Reset efetivado — auditoria de sucesso (best-effort, plan §5.1)
    _audit_reset(
        db,
        username=username,
        result=RESULT_SUCCESS,
        description=f"Redefinição de senha do usuário '{username}' (sessões invalidadas) — origem: CLI",
        resource_id=user.id,
    )
    print(_MSG_SUCESSO.format(username=username))
    return 0



def main():
    init_db()
    # Garante catálogo de permissões e perfis padrão antes de qualquer comando
    db_seed = SessionLocal()
    try:
        ensure_default_roles(db_seed)
    finally:
        db_seed.close()
    parser = argparse.ArgumentParser(description="SisPatrimônio Pro - Interface de Linha de Comando (CLI)")
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponíveis")

    # Command: stats
    subparsers.add_parser("stats", help="Exibe estatísticas gerais e KPIs do patrimônio")

    # Command: list
    list_parser = subparsers.add_parser("list", help="Lista equipamentos cadastrados")
    list_parser.add_argument("--search", "-s", help="Termo de busca (tag, nome, marca)")
    list_parser.add_argument("--status", choices=[s.value for s in AssetStatus], help="Filtrar por status")

    # Command: show
    show_parser = subparsers.add_parser("show", help="Mostra detalhes e histórico de fluxo de um bem")
    show_parser.add_argument("tag", help="Tombamento / Tag do equipamento (ex: PAT-00101)")

    # Command: move
    move_parser = subparsers.add_parser("move", help="Registra uma movimentação no fluxo de um bem")
    move_parser.add_argument("tag", help="Tombamento / Tag do equipamento")
    move_parser.add_argument("--type", required=True, choices=[m.value for m in MovementType], help="Tipo de movimentação")
    move_parser.add_argument("--reason", required=True, help="Motivo / Justificativa")
    move_parser.add_argument("--custodian-id", type=int, help="ID do colaborador de destino")
    move_parser.add_argument("--location-id", type=int, help="ID do local de destino")
    move_parser.add_argument("--operator", default="CLI User", help="Nome do operador")

    # Command: create-user
    create_user_parser = subparsers.add_parser("create-user", help="Cria um usuário do sistema (login)")
    create_user_parser.add_argument("--username", required=True, help="Nome de usuário (login)")
    create_user_parser.add_argument("--password", help="Senha (mínimo 8 caracteres). Se omitida, será solicitada interativamente.")
    create_user_parser.add_argument("--name", default="", help="Nome completo do usuário")
    create_user_parser.add_argument("--email", default="", help="E-mail do usuário")
    create_user_parser.add_argument("--admin", action="store_true", help="Marca o usuário como administrador (superusuário)")
    create_user_parser.add_argument("--role", action="append", default=[], help="Perfil a atribuir (pode repetir para múltiplos perfis). Ex: --role 'Técnico de TI'")

    # Command: reset-password (feature 002 — senha NUNCA via argumento/opção)
    reset_password_parser = subparsers.add_parser(
        "reset-password",
        help="Redefine a senha de um usuário local (entrada oculta, com confirmação; não altera usuários do Active Directory)",
    )
    reset_password_parser.add_argument(
        "--username",
        required=True,
        help="Nome de usuário (login) do usuário LOCAL alvo. A senha é sempre solicitada de forma oculta, duas vezes.",
    )

    args = parser.parse_args()
    db = SessionLocal()

    try:
        if args.command == "stats":
            stats = DashboardService.get_stats(db)
            print("=" * 55)
            print("          SISPATRIMÔNIO PRO - RESUMO DO ACERVO")
            print("=" * 55)
            print(f"Total de Equipamentos: {stats['total_assets']}")
            print(f"Valor Total do Ativo:  R$ {stats['total_value']:,.2f}")
            print(f"Bens em Uso (Alocados): {stats['status_counts']['in_use']}")
            print(f"Disponíveis em Estoque: {stats['status_counts']['available']}")
            print(f"Em Manutenção:          {stats['status_counts']['in_maintenance']}")
            print(f"Total de Movimentações: {stats['total_movements']}")
            print("=" * 55)

        elif args.command == "list":
            status_enum = AssetStatus(args.status) if args.status else None
            assets, total = AssetService.get_all(db, search=args.search, status=status_enum, limit=50)
            print(f"\nEncontrados {total} equipamentos (exibindo até 50):\n")
            print(f"{'TAG':<12} | {'NOME / MODELO':<30} | {'STATUS':<15} | {'CUSTÓDIA':<20} | {'VALOR':<10}")
            print("-" * 95)
            for a in assets:
                cust_name = a.custodian.name if a.custodian else "Estoque"
                print(f"{a.tag:<12} | {a.name[:28]:<30} | {a.status.value:<15} | {cust_name[:18]:<20} | R$ {a.purchase_value:>8.2f}")

        elif args.command == "show":
            asset = AssetService.get_by_tag(db, args.tag)
            if not asset:
                print(f"Erro: Equipamento com tag '{args.tag}' não encontrado.")
                sys.exit(1)

            deprec = AssetService.calculate_depreciation(asset)
            timeline = MovementService.get_timeline_for_asset(db, asset.id)

            print("\n" + "=" * 65)
            print(f" DETALHES DO BEM: [{asset.tag}] {asset.name}")
            print("=" * 65)
            print(f"Categoria:        {asset.category.value}")
            print(f"Marca/Modelo:     {asset.brand or 'N/A'} / {asset.model or 'N/A'}")
            print(f"Número de Série:  {asset.serial_number or 'N/A'}")
            print(f"Status Atual:     {asset.status.value}")
            print(f"Condição:         {asset.condition.value}")
            print(f"Local Atual:      {asset.location.name if asset.location else 'Estoque Geral'}")
            print(f"Responsável:      {asset.custodian.name if asset.custodian else 'Livre / Estoque'}")
            print(f"Valor Aquisição:  R$ {asset.purchase_value:,.2f} (Atual: R$ {deprec['current_value']:,.2f})")
            print("-" * 65)
            print(" HISTÓRICO DE FLUXO DE MOVIMENTAÇÕES (AUDIT TRAIL):")
            print("-" * 65)
            for item in timeline:
                # A timeline é uma lista de dicts: {'type': 'movement'|'audit', 'data': ...}
                if item.get("type") != "movement":
                    continue  # eventos de auditoria genéricos não fazem parte do fluxo do CLI
                m = item["data"]
                dt = m.timestamp.strftime("%d/%m/%Y %H:%M")
                print(f"[{dt}] {m.movement_type.value}")
                print(f"  Origem:  {m.origin_location_name or '-'} ({m.origin_custodian_name or '-'})")
                print(f"  Destino: {m.destination_location_name or '-'} ({m.destination_custodian_name or '-'})")
                print(f"  Motivo:  {m.reason} (Op: {m.operator_name})")
                if m.term_code:
                    print(f"  Termo:   {m.term_code}")
                print()

        elif args.command == "move":
            asset = AssetService.get_by_tag(db, args.tag)
            if not asset:
                print(f"Erro: Equipamento com tag '{args.tag}' não encontrado.")
                sys.exit(1)

            move_data = MovementCreate(
                asset_id=asset.id,
                movement_type=MovementType(args.type),
                destination_location_id=args.location_id,
                destination_custodian_id=args.custodian_id,
                reason=args.reason,
                operator_name=args.operator
            )
            movement = MovementService.create_movement(db, move_data)
            print(f"Sucesso: Movimentação gravada! Novo status do bem: {movement.new_status.value}")
            if movement.term_code:
                print(f"Código do Termo Gerado: {movement.term_code}")

        elif args.command == "create-user":
            import getpass
            password = args.password
            if not password:
                password = getpass.getpass("Senha: ")
                confirm = getpass.getpass("Confirme a senha: ")
                if password != confirm:
                    print("Erro: as senhas não conferem.")
                    sys.exit(1)
            try:
                user = create_user(
                    db,
                    username=args.username,
                    password=password,
                    full_name=args.name or None,
                    email=args.email or None,
                    is_admin=args.admin,
                )
                # Atribui os perfis solicitados (se existirem)
                ensure_default_roles(db)
                assigned = []
                for role_name in args.role:
                    role = get_role_by_name(db, role_name)
                    if not role:
                        available = ", ".join(r.name for r in get_all_roles(db))
                        print(f"Aviso: perfil '{role_name}' não encontrado. Perfis disponíveis: {available}")
                        continue
                    assign_role(db, user, role)
                    assigned.append(role.name)
                print(f"Sucesso: usuário '{user.username}' criado!")
                if assigned:
                    print(f"Perfis atribuídos: {', '.join(assigned)}")
                elif not args.admin:
                    print("Atenção: nenhum perfil atribuído. O usuário não terá acesso a módulos até receber um perfil.")
            except ValueError as e:
                print(f"Erro: {e}")
                sys.exit(1)

        elif args.command == "reset-password":
            sys.exit(run_reset_password(db, args.username))

        else:
            parser.print_help()

    finally:
        db.close()


if __name__ == "__main__":
    main()
