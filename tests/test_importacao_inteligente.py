"""
Testes da Feature 048 — Importação Inteligente (camada pré-gravação).

Cobertura (quickstart.md, testes A–Q):
  - Camada compartilhada: analyze_columns (T002/T003)
  - US1: passo de mapeamento antes da gravação (T004–T007)
  - US2: classificação por registro e pré-visualização sem gravação (T008–T012)
  - US3: confirmação, gravação segura e relatório (T013–T016)

Regra de compatibilidade (R9/SC-007): nenhum teste existente é alterado aqui;
a suíte anterior (775 passed) deve permanecer verde.
"""

import io
import json

import pytest

from app.services.import_intelligence import (
    analyze_columns,
    classify_rows,
    apply_resolutions,
)


def _apply(content: str, kind: str):
    """Renormaliza o CSV pelo mapeamento auto (mesma lógica da rota) para
    exercitar classify_rows diretamente (testes de service — T008)."""
    import csv as _csv
    import io as _io
    from app.services.import_intelligence import _detect_delimiter

    delimiter = _detect_delimiter(content, kind)
    reader = _csv.DictReader(_io.StringIO(content), delimiter=delimiter)
    analysis = analyze_columns(content, kind)
    mapping = {
        s["column"]: s["field"]
        for s in analysis["suggestions"]
        if s["field"]
    }
    rows = []
    row_num = 2
    for raw in reader:
        resolved = {field: "" for field in set(mapping.values())}
        for original_col, value in raw.items():
            field = mapping.get(original_col or "")
            if field:
                resolved[field] = (value or "").strip()
        rows.append({"row_num": row_num, "resolved": resolved})
        row_num += 1
    return rows


def db_from_client(client):
    """Sessão do mesmo engine do client (mesma base em memória), obtida do
    override de get_db registrado pelo fixture `client`."""
    from app.main import app
    from app.database import get_db

    gen = app.dependency_overrides[get_db]()
    return next(gen)


def _extract_preview_payload(step_analyze):
    """Extrai e desserializa o payload classificado do textarea oculto."""
    import html as _html
    raw = step_analyze.text.split('name="csv_data" style="display:none;">')[1].split("</textarea>")[0]
    return json.loads(_html.unescape(raw))


def _login(client, username, password="senha@1234"):
    resp = client.post(
        "/api/v1/auth/login", data={"username": username, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return resp


# ============================================================
# Camada compartilhada — analyze_columns (T002)
# ============================================================

CSV_ASSETS_CANONICO = """\
tombamento,equipamento,categoria,marca,modelo
TMB-0001,Notebook Dell,notebook,Dell,Latitude
TMB-0002,Monitor LG,monitor,LG,27UK850
"""

CSV_ASSETS_VARIACOES = """\
TOMBAMENTO;Nº Tombamento;Patrimonio;Descrição;Marca
TMB-0001;TMB-0002;TMB-0003;Notebook;Dell
"""

CSV_LOCALS_DESCRICAO = """\
descricao;filial;departamento
Sala de TI;Matriz SP;Tecnologia da Informação
"""


def _by_column(analysis):
    return {s["column"]: s for s in analysis["suggestions"]}


def test_coluna_canonica_reconhecida_auto():
    """Coluna com nome canônico → sugestão auto para o campo do sistema."""
    analysis = analyze_columns(CSV_ASSETS_CANONICO, "assets")
    by_col = _by_column(analysis)

    assert by_col["tombamento"]["field"] == "tombamento"
    assert by_col["tombamento"]["confidence"] == "auto"
    assert by_col["equipamento"]["field"] == "equipamento"
    assert by_col["equipamento"]["confidence"] == "auto"
    assert by_col["categoria"]["field"] == "categoria"
    assert by_col["marca"]["field"] == "marca"
    assert by_col["modelo"]["field"] == "modelo"


def test_variacoes_de_cabecalho_reconhecidas_auto():
    """Variações de caixa/acentos/abreviação já cobertas pelos aliases → auto."""
    analysis = analyze_columns(CSV_ASSETS_VARIACOES, "assets")
    by_col = _by_column(analysis)

    assert by_col["TOMBAMENTO"]["field"] == "tombamento"
    assert by_col["TOMBAMENTO"]["confidence"] == "auto"
    assert by_col["Nº Tombamento"]["field"] == "tombamento"
    assert by_col["Patrimonio"]["field"] == "tombamento"
    # descrição → equipamento (alias existente do importador de equipamentos)
    assert by_col["Descrição"]["field"] == "equipamento"
    assert by_col["Marca"]["field"] == "marca"


def test_coluna_desconhecida_marcada():
    """Coluna sem campo correspondente (cor) → desconhecida, nunca silenciada (FR-005)."""
    content = "tombamento,equipamento,categoria,cor\nTMB-0001,Notebook,notebook,preto\n"
    analysis = analyze_columns(content, "assets")
    by_col = _by_column(analysis)

    assert by_col["cor"]["confidence"] == "desconhecida"
    assert by_col["cor"]["field"] is None


def test_coluna_ambigua_por_colisao_no_kind(monkeypatch):
    """Colisão de 2+ campos canônicos do mesmo kind na reversão dos aliases →
    ambigua com candidates, sem escolha silenciosa (FR-003/A1).

    As tabelas vigentes em runtime não têm colisões (chaves literais
    duplicadas ficam com o último valor — comportamento atual do parser).
    A colisão é injetada via monkeypatch para exercitar a maquinaria de
    ambiguidade da camada, sem alterar nenhum arquivo-fonte.
    """
    import app.services.import_intelligence as ii

    tabela_com_colisao = {
        "descricao": "name",
        "descrição": "description",  # variante acentada da MESMA chave bruta
        "filial": "branch",          # apontando para campo distinto → ambígua
        "departamento": "department",
    }
    monkeypatch.setitem(ii._KIND_ALIASES, "locations", tabela_com_colisao)

    analysis = analyze_columns(CSV_LOCALS_DESCRICAO, "locations")
    by_col = _by_column(analysis)

    sug = by_col["descricao"]
    assert sug["confidence"] == "ambigua"
    assert set(sug["candidates"]) == {"description", "name"}
    # filial/departamento seguem reconhecidas normalmente
    assert by_col["filial"]["field"] == "branch"
    assert by_col["departamento"]["field"] == "department"


def test_tabela_real_consistente_com_parser():
    """R9: com a tabela vigente, a sugestão da camada é a mesma associação
    que o parser existente faz (ex.: 'descricao' em locais → description).
    """
    from app.services.location_import_service import _normalize_column_name as loc_norm

    analysis = analyze_columns(CSV_LOCALS_DESCRICAO, "locations")
    by_col = _by_column(analysis)

    assert by_col["descricao"]["confidence"] == "auto"
    assert by_col["descricao"]["field"] == loc_norm("descricao")


def test_contagem_de_registros_e_delimitador():
    """Contagem de registros e delimitador ,/; detectados pelo parser existente."""
    analysis_virgula = analyze_columns(CSV_ASSETS_CANONICO, "assets")
    assert analysis_virgula["delimiter"] == ","
    assert analysis_virgula["total_rows"] == 2
    assert analysis_virgula["header"] == [
        "tombamento", "equipamento", "categoria", "marca", "modelo",
    ]

    content_pv = "matricula;nome;email;cargo;setor\nMAT-1;Ana;ana@x.com;Cargo;Setor\nMAT-2;Bia;bia@x.com;Cargo;Setor\n"
    analysis_pv = analyze_columns(content_pv, "custodians")
    assert analysis_pv["delimiter"] == ";"
    assert analysis_pv["total_rows"] == 2
    by_col = _by_column(analysis_pv)
    assert by_col["matricula"]["field"] == "registration_code"
    assert by_col["nome"]["field"] == "name"
    assert by_col["email"]["field"] == "email"


def test_analise_nao_grava_no_banco(db_session):
    """SC-001: a análise é somente leitura — nenhuma escrita no banco."""
    from app.models.asset import Asset
    from app.models.custodian import Custodian
    from app.models.location import Location

    before = (
        db_session.query(Asset).count(),
        db_session.query(Custodian).count(),
        db_session.query(Location).count(),
    )

    analyze_columns(CSV_ASSETS_CANONICO, "assets")
    analyze_columns(CSV_LOCALS_DESCRICAO, "locations")
    analyze_columns(
        "matricula;nome;email;cargo;setor\nMAT-1;Ana;ana@x.com;Cargo;Setor\n",
        "custodians",
    )

    after = (
        db_session.query(Asset).count(),
        db_session.query(Custodian).count(),
        db_session.query(Location).count(),
    )
    assert before == after


def test_guarda_arquivo_vazio_e_so_bom():
    """R6: arquivo vazio ou só com BOM → parse_errors, sem exceção."""
    analysis_vazio = analyze_columns("", "assets")
    assert analysis_vazio["parse_errors"]
    assert analysis_vazio["total_rows"] == 0

    analysis_bom = analyze_columns("﻿", "assets")
    assert analysis_bom["parse_errors"]


def test_guarda_csv_sem_registros():
    """R6: CSV só com cabeçalho (sem registros) → parse_errors claro."""
    analysis = analyze_columns("tombamento,equipamento,categoria\n", "assets")
    assert analysis["parse_errors"]
    assert analysis["total_rows"] == 0


def test_guarda_csv_sem_cabecalho():
    """R6: cabeçalho sem nenhuma coluna utilizável → parse_errors claro."""
    analysis = analyze_columns(",,\n,,\n", "assets")
    assert analysis["parse_errors"]


# ============================================================
# US1 — Passo de mapeamento nas rotas (T004)
# ============================================================

def _upload_csv(client, url, content, filename="arquivo.csv"):
    return client.post(
        url,
        files={"file": (filename, io.BytesIO(content.encode("utf-8")), "text/csv")},
        data={"skip_duplicates": "true"},
    )


def test_upload_renderiza_passo_de_mapeamento(client):
    """Contrato §3: POST com file → passo de mapeamento com sugestões
    pré-selecionadas (auto) — nada gravado, nada perdido (SC-001)."""
    resp = _upload_csv(client, "/assets/import", CSV_ASSETS_CANONICO)
    assert resp.status_code == 200
    assert "Mapeamento de Colunas" in resp.text
    assert "tombamento" in resp.text
    assert "TMB-0001" in resp.text  # amostra do conteúdo da coluna
    # Sugestões auto pré-selecionadas no select
    assert 'data-confidence="auto"' in resp.text


def test_mapeamento_colunas_desconhecidas(client):
    """FR-005: coluna sem campo → "não utilizada", destacada, nunca silenciada."""
    content = "tombamento,equipamento,categoria,cor\nTMB-0001,Notebook,notebook,preto\n"
    resp = _upload_csv(client, "/assets/import", content)
    assert resp.status_code == 200
    assert "Mapeamento de Colunas" in resp.text
    assert "não utilizada" in resp.text
    assert 'data-confidence="desconhecida"' in resp.text


def test_mapeamento_colunas_ambiguas_sem_selecao(client):
    """FR-003: coluna ambígua aparece como sugestão a confirmar (sem seleção)."""
    import app.services.import_intelligence as ii

    tabela_com_colisao = {
        "descricao": "name",
        "descrição": "description",
        "filial": "branch",
        "departamento": "department",
    }
    orig = dict(ii._KIND_ALIASES["locations"])
    ii._KIND_ALIASES["locations"] = tabela_com_colisao
    try:
        resp = _upload_csv(client, "/locations/import", CSV_LOCALS_DESCRICAO)
    finally:
        ii._KIND_ALIASES["locations"] = orig

    assert resp.status_code == 200
    assert "Mapeamento de Colunas" in resp.text
    assert 'data-confidence="ambigua"' in resp.text
    assert "confirme o campo" in resp.text


def test_mapeamento_manual_alterado_e_aplicado(client):
    """Teste I: mapeamento manual alterado é aplicado na fase seguinte."""
    # Coluna 'cod' não é reconhecida: usuário mapeia manualmente para tombamento
    content = "cod,equipamento,categoria\nTMB-MANUAL,Notebook,notebook\n"
    step_map = _upload_csv(client, "/assets/import", content)
    assert "Mapeamento de Colunas" in step_map.text

    # Usuário altera o select da coluna 'cod' para tombamento e avança
    analysis = analyze_columns(content, "assets")
    header = analysis["header"]
    assert header == ["cod", "equipamento", "categoria"]

    step_analyze = client.post(
        "/assets/import",
        data={
            "step": "analyze",
            "csv_content": content,
            "mapping": '{"cod": "tombamento", "equipamento": "equipamento", "categoria": "categoria"}',
            "skip_duplicates": "true",
        },
    )
    assert step_analyze.status_code == 200
    assert "Pré-visualização" in step_analyze.text
    assert "TMB-MANUAL" in step_analyze.text  # mapeamento manual aplicado


def test_avancar_sem_obrigatorios_bloqueado(client):
    """Contrato §3: avançar exige obrigatórios da entidade mapeados."""
    content = "cod,equipamento\nTMB-SEM-CAT,Notebook\n"
    resp = _upload_csv(client, "/assets/import", content)
    assert "Mapeamento de Colunas" in resp.text
    # categoria ausente do mapeamento → bloqueio server-side
    analysis = analyze_columns(content, "assets")
    mapeados = {"cod": "tombamento", "equipamento": "equipamento"}
    faltantes = [f for f in ("tombamento", "equipamento", "categoria") if f not in mapeados.values()]
    assert faltantes == ["categoria"]

    step_analyze = client.post(
        "/assets/import",
        data={
            "step": "analyze",
            "csv_content": content,
            "mapping": '{"cod": "tombamento", "equipamento": "equipamento"}',
            "skip_duplicates": "true",
        },
    )
    assert "Pré-visualização" not in step_analyze.text
    assert "Mapeamento de Colunas" in step_analyze.text
    assert "categoria" in step_analyze.text


def test_arquivo_vazio_erro_compreensivel(client):
    """Teste J (R6/FR-021): arquivo vazio → mensagem amigável, sem traceback."""
    resp = _upload_csv(client, "/assets/import", "")
    assert resp.status_code == 200
    assert "Mapeamento de Colunas" not in resp.text
    assert "vazio" in resp.text.lower()
    assert "Traceback" not in resp.text


def test_csv_corrompido_erro_controlado(client):
    """Teste K (R6): CSV corrompido (aspas não fechadas) → erro controlado."""
    content = 'tombamento,equipamento,categoria\nTMB-001,"Notebook,notebook\n'
    resp = _upload_csv(client, "/assets/import", content)
    assert resp.status_code == 200
    assert "Traceback" not in resp.text


def test_encoding_invalido_erro_controlado(client):
    """R6: bytes não-UTF-8 → mensagem amigável, sem traceback."""
    resp = client.post(
        "/assets/import",
        files={"file": ("latin.csv", io.BytesIO(b"tombamento;nome\xff\xfe\xfd"), "text/csv")},
        data={"skip_duplicates": "true"},
    )
    assert resp.status_code == 200
    assert "Traceback" not in resp.text
    assert "Mapeamento de Colunas" not in resp.text


def test_extensao_nao_csv_rejeitada(client):
    """R6/FR-021: extensão não-CSV → mensagem compreensível (guarda vigente)."""
    resp = client.post(
        "/assets/import",
        files={"file": ("dados.txt", io.BytesIO(b"qualquer coisa"), "text/plain")},
        data={"skip_duplicates": "true"},
    )
    assert resp.status_code == 200
    assert "Arquivo inválido" in resp.text


def test_encoding_utf8_sig_e_acentos_preservados(client):
    """Teste L (FR-019/FR-020): BOM + ponto e vírgula + acentuação lidos e
    preservados na análise."""
    content = "\ufefftombamento;equipamento;categoria\nTMB-BOM1;Notebookação;notebook\n"
    resp = _upload_csv(client, "/assets/import", content)
    assert resp.status_code == 200
    assert "Mapeamento de Colunas" in resp.text
    assert "Notebookação" in resp.text  # valor com acento preservado na amostra

    analysis = analyze_columns(content.replace("\ufeff", ""), "assets")
    by_col = _by_column(analysis)
    assert by_col["tombamento"]["field"] == "tombamento"


def test_upload_custodians_e_locations_renderizam_mapeamento(client):
    """O mesmo passo de mapeamento nos 3 importadores (contrato §2)."""
    resp_c = _upload_csv(
        client,
        "/custodians/import",
        "matricula;nome;email;cargo;setor\nMAT-1;Ana;ana@x.com;Cargo;Setor\n",
    )
    assert "Mapeamento de Colunas" in resp_c.text
    assert 'data-confidence="auto"' in resp_c.text

    resp_l = _upload_csv(
        client,
        "/locations/import",
        "nome;filial;departamento\nSala de TI;Matriz SP;TI\n",
    )
    assert "Mapeamento de Colunas" in resp_l.text


def test_upload_nao_grava_no_banco(client, db_session):
    """SC-001 na rota: upload/mapeamento não escreve nada no banco."""
    from app.models.asset import Asset

    before = db_session.query(Asset).count()

    _upload_csv(client, "/assets/import", CSV_ASSETS_CANONICO)

    after = db_session.query(Asset).count()
    assert before == after


# ============================================================
# US2 — Classificação por registro (T008: testes A–G do quickstart)
# ============================================================

def test_csv_totalmente_valido_importa_todos(db_session):
    """Teste A: CSV totalmente válido (todos os campos preenchidos) → todos VALIDO."""
    from app.models.location import Location
    from app.models.custodian import Custodian

    db_session.add(Location(name="Sala A", branch="B", department="D"))
    db_session.add(Custodian(registration_code="MAT-A", name="Ana Autoridade",
                             email="ana@x.com", role="Tech", department="TI"))
    db_session.commit()

    content = (
        "tombamento,equipamento,categoria,localizacao,responsavel\n"
        "TMB-A1,Notebook,notebook,Sala A,Ana Autoridade\n"
        "TMB-A2,Monitor,monitor,Sala A,Ana Autoridade\n"
    )
    rows = _apply(content, "assets")
    preview = classify_rows(rows, db_session, "assets")
    assert preview["summary"]["validos"] == 2, preview["rows"]
    assert preview["summary"]["total"] == 2


def test_registros_parciais_aceitos_sem_fabricar_valores(db_session):
    """Teste B (F3/SC-004): sem responsável/sem local → VALIDO com AVISO
    informacional; nenhum valor fabricado."""
    content = "tombamento,equipamento,categoria\nTMB-B1,Cadeira,mobiliario\n"
    rows = _apply(content, "assets")
    preview = classify_rows(rows, db_session, "assets")
    row = preview["rows"][0]
    assert row["status"] == "AVISO"
    assert "Responsável não informado" in row["problems"]
    assert "Local não informado" in row["problems"]
    assert not any("Estoque Central" in p or "Sem responsável" in p for p in row["problems"])


def test_csv_misto_classifica_por_linha(db_session):
    """Teste C (SC-002): CSV misto → classificação individual, sem rejeição em bloco."""
    content = (
        "tombamento,equipamento,categoria\n"
        "TMB-C1,Notebook,notebook\n"        # válido
        "TMB-C2,Impressora,\n"             # ERRO (sem categoria)
        "TMB-C1,Outro,notebook\n"          # DUPLICADO interno
        ",,,\n"                             # IGNORADO (linha em branco)
    )
    rows = _apply(content, "assets")
    preview = classify_rows(rows, db_session, "assets")
    statuses = [r["status"] for r in preview["rows"]]
    # linha 1 (sem local/responsável) → AVISO informacional (F3)
    assert "AVISO" in statuses and "ERRO" in statuses
    assert "DUPLICADO" in statuses and "IGNORADO" in statuses


def test_tombamento_duplicado_classificado_antes_gravacao(db_session):
    """Teste D: tombamento existente no banco → DUPLICADO antes da gravação."""
    from app.models.asset import Asset

    db_session.add(Asset(tag="TMB-D1", name="Existente", category="OTHER"))
    db_session.commit()

    content = "tombamento,equipamento,categoria\nTMB-D1,Novo,notebook\n"
    rows = _apply(content, "assets")
    preview = classify_rows(rows, db_session, "assets")
    row = preview["rows"][0]
    assert row["status"] == "DUPLICADO"
    assert "já existe" in row["problems"][0]


def test_duplicidade_interna_do_arquivo(db_session):
    """Teste E: tombamento repetido no arquivo → DUPLICADO com internal_dup_of."""
    content = "tombamento,equipamento,categoria\nTMB-E1,Primeiro,notebook\nTMB-E1,Segundo,notebook\n"
    rows = _apply(content, "assets")
    preview = classify_rows(rows, db_session, "assets")
    dup = [r for r in preview["rows"] if r["status"] == "DUPLICADO"]
    assert len(dup) == 1
    assert dup[0]["internal_dup_of"] == 2
    assert "linha 2" in dup[0]["problems"][0]


def test_responsavel_inexistente_resolucao_interativa(db_session):
    """Teste F (FR-010): responsável inexistente → NAO_ENCONTRADO, com resolução
    R4 disponível (assign/sem_custodia/skip) — nenhuma atribuição automática."""
    content = "tombamento,equipamento,categoria,responsavel\nTMB-F1,Notebook,notebook,Inexistente Silva\n"
    rows = _apply(content, "assets")
    preview = classify_rows(rows, db_session, "assets")
    row = preview["rows"][0]
    assert row["status"] == "NAO_ENCONTRADO"
    assert "Responsável não encontrado: Inexistente Silva" in row["problems"][0]
    assert preview["needs_resolution"] == [row["row_num"]]

    # Resolução R4: sem_custodia → linha entra no lote SEM custodiante;
    # assign → com o colaborador escolhido; skip → linha removida.
    from app.models.custodian import Custodian
    db_session.add(Custodian(registration_code="MAT-R4", name="Colaborador R4",
                             email="r4@x.com", role="Tech", department="TI"))
    db_session.commit()
    c = db_session.query(Custodian).filter_by(registration_code="MAT-R4").first()

    lote_skip = apply_resolutions(preview["rows"], {row["row_num"]: "skip"}, db_session)
    assert lote_skip == []

    lote_sem = apply_resolutions(preview["rows"], {row["row_num"]: "sem_custodia"}, db_session)
    assert len(lote_sem) == 1 and lote_sem[0]["custodiante"] == ""

    lote_assign = apply_resolutions(preview["rows"], {row["row_num"]: f"assign:{c.id}"}, db_session)
    # assign resolve para a MATRÍCULA do colaborador escolhido (identificador
    # único e determinístico; _resolver_custodiante prioriza matrícula)
    assert lote_assign[0]["custodiante"] == "MAT-R4"


def test_duplicado_com_responsavel_inexistente_revela_ambos(db_session):
    """Regressão do caso real (homologação): linha com tombamento JÁ CADASTRADO
    e responsável INEXISTENTE era classificada só como DUPLICADO — o problema do
    responsável só estourava na execução ('Linha 20: colaborador ... não
    encontrado'). Agora a preview mostra NAO_ENCONTRADO com ambos os motivos e
    oferece a resolução interativa também nessas linhas."""
    from app.models.asset import Asset

    db_session.add(Asset(tag="TMB-DUPCUST", name="Existente", category="OTHER"))
    db_session.commit()

    content = (
        "tombamento,equipamento,categoria,responsavel\n"
        "TMB-DUPCUST,Notebook Atualizado,notebook,Fabíola Inexistente\n"
    )
    rows = _apply(content, "assets")
    preview = classify_rows(rows, db_session, "assets")
    row = preview["rows"][0]

    # A linha NÃO passa como DUPLICADO 'limpo': o problema do responsável fica
    # visível ANTES da gravação (SC-005/SC-009)
    assert row["status"] == "NAO_ENCONTRADO"
    assert any("Responsável não encontrado: Fabíola Inexistente" in p for p in row["problems"])
    assert any("Tombamento já existe" in p for p in row["problems"])
    assert preview["needs_resolution"] == [row["row_num"]]


def test_local_inexistente_avisos_e_regras_atuais(db_session):
    """Teste G (F6): local inexistente em equipamentos → regra atual preservada
    (linha rejeitada com mensagem clara); sem local → AVISO informacional."""
    content = (
        "tombamento,equipamento,categoria,localizacao\n"
        "TMB-G1,Notebook,notebook,Local Inexistente XY\n"
        "TMB-G2,Monitor,monitor,\n"
    )
    rows = _apply(content, "assets")
    preview = classify_rows(rows, db_session, "assets")
    by_status = {r["status"]: r for r in preview["rows"]}
    assert by_status["ERRO"]["problems"][0].startswith("Local 'Local Inexistente XY' não encontrado")
    assert by_status["AVISO"]["problems"] == ["Local não informado", "Responsável não informado"]


def test_linhas_em_branco_ignoradas(db_session):
    """Edge case: linhas em branco → IGNORADO, sem erro."""
    rows = _apply("tombamento,equipamento,categoria\nTMB-H1,Notebook,notebook\n,,,\n", "assets")
    preview = classify_rows(rows, db_session, "assets")
    ign = [r for r in preview["rows"] if r["status"] == "IGNORADO"]
    assert len(ign) == 1


def test_colunas_desconhecidas_marcadas_nao_utilizadas(db_session):
    """Teste H (FR-005): coluna desconhecida não entra nos valores resolved —
    nada descartado em silêncio (fica visível no mapeamento) nem gravado."""
    content = "tombamento,equipamento,categoria,cor\nTMB-H2,Notebook,notebook,preto\n"
    rows = _apply(content, "assets")
    preview = classify_rows(rows, db_session, "assets")
    assert "cor" not in preview["rows"][0]["resolved_values"]
    # sem local/responsável → AVISO (F3), não VALIDO
    assert preview["summary"]["avisos"] == 1
    assert preview["summary"]["validos"] == 0


def test_classificacao_colaboradores_e_locais(db_session):
    """US2 nos outros importadores: duplicata por e-mail (014) e por nome (locais)."""
    from app.models.custodian import Custodian
    from app.models.location import Location

    db_session.add(Custodian(registration_code="MAT-U2", name="Existente U2",
                             email="u2@x.com", role="Tech", department="TI"))
    db_session.add(Location(name="Sala U2", branch="B", department="D"))
    db_session.commit()

    rows_c = _apply(
        "matricula;nome;email;cargo;setor\nMAT-U2;Outro Nome;outra@x.com;Cargo;Setor\n",
        "custodians",
    )
    preview_c = classify_rows(rows_c, db_session, "custodians")
    assert preview_c["rows"][0]["status"] == "DUPLICADO"
    assert "Matrícula já cadastrada" in preview_c["rows"][0]["problems"][0]

    rows_l = _apply("nome;filial;departamento\nSala U2;B;D\n", "locations")
    preview_l = classify_rows(rows_l, db_session, "locations")
    assert preview_l["rows"][0]["status"] == "DUPLICADO"


# ============================================================
# US3 — Confirmação, gravação segura e relatório (T013)
# ============================================================

def _confirmar_smart(client, url_confirm, csv_content, kind, extra=None):
    """Fluxo completo: upload → mapeamento (padrão) → confirm com payload
    classificado. Retorna (resposta_do_confirm, payload_da_preview)."""
    upload = _upload_csv(client, url_confirm.replace("/confirm", ""), csv_content)
    assert "Mapeamento de Colunas" in upload.text
    analysis = analyze_columns(csv_content, kind)
    mapping = {
        s["column"]: s["field"]
        for s in analysis["suggestions"]
        if s["confidence"] == "auto" and s["field"]
    }
    step_analyze = client.post(
        url_confirm.replace("/confirm", ""),
        data={"step": "analyze", "csv_content": csv_content, "mapping": json.dumps(mapping),
              "skip_duplicates": "true"},
    )
    assert "Pré-visualização Classificada" in step_analyze.text

    data = {
        "csv_data": step_analyze.text.split('name="csv_data" style="display:none;">')[1].split("</textarea>")[0],
        "skip_duplicates": "true",
    }
    data.update(extra or {})
    confirm = client.post(url_confirm, data=data)
    return confirm, None


def test_us3_confirmacao_grava_validos_e_nunca_erros(client):
    """US3.1/SC-006: confirm grava válidos (e avisos), nunca ERRO;
    DUPLICADO segue skip_duplicates (marcado → pulados)."""
    content = (
        "tombamento,equipamento,categoria\n"
        "TMB-U31,Notebook,notebook\n"      # válido
        "TMB-U32,Impressora,\n"            # ERRO — nunca gravado
        "TMB-U33,Monitor,monitor\n"        # válido
    )
    confirm, _ = _confirmar_smart(client, "/assets/import/confirm", content, "assets")
    assert confirm.status_code == 200
    assert "Importação Concluída" in confirm.text

    from app.models.asset import Asset
    db = db_from_client(client)
    try:
        tags = {a.tag for a in db.query(Asset).all()}
        assert {"TMB-U31", "TMB-U33"} <= tags
        assert "TMB-U32" not in tags
    finally:
        db.close()


def test_us3_resolucoes_aplicadas_na_gravacao(client):
    """US3.2 (R4): resolutions aplicadas antes do execute — skip remove a linha,
    sem_custodia grava sem custodiante, assign grava com o colaborador."""
    from app.models.custodian import Custodian

    db = db_from_client(client)
    try:
        db.add(Custodian(registration_code="MAT-U3A", name="Colaborador U3A",
                         email="u3a@x.com", role="Tech", department="TI"))
        db.commit()
        c = db.query(Custodian).filter_by(registration_code="MAT-U3A").first()
        c_id = c.id
    finally:
        db.close()

    content = (
        "tombamento,equipamento,categoria,responsavel\n"
        "TMB-U3A,Notebook A,notebook,Ninguém Com Este Nome\n"  # NAO_ENCONTRADO
        "TMB-U3B,Notebook B,notebook,Outro Cara\n"              # NAO_ENCONTRADO
        "TMB-U3C,Notebook C,notebook,\n"                        # válido (sem responsável)
    )
    upload = _upload_csv(client, "/assets/import", content)
    analysis = analyze_columns(content, "assets")
    mapping = {s["column"]: s["field"] for s in analysis["suggestions"] if s["field"]}
    step_analyze = client.post(
        "/assets/import",
        data={"step": "analyze", "csv_content": content, "mapping": json.dumps(mapping),
              "skip_duplicates": "true"},
    )

    import re as _re
    payload = step_analyze.text.split('name="csv_data" style="display:none;">')[1].split("</textarea>")[0]
    rows_payload = _extract_preview_payload(step_analyze)
    neno = [r for r in rows_payload if r["status"] == "NAO_ENCONTRADO"]
    assert len(neno) == 2
    resolutions = {
        neno[0]["row_num"]: f"assign:{c_id}",
        neno[1]["row_num"]: "sem_custodia",
    }

    confirm = client.post(
        "/assets/import/confirm",
        data={
            "csv_data": payload,
            "skip_duplicates": "true",
            "resolutions": json.dumps(resolutions),
        },
    )
    assert confirm.status_code == 200

    from app.models.asset import Asset
    from app.models.movement import Movement
    from app.models.enums import MovementType
    db = db_from_client(client)
    try:
        a = db.query(Asset).filter(Asset.tag == "TMB-U3A").first()
        b = db.query(Asset).filter(Asset.tag == "TMB-U3B").first()
        cc = db.query(Asset).filter(Asset.tag == "TMB-U3C").first()
        assert a is not None and a.custodian_id == c_id   # assign aplicado
        assert b is not None and b.custodian_id is None   # sem_custodia
        assert cc is not None and cc.custodian_id is None # sem responsável
        # Fluxo patrimonial preservado (FR-016): custódia via movimentação
        movs_a = db.query(Movement).filter(Movement.asset_id == a.id).all()
        assert any(m.movement_type == MovementType.ALLOCATION for m in movs_a)
    finally:
        db.close()


def test_us3_duplicados_com_skip_duplicates(client):
    """Clarify: skip_duplicates marcado → duplicados pulados; desmarcado →
    reimportação atualiza (regra 029 preservada)."""
    content = "tombamento,equipamento,categoria\nTMB-U3D,Notebook,notebook\n"
    # 1ª importação
    confirm1, _ = _confirmar_smart(client, "/assets/import/confirm", content, "assets")
    assert confirm1.status_code == 200

    # Reenvio do mesmo arquivo (skip marcado) → DUPLICADO pulado (FR-018)
    confirm2, _ = _confirmar_smart(client, "/assets/import/confirm", content, "assets")
    assert confirm2.status_code == 200
    from app.models.asset import Asset
    db = db_from_client(client)
    try:
        assert db.query(Asset).filter(Asset.tag == "TMB-U3D").count() == 1
    finally:
        db.close()

    # Reenvio sem skip → atualiza (não duplica)
    upload = _upload_csv(client, "/assets/import", content)
    analysis = analyze_columns(content, "assets")
    mapping = {s["column"]: s["field"] for s in analysis["suggestions"] if s["field"]}
    step_analyze = client.post(
        "/assets/import",
        data={"step": "analyze", "csv_content": content, "mapping": json.dumps(mapping),
              "skip_duplicates": "false"},
    )
    payload = step_analyze.text.split('name="csv_data" style="display:none;">')[1].split("</textarea>")[0]
    confirm3 = client.post(
        "/assets/import/confirm",
        data={"csv_data": payload, "skip_duplicates": "false"},
    )
    assert "Importação Concluída" in confirm3.text
    db = db_from_client(client)
    try:
        a = db.query(Asset).filter(Asset.tag == "TMB-U3D").first()
        assert a is not None and a.name == "Notebook"
        assert db.query(Asset).filter(Asset.tag == "TMB-U3D").count() == 1
    finally:
        db.close()


def test_us3_erro_na_gravacao_rollback_da_linha(client):
    """Teste N (F7): erro na gravação → rollback da linha (029), demais linhas
    preservadas, mensagem clara — sem estado parcial oculto."""
    # TMB-U3E tem serial conflitante com linha seguinte → 2ª linha em erro
    # na execução; a 1ª e a 3ª linhas devem ser gravadas.
    content = (
        "tombamento,equipamento,categoria,serie\n"
        "TMB-U3E1,Notebook 1,notebook,SN-OK-1\n"
        "TMB-U3E2,Notebook 2,notebook,SN-CONFLITO\n"
        "TMB-U3E3,Notebook 3,notebook,\n"
    )
    # Semeia o conflito de serial ANTES (serial único já cadastrado)
    from app.models.asset import Asset as _Asset
    db = db_from_client(client)
    try:
        db.add(_Asset(tag="TMB-SEED", name="Seed", category="OTHER", serial_number="SN-CONFLITO"))
        db.commit()
    finally:
        db.close()

    confirm, _ = _confirmar_smart(client, "/assets/import/confirm", content, "assets")
    # _confirmar_smart usa a URL para ambas as fases; passa a URL correta:
    assert confirm.status_code == 200

    db = db_from_client(client)
    try:
        from app.models.asset import Asset as _AssetQ
        assert db.query(_AssetQ).filter(_AssetQ.tag == "TMB-U3E1").first() is not None
        assert db.query(_AssetQ).filter(_AssetQ.tag == "TMB-U3E2").first() is None
        assert db.query(_AssetQ).filter(_AssetQ.tag == "TMB-U3E3").first() is not None
        # Mensagem clara com o motivo (relatório por linha — SC-009)
        assert "SN-CONFLITO" in confirm.text
    finally:
        db.close()


def test_us3_auditoria_com_quantidades_por_classificacao(client):
    """Teste O (FR-022/SC-008): write_audit com quantidades por classificação,
    sem segredos."""
    content = (
        "tombamento,equipamento,categoria,localizacao\n"
        "TMB-U3F1,Notebook,notebook,Sala O\n"
        "TMB-U3F2,Impressora,\n"   # ERRO
    )
    from app.models.location import Location as _LocO
    db0 = db_from_client(client)
    try:
        db0.add(_LocO(name="Sala O", branch="B", department="D"))
        db0.commit()
    finally:
        db0.close()
    confirm, _ = _confirmar_smart(client, "/assets/import/confirm", content, "assets")
    assert confirm.status_code == 200

    from app.models.audit_log import AuditLog
    from app.services.audit_service import ACTION_IMPORT
    db = db_from_client(client)
    try:
        log = (
            db.query(AuditLog)
            .filter(AuditLog.action == ACTION_IMPORT, AuditLog.module == "Patrimônio")
            .order_by(AuditLog.id.desc())
            .first()
        )
        assert log is not None
        assert "ERRO: 1" in (log.description or "")
        assert "AVISO: 1" in (log.description or "")
        # Nenhuma credencial na descrição (SC-008)
        assert "senha" not in (log.description or "").lower()
        assert "token" not in (log.description or "").lower()
    finally:
        db.close()


def test_us3_reenvio_mesmo_arquivo_classifica_duplicado(client):
    """US3.4/FR-018: reenvio do mesmo arquivo → já importados como DUPLICADO
    (estado atual do banco relido — nada duplicado)."""
    content = "tombamento,equipamento,categoria\nTMB-U3G,Notebook,notebook\n"
    confirm1, _ = _confirmar_smart(client, "/assets/import/confirm", content, "assets")
    assert "Importação Concluída" in confirm1.text

    upload = _upload_csv(client, "/assets/import", content)
    analysis = analyze_columns(content, "assets")
    mapping = {s["column"]: s["field"] for s in analysis["suggestions"] if s["field"]}
    step_analyze = client.post(
        "/assets/import",
        data={"step": "analyze", "csv_content": content, "mapping": json.dumps(mapping),
              "skip_duplicates": "true"},
    )
    # A segunda análise relê o banco: registro já importado aparece DUPLICADO
    assert "DUPLICADO" in step_analyze.text
    assert "Tombamento já existe no cadastro: TMB-U3G" in step_analyze.text


def test_us3_relatorio_final_por_linha(client):
    """US3.3/SC-009 (contrato §6): relatório final com resumo + tabela por linha
    (linha, situação, identificador, motivo) construída de row_results."""
    content = (
        "tombamento,equipamento,categoria,serie\n"
        "TMB-U3H1,Notebook 1,notebook,SN-CONF-H\n"
        "TMB-U3H2,Notebook 2,notebook,\n"
    )
    from app.models.asset import Asset as _AssetH
    db = db_from_client(client)
    try:
        db.add(_AssetH(tag="TMB-SEED-H", name="Seed H", category="OTHER", serial_number="SN-CONF-H"))
        db.commit()
    finally:
        db.close()

    confirm, _ = _confirmar_smart(client, "/assets/import/confirm", content, "assets")
    assert confirm.status_code == 200
    assert "Relatório da Importação" in confirm.text
    assert "TMB-U3H1" in confirm.text
    assert "SN-CONF-H" in confirm.text
    assert "Linha" in confirm.text


def test_fluxo_real_do_formulario_mapeamento(client):
    """Regressão do fluxo REAL da UI: o passo de mapeamento envia um select por
    coluna (mapping_<coluna>) — sem campo JSON `mapping`. O servidor deve montar
    o mapeamento a partir dos campos dinâmicos (bug de campo ausente corrigido)."""
    content = "tombamento,equipamento,categoria\nTMB-FORM1,Notebook,notebook\n"
    upload = _upload_csv(client, "/assets/import", content)
    assert "Mapeamento de Colunas" in upload.text

    # O que o navegador envia ao avançar (nenhum campo `mapping`):
    step_analyze = client.post(
        "/assets/import",
        data={
            "step": "analyze",
            "csv_content": content,
            "filename": "arquivo.csv",
            "skip_duplicates": "true",
            "mapping_tombamento": "tombamento",
            "mapping_equipamento": "equipamento",
            "mapping_categoria": "categoria",
        },
    )
    assert step_analyze.status_code == 200
    assert "Pré-visualização Classificada" in step_analyze.text
    assert "TMB-FORM1" in step_analyze.text


def test_preview_renderiza_dropdown_atribuir_a(client):
    """Regressão da resolução real: cada linha NAO_ENCONTRADO oferece o grupo
    "Atribuir a…" com opções assign:<id> dos colaboradores ativos do cadastro
    (nome + matrícula) — e não mais o placeholder sem ação."""
    from app.models.custodian import Custodian as _C
    db = db_from_client(client)
    try:
        db.add(_C(registration_code="MAT-DROP1", name="Diana Droppable",
                  email="diana@x.com", role="Tech", department="TI"))
        db.commit()
    finally:
        db.close()

    content = (
        "tombamento,equipamento,categoria,responsavel\n"
        "TMB-DROP1,Notebook,notebook,Ninguém Assim\n"
    )
    upload = _upload_csv(client, "/assets/import", content)
    step_analyze = client.post(
        "/assets/import",
        data={
            "step": "analyze",
            "csv_content": content,
            "skip_duplicates": "true",
            "mapping_tombamento": "tombamento",
            "mapping_equipamento": "equipamento",
            "mapping_categoria": "categoria",
            "mapping_responsavel": "custodiante",
        },
    )
    assert "Pré-visualização Classificada" in step_analyze.text
    assert 'optgroup label="Atribuir a…"' in step_analyze.text
    diana = db_from_client(client)
    try:
        c = diana.query(_C).filter_by(registration_code="MAT-DROP1").first()
        assert f'assign:{c.id}' in step_analyze.text
        assert "Diana Droppable (MAT-DROP1)" in step_analyze.text
    finally:
        diana.close()


def test_preview_explica_as_tres_opcoes_de_resolucao(client):
    """Orientação ao usuário (Princípio XI): quando há linhas NAO_ENCONTRADO, a
    preview explica a diferença entre as três opções — Importar sem custódia
    (cadastra o bem sem responsável), Pular linha (nada é gravado) e Atribuir
    a… (custódia do colaborador escolhido)."""
    content = (
        "tombamento,equipamento,categoria,responsavel\n"
        "TMB-HELP1,Notebook,notebook,Ninguém Assim\n"
    )
    upload = _upload_csv(client, "/assets/import", content)
    step_analyze = client.post(
        "/assets/import",
        data={
            "step": "analyze",
            "csv_content": content,
            "skip_duplicates": "true",
            "mapping_tombamento": "tombamento",
            "mapping_equipamento": "equipamento",
            "mapping_categoria": "categoria",
            "mapping_responsavel": "custodiante",
        },
    )
    assert "Pré-visualização Classificada" in step_analyze.text
    # Painel explicativo das três opções
    assert "cadastra o equipamento" in step_analyze.text          # sem custódia
    assert "nada é gravado" in step_analyze.text                  # pular linha
    assert "com a custódia" in step_analyze.text                  # atribuir a…
    assert "Fluxo &amp; Movimentação" in step_analyze.text        # destino pós-importação


def test_fluxo_real_resolucao_por_linha_no_confirm(client):
    """Regressão do confirm real: resoluções chegam como selects por linha
    (resolution_<row_num>), não como JSON único. sem_custodia grava sem
    custodiante; skip remove a linha."""
    content = (
        "tombamento,equipamento,categoria,responsavel\n"
        "TMB-RES1,Notebook 1,notebook,Ninguém Assim\n"
        "TMB-RES2,Notebook 2,notebook,Ninguém Assim\n"
    )
    upload = _upload_csv(client, "/assets/import", content)
    assert "Mapeamento de Colunas" in upload.text

    step_analyze = client.post(
        "/assets/import",
        data={
            "step": "analyze",
            "csv_content": content,
            "filename": "arquivo.csv",
            "skip_duplicates": "true",
            "mapping_tombamento": "tombamento",
            "mapping_equipamento": "equipamento",
            "mapping_categoria": "categoria",
            "mapping_responsavel": "custodiante",
        },
    )
    assert "Pré-visualização Classificada" in step_analyze.text
    payload = _extract_preview_payload(step_analyze)
    neno = [r for r in payload if r["status"] == "NAO_ENCONTRADO"]
    assert len(neno) == 2

    confirm = client.post(
        "/assets/import/confirm",
        data={
            "csv_data": step_analyze.text.split('name="csv_data" style="display:none;">')[1].split("</textarea>")[0],
            "skip_duplicates": "true",
            f"resolution_{neno[0]['row_num']}": "sem_custodia",
            f"resolution_{neno[1]['row_num']}": "skip",
        },
    )
    assert confirm.status_code == 200
    assert "Importação Concluída" in confirm.text

    from app.models.asset import Asset as _A
    db = db_from_client(client)
    try:
        assert db.query(_A).filter(_A.tag == "TMB-RES1").first() is not None  # sem_custodia gravou
        assert db.query(_A).filter(_A.tag == "TMB-RES1").first().custodian_id is None
        assert db.query(_A).filter(_A.tag == "TMB-RES2").first() is None      # skip removeu
    finally:
        db.close()


def test_importacao_bloqueada_sem_permissao(db_session, unauth_client):
    """Teste P (FR-023): usuário sem permissão bloqueado nas fases de
    import/confirm das 3 rotas (permissões vigentes inalteradas)."""
    def _make_user(db, username, role_names=None, is_admin=False):
        from tests.test_rbac import _make_user as rbac_make_user
        return rbac_make_user(db, username, role_names, is_admin)

    _make_user(db_session, "semperm048", role_names=["Consulta"])
    _login(unauth_client, "semperm048")

    assert unauth_client.get("/assets/import").status_code == 403
    assert unauth_client.post(
        "/assets/import",
        files={"file": ("a.csv", io.BytesIO(b"tombamento\nX"), "text/csv")},
    ).status_code == 403
    assert unauth_client.post("/assets/import/confirm", data={"csv_data": "[]"}).status_code == 403

    assert unauth_client.get("/custodians/import").status_code == 403
    assert unauth_client.post("/custodians/import/confirm", data={"csv_data": "[]"}).status_code == 403

    assert unauth_client.get("/locations/import").status_code == 403
    assert unauth_client.post(
        "/locations/import/confirm", data={"csv_data": "[]"}
    ).status_code == 403
