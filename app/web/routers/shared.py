"""Shared module for domain routers (Feature 051).

Contains code SHARED between domains, moved LITERALLY from
`app/web/routes.py` (MOVE, DO NOT REWRITE — plan F1):

- Import helpers of Feature 048 (`_confirm_payload_rows`,
  `_apply_mapping_to_rows`, `_read_csv_upload`, `_mapping_samples`,
  `_render_mapping_step`, `_render_smart_preview`, `_dynamic_form`) —
  used by assets, custodians and locations.

Imports `templates` from the facade (`app.web.routes`), which holds the
Jinja2 configuration and global injection (FR-004: single occurrence).
"""
from typing import Optional

from fastapi import Request, UploadFile
from sqlalchemy.orm import Session

from app.services.import_intelligence import (
    analyze_columns,
    classify_rows,
    apply_resolutions,
    classify_summary_counts,
    REQUIRED_FIELDS as IMPORT_REQUIRED_FIELDS,
    FIELD_LABELS as IMPORT_FIELD_LABELS,
)
from app.web.routers.templates_env import templates


def _confirm_payload_rows(csv_data: Optional[str], resolutions: Optional[str],
                          db: Session, dynamic_form: Optional[dict] = None,
                          csv_content: Optional[str] = None,
                          mapping_raw: Optional[str] = None,
                          kind: Optional[str] = None):
    """Feature 048: monta o lote do confirm a partir de três fontes, em ordem:
    (a) csv_content + mapping (fluxo real da preview 048): o servidor REEXECUTA
        a classificação contra o estado atual do banco (nunca confia no payload
        vindo do cliente — defesa em profundidade) e aplica as resoluções
        coletadas (ERRO/IGNORADO nunca — FR-014; NAO_ENCONTRADO conforme as
        decisões por linha — R4);
    (b) csv_data como payload classificado ({row_num, status, resolved_values})
        — compatibilidade com o formato intermediário;
    (c) csv_data como lista canônica (fluxo antigo/R9, sem alteração).
    As resoluções chegam como selects por linha (resolution_<row_num>, formato
    da preview real) ou como JSON único no campo `resolutions` (automações).
    Retorna (lote_para_execute, counts_ou_None, erro_ou_None)."""
    import json as _json
    import html as _html_mod

    resolutions_map: dict = {}
    if resolutions:
        try:
            parsed = _json.loads(resolutions)
            if isinstance(parsed, dict):
                resolutions_map = parsed
        except (ValueError, _json.JSONDecodeError):
            resolutions_map = {}
    for key, value in (dynamic_form or {}).items():
        if isinstance(key, str) and key.startswith("resolution_"):
            try:
                resolutions_map[int(key.rsplit("_", 1)[1])] = value
            except (ValueError, IndexError):
                continue

    # (a) fluxo real: reclassifica server-side a partir do conteúdo + mapeamento
    if csv_content and mapping_raw and kind:
        try:
            parsed_mapping = _json.loads(mapping_raw)
            if not isinstance(parsed_mapping, dict) or not parsed_mapping:
                raise ValueError
        except (ValueError, _json.JSONDecodeError):
            return None, None, "Mapeamento inválido no confirm."
        rows_renorm = _apply_mapping_to_rows(csv_content, parsed_mapping, kind)
        preview = classify_rows(rows_renorm, db, kind)
        lote = apply_resolutions(preview["rows"], resolutions_map, db)
        counts = classify_summary_counts(preview["rows"])
        return lote, counts, None

    # (b)/(c) csv_data legado
    if csv_data:
        try:
            decoded = _html_mod.unescape(csv_data)
            payload = _json.loads(decoded)
            if not isinstance(payload, list):
                raise ValueError("Dados inválidos: esperado uma lista de registros")
        except (ValueError, _json.JSONDecodeError) as e:
            return None, None, str(e)

        if payload and isinstance(payload[0], dict) and "resolved_values" in payload[0]:
            lote = apply_resolutions(payload, resolutions_map, db)
            counts = classify_summary_counts(payload)
            return lote, counts, None
        return payload, None, None

    return None, None, "Dados da confirmação ausentes. Envie o arquivo novamente."


def _read_csv_upload(request: Request, file: UploadFile, template_name: str, active_tab: str):
    """Feature 048 (R6/FR-021): leitura guardada do upload — extensão, encoding
    e decodificação controladas. Retorna (content, error_response).
    Nenhuma exceção cruza para o usuário."""
    if not file.filename or not file.filename.endswith(".csv"):
        return None, templates.TemplateResponse(
            request=request,
            name=template_name,
            context={
                "active_tab": active_tab,
                "error": "Arquivo inválido. Envie um arquivo .csv",
            }
        )
    raw = file.file.read()
    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None, templates.TemplateResponse(
            request=request,
            name=template_name,
            context={
                "active_tab": active_tab,
                "error": "Encoding inválido: o arquivo deve estar em UTF-8 (com ou sem BOM). "
                         "Refaça o upload salvando o arquivo como UTF-8.",
            }
        )
    return content, None


def _mapping_samples(content: str, kind: str) -> dict:
    """Feature 048: primeira linha de dados por coluna (amostra do passo de
    mapeamento), usando a detecção de delimitador do kind."""
    import csv as _csv
    import io as _io
    from app.services.import_intelligence import _detect_delimiter

    analysis = analyze_columns(content, kind)
    if analysis["parse_errors"] and analysis["total_rows"] == 0:
        return {}
    try:
        reader = _csv.DictReader(_io.StringIO(content), delimiter=analysis["delimiter"])
        first = next(reader, None) or {}
        return {
            col: (first.get(col) or "").strip()
            for col in (analysis["header"] or [])
        }
    except Exception:
        return {}


def _render_mapping_step(request: Request, template_name: str, kind: str,
                         content: str, filename: str, skip_duplicates: bool,
                         active_tab: str, form_action: str, back_url: str):
    """Feature 048 (R5): passo intermediário dedicado de mapeamento de colunas
    (decisão clarify 2026-09-26). Renderiza o parcial compartilhado com as
    sugestões de analyze_columns. Somente leitura — nada é gravado (SC-001)."""
    analysis = analyze_columns(content, kind)
    return templates.TemplateResponse(
        request=request,
        name=template_name,
        context={
            "active_tab": active_tab,
            "show_mapping": True,
            "analysis": analysis,
            "samples": _mapping_samples(content, kind),
            "csv_content": content,
            "filename": filename,
            "skip_duplicates": skip_duplicates,
            "field_labels": IMPORT_FIELD_LABELS[kind],
            "required_fields": IMPORT_REQUIRED_FIELDS[kind],
            "form_action": form_action,
            "back_url": back_url,
        }
    )


def _dynamic_form(request: Request):
    """Feature 048: formulários com campos gerados dinamicamente (um select por
    coluna do CSV: mapping_<coluna>; uma decisão por linha NAO_ENCONTRADO:
    resolution_<row_num>) contêm chaves que a assinatura da rota não declara.
    O FastAPI já parseou e cacheou o formulário em request._form quando há
    campos Form(...) declarados — aqui apenas o lemos (parsed by FastAPI;
    nenhuma leitura duplicada do stream). Fallback seguro quando ausente."""
    form = getattr(request, "_form", None)
    return form if form is not None else {}


def _apply_mapping_to_rows(content: str, mapping: dict, kind: str) -> list:
    """Feature 048: renormaliza as linhas do CSV pelo mapeamento confirmado
    (data-model §2.3 resolved_values). Valores originais preservados (R7) —
    o strip() já vigente nos services é mantido."""
    import csv as _csv
    import io as _io
    from app.services.import_intelligence import _detect_delimiter

    delimiter = _detect_delimiter(content, kind)
    reader = _csv.DictReader(_io.StringIO(content), delimiter=delimiter)
    rows = []
    row_num = 2  # linha 1 = cabeçalho (mesma convenção dos parsers)
    for raw in reader:
        resolved = {field: "" for field in set(mapping.values()) if field}
        for original_col, value in raw.items():
            field = mapping.get(original_col or "")
            if field:
                # mesma normalização do parse_csv (travessão de autocorreção,
                # NBSP, espaços múltiplos) para os dois caminhos ficarem iguais
                from app.services.import_service import _normalize_text
                resolved[field] = _normalize_text(value or "")
        rows.append({"row_num": row_num, "resolved": resolved})
        row_num += 1
    return rows


def _render_smart_preview(request: Request, template_name: str, kind: str,
                          content: str, mapping_raw: Optional[str], filename: str,
                          skip_duplicates: bool, active_tab: str,
                          form_action: str, back_url: str, db: Session,
                          dynamic_form: Optional[dict] = None,
                          confirm_action: str = "", filtro: str = "todos"):
    """Feature 048 (US2): classificação por registro + pré-visualização
    classificada. Reexecuta a análise server-side (nunca confia só no cliente).
    Somente leitura — o banco permanece inalterado (SC-001).

    Aceita o mapeamento de duas formas (a UI real usa a primeira):
      (a) campos dinâmicos mapping_<coluna> do formulário do passo de mapeamento;
      (b) campo único `mapping` com JSON {coluna: campo} (automações/testes).

    form_action é a URL de POST da fase analyze (re-POST dos filtros);
    confirm_action é a URL do /confirm (gravação — botão Confirmar).
    """
    import json as _json

    mapping: Optional[dict] = None
    if mapping_raw:
        try:
            parsed = _json.loads(mapping_raw)
            if isinstance(parsed, dict):
                mapping = parsed
        except (ValueError, _json.JSONDecodeError):
            mapping = None
    if mapping is None and dynamic_form:
        mapping = {
            key[len("mapping_"):]: value
            for key, value in dynamic_form.items()
            if isinstance(key, str) and key.startswith("mapping_")
        }
    if not mapping:
        return templates.TemplateResponse(
            request=request,
            name=template_name,
            context={
                "active_tab": active_tab,
                "error": "Dados do mapeamento ausentes. Envie o arquivo novamente.",
            }
        )

    # Guarda do contrato §3: obrigatórios da entidade mapeados
    required = IMPORT_REQUIRED_FIELDS[kind]
    mapped_fields = {v for v in mapping.values() if v}
    missing = [f for f in required if f not in mapped_fields]
    if missing:
        analysis = analyze_columns(content, kind)
        labels = IMPORT_FIELD_LABELS[kind]
        return templates.TemplateResponse(
            request=request,
            name=template_name,
            context={
                "active_tab": active_tab,
                "show_mapping": True,
                "analysis": analysis,
                "samples": _mapping_samples(content, kind),
                "csv_content": content,
                "filename": filename,
                "skip_duplicates": skip_duplicates,
                "field_labels": labels,
                "required_fields": required,
                "form_action": form_action.replace("/confirm", ""),
                "back_url": back_url,
                "mapping_error": (
                    "Avançar exige os campos obrigatórios mapeados: "
                    + ", ".join(labels.get(f, f) for f in missing)
                ),
            }
        )

    analysis = analyze_columns(content, kind)
    rows = _apply_mapping_to_rows(content, mapping, kind)
    preview = classify_rows(rows, db, kind)

    # R4: colaboradores ativos para o dropdown "Atribuir a…" das linhas
    # NAO_ENCONTRADO (pesquisa do cadastro reutilizada; nunca cria)
    custodians_for_assign = []
    if preview["needs_resolution"]:
        from app.models.custodian import Custodian as _Custodian

        custodians_for_assign = (
            db.query(_Custodian)
            .filter(_Custodian.is_active == True)  # noqa: E712 — filtro SQLAlchemy
            .order_by(_Custodian.name.asc())
            .all()
        )

    # Contagens por status para os botões de filtro (badge com quantidade)
    counts_by_status: dict = {}
    for item in preview["rows"]:
        counts_by_status[item["status"]] = counts_by_status.get(item["status"], 0) + 1
    counts_by_status["todos"] = len(preview["rows"])

    return templates.TemplateResponse(
        request=request,
        name=template_name,
        context={
            "active_tab": active_tab,
            "show_smart_preview": True,
            "smart": preview,
            "mapping": mapping,
            "mapping_json": _json.dumps(mapping),
            "csv_content": content,
            "filename": filename,
            "skip_duplicates": skip_duplicates,
            "field_labels": IMPORT_FIELD_LABELS[kind],
            "custodians_for_assign": custodians_for_assign,
            "form_action": form_action,
            "confirm_action": confirm_action or form_action,
            "filtro": filtro,
            "counts_by_status": counts_by_status,
            "resolutions_previas": dynamic_form or {},
            "back_url": back_url,
        }
    )
