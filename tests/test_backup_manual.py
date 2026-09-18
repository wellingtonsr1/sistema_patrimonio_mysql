"""Backup Manual do SisPatrimônio Pro (features 015 e 016).

Cobertura 015 (spec FR-012, quickstart §2):
  1. Geração (executor fake) → arquivo em data/backups/ + auditoria SUCCESS
  2. Falha de geração → auditoria FAILURE, nenhum artefato listado
  3. Listagem → ordenada desc, artefatos alheios ignorados
  4. Download → bytes íntegros + evento BACKUP_DOWNLOAD
  5. Download inexistente/fora do padrão → 404 sem tocar disco
  6. RBAC → 403 sem permissão nas 3 rotas; admin → 200
  7. Menu → item "Backups" apenas com can('backup.gerenciar')

Cobertura 016 (quickstart §2 — testes A–J): geração atômica `.part` →
`.sql.gz` comprimido com SHA-256, log técnico sem segredos, falha literal
BACKUP_FALHA (Teste G), múltiplos via web (Teste H), integridade (Teste I),
listagem v2 com Integridade/SHA-256, compatibilidade `.sql` antigos.

O executor de dump é sempre FAKE na suíte (SQLite não roda mysqldump —
research R4); o dump real é validado manualmente (quickstart §3).
"""

import json
import re
from datetime import datetime, timedelta

import pytest

from app.services.audit_service import get_audit_logs
from app.services.backup_service import BackupService
from app.services.permission_service import (
    ensure_default_roles,
    get_role_by_name,
    get_role_permission_names,
)
from tests.test_rbac import PASSWORD, _login, _make_user

# Padrão estrito do nome (data-model §1; remediação I1: timestamp UTC).
# 016: aceita `.sql` (015, compatibilidade BV-10) e `.sql.gz` (016).
_BACKUP_NAME_RE = re.compile(r"^backup_\d{8}_\d{6}_\d{6}\.sql(\.gz)?$")

# Temporários da 016 — NUNCA casam o padrão final (data-model BV-8)
_PART_BACKUP_RE = re.compile(r"^backup_\d{8}_\d{6}_\d{6}\.part(\.gz)?$")

FAKE_DUMP_CONTENT = b"-- SisPatrimonio Pro fake dump\nSET autocommit=0;\n"


# ============================================================================
# HELPERS
# ============================================================================

def _fake_dump(path):
    """Executor fake: grava conteúdo determinístico no caminho recebido (R4)."""
    with open(path, "wb") as f:
        f.write(FAKE_DUMP_CONTENT)


def _failing_dump(path):
    """Executor fake que falha como um mysqldump com erro (exit != 0)."""
    raise RuntimeError("dump falhou (simulado)")


def _cleanup_backups():
    """Remove os backups e temporários gerados pelos testes (016: `.part*` também)
    e os artefatos de teste fora do padrão (ex.: nao-e-backup.txt do teste de
    listagem), preservando backups legítimos."""
    from app.config import BACKUP_DIR

    if BACKUP_DIR.exists():
        for p in BACKUP_DIR.iterdir():
            if (
                _BACKUP_NAME_RE.match(p.name)
                or _PART_BACKUP_RE.match(p.name)
                or p.name == "nao-e-backup.txt"
            ):
                if p.is_file():
                    p.unlink()


@pytest.fixture(autouse=True)
def _clean_backup_dir():
    _cleanup_backups()
    yield
    _cleanup_backups()


def _audit_entries(db, action):
    return [log for log in get_audit_logs(db) if log.action == action]


def _new_data(log):
    """AuditLog.new_data é Text com JSON serializado (app/models/audit_log.py) — desserializa."""
    return json.loads(log.new_data) if log.new_data else {}


# ============================================================================
# FOUNDATIONAL — permissão/seed (T003) e núcleo do service (T004)
# ============================================================================

def test_seed_cria_permissao_backup_gerenciar(db_session):
    ensure_default_roles(db_session)
    from app.models.permission import Permission

    perm = (
        db_session.query(Permission)
        .filter(Permission.name == "backup.gerenciar")
        .first()
    )
    assert perm is not None
    assert perm.module == "Backup"

    admin = get_role_by_name(db_session, "Administrador")
    assert "backup.gerenciar" in get_role_permission_names(db_session, admin)


def test_seed_idempotente_nao_duplica(db_session):
    ensure_default_roles(db_session)
    ensure_default_roles(db_session)
    from app.models.permission import Permission

    perms = (
        db_session.query(Permission)
        .filter(Permission.name == "backup.gerenciar")
        .all()
    )
    assert len(perms) == 1


def test_list_backups_diretorio_vazio_ou_inexistente(db_session):
    assert BackupService.list_backups() == []


def test_list_backups_ignora_arquivos_fora_do_padrao(db_session):
    from app.config import BACKUP_DIR

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    (BACKUP_DIR / "nao-e-backup.txt").write_bytes(b"x")
    (BACKUP_DIR / "backup_20260917_120000_000123.sql").write_bytes(b"ok")
    # 016: temporários em voo nunca são listáveis (BV-8; US2b — remediação C1)
    (BACKUP_DIR / "backup_20260917_120000_000124.part").write_bytes(b"dump parcial")
    (BACKUP_DIR / "backup_20260917_120000_000125.part.gz").write_bytes(b"gz parcial")

    backups = BackupService.list_backups()

    names = [b["filename"] for b in backups]
    assert names == ["backup_20260917_120000_000123.sql"]
    assert not any(".part" in n for n in names)


def test_list_backups_ordenado_mais_recente_primeiro(db_session):
    from app.config import BACKUP_DIR

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    antigo = BACKUP_DIR / "backup_20260917_100000_000001.sql"
    novo = BACKUP_DIR / "backup_20260917_120000_000002.sql"
    antigo.write_bytes(b"a" * 10)
    novo.write_bytes(b"b" * 20)

    backups = BackupService.list_backups()

    assert [b["filename"] for b in backups] == [novo.name, antigo.name]
    assert backups[0]["size_bytes"] == 20
    assert isinstance(backups[0]["timestamp"], datetime)


# ============================================================================
# 016 — US3 (T013): listagem v2 — campos sha256 e integrity (contract §3)
# ============================================================================

def _gz_bytes(payload: bytes) -> bytes:
    import gzip as gzip_mod
    import io as io_mod

    buf = io_mod.BytesIO()
    with gzip_mod.GzipFile(fileobj=buf, mode="wb") as gz:
        gz.write(payload)
    return buf.getvalue()


def test_listagem_v2_campos_sha256_e_integridade(db_session):
    """.sql.gz válido → integrity OK + sha256 do arquivo; .sql antigo → — + None."""
    import hashlib as hashlib_mod

    from app.config import BACKUP_DIR

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    gz_name = "backup_20260917_120000_000002.sql.gz"
    gz_payload = _gz_bytes(FAKE_DUMP_CONTENT)
    (BACKUP_DIR / gz_name).write_bytes(gz_payload)
    (BACKUP_DIR / "backup_20260917_100000_000001.sql").write_bytes(b"legado")

    backups = BackupService.list_backups()

    by_name = {b["filename"]: b for b in backups}
    novo = by_name[gz_name]
    antigo = by_name["backup_20260917_100000_000001.sql"]

    # Gzip válido: OK + hash correto (== sha256 dos bytes em disco)
    assert novo["integrity"] == "OK"
    assert novo["sha256"] == hashlib_mod.sha256(gz_payload).hexdigest()

    # .sql antigo: sem checksum, marcador neutro (BV-10)
    assert antigo["sha256"] is None
    assert antigo["integrity"] == "—"


def test_listagem_v2_gzip_corrompido_marcado(db_session):
    """gzip com bytes do meio removidos → integrity CORROMPIDO (não lança)."""
    from app.config import BACKUP_DIR

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    name = "backup_20260917_120000_000003.sql.gz"
    data = bytearray(_gz_bytes(FAKE_DUMP_CONTENT * 20))  # payload maior
    del data[30:-8]  # corrompe o fluxo deflate (magic/trailer preservados)
    (BACKUP_DIR / name).write_bytes(bytes(data))

    backups = BackupService.list_backups()

    assert len(backups) == 1
    entry = backups[0]
    assert entry["integrity"] == "CORROMPIDO"
    assert entry["sha256"] is None


def test_template_renderiza_colunas_integridade_e_sha256(client, db_session):
    """ui-contract §1: colunas Integridade/SHA-256 com badge OK e hash truncado."""
    import hashlib as hashlib_mod

    from app.config import BACKUP_DIR

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    name = "backup_20260917_120000_000004.sql.gz"
    payload = _gz_bytes(FAKE_DUMP_CONTENT)
    (BACKUP_DIR / name).write_bytes(payload)

    resp = client.get("/admin/backups")

    assert resp.status_code == 200
    body = resp.text
    assert "Integridade" in body and "SHA-256" in body
    assert "OK" in body
    full_hash = hashlib_mod.sha256(payload).hexdigest()
    assert full_hash[:12] in body  # truncado na célula
    assert full_hash in body or full_hash[:12] in body  # title completo ou truncado


def test_get_backup_path_valido_aponta_para_data_backups(db_session):
    from app.config import BACKUP_DIR

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    name = "backup_20260917_120000_000123.sql"
    (BACKUP_DIR / name).write_bytes(b"ok")

    path = BackupService.get_backup_path(name)

    assert path.parent == BACKUP_DIR
    assert path.name == name


def test_get_backup_path_rejeita_nome_fora_do_padrao(db_session):
    with pytest.raises(Exception):
        BackupService.get_backup_path("../../etc/passwd")


def test_get_backup_path_rejeita_inexistente(db_session):
    with pytest.raises(Exception):
        BackupService.get_backup_path("backup_20260917_120000_000999.sql")


# ============================================================================
# FOUNDATIONAL 016 (T002) — compatibilidade `.sql`/`.sql.gz` + temporários
# Cobertura extra da US2b (segurança de acesso/download — remediação C1)
# ============================================================================

def test_get_backup_path_aceita_sql_gz_compatibilidade(db_session):
    """BV-10: o formato v2 (.sql.gz) é servido pelo download como o .sql antigo."""
    from app.config import BACKUP_DIR

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    name = "backup_20260917_120000_000456.sql.gz"
    (BACKUP_DIR / name).write_bytes(b"\x1f\x8b\x08")  # magic gzip

    path = BackupService.get_backup_path(name)

    assert path.parent == BACKUP_DIR
    assert path.name == name


def test_get_backup_path_rejeita_part_e_part_gz(db_session):
    """Temporários da 016 nunca são baixáveis (research R8; US2b)."""
    from app.config import BACKUP_DIR

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    (BACKUP_DIR / "backup_20260917_120000_000700.part").write_bytes(b"x")
    (BACKUP_DIR / "backup_20260917_120000_000701.part.gz").write_bytes(b"x")

    with pytest.raises(FileNotFoundError):
        BackupService.get_backup_path("backup_20260917_120000_000700.part")
    with pytest.raises(FileNotFoundError):
        BackupService.get_backup_path("backup_20260917_120000_000701.part.gz")


# ============================================================================
# US1 — geração (T010) e rota web (T011)
# ============================================================================

def test_geracao_sucesso_cria_arquivo_e_audita(db_session):
    from app.services.audit_service import ACTION_BACKUP_CREATED, RESULT_SUCCESS

    user = _make_user(db_session, "bkpadmin", role_names=["Administrador"])

    result = BackupService.generate_backup(
        db_session, user, "127.0.0.1", dump_executor=_fake_dump
    )

    # Retorno com os 4 campos (016: sha256 aditivo — contract §7, Teste A adaptado)
    assert set(result.keys()) == {"filename", "timestamp", "size_bytes", "sha256"}
    assert _BACKUP_NAME_RE.match(result["filename"])
    assert result["size_bytes"] > 0  # 016: tamanho é o do gzip (comprimido)

    # Auditoria SUCCESS com new_data sem credenciais
    events = _audit_entries(db_session, ACTION_BACKUP_CREATED)
    assert len(events) == 1
    ev = events[0]
    assert ev.result == RESULT_SUCCESS
    nd = _new_data(ev)
    assert nd["arquivo"] == result["filename"]
    assert nd["tamanho_bytes"] == result["size_bytes"]
    assert nd["sha256"] == result["sha256"]


def test_geracao_falha_audita_failure_e_nao_deixa_artefato(db_session):
    """016 (contract §7, Teste G adaptado): falha literal BACKUP_FALHA."""
    from app.services.audit_service import ACTION_BACKUP_FAILED, RESULT_FAILURE

    user = _make_user(db_session, "bkpadmin2", role_names=["Administrador"])

    with pytest.raises(Exception):
        BackupService.generate_backup(
            db_session, user, "127.0.0.1", dump_executor=_failing_dump
        )

    events = _audit_entries(db_session, ACTION_BACKUP_FAILED)
    assert len(events) == 1
    assert events[0].result == RESULT_FAILURE
    # Sem comando/credenciais na descrição (Princípio VI)
    desc = (events[0].description or "")
    assert "mysqldump" not in desc and "PASSWORD" not in desc

    assert BackupService.list_backups() == []


def test_geracoes_repetidas_nomes_distintos(db_session):
    user = _make_user(db_session, "bkpadmin3", role_names=["Administrador"])

    r1 = BackupService.generate_backup(
        db_session, user, "127.0.0.1", dump_executor=_fake_dump
    )
    r2 = BackupService.generate_backup(
        db_session, user, "127.0.0.1", dump_executor=_fake_dump
    )

    assert r1["filename"] != r2["filename"]
    assert len(BackupService.list_backups()) == 2


# ============================================================================
# 016 — US1 (T006): geração atômica v2 — gzip + SHA-256 + .part → renomear
# ============================================================================

def test_geracao_v2_produz_gz_com_sha256(db_session):
    """(a) Sucesso: gzip legível, nome .sql.gz, sha256 == recomputado (Teste I)."""
    import gzip as gzip_mod
    import hashlib

    from app.services.audit_service import ACTION_BACKUP_CREATED, RESULT_SUCCESS

    user = _make_user(db_session, "bkpadminv2", role_names=["Administrador"])

    result = BackupService.generate_backup(
        db_session, user, "127.0.0.1", dump_executor=_fake_dump
    )

    # Nome no padrão v2 (regex do módulo aceita ambos — filename termina .gz)
    assert result["filename"].endswith(".sql.gz")

    from app.config import BACKUP_DIR

    final_path = BACKUP_DIR / result["filename"]
    assert final_path.is_file()

    # Gzip legível e conteúdo íntegro (blocos verificáveis)
    with gzip_mod.open(final_path, "rb") as gz:
        assert gz.read() == FAKE_DUMP_CONTENT

    # SHA-256 retornado == recomputado do arquivo (Teste I)
    h = hashlib.sha256(final_path.read_bytes()).hexdigest()
    assert result["sha256"] == h

    # Retorno com os 4 campos v2
    assert set(result.keys()) == {"filename", "timestamp", "size_bytes", "sha256"}

    # Auditoria SUCCESS com new_data incluindo sha256
    events = _audit_entries(db_session, ACTION_BACKUP_CREATED)
    assert len(events) == 1
    assert events[0].result == RESULT_SUCCESS
    nd = _new_data(events[0])
    assert nd["arquivo"] == result["filename"]
    assert nd["tamanho_bytes"] == result["size_bytes"]
    assert nd["sha256"] == h


def test_geracao_v2_gzip_sem_fname_part(db_session):
    """O cabeçalho gzip NÃO embute o nome do temporário (FNAME): ao extrair o
    .sql.gz com ferramentas externas (7-Zip/gunzip -N), o arquivo resultante
    é `backup_....sql` — não `backup_....part` (fix do cabeçalho FNAME)."""
    import gzip as gzip_mod

    from app.config import BACKUP_DIR

    user = _make_user(db_session, "bkpfname", role_names=["Administrador"])
    result = BackupService.generate_backup(
        db_session, user, "127.0.0.1", dump_executor=_fake_dump
    )

    raw = (BACKUP_DIR / result["filename"]).read_bytes()
    # FLG (byte 3): bit FNAME = 0x08 não pode estar setado
    assert not raw[3] & 0x08, f"gzip embute FNAME: {raw[:20]!r}"

    # Extração externa equivalente: gunzip -N restaura o nome SEM o FNAME,
    # i.e. o nome base do arquivo .gz sem o sufixo .gz
    base = result["filename"][:-3]  # remove ".gz"
    assert base.endswith(".sql")


def test_geracao_v2_atomicidade_part_invisivel(db_session):
    """(b) Atomicidade (Teste G parcial; remediação U1): o executor fake captura
    o estado do diretório DENTRO do callback — durante a geração nada casa o
    regex final; ao final nenhum .part existe e só o .sql.gz está listado."""
    import gzip as gzip_mod

    from app.config import BACKUP_DIR

    captured = {}

    def _observing_dump(path):
        _fake_dump(path)
        # Estado do diretório no meio da geração (remediação U1) —
        # apenas arquivos no padrão de backup/temporário (alheios são ignorados)
        captured["during"] = [
            p.name
            for p in BACKUP_DIR.iterdir()
            if _BACKUP_NAME_RE.match(p.name) or _PART_BACKUP_RE.match(p.name)
        ]

    user = _make_user(db_session, "bkpatomic", role_names=["Administrador"])
    result = BackupService.generate_backup(
        db_session, user, "127.0.0.1", dump_executor=_observing_dump
    )

    during = captured["during"]
    # Durante: apenas o temporário .part (nada casa o regex final)
    assert len(during) == 1
    assert during[0].endswith(".part")
    assert _BACKUP_NAME_RE.match(during[0]) is None

    # Ao final: nenhum .part*; só o final listado
    leftovers = [p.name for p in BACKUP_DIR.iterdir() if p.name.endswith(".part") or p.name.endswith(".part.gz")]
    assert leftovers == []
    names = [b["filename"] for b in BackupService.list_backups()]
    assert names == [result["filename"]]

    # Gzip final legível (nasceu completo — nunca parcial listável)
    with gzip_mod.open(BACKUP_DIR / result["filename"], "rb") as gz:
        gz.read()


def test_geracao_v2_log_tecnico_sem_segredos(db_session, caplog):
    """(d) Log técnico (research R6): início/conclusão presentes; sem segredos."""
    import logging

    user = _make_user(db_session, "bkplog", role_names=["Administrador"])

    with caplog.at_level(logging.INFO, logger="app.services.backup_service"):
        BackupService.generate_backup(
            db_session, user, "127.0.0.1", dump_executor=_fake_dump
        )

    messages = [r.getMessage() for r in caplog.records]
    joined = " ".join(messages)
    assert any("Início" in m for m in messages)
    assert any("concluído" in m for m in messages)
    assert "MYSQL_PWD" not in joined
    assert "password" not in joined.lower() or "sem senha" in joined.lower()
    # Comando mysqldump completo nunca aparece no log
    assert "--user=" not in joined


def test_rota_gerar_com_admin_cria_e_audita(client, db_session, monkeypatch):
    from app.services import backup_service

    monkeypatch.setattr(backup_service, "_run_mysqldump", _fake_dump)

    resp = client.post("/admin/backups/gerar", follow_redirects=False)

    assert resp.status_code == 303
    assert resp.headers["location"].startswith("/admin/backups")
    assert len(BackupService.list_backups()) == 1


def test_rota_gerar_sem_permissao_negada(client, db_session):
    _make_user(db_session, "semperm", role_names=["Consulta"])
    _login(client, "semperm")

    resp = client.post("/admin/backups/gerar", follow_redirects=False)

    assert resp.status_code == 403
    assert BackupService.list_backups() == []


# ============================================================================
# US2 — tela de listagem e menu (T015)
# ============================================================================

def test_tela_backups_com_admin_lista_ordenado(client, db_session):
    from app.config import BACKUP_DIR

    ensure_default_roles(db_session)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    (BACKUP_DIR / "backup_20260917_100000_000001.sql").write_bytes(b"a" * 10)
    (BACKUP_DIR / "backup_20260917_120000_000002.sql").write_bytes(b"b" * 20)

    resp = client.get("/admin/backups")

    assert resp.status_code == 200
    body = resp.text
    assert "backup_20260917_120000_000002.sql" in body
    assert body.index("backup_20260917_120000_000002.sql") < body.index(
        "backup_20260917_100000_000001.sql"
    )


def test_tela_backups_vazia_estado_amigavel(client, db_session):
    resp = client.get("/admin/backups")

    assert resp.status_code == 200
    assert "Nenhum backup" in resp.text


# ============================================================================
# 016 — US1 (T007): Teste H literal — múltiplas gerações via web
# ============================================================================

def test_rota_gerar_duas_vezes_cria_dois_gz_distintos(client, db_session, monkeypatch):
    """Teste H (§34): 2 POSTs → 2 arquivos .sql.gz distintos; listagem com os 2;
    nenhum sobrescreveu; download serve bytes íntegros (Testes A/C adaptados)."""
    import gzip as gzip_mod

    from app.config import BACKUP_DIR
    from app.services import backup_service

    monkeypatch.setattr(backup_service, "_run_mysqldump", _fake_dump)

    resp1 = client.post("/admin/backups/gerar", follow_redirects=False)
    resp2 = client.post("/admin/backups/gerar", follow_redirects=False)
    assert resp1.status_code == 303 and resp2.status_code == 303

    backups = BackupService.list_backups()
    assert len(backups) == 2
    assert all(b["filename"].endswith(".sql.gz") for b in backups)
    assert backups[0]["filename"] != backups[1]["filename"]

    # Download íntegro de um .sql.gz via rota (bytes == conteúdo do gzip)
    name = backups[0]["filename"]
    dl = client.get(f"/admin/backups/{name}/download")
    assert dl.status_code == 200
    with gzip_mod.open(BACKUP_DIR / name, "rb") as gz:
        assert gz.read() == FAKE_DUMP_CONTENT


def test_tela_backups_sem_permissao_negada(client, db_session):
    _make_user(db_session, "semperm2", role_names=["Consulta"])
    _login(client, "semperm2")

    resp = client.get("/admin/backups")

    assert resp.status_code == 403


def test_menu_contem_item_backups_com_permissao(client, db_session):
    resp = client.get("/")

    assert resp.status_code == 200
    assert "/admin/backups" in resp.text
    assert "Backups" in resp.text


# ============================================================================
# 016 — US2 (T010): falha literal — BACKUP_FALHA sem falso sucesso (Teste G)
# ============================================================================

def test_falha_gera_evento_backup_falha_literal(db_session, caplog):
    """Teste G literal: executor lança → BACKUP_FALHA (FALHA), não mais
    BACKUP_CRIADO/FAILURE; descrição segura; log de erro sem segredos; nada
    parcial nem final listado."""
    import logging as logging_mod

    from app.services.audit_service import (
        ACTION_BACKUP_CREATED,
        ACTION_BACKUP_FAILED,
        RESULT_FAILURE,
    )

    user = _make_user(db_session, "bkpfail", role_names=["Administrador"])

    with caplog.at_level(logging_mod.ERROR, logger="app.services.backup_service"):
        with pytest.raises(Exception):
            BackupService.generate_backup(
                db_session, user, "127.0.0.1", dump_executor=_failing_dump
            )

    # Evento literal novo — e nenhum BACKUP_CRIADO (nem FAILURE)
    failed = _audit_entries(db_session, ACTION_BACKUP_FAILED)
    assert len(failed) == 1
    assert failed[0].result == RESULT_FAILURE
    assert _audit_entries(db_session, ACTION_BACKUP_CREATED) == []

    # Descrição segura (sem comando/credenciais — §19/§25/§26)
    desc = failed[0].description or ""
    assert "mysqldump" not in desc and "PASSWORD" not in desc

    # Log de erro presente, sem segredos
    assert any("Falha" in r.getMessage() for r in caplog.records)
    joined = " ".join(r.getMessage() for r in caplog.records)
    assert "MYSQL_PWD" not in joined and "--user=" not in joined

    # Nenhum parcial (.part*) nem final listado
    from app.config import BACKUP_DIR

    leftovers = [p.name for p in BACKUP_DIR.iterdir() if _PART_BACKUP_RE.match(p.name)]
    assert leftovers == []
    assert BackupService.list_backups() == []


def test_falha_no_meio_da_compressao_sem_falso_sucesso(db_session):
    """Teste G variante: falha ENTRE o dump e o rename (compressão/I/O) →
    BACKUP_FALHA, nenhum .sql.gz listado, nenhum falso sucesso.

    Mecanismo: o executor grava o dump e o remove (falha de I/O simulada) —
    a compressão falha ao abrir a origem (OSError → BACKUP_FALHA).
    """
    from app.services.audit_service import ACTION_BACKUP_FAILED

    def _dump_vanish(path):
        path.write_bytes(FAKE_DUMP_CONTENT)
        path.unlink()  # falha de I/O simulada: origem some antes da compressão

    user = _make_user(db_session, "bkpfail2", role_names=["Administrador"])

    with pytest.raises(Exception):
        BackupService.generate_backup(
            db_session, user, "127.0.0.1", dump_executor=_dump_vanish
        )

    assert len(_audit_entries(db_session, ACTION_BACKUP_FAILED)) == 1
    assert BackupService.list_backups() == []

    from app.config import BACKUP_DIR

    leftovers = [p.name for p in BACKUP_DIR.iterdir() if _PART_BACKUP_RE.match(p.name)]
    assert leftovers == []


# ============================================================================
# US3 — download (T018)
# ============================================================================

def test_download_serve_bytes_e_audita(client, db_session):
    from app.config import BACKUP_DIR
    from app.services.audit_service import ACTION_BACKUP_DOWNLOAD, RESULT_SUCCESS

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    name = "backup_20260917_120000_000123.sql"
    (BACKUP_DIR / name).write_bytes(FAKE_DUMP_CONTENT)

    resp = client.get(f"/admin/backups/{name}/download")

    assert resp.status_code == 200
    assert resp.content == FAKE_DUMP_CONTENT  # SC-003 integridade
    assert "attachment" in resp.headers.get("content-disposition", "")
    assert name in resp.headers.get("content-disposition", "")

    events = _audit_entries(db_session, ACTION_BACKUP_DOWNLOAD)
    assert len(events) == 1
    assert events[0].result == RESULT_SUCCESS
    assert _new_data(events[0])["arquivo"] == name


def test_download_sem_permissao_negado(client, db_session):
    _make_user(db_session, "semperm3", role_names=["Consulta"])
    _login(client, "semperm3")

    name = "backup_20260917_120000_000123.sql"
    resp = client.get(f"/admin/backups/{name}/download")

    assert resp.status_code == 403


def test_download_nome_fora_do_padrao_404_sem_evento(client, db_session):
    from app.services.audit_service import ACTION_BACKUP_DOWNLOAD

    resp = client.get("/admin/backups/../../etc/passwd/download")

    assert resp.status_code in (400, 404)

    assert _audit_entries(db_session, ACTION_BACKUP_DOWNLOAD) == []


def test_download_inexistente_404_sem_evento(client, db_session):
    from app.services.audit_service import ACTION_BACKUP_DOWNLOAD

    name = "backup_20260917_120000_000999.sql"
    resp = client.get(f"/admin/backups/{name}/download")

    assert resp.status_code == 404
    assert _audit_entries(db_session, ACTION_BACKUP_DOWNLOAD) == []


# ============================================================================
# US4 — matriz de segurança (T021)
# ============================================================================

def test_matriz_sem_permissao_403_nas_tres_rotas(client, db_session):
    _make_user(db_session, "matriz", role_names=["Consulta"])
    _login(client, "matriz")

    assert client.get("/admin/backups").status_code == 403
    assert client.post("/admin/backups/gerar", follow_redirects=False).status_code == 403
    name = "backup_20260917_120000_000123.sql"
    assert client.get(f"/admin/backups/{name}/download").status_code == 403

    # Nenhum evento de backup criado por esses acessos negados
    from app.services.audit_service import ACTION_BACKUP_CREATED

    assert _audit_entries(db_session, ACTION_BACKUP_CREATED) == []


def test_eventos_nao_contem_credenciais_nem_comando(db_session):
    from app.services.audit_service import ACTION_BACKUP_CREATED

    user = _make_user(db_session, "bkpaudit", role_names=["Administrador"])
    BackupService.generate_backup(
        db_session, user, "127.0.0.1", dump_executor=_fake_dump
    )

    ev = _audit_entries(db_session, ACTION_BACKUP_CREATED)[0]
    new_data = _new_data(ev)
    assert set(new_data.keys()) <= {"arquivo", "tamanho_bytes", "sha256"}


# ============================================================================
# 018 — US1: resolução do executável de dump e ambiente do subprocesso
# (research R1/R3: MYSQLDUMP_PATH → fallback PATH → erro diagnosticável;
#  ambiente herdado + MYSQL_PWD — a senha EXCLUSIVAMENTE no ambiente)
# ============================================================================

_DUMP_URL = "mariadb+pymysql://usuario:senha_falsa@localhost:3306/banco"


def _fake_run_capture(captured, result_returncode=0):
    """Falso subprocess.run que captura argv/kwargs (nunca executa nada)."""
    from types import SimpleNamespace

    def _run(cmd, **kwargs):
        captured["args"] = cmd
        captured["kwargs"] = kwargs
        return SimpleNamespace(returncode=result_returncode)

    return _run


def test_018_us1_mysqldump_path_configurado_define_argv(monkeypatch, tmp_path):
    """MYSQLDUMP_PATH configurado → o argv começa com o executável configurado (R3)."""
    import sys

    from app.services import backup_service

    captured = {}
    monkeypatch.setattr(
        backup_service, "MYSQLDUMP_PATH", sys.executable, raising=False
    )
    monkeypatch.setattr(backup_service.subprocess, "run", _fake_run_capture(captured))
    monkeypatch.setattr(backup_service, "DATABASE_URL", _DUMP_URL)

    backup_service._run_mysqldump(tmp_path / "dump.part")

    assert captured["args"][0] == sys.executable


def test_018_us1_fallback_path_do_sistema(monkeypatch, tmp_path):
    """Sem MYSQLDUMP_PATH → shutil.which resolve no PATH do processo (R2 — Teste F: Linux)."""
    from types import SimpleNamespace

    from app.services import backup_service

    captured = {}
    monkeypatch.setattr(backup_service, "MYSQLDUMP_PATH", None, raising=False)
    monkeypatch.setattr(
        backup_service,
        "shutil",
        SimpleNamespace(which=lambda name: "/usr/bin/mysqldump"),
        raising=False,
    )
    monkeypatch.setattr(backup_service.subprocess, "run", _fake_run_capture(captured))
    monkeypatch.setattr(backup_service, "DATABASE_URL", _DUMP_URL)

    backup_service._run_mysqldump(tmp_path / "dump.part")

    assert captured["args"][0] == "/usr/bin/mysqldump"


def test_018_us1_nada_disponivel_erro_nao_encontrado(monkeypatch, tmp_path):
    """Executável ausente → BackupError distinta de 'não encontrado' (R6 — Teste B; sem falso sucesso)."""
    from types import SimpleNamespace

    import pytest

    from app.services import backup_service
    from app.services.backup_service import BackupError

    monkeypatch.setattr(backup_service, "MYSQLDUMP_PATH", None, raising=False)
    monkeypatch.setattr(
        backup_service, "shutil", SimpleNamespace(which=lambda name: None), raising=False
    )

    with pytest.raises(BackupError, match="não foi encontrado"):
        backup_service._run_mysqldump(tmp_path / "dump.part")


def test_018_us1_mysqldump_path_inexistente_falha_clara(monkeypatch, tmp_path):
    """MYSQLDUMP_PATH apontando para caminho inexistente → BackupError clara (antes do subprocesso)."""
    import pytest

    from app.services import backup_service
    from app.services.backup_service import BackupError

    monkeypatch.setattr(
        backup_service,
        "MYSQLDUMP_PATH",
        "Z:/caminho/inexistente/mysqldump.exe",
        raising=False,
    )

    with pytest.raises(BackupError, match="não foi encontrado"):
        backup_service._run_mysqldump(tmp_path / "dump.part")


def test_018_us1_env_herdado_com_mysql_pwd(monkeypatch, tmp_path):
    """Ambiente do subprocesso: herda o processo + MYSQL_PWD (R1 — sem PATH fixo Unix)."""
    import os
    import sys

    from app.services import backup_service

    captured = {}
    monkeypatch.setattr(
        backup_service, "MYSQLDUMP_PATH", sys.executable, raising=False
    )
    monkeypatch.setattr(backup_service.subprocess, "run", _fake_run_capture(captured))
    monkeypatch.setattr(backup_service, "DATABASE_URL", _DUMP_URL)

    backup_service._run_mysqldump(tmp_path / "dump.part")

    env = captured["kwargs"]["env"]
    assert env["MYSQL_PWD"] == "senha_falsa"
    assert env["PATH"] != "/usr/local/bin:/usr/bin:/bin"
    assert env["PATH"] == os.environ.get("PATH", "")


def test_018_us1_senha_nunca_em_argv(monkeypatch, tmp_path):
    """A senha da DATABASE_URL NUNCA aparece nos argumentos do subprocesso (FR-005 — Teste H)."""
    import sys

    from app.services import backup_service

    captured = {}
    monkeypatch.setattr(
        backup_service, "MYSQLDUMP_PATH", sys.executable, raising=False
    )
    monkeypatch.setattr(backup_service.subprocess, "run", _fake_run_capture(captured))
    monkeypatch.setattr(backup_service, "DATABASE_URL", _DUMP_URL)

    backup_service._run_mysqldump(tmp_path / "dump.part")

    assert all("senha_falsa" not in str(arg) for arg in captured["args"])


# ============================================================================
# 018 — US2: diagnóstico técnico sem segredos + mensagens distintas
# (research R5/R6: paridade com o import; Testes D e H do briefing)
# ============================================================================


def _fake_run_calledprocess(stderr_bytes, returncode=2):
    """Falso subprocess.run que levanta CalledProcessError com stderr (Teste D)."""
    import subprocess as sp_mod

    def _run(cmd, **kwargs):
        raise sp_mod.CalledProcessError(
            returncode, cmd, stderr=stderr_bytes
        )

    return _run


def test_018_us2_log_tecnico_dump_exit_e_stderr(monkeypatch, tmp_path, caplog):
    """Falha de retorno: log com etapa=dump, exit code e diagnóstico (Teste D)."""
    import logging
    import sys

    from app.services import backup_service

    monkeypatch.setattr(
        backup_service, "MYSQLDUMP_PATH", sys.executable, raising=False
    )
    monkeypatch.setattr(backup_service, "DATABASE_URL", _DUMP_URL)
    monkeypatch.setattr(
        backup_service.subprocess,
        "run",
        _fake_run_calledprocess(b"mysqldump: [Warning] unknown option\n"),
    )

    with caplog.at_level(logging.ERROR, logger="app.services.backup_service"):
        with pytest.raises(Exception):
            backup_service._run_mysqldump(tmp_path / "dump.part")

    joined = " ".join(r.getMessage() for r in caplog.records)
    assert "etapa=dump" in joined
    assert "exit=2" in joined
    assert "unknown option" in joined


def test_018_us2_stderr_sanitizado_sem_senha(monkeypatch, tmp_path, caplog):
    """stderr contendo a senha do banco → mascarada no log (Teste H — Princípio VI)."""
    import logging
    import sys

    from app.services import backup_service

    monkeypatch.setattr(
        backup_service, "MYSQLDUMP_PATH", sys.executable, raising=False
    )
    monkeypatch.setattr(backup_service, "DATABASE_URL", _DUMP_URL)
    monkeypatch.setattr(
        backup_service.subprocess,
        "run",
        _fake_run_calledprocess(
            b"mysqldump: Got error: 1045: Access denied ... senha_falsa ...\n"
        ),
    )

    with caplog.at_level(logging.ERROR, logger="app.services.backup_service"):
        with pytest.raises(Exception):
            backup_service._run_mysqldump(tmp_path / "dump.part")

    joined = " ".join(r.getMessage() for r in caplog.records)
    assert "senha_falsa" not in joined
    assert "***" in joined


def test_018_us2_mensagens_distintas_nao_encontrado_vs_erro(monkeypatch, tmp_path):
    """FR-014: 'não encontrado' ≠ 'retornou erro' — operador distingue as causas."""
    from types import SimpleNamespace

    import pytest

    from app.services import backup_service
    from app.services.backup_service import BackupError

    # Ausente → "não foi encontrado"
    monkeypatch.setattr(backup_service, "MYSQLDUMP_PATH", None, raising=False)
    monkeypatch.setattr(
        backup_service, "shutil", SimpleNamespace(which=lambda name: None), raising=False
    )
    with pytest.raises(BackupError, match="não foi encontrado"):
        backup_service._run_mysqldump(tmp_path / "dump.part")

    # Presente mas retornando erro → "retornou erro" (mensagem existente)
    import sys

    monkeypatch.setattr(
        backup_service, "MYSQLDUMP_PATH", sys.executable, raising=False
    )
    monkeypatch.setattr(
        backup_service.subprocess,
        "run",
        _fake_run_calledprocess(b"erro qualquer\n"),
    )
    with pytest.raises(BackupError, match="retornou erro"):
        backup_service._run_mysqldump(tmp_path / "dump.part")


def test_018_us2_stderr_nunca_no_usuario(monkeypatch, tmp_path):
    """A mensagem da BackupError NUNCA contém o texto do stderr (Princípio VI)."""
    import sys

    import pytest

    from app.services import backup_service
    from app.services.backup_service import BackupError

    monkeypatch.setattr(
        backup_service, "MYSQLDUMP_PATH", sys.executable, raising=False
    )
    monkeypatch.setattr(backup_service, "DATABASE_URL", _DUMP_URL)
    monkeypatch.setattr(
        backup_service.subprocess,
        "run",
        _fake_run_calledprocess(b"DETALHE INTERNO SECRETO DO STDERR\n"),
    )

    with pytest.raises(BackupError) as excinfo:
        backup_service._run_mysqldump(tmp_path / "dump.part")

    assert "DETALHE INTERNO SECRETO" not in str(excinfo.value)


# ============================================================================
# 018 — US3: paridade do import (restauração 017) e robustez
# (Testes D/E/F/G/H do briefing; R1/R4)
# ============================================================================


def test_018_us3_import_derivado_do_mysqldump_path(monkeypatch, tmp_path):
    """R4: MYSQLDUMP_PATH aponta o mysqldump → cliente mysql derivado do mesmo bin."""
    import sys
    from types import SimpleNamespace

    from app.services import backup_service

    dump_fake = tmp_path / "mysqldump.exe"
    dump_fake.write_bytes(b"")
    mysql_fake = tmp_path / "mysql.exe"
    mysql_fake.write_bytes(b"")

    captured = {}

    class _FakeStdin:
        def write(self, chunk):
            pass

        def close(self):
            pass

    class _FakeProc:
        def __init__(self):
            self.stdin = _FakeStdin()
            self.stderr = SimpleNamespace(read=lambda: b"", close=lambda: None)
            self.returncode = 0

        def wait(self, timeout=None):
            return 0

    def _fake_popen(cmd, **kwargs):
        captured["args"] = cmd
        captured["kwargs"] = kwargs
        return _FakeProc()

    monkeypatch.setattr(backup_service, "MYSQLDUMP_PATH", str(dump_fake), raising=False)
    monkeypatch.setattr(backup_service.subprocess, "Popen", _fake_popen)
    monkeypatch.setattr(backup_service, "DATABASE_URL", _DUMP_URL)

    dump = tmp_path / "dump.sql"
    dump.write_bytes(b"-- conteudo\n")
    backup_service._run_mysql_import(dump, is_gzip=False)

    assert captured["args"][0] == str(mysql_fake)


def test_018_us3_import_env_herdado_com_mysql_pwd(monkeypatch, tmp_path):
    """R1: o import usa o mesmo ambiente do dump (herdado + MYSQL_PWD)."""
    import os
    from types import SimpleNamespace

    from app.services import backup_service

    captured = {}

    class _FakeStdin:
        def write(self, chunk):
            pass

        def close(self):
            pass

    class _FakeProc:
        def __init__(self):
            self.stdin = _FakeStdin()
            self.stderr = SimpleNamespace(read=lambda: b"", close=lambda: None)
            self.returncode = 0

        def wait(self, timeout=None):
            return 0

    monkeypatch.setattr(backup_service, "MYSQLDUMP_PATH", None, raising=False)
    monkeypatch.setattr(
        backup_service.subprocess,
        "Popen",
        lambda cmd, **kwargs: (captured.update(args=cmd, kwargs=kwargs), _FakeProc())[1],
    )
    monkeypatch.setattr(backup_service, "DATABASE_URL", _DUMP_URL)

    dump = tmp_path / "dump.sql"
    dump.write_bytes(b"-- conteudo\n")
    backup_service._run_mysql_import(dump, is_gzip=False)

    env = captured["kwargs"]["env"]
    assert env["MYSQL_PWD"] == "senha_falsa"
    assert env["PATH"] == os.environ.get("PATH", "")


def test_018_us3_import_executavel_ausente_mensagem_clara(monkeypatch, tmp_path):
    """Import sem executável em lugar nenhum → BackupError 'não encontrado' (R4/R6).

    Hermeticidade: mesmo que um cliente 'mysql' real exista no PATH da máquina
    (ex.: /usr/bin/mysql no dev), o Popen é fakeado para levantar
    FileNotFoundError — exatamente o que o SO faria com o executável ausente.
    """
    import pytest

    from app.services import backup_service
    from app.services.backup_service import BackupError

    monkeypatch.setattr(backup_service, "MYSQLDUMP_PATH", None, raising=False)
    monkeypatch.setattr(backup_service.shutil, "which", lambda name: None)

    def _popen_sem_executavel(cmd, **kwargs):
        raise FileNotFoundError(2, "No such file or directory")

    monkeypatch.setattr(
        backup_service.subprocess, "Popen", _popen_sem_executavel
    )

    dump = tmp_path / "dump.sql"
    dump.write_bytes(b"-- conteudo\n")

    with pytest.raises(BackupError, match="não foi encontrado"):
        backup_service._run_mysql_import(dump, is_gzip=False)


def test_018_us3_dump_falha_gera_auditoria_failure(db_session, monkeypatch):
    """Teste G: utilitário ausente → ACTION_BACKUP_FAILED com descrição controlada."""
    from types import SimpleNamespace

    from app.services import backup_service
    from app.services.audit_service import ACTION_BACKUP_FAILED
    from app.services.backup_service import BackupError

    user = _make_user(db_session, "bkp18fail", role_names=["Administrador"])

    monkeypatch.setattr(backup_service, "MYSQLDUMP_PATH", None, raising=False)
    monkeypatch.setattr(
        backup_service, "shutil", SimpleNamespace(which=lambda name: None)
    )

    with pytest.raises(BackupError):
        BackupService.generate_backup(db_session, user, "127.0.0.1")

    failures = _audit_entries(db_session, ACTION_BACKUP_FAILED)
    assert len(failures) == 1
    assert "não foi encontrado" in failures[0].description or "Falha" in failures[0].description


def test_018_us3_todos_os_logs_da_feature_sem_senha(monkeypatch, tmp_path, caplog):
    """Teste H (fechamento): nenhum log da 018 contém a senha falsa das URLs de teste."""
    import logging
    import sys

    from app.services import backup_service

    monkeypatch.setattr(
        backup_service, "MYSQLDUMP_PATH", sys.executable, raising=False
    )
    monkeypatch.setattr(backup_service, "DATABASE_URL", _DUMP_URL)
    monkeypatch.setattr(
        backup_service.subprocess,
        "run",
        _fake_run_calledprocess(b"Access denied para usuario com senha_falsa\n"),
    )

    with caplog.at_level(logging.ERROR, logger="app.services.backup_service"):
        with pytest.raises(Exception):
            backup_service._run_mysqldump(tmp_path / "dump.part")

    joined = " ".join(r.getMessage() for r in caplog.records)
    assert "senha_falsa" not in joined


def test_018_us3_config_le_apos_load_dotenv():
    """Guarda de regressão do incidente real (2026-09-18): a leitura de
    MYSQLDUMP_PATH em app/config.py foi posicionada ANTES de load_dotenv(),
    fazendo a variável do .env nunca ser vista (sempre None) mesmo com o
    servidor reiniciado. Toda variável lida via os.getenv deve vir depois
    da chamada load_dotenv()."""
    from pathlib import Path

    source = Path("app/config.py").read_text(encoding="utf-8")
    pos_load = source.find("load_dotenv()")
    assert pos_load != -1, "load_dotenv() ausente do app/config.py"

    for var in ("DATABASE_URL", "MYSQLDUMP_PATH"):
        pos_var = source.find(f"{var} = os.getenv(")
        assert pos_var != -1, f"leitura de {var} ausente do app/config.py"
        assert pos_var > pos_load, (
            f"{var} é lida ANTES de load_dotenv() em app/config.py — "
            "o valor do .env nunca seria carregado (bug da feature 018)"
        )
