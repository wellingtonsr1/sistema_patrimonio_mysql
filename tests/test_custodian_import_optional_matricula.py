"""Feature 014 — Matrícula opcional na importação de colaboradores via CSV.

Cenários do briefing (spec.md §6): T1 informada, T2 vazia, T3 só espaços,
T4 coluna ausente, T5 mista, T6 duplicada informada, T7 várias sem matrícula,
T8 regressão (suíte completa).

Regras verificadas (research.md): ausência (vazio/espaços/chave ausente) gera
PROV-%06d via fachada do gerador único da feature 010; matrícula informada
mantém normalização/unicidade/duplicidade byte-a-byte.
"""

import re

from app.models.custodian import Custodian
from app.services.custodian_import_service import (
    parse_custodian_csv,
    preview_custodian_import,
    execute_custodian_import,
)
from app.services.custodian_service import CustodianService
from app.schemas.custodian import CustodianCreate

_PROV_RE = re.compile(r"^PROV-\d{6}$")

_HEADER = "matricula;nome;email;cargo;setor"


def _csv(*lines: str, header: str = _HEADER) -> str:
    """Monta um conteúdo CSV com delimitador ';' (padrão BR do importador)."""
    return "\n".join((header,) + lines) + "\n"


def _create_custodian(db, registration_code, name, email, role="Analista", department="TI"):
    """Cria um colaborador existente pelo service (padrão de test_custodian_import.py)."""
    return CustodianService.create(db, CustodianCreate(
        registration_code=registration_code,
        name=name,
        email=email,
        role=role,
        department=department,
    ))


def _create_provisional(db, code, name, email):
    """Cria registro PROV-* diretamente pelo modelo (simula os gerados pelo sistema).

    O anti-fabricação da feature 010 impede PROV-* informado via service —
    comportamento correto verificado (research R8)."""
    custodian = Custodian(registration_code=code, name=name, email=email,
                          role="Analista", department="TI", is_active=True)
    db.add(custodian)
    db.commit()
    return custodian


def _codes(db) -> set:
    return {c.registration_code for c in db.query(Custodian).all()}


# ---------------------------------------------------------------- Foundational


def test_parse_matricula_vazia_nao_e_erro(db_session):
    """T2 (parse): célula vazia entra em rows, sem erro de matrícula obrigatória."""
    csv_content = _csv(";Maria Souza;maria.souza@empresa.com;Assistente;RH")
    rows, errors = parse_custodian_csv(csv_content)

    assert errors == []
    assert len(rows) == 1
    assert rows[0]["registration_code"] == ""


def test_parse_matricula_somente_espacos_nao_e_erro(db_session):
    """T3 (parse): só espaços é tratado como não informada."""
    csv_content = _csv("   ;Ana Lima;ana.lima@empresa.com;Coordenadora;Financeiro")
    rows, errors = parse_custodian_csv(csv_content)

    assert errors == []
    assert len(rows) == 1
    assert rows[0]["registration_code"] == ""  # parse já aplica strip


def test_parse_coluna_matricula_ausente_nao_e_erro(db_session):
    """T4 (parse): CSV sem a coluna matricula continua válido."""
    csv_content = _csv(
        "João Silva;joao.silva@empresa.com;Analista;TI",
        "Bia Campos;bia.campos@empresa.com;Designer;UX",
        header="nome;email;cargo;setor",
    )
    rows, errors = parse_custodian_csv(csv_content)

    assert errors == []
    assert len(rows) == 2
    # Coluna ausente → chave pode não existir no dict (contrato §2.2): ausência == vazio
    assert all(not r.get("registration_code", "").strip() for r in rows)


def test_parse_demais_obrigatoriedades_preservadas(db_session):
    """T8 parcial: sem nome/email/cargo/setor os erros continuam (FR-008)."""
    csv_content = _csv(
        "MAT-9001;Ana Souza;ana@empresa.com;;TI",      # cargo ausente
        ";Bruno Lima;bruno@empresa.com;Dev;TI",         # matricula vazia → sem erro
        "MAT-9002;;nao-e-email;Dev;TI",                 # nome ausente + email inválido
    )
    rows, errors = parse_custodian_csv(csv_content)

    assert len(rows) == 1  # apenas a linha sem matrícula é válida
    assert rows[0]["registration_code"] == ""
    assert len(errors) == 3
    assert any("cargo é obrigatório" in e for e in errors)
    assert any("nome é obrigatório" in e for e in errors)
    assert any("email inválido" in e for e in errors)
    assert not any("matricula" in e for e in errors)


# ---------------------------------------------------------------- Fachada (R1)


def test_fachada_gera_proximo_provisional(db_session):
    """Fachada retorna PROV-%06d (contrato §1, research R1)."""
    code = CustodianService.generate_available_provisional_code(db_session)

    assert _PROV_RE.match(code)


def test_fachada_continua_sequencial_existente(db_session):
    """Com PROV-000005 pré-existente, a fachada retorna PROV-000006."""
    _create_provisional(db_session, "PROV-000005", "Prov Antigo", "prov5@empresa.com")

    code = CustodianService.generate_available_provisional_code(db_session)

    assert code == "PROV-000006"


def test_fachada_pula_codigo_existente(db_session):
    """Se o próximo sequencial já existe, a fachada repete até achar livre (create pré-inserção)."""
    _create_provisional(db_session, "PROV-000005", "Prov 5", "p5@empresa.com")
    _create_provisional(db_session, "PROV-000006", "Prov 6", "p6@empresa.com")

    code = CustodianService.generate_available_provisional_code(db_session)

    assert code == "PROV-000007"


# ------------------------------------------------------- US1: execução (T2/T3/T4/T5)


def test_execucao_matricula_vazia_gera_provisional(db_session):
    """T2: célula vazia → colaborador criado com PROV-%06d, sem erro."""
    rows, errors = parse_custodian_csv(_csv(";Maria Souza;maria.souza@empresa.com;Assistente;RH"))
    assert errors == []

    result = execute_custodian_import(rows, db_session)

    assert result["imported"] == 1
    assert result["errors"] == []
    codes = _codes(db_session)
    assert len(codes) == 1
    code = codes.pop()
    assert _PROV_RE.match(code), f"esperado PROV-%06d, obtido {code!r}"


def test_execucao_matricula_somente_espacos_gera_provisional(db_session):
    """T3: só espaços é tratado como não informada → PROV-%06d."""
    rows, errors = parse_custodian_csv(_csv("   ;Ana Lima;ana.lima@empresa.com;Coordenadora;Financeiro"))
    assert errors == []

    result = execute_custodian_import(rows, db_session)

    assert result["imported"] == 1
    assert result["errors"] == []
    code = _codes(db_session).pop()
    assert _PROV_RE.match(code)


def test_execucao_chave_ausente_gera_provisional(db_session):
    """T4 (execução): chamada direta sem a chave registration_code → PROV-%06d."""
    result = execute_custodian_import(
        [{"name": "Bia Campos", "email": "bia.campos@empresa.com", "role": "Designer", "department": "UX"}],
        db_session,
    )

    assert result["imported"] == 1
    assert result["errors"] == []
    code = _codes(db_session).pop()
    assert _PROV_RE.match(code)


def test_execucao_mista_informadas_e_provisionais(db_session):
    """T5: mesma execução com matrículas informadas e ausentes — cada linha tratada individualmente."""
    csv_content = _csv(
        "MAT-1045;João Silva;joao.silva@empresa.com;Analista;TI",
        ";Maria Souza;maria.souza@empresa.com;Assistente;RH",
        "MAT-1088;Pedro Santos;pedro.santos@empresa.com;Analista;Patrimônio",
        "   ;Ana Lima;ana.lima@empresa.com;Coordenadora;Financeiro",
    )
    rows, errors = parse_custodian_csv(csv_content)
    assert errors == []

    result = execute_custodian_import(rows, db_session)

    assert result["imported"] == 4
    assert result["errors"] == []
    codes = _codes(db_session)
    assert "MAT-1045" in codes and "MAT-1088" in codes
    prov_codes = [c for c in codes if c.startswith("PROV-")]
    assert len(prov_codes) == 2
    assert all(_PROV_RE.match(c) for c in prov_codes)


# --------------------------------------------- US2: informadas preservadas (T1/T6, guarda)


def test_informada_valida_e_utilizada_sem_provisional(db_session):
    """T1: matrícula informada válida é usada como está — nenhuma PROV gerada."""
    rows, errors = parse_custodian_csv(_csv("MAT-1045;João Silva;joao.silva@empresa.com;Analista;TI"))
    assert errors == []

    result = execute_custodian_import(rows, db_session)

    assert result["imported"] == 1
    codes = _codes(db_session)
    assert codes == {"MAT-1045"}


def test_informada_normalizacao_trim_upper_preservada(db_session):
    """Normalização atual (trim+upper de _normalize_registration_code) mantida."""
    rows, errors = parse_custodian_csv(_csv(" mat-1045 ;João Silva;joao.silva@empresa.com;Analista;TI"))
    assert errors == []

    result = execute_custodian_import(rows, db_session)

    assert result["imported"] == 1
    assert _codes(db_session) == {"MAT-1045"}


def test_informada_duplicada_com_skip(db_session):
    """T6 (skip_duplicates=True): duplicata informada é pulada — NUNCA vira PROV (FR-004)."""
    _create_custodian(db_session, "MAT-1045", "João Original", "joao.silva@empresa.com")

    rows, _ = parse_custodian_csv(_csv("MAT-1045;João Silva Novo;joao.silva@empresa.com;Analista;TI"))
    result = execute_custodian_import(rows, db_session, skip_duplicates=True)

    assert result["skipped"] == 1
    assert result["imported"] == 0
    assert result["errors"] == []
    joao = db_session.query(Custodian).filter(Custodian.registration_code == "MAT-1045").first()
    assert joao.name == "João Original"  # intocado


def test_informada_duplicada_sem_skip_atualiza_mantendo_matricula(db_session):
    """T6 (skip_duplicates=False): atualização in-place mantém a matrícula original."""
    _create_custodian(db_session, "MAT-1045", "João Original", "joao.silva@empresa.com")

    rows, _ = parse_custodian_csv(_csv("MAT-1045;João Silva Novo;joao.silva@empresa.com;Analista;TI"))
    result = execute_custodian_import(rows, db_session, skip_duplicates=False)

    assert result["imported"] == 1
    joao = db_session.query(Custodian).filter(Custodian.registration_code == "MAT-1045").first()
    assert joao.name == "João Silva Novo"
    assert joao.role == "Analista"
    assert not any(c.startswith("PROV-") for c in _codes(db_session))


# ------------------------------------------ US3: unicidade intra-importação (T7, guarda)


def test_varias_sem_matricula_recebem_provisionais_distintas(db_session):
    """T7: cada colaborador sem matrícula recebe sua própria PROV única (RV-3)."""
    csv_content = _csv(
        ";Maria Souza;maria.souza@empresa.com;Assistente;RH",
        ";Ana Lima;ana.lima@empresa.com;Coordenadora;Financeiro",
        ";Bia Campos;bia.campos@empresa.com;Designer;UX",
    )
    rows, errors = parse_custodian_csv(csv_content)
    assert errors == []

    result = execute_custodian_import(rows, db_session)

    assert result["imported"] == 3
    assert result["errors"] == []
    prov_codes = [c for c in _codes(db_session) if c.startswith("PROV-")]
    assert len(prov_codes) == 3
    assert len(set(prov_codes)) == 3  # duas a duas distintas
    assert all(_PROV_RE.match(c) for c in prov_codes)


def test_provisionais_continuam_sequenciais_do_sistema(db_session):
    """As provisórias geradas seguem a sequência do gerador único (não reiniciam)."""
    _create_provisional(db_session, "PROV-000005", "Prov 5", "p5@empresa.com")

    rows, _ = parse_custodian_csv(_csv(
        ";Maria Souza;maria.souza@empresa.com;Assistente;RH",
        ";Ana Lima;ana.lima@empresa.com;Coordenadora;Financeiro",
    ))
    result = execute_custodian_import(rows, db_session)

    assert result["imported"] == 2
    prov_codes = sorted(c for c in _codes(db_session) if c.startswith("PROV-"))
    # Pré-existente (000005) + as duas novas na sequência do gerador único
    assert prov_codes == ["PROV-000005", "PROV-000006", "PROV-000007"]


# ------------------------------------------------ US4: preview coerente (FR-007, R3)


def test_preview_sem_matricula_flag_e_sem_duplicata(db_session):
    """Linha sem matrícula: listada, flag provisória, sem duplicata por matrícula vazia."""
    rows, errors = parse_custodian_csv(_csv(";Maria Souza;maria.souza@empresa.com;Assistente;RH"))
    assert errors == []

    preview = preview_custodian_import(rows, db_session)

    assert preview["total"] == 1
    p = preview["previews"][0]
    assert p["registration_code"] == ""          # sem fabricar número (FR-007)
    assert p["will_generate_provisional"] is True  # flag aditiva (contrato §2.3)
    assert p["is_duplicate"] is False
    assert preview["duplicates"] == 0
    assert preview["new_items"] == 1


def test_preview_sem_matricula_email_duplicado_permanece_duplicata(db_session):
    """Sem matrícula + e-mail já cadastrado → duplicata por E-MAIL (regra atual, R3)."""
    _create_custodian(db_session, "MAT-2001", "Maria Original", "maria.souza@empresa.com")

    rows, _ = parse_custodian_csv(_csv(";Maria Souza;maria.souza@empresa.com;Assistente;RH"))
    preview = preview_custodian_import(rows, db_session)

    p = preview["previews"][0]
    assert p["is_duplicate"] is True
    assert p["existing_custodian_id"] is not None
    assert p["will_generate_provisional"] is True


def test_preview_informada_duplicada_como_hoje(db_session):
    """Matrícula informada duplicada → duplicata exatamente como hoje (RV-5)."""
    _create_custodian(db_session, "MAT-1045", "João Original", "joao.silva@empresa.com")

    rows, _ = parse_custodian_csv(_csv("MAT-1045;João Silva;joao.silva@empresa.com;Analista;TI"))
    preview = preview_custodian_import(rows, db_session)

    p = preview["previews"][0]
    assert p["is_duplicate"] is True
    assert p["will_generate_provisional"] is False


def test_preview_informada_nova_nao_tem_flag(db_session):
    """Matrícula informada nova → flag False, fluxo atual intacto."""
    rows, _ = parse_custodian_csv(_csv("MAT-1045;João Silva;joao.silva@empresa.com;Analista;TI"))
    preview = preview_custodian_import(rows, db_session)

    p = preview["previews"][0]
    assert p["registration_code"] == "MAT-1045"
    assert p["will_generate_provisional"] is False
    assert p["is_duplicate"] is False
