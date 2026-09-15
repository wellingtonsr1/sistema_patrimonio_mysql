"""
Testes da funcionalidade CLI: reset administrativo de senha (feature 002).

Cobre o orquestrador `run_reset_password` de `app/cli.py` — a regra de
negócio (política, hash, invalidação de sessões) permanece em
`app/services/auth_service.py` e não é duplicada aqui.

Entrada de senha injetada via `password_reader` (getpass no uso real),
seguindo o design testável do plan §2d.
"""

import json
from datetime import datetime, timedelta

from app.cli import run_reset_password
from app.models.audit_log import AuditLog
from app.models.session import UserSession
from app.models.user import User
from app.services.auth_service import (
    create_user,
    verify_password,
)
from app.services.audit_service import (
    ACTION_PASSWORD_RESET,
    RESULT_FAILURE,
    RESULT_SUCCESS,
)
from app.services.permission_service import (
    assign_role,
    ensure_default_roles,
    get_role_by_name,
)

# Senha segura para os testes (>= 8 caracteres — política do auth_service)
SENHA_ANTIGA = "senha@antiga"
SENHA_NOVA = "nova@senha9"


def _mk_user(db, username="resetusr", password=SENHA_ANTIGA, **kwargs):
    """Cria um usuário local de teste (padrão create_user do auth_service)."""
    user = create_user(
        db,
        username=username,
        password=password,
        full_name=kwargs.pop("full_name", "Usuário de Reset"),
        email=kwargs.pop("email", "resetusr@test.local"),
        **kwargs,
    )
    return user


def _sessoes(db, user_id):
    return db.query(UserSession).filter(UserSession.user_id == user_id).all()


def _auditoria_reset(db):
    return (
        db.query(AuditLog)
        .filter(AuditLog.action == ACTION_PASSWORD_RESET)
        .all()
    )


def _reader(seq):
    """Leitor de senha injetado que devolve os valores de `seq` em ordem."""
    valores = list(seq)
    chamadas = {"n": 0}

    def _ler(prompt=""):
        n = chamadas["n"]
        chamadas["n"] += 1
        return valores[n]

    return _ler


def _snapshot_alvo(user):
    """Campos do alvo que devem permanecer idênticos após qualquer erro."""
    return {
        "password_hash": user.password_hash,
        "is_active": user.is_active,
        "auth_provider": user.auth_provider,
        "full_name": user.full_name,
        "email": user.email,
        "is_admin": user.is_admin,
        "failed_login_attempts": user.failed_login_attempts,
        "locked_until": user.locked_until,
    }


# ============================================
# US1 — RESET BEM-SUCEDIDO DE USUÁRIO LOCAL
# ============================================

def test_us1_reset_sucesso_retorna_zero_e_troca_o_hash(db_session, capsys):
    _mk_user(db_session)

    rc = run_reset_password(
        db_session, "resetusr", password_reader=_reader([SENHA_NOVA, SENHA_NOVA])
    )

    assert rc == 0
    user = db_session.query(User).filter(User.username == "resetusr").first()
    assert verify_password(SENHA_NOVA, user.password_hash)
    assert not verify_password(SENHA_ANTIGA, user.password_hash)

    saida = capsys.readouterr().out
    assert "Sucesso: senha redefinida para o usuário 'resetusr'." in saida
    assert "Sessões ativas foram invalidadas." in saida
    # A senha nunca aparece na saída
    assert SENHA_NOVA not in saida


def test_us1_invalida_as_sessoes_do_alvo(db_session):
    user = _mk_user(db_session)
    db_session.add(
        UserSession(
            token_hash="a" * 64,
            user_id=user.id,
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
    )
    db_session.add(
        UserSession(
            token_hash="b" * 64,
            user_id=user.id,
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
    )
    db_session.commit()
    assert len(_sessoes(db_session, user.id)) == 2

    rc = run_reset_password(
        db_session, "resetusr", password_reader=_reader([SENHA_NOVA, SENHA_NOVA])
    )

    assert rc == 0
    db_session.expire_all()
    assert len(_sessoes(db_session, user.id)) == 0


def test_us1_preserva_perfis_e_demais_atributos(db_session):
    ensure_default_roles(db_session)
    user = _mk_user(db_session)
    consulta = get_role_by_name(db_session, "Consulta")
    assign_role(db_session, user, consulta)
    ids_antes = sorted(ur.role_id for ur in user.user_roles)

    rc = run_reset_password(
        db_session, "resetusr", password_reader=_reader([SENHA_NOVA, SENHA_NOVA])
    )

    assert rc == 0
    db_session.expire_all()
    user = db_session.query(User).filter(User.username == "resetusr").first()
    assert sorted(ur.role_id for ur in user.user_roles) == ids_antes
    assert user.is_active is True
    assert user.full_name == "Usuário de Reset"
    assert user.email == "resetusr@test.local"
    assert user.auth_provider == "local"
    assert user.is_admin is False


def test_us1_usuario_inativo_permite_reset_sem_reativar(db_session):
    """D-3: reset permitido para inativo, sem reativar a conta."""
    user = _mk_user(db_session)
    user.is_active = False
    db_session.commit()

    rc = run_reset_password(
        db_session, "resetusr", password_reader=_reader([SENHA_NOVA, SENHA_NOVA])
    )

    assert rc == 0
    db_session.expire_all()
    user = db_session.query(User).filter(User.username == "resetusr").first()
    assert user.is_active is False
    assert verify_password(SENHA_NOVA, user.password_hash)


def test_us1_limpa_lockout_do_usuario(db_session):
    user = _mk_user(db_session)
    user.failed_login_attempts = 3
    user.locked_until = datetime.utcnow() + timedelta(minutes=30)
    db_session.commit()

    rc = run_reset_password(
        db_session, "resetusr", password_reader=_reader([SENHA_NOVA, SENHA_NOVA])
    )

    assert rc == 0
    db_session.expire_all()
    user = db_session.query(User).filter(User.username == "resetusr").first()
    assert user.failed_login_attempts == 0
    assert user.locked_until is None


def test_us1_registra_um_evento_de_auditoria_de_sucesso(db_session):
    user = _mk_user(db_session)

    rc = run_reset_password(
        db_session, "resetusr", password_reader=_reader([SENHA_NOVA, SENHA_NOVA])
    )

    assert rc == 0
    registros = _auditoria_reset(db_session)
    assert len(registros) == 1
    reg = registros[0]
    assert reg.result == RESULT_SUCCESS
    # Ator nulo (decisão D-2) com snapshot do username do alvo
    assert reg.user_id is None
    assert reg.username == "resetusr"
    assert reg.resource_id == user.id
    assert reg.resource_ref == "resetusr"
    assert "CLI" in reg.description
    # Origem CLI gravada em new_data; nenhum segredo em nenhum campo
    dados = json.loads(reg.new_data)
    assert dados.get("origem") == "CLI"
    assert SENHA_NOVA not in (reg.description or "")
    assert SENHA_NOVA not in (reg.new_data or "")
    assert SENHA_NOVA not in (reg.previous_data or "")


# ============================================
# US2 — TODO ERRO FALHA DE FORMA SEGURA
# ============================================

def test_us2_usuario_inexistente_retorna_1_sem_prompt(db_session, capsys):
    rc = run_reset_password(db_session, "fantasma", password_reader=_reader(["x", "x"]))

    assert rc == 1
    saida = capsys.readouterr().out
    assert "Erro: usuário 'fantasma' não encontrado." in saida
    # Nenhum usuário criado e nenhuma auditoria de sucesso
    assert db_session.query(User).filter(User.username == "fantasma").first() is None
    registros = _auditoria_reset(db_session)
    assert len(registros) == 1
    assert registros[0].result == RESULT_FAILURE


def test_us2_usuario_ad_recusado_antes_de_qualquer_prompt(db_session, capsys):
    """FR-003: recusa do usuário AD ocorre antes de qualquer prompt de senha."""
    user = _mk_user(db_session)
    user.auth_provider = "ad"
    user.password_hash = "!ad-external"  # sentinela real do ad_service
    db_session.commit()
    snapshot = _snapshot_alvo(user)

    # Se algum prompt fosse chamado, o teste falha (leitor limitado a 0 valores)
    leitor_que_nao_deve_ser_chamado = _reader([])
    rc = run_reset_password(
        db_session, "resetusr", password_reader=leitor_que_nao_deve_ser_chamado
    )

    assert rc == 1
    saida = capsys.readouterr().out
    assert "senha local" in saida
    assert "Active Directory" in saida
    db_session.expire_all()
    user = db_session.query(User).filter(User.username == "resetusr").first()
    assert _snapshot_alvo(user) == snapshot  # sentinela intacta
    registros = _auditoria_reset(db_session)
    assert len(registros) == 1
    assert registros[0].result == RESULT_FAILURE


def test_us2_senha_curta_mensagem_do_service_e_hash_intacto(db_session, capsys):
    _mk_user(db_session)
    antes = (
        db_session.query(User)
        .filter(User.username == "resetusr")
        .first()
        .password_hash
    )

    rc = run_reset_password(
        db_session, "resetusr", password_reader=_reader(["curta7", "curta7"])
    )

    assert rc == 1
    saida = capsys.readouterr().out
    assert "A nova senha deve ter no mínimo 8 caracteres." in saida
    db_session.expire_all()
    user = db_session.query(User).filter(User.username == "resetusr").first()
    assert user.password_hash == antes  # hash antigo ainda válido
    assert verify_password(SENHA_ANTIGA, user.password_hash)
    registros = _auditoria_reset(db_session)
    assert len(registros) == 1
    assert registros[0].result == RESULT_FAILURE


def test_us2_confirmacao_divergente_nada_alterado(db_session, capsys):
    _mk_user(db_session)
    antes = (
        db_session.query(User)
        .filter(User.username == "resetusr")
        .first()
        .password_hash
    )

    rc = run_reset_password(
        db_session, "resetusr", password_reader=_reader([SENHA_NOVA, "outra@senha9"])
    )

    assert rc == 1
    saida = capsys.readouterr().out
    assert "as senhas não conferem" in saida
    db_session.expire_all()
    user = db_session.query(User).filter(User.username == "resetusr").first()
    assert user.password_hash == antes
    registros = _auditoria_reset(db_session)
    assert len(registros) == 1
    assert registros[0].result == RESULT_FAILURE


def test_us2_eof_no_prompt_aborta_sem_alterar(db_session, capsys):
    _mk_user(db_session)
    antes = (
        db_session.query(User)
        .filter(User.username == "resetusr")
        .first()
        .password_hash
    )

    def leitor_eof(prompt=""):
        raise EOFError

    rc = run_reset_password(db_session, "resetusr", password_reader=leitor_eof)

    assert rc == 1
    saida = capsys.readouterr().out
    assert "entrada de senha indisponível" in saida
    db_session.expire_all()
    user = db_session.query(User).filter(User.username == "resetusr").first()
    assert user.password_hash == antes
    registros = _auditoria_reset(db_session)
    assert len(registros) == 1
    assert registros[0].result == RESULT_FAILURE


def test_us2_erro_inesperado_no_service_mensagem_generica(db_session, capsys, monkeypatch):
    """FR-013/FR-014: exceção interna NÃO vaza para o operador."""
    _mk_user(db_session)

    def explodir(db, user, senha):
        raise RuntimeError("pvkb2 internal overflow at 0xDEADBEEF")

    monkeypatch.setattr("app.cli._reset_password", explodir)

    rc = run_reset_password(
        db_session, "resetusr", password_reader=_reader([SENHA_NOVA, SENHA_NOVA])
    )

    assert rc == 1
    saida = capsys.readouterr().out
    assert "Erro: falha ao atualizar a senha. Tente novamente." in saida
    assert "0xDEADBEEF" not in saida  # detalhes internos não vazam
    registros = _auditoria_reset(db_session)
    assert len(registros) == 1
    assert registros[0].result == RESULT_FAILURE
    assert "0xDEADBEEF" not in (registros[0].description or "")


# ============================================
# US3 — AUDITORIA COMPLETA SEM SEGREDOS
# ============================================

def test_us3_registra_sudo_user_como_operador_do_so(db_session, monkeypatch):
    """D-2: SUDO_USER tem prioridade e vai para new_data do registro."""
    _mk_user(db_session)
    monkeypatch.setenv("SUDO_USER", "op_sudo")

    rc = run_reset_password(
        db_session, "resetusr", password_reader=_reader([SENHA_NOVA, SENHA_NOVA])
    )

    assert rc == 0
    reg = _auditoria_reset(db_session)[0]
    dados = json.loads(reg.new_data)
    assert dados["origem"] == "CLI"
    assert dados["operador_so"] == "op_sudo"


def test_us3_fallback_getpass_getuser_quando_sem_sudo(db_session, monkeypatch):
    """D-2: sem SUDO_USER, o fallback é getpass.getuser()."""
    _mk_user(db_session)
    monkeypatch.delenv("SUDO_USER", raising=False)
    monkeypatch.setattr("app.cli.getpass.getuser", lambda: "op_fallback")

    rc = run_reset_password(
        db_session, "resetusr", password_reader=_reader([SENHA_NOVA, SENHA_NOVA])
    )

    assert rc == 0
    reg = _auditoria_reset(db_session)[0]
    dados = json.loads(reg.new_data)
    assert dados["operador_so"] == "op_fallback"


def test_us3_operador_indisponivel_nao_falha_a_operacao(db_session, capsys, monkeypatch):
    """D-2/cenário 4 da US3: sem identidade do SO, o campo é omitido e o
    comando NÃO falha por isso."""
    _mk_user(db_session)
    monkeypatch.delenv("SUDO_USER", raising=False)

    def sem_identidade():
        raise OSError("não foi possível determinar o usuário")

    monkeypatch.setattr("app.cli.getpass.getuser", sem_identidade)

    rc = run_reset_password(
        db_session, "resetusr", password_reader=_reader([SENHA_NOVA, SENHA_NOVA])
    )

    assert rc == 0
    saida = capsys.readouterr().out
    assert "Sucesso: senha redefinida" in saida
    reg = _auditoria_reset(db_session)[0]
    dados = json.loads(reg.new_data)
    assert dados == {"origem": "CLI"}  # apenas origem; sem operador


def test_us3_auditoria_falha_apos_reset_mantem_retorno_zero(db_session, capsys, monkeypatch):
    """Plan §5.1: write_audit falhando APÓS o reset efetivado → retorno 0,
    aviso único, senha nova vigente e sessões invalidadas."""
    user = _mk_user(db_session)
    db_session.add(
        UserSession(
            token_hash="c" * 64,
            user_id=user.id,
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
    )
    db_session.commit()

    def auditoria_quebrada(*args, **kwargs):
        raise RuntimeError("disco cheio no write_audit")

    monkeypatch.setattr("app.cli.write_audit", auditoria_quebrada)

    rc = run_reset_password(
        db_session, "resetusr", password_reader=_reader([SENHA_NOVA, SENHA_NOVA])
    )

    assert rc == 0
    saida = capsys.readouterr().out
    assert "Atenção: não foi possível registrar o evento de auditoria." in saida
    assert saida.count("Atenção:") == 1  # aviso único, sem detalhes internos
    assert "disco cheio" not in saida
    db_session.expire_all()
    user = db_session.query(User).filter(User.username == "resetusr").first()
    assert verify_password(SENHA_NOVA, user.password_hash)  # senha permanece alterada
    assert len(_sessoes(db_session, user.id)) == 0  # sessões permanecem invalidadas


def test_us3_auditoria_falha_em_caminho_de_erro_mantem_mensagem_original(db_session, capsys, monkeypatch):
    """Plan §5.1: falha de auditoria em caminho de erro → retorno 1 e a
    mensagem original do erro é preservada."""
    user = _mk_user(db_session)
    user.auth_provider = "ad"
    user.password_hash = "!ad-external"
    db_session.commit()

    def auditoria_quebrada(*args, **kwargs):
        raise RuntimeError("x")

    monkeypatch.setattr("app.cli.write_audit", auditoria_quebrada)

    rc = run_reset_password(db_session, "resetusr", password_reader=_reader([]))

    assert rc == 1
    saida = capsys.readouterr().out
    assert "Active Directory" in saida  # mensagem original preservada
    assert "Atenção:" in saida  # aviso de auditoria também emitido
    db_session.expire_all()
    user = db_session.query(User).filter(User.username == "resetusr").first()
    assert user.password_hash == "!ad-external"  # nada alterado


def test_us3_nenhum_segredo_em_nenhum_registro_de_auditoria(db_session, monkeypatch):
    """FR-012: varredura de segredos em TODOS os registros da suíte."""
    # Sucesso
    _mk_user(db_session, username="usr_ok")
    run_reset_password(
        db_session, "usr_ok", password_reader=_reader([SENHA_NOVA, SENHA_NOVA])
    )
    # Erro de política (senha curta no prompt)
    run_reset_password(
        db_session, "usr_ok", password_reader=_reader(["curta7", "curta7"])
    )
    # Erro de confirmação
    run_reset_password(
        db_session, "usr_ok", password_reader=_reader(["outra@senha11", "diverge@11"])
    )
    # Usuário inexistente
    run_reset_password(db_session, "nada", password_reader=_reader(["x", "x"]))

    registros = _auditoria_reset(db_session)
    assert len(registros) == 4
    for reg in registros:
        for campo in (reg.description, reg.new_data, reg.previous_data):
            texto = campo or ""
            assert SENHA_NOVA not in texto
            assert "outra@senha11" not in texto
            assert "diverge@11" not in texto
            assert "curta7" not in texto
