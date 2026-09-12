import io
import csv
from datetime import datetime
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.asset import Asset
from app.models.movement import Movement
from app.models.custodian import Custodian
from app.services.asset_service import AssetService
from app.services.custodian_service import CustodianService
from app.services.inventario_service import InventarioService
from app.models.enums import AssetStatus, AssetCategory, InventarioStatus, InventarioItemStatus
from app.models.inventario import Inventario, InventarioItem


class ReportService:
    @staticmethod
    def get_filtered_assets(db: Session, search: Optional[str] = None,
                           status: Optional[str] = None, category: Optional[str] = None,
                           location_id: Optional[int] = None, custodian_id: Optional[int] = None,
                           brand: Optional[str] = None, model: Optional[str] = None,
                           department: Optional[str] = None, maintenance_status: Optional[str] = None,
                           purchase_date_from: Optional[datetime] = None, purchase_date_to: Optional[datetime] = None,
                           skip: int = 0, limit: int = 0) -> Tuple[List[Asset], int]:
        """
        Retorna os assets filtrados conforme os parâmetros informados.
        Se limit=0, retorna todos os resultados sem paginação.
        """
        status_enum = None
        if status:
            try:
                status_enum = AssetStatus(status)
            except ValueError:
                pass
        
        category_enum = None
        if category:
            try:
                category_enum = AssetCategory(category)
            except ValueError:
                pass
        
        # Define limite: se for 0, usa um valor alto para pegar todos
        limit_query = limit if limit > 0 else 10000
        
        assets, total = AssetService.get_all(
            db,
            search=search,
            status=status_enum,
            category=category_enum,
            location_id=location_id,
            custodian_id=custodian_id,
            brand=brand,
            model=model,
            department=department,
            maintenance_status=maintenance_status,
            purchase_date_from=purchase_date_from,
            purchase_date_to=purchase_date_to,
            skip=skip,
            limit=limit_query
        )
        return assets, total

    @staticmethod
    def generate_inventory_csv(db: Session, assets: Optional[List[Asset]] = None,
                               search: Optional[str] = None, status: Optional[str] = None,
                               category: Optional[str] = None, location_id: Optional[int] = None,
                               custodian_id: Optional[int] = None, brand: Optional[str] = None,
                               model: Optional[str] = None, department: Optional[str] = None,
                               maintenance_status: Optional[str] = None,
                               purchase_date_from: Optional[datetime] = None,
                               purchase_date_to: Optional[datetime] = None) -> str:
        """Gera um arquivo CSV com os bens filtrados conforme os parâmetros informados"""
        assets, _ = ReportService.get_filtered_assets(
            db, search=search, status=status, category=category,
            location_id=location_id, custodian_id=custodian_id,
            brand=brand, model=model, department=department,
            maintenance_status=maintenance_status,
            purchase_date_from=purchase_date_from, purchase_date_to=purchase_date_to,
            limit=0  # Sem paginação - exporta todos
        )

        output = io.StringIO()
        writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_MINIMAL)

        # Cabeçalho
        writer.writerow([
            "Tombamento / Tag",
            "Nome do Bem",
            "Categoria",
            "Marca",
            "Modelo",
            "Número de Série",
            "Status",
            "Condição",
            "Localização Atual",
            "Responsável Atual",
            "Data Aquisição",
            "Valor de Compra (R$)",
            "Depreciação Acumulada (R$)",
            "Valor Contábil Atual (R$)",
            "Nota Fiscal",
            "Fornecedor"
        ])

        for asset in assets:
            deprec = AssetService.calculate_depreciation(asset)
            loc_name = f"{asset.location.branch} - {asset.location.department}" if asset.location else "Não alocado"
            cust_name = f"{asset.custodian.name} ({asset.custodian.registration_code})" if asset.custodian else "Estoque / Livre"
            dt_purchase = asset.purchase_date.strftime("%d/%m/%Y") if asset.purchase_date else ""

            writer.writerow([
                asset.tag,
                asset.name,
                asset.category.label,
                asset.brand or "",
                asset.model or "",
                asset.serial_number or "",
                asset.status.label,
                asset.condition.label,
                loc_name,
                cust_name,
                dt_purchase,
                f"{asset.purchase_value:.2f}",
                f"{deprec['depreciated_amount']:.2f}",
                f"{deprec['current_value']:.2f}",
                asset.invoice_number or "",
                asset.supplier or ""
            ])

        return output.getvalue()

    @staticmethod
    def generate_inventory_excel(db: Session, assets: Optional[List[Asset]] = None,
                               search: Optional[str] = None, status: Optional[str] = None,
                               category: Optional[str] = None, location_id: Optional[int] = None,
                               custodian_id: Optional[int] = None, brand: Optional[str] = None,
                               model: Optional[str] = None, department: Optional[str] = None,
                               maintenance_status: Optional[str] = None,
                               purchase_date_from: Optional[datetime] = None,
                               purchase_date_to: Optional[datetime] = None) -> bytes:
        """Gera um arquivo Excel .xlsx com os bens filtrados conforme os parâmetros informados"""
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
        from openpyxl.utils import get_column_letter
        
        assets, _ = ReportService.get_filtered_assets(
            db, search=search, status=status, category=category,
            location_id=location_id, custodian_id=custodian_id,
            brand=brand, model=model, department=department,
            maintenance_status=maintenance_status,
            purchase_date_from=purchase_date_from, purchase_date_to=purchase_date_to,
            limit=0
        )
        
        wb = Workbook()
        ws = wb.active
        ws.title = "Inventário Patrimonial"
        
        # Cabeçalho
        headers = [
            "Tombamento / Tag",
            "Nome do Bem",
            "Categoria",
            "Marca",
            "Modelo",
            "Número de Série",
            "Status",
            "Condição",
            "Localização Atual",
            "Responsável Atual",
            "Data Aquisição",
            "Valor de Compra (R$)",
            "Depreciação Acumulada (R$)",
            "Valor Contábil Atual (R$)",
            "Nota Fiscal",
            "Fornecedor"
        ]
        
        # Estilos
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # Escrever cabeçalho
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border
        
        # Escrever dados
        for row_idx, asset in enumerate(assets, 2):
            deprec = AssetService.calculate_depreciation(asset)
            loc_name = f"{asset.location.branch} - {asset.location.department}" if asset.location else "Não alocado"
            cust_name = f"{asset.custodian.name} ({asset.custodian.registration_code})" if asset.custodian else "Estoque / Livre"
            dt_purchase = asset.purchase_date.strftime("%d/%m/%Y") if asset.purchase_date else ""
            
            row_data = [
                asset.tag,
                asset.name,
                asset.category.label,
                asset.brand or "",
                asset.model or "",
                asset.serial_number or "",
                asset.status.label,
                asset.condition.label,
                loc_name,
                cust_name,
                dt_purchase,
                asset.purchase_value,
                deprec['depreciated_amount'],
                deprec['current_value'],
                asset.invoice_number or "",
                asset.supplier or ""
            ]
            
            for col, value in enumerate(row_data, 1):
                cell = ws.cell(row=row_idx, column=col, value=value)
                cell.border = thin_border
                if col >= 12:  # Colunas numéricas
                    cell.number_format = "#,##0.00"
        
        # Ajustar largura das colunas
        for col in range(1, len(headers) + 1):
            max_length = len(str(ws.cell(row=1, column=col).value))
            for row in range(2, len(assets) + 2):
                cell_value = str(ws.cell(row=row, column=col).value) if ws.cell(row=row, column=col).value else ""
                max_length = max(max_length, len(cell_value))
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[get_column_letter(col)].width = adjusted_width
        
        # Salvar em bytes
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output.getvalue()

    @staticmethod
    def generate_inventory_pdf(db: Session, assets: Optional[List[Asset]] = None,
                               search: Optional[str] = None, status: Optional[str] = None,
                               category: Optional[str] = None, location_id: Optional[int] = None,
                               custodian_id: Optional[int] = None, brand: Optional[str] = None,
                               model: Optional[str] = None, department: Optional[str] = None,
                               maintenance_status: Optional[str] = None,
                               purchase_date_from: Optional[datetime] = None,
                               purchase_date_to: Optional[datetime] = None) -> bytes:
        """Gera um arquivo PDF com os bens filtrados conforme os parâmetros informados"""
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        
        assets, _ = ReportService.get_filtered_assets(
            db, search=search, status=status, category=category,
            location_id=location_id, custodian_id=custodian_id,
            brand=brand, model=model, department=department,
            maintenance_status=maintenance_status,
            purchase_date_from=purchase_date_from, purchase_date_to=purchase_date_to,
            limit=0
        )
        
        output = io.BytesIO()
        
        # Usar A4 em paisagem para maior largura
        page_size = landscape(A4)
        # Margens: 12mm nas laterais para dar mais espaço à tabela
        left_margin = 12*mm
        right_margin = 12*mm
        top_margin = 18*mm
        bottom_margin = 15*mm
        
        # Calcula largura útil da página
        available_width = page_size[0] - left_margin - right_margin
        
        doc = SimpleDocTemplate(output, pagesize=page_size, 
                                leftMargin=left_margin, rightMargin=right_margin,
                                topMargin=top_margin, bottomMargin=bottom_margin)
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=14, alignment=TA_CENTER, spaceAfter=10)
        subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'], fontSize=10, alignment=TA_CENTER, textColor=colors.grey, spaceAfter=15)
        
        elements = []
        
        # Título
        elements.append(Paragraph("Inventário Patrimonial", title_style))
        elements.append(Paragraph(f"SisPatrimônio Pro - {datetime.now().strftime('%d/%m/%Y %H:%M')}", subtitle_style))
        
        # Filtros aplicados
        filters_text = ""
        if search:
            filters_text += f"Busca: {search}"
        if status:
            filters_text += (f" | Status: {status}" if filters_text else f"Status: {status}")
        if category:
            filters_text += (f" | Categoria: {category}" if filters_text else f"Categoria: {category}")
        if location_id:
            filters_text += (f" | Localização: {location_id}" if filters_text else f"Localização: {location_id}")
        if custodian_id:
            filters_text += (f" | Responsável: {custodian_id}" if filters_text else f"Responsável: {custodian_id}")
        if filters_text:
            elements.append(Paragraph(f"<b>Filtros aplicados:</b> {filters_text}", ParagraphStyle('Filters', parent=styles['Normal'], fontSize=9, textColor=colors.grey, spaceAfter=12)))
        
        # Cabeçalho da tabela
        headers = [
            "Tag",
            "Nome",
            "Categoria",
            "Marca",
            "Modelo",
            "Série",
            "Status",
            "Localização",
            "Responsável",
            "Data",
            "Valor (R$)"
        ]
        
        # Construir dados da tabela
        table_data = [headers]
        for asset in assets:
            loc_name = f"{asset.location.branch} - {asset.location.department}" if asset.location else "Não alocado"
            cust_name = f"{asset.custodian.name}" if asset.custodian else "Estoque"
            dt_purchase = asset.purchase_date.strftime("%d/%m/%Y") if asset.purchase_date else ""
            
            # Usar Paragraph para todos os campos que podem ter texto longo, garantindo quebra de linha
            cell_style = ParagraphStyle('CellSmall', parent=styles['Normal'], fontSize=7, leading=9)
            
            row = [
                Paragraph(asset.tag or "", cell_style),
                Paragraph(asset.name or "", cell_style),
                Paragraph(asset.category.label if asset.category else "", cell_style),
                Paragraph(asset.brand or "", cell_style),
                Paragraph(asset.model or "", cell_style),
                Paragraph(asset.serial_number or "", cell_style),
                Paragraph(asset.status.label if asset.status else "", cell_style),
                Paragraph(loc_name, cell_style),
                Paragraph(cust_name, cell_style),
                Paragraph(dt_purchase, cell_style),
                Paragraph(f"R$ {asset.purchase_value:,.2f}", ParagraphStyle('CellRight', parent=styles['Normal'], fontSize=7, leading=9, alignment=TA_CENTER))
            ]
            table_data.append(row)
        
        # Calcular larguras das colunas proporcionalmente à área disponível
        # Distribuição ponderada por importância/visibilidade dos dados
        column_weights = [
            4,   # Tag
            7,   # Nome
            4,   # Categoria
            3,   # Marca
            4,   # Modelo
            3,   # Série
            3,   # Status
            5,   # Localização
            4,   # Responsável
            2,   # Data
            3    # Valor
        ]
        total_weight = sum(column_weights)
        
        # Calcular largura de cada coluna baseada no peso e na área disponível
        col_widths = []
        for weight in column_weights:
            col_width = (available_width * weight) / total_weight
            col_widths.append(col_width)
        
        # Criar tabela
        if len(table_data) > 1:
            table = Table(table_data, colWidths=col_widths, repeatRows=1)  # repeatRows=1 repete cabeçalho em todas as páginas
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 7),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('LEFTPADDING', (0, 0), (-1, -1), 2),
                ('RIGHTPADDING', (0, 0), (-1, -1), 2),
                ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.HexColor('#f0f0f0')]),
            ]))
            elements.append(table)
        else:
            elements.append(Paragraph("Nenhum equipamento encontrado com os filtros aplicados.", ParagraphStyle('Empty', parent=styles['Normal'], fontSize=11, textColor=colors.grey, spaceAfter=12)))
        
        # Rodapé com total
        elements.append(Spacer(1, 10*mm))
        elements.append(Paragraph(f"<b>Total de equipamentos:</b> {len(assets)} | Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ParagraphStyle('Footer', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER, textColor=colors.grey)))
        
        doc.build(elements)
        output.seek(0)
        return output.getvalue()

    @staticmethod
    def generate_custodians_csv(db: Session, custodians: Optional[List[Custodian]] = None) -> str:
        """
        Gera um CSV com todos os colaboradores no mesmo formato aceito pela
        importação via CSV (colunas: matricula;nome;email;cargo;setor;cpf;ativo).
        """
        if custodians is None:
            custodians = CustodianService.get_all(db)

        output = io.StringIO()
        writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_MINIMAL)

        writer.writerow([
            "matricula",
            "nome",
            "email",
            "cargo",
            "setor",
            "cpf",
            "ativo",
        ])

        for c in custodians:
            writer.writerow([
                c.registration_code,
                c.name,
                c.email,
                c.role,
                c.department,
                c.cpf or "",
                "sim" if c.is_active else "não",
            ])

        return output.getvalue()

    @staticmethod
    def generate_movements_csv(db: Session, movements: Optional[List[Movement]] = None) -> str:
        """Gera um CSV com a trilha de auditoria e fluxo de movimentação"""
        if movements is None:
            movements = db.query(Movement).order_by(Movement.timestamp.desc()).all()

        output = io.StringIO()
        writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_MINIMAL)

        writer.writerow([
            "Código Movimentação",
            "Data e Hora",
            "Tombamento",
            "Equipamento",
            "Tipo de Movimento",
            "Origem (Local)",
            "Origem (Responsável)",
            "Destino (Local)",
            "Destino (Responsável)",
            "Status Resultante",
            "Motivo / Justificativa",
            "Operador do Registro",
            "Termo de Cautela"
        ])

        for m in movements:
            tag = m.asset.tag if m.asset else "N/A"
            name = m.asset.name if m.asset else "N/A"
            writer.writerow([
                m.movement_uuid,
                m.timestamp.strftime("%d/%m/%Y %H:%M:%S"),
                tag,
                name,
                m.movement_type.label,
                m.origin_location_name or "-",
                m.origin_custodian_name or "-",
                m.destination_location_name or "-",
                m.destination_custodian_name or "-",
                m.new_status.label,
                m.reason,
                m.operator_name,
                m.term_code or "-"
            ])

        return output.getvalue()

    # ==================================================================
    # INVENTÁRIO PATRIMONIAL — ATA COMPROBATÓRIA (CSV / PDF)
    # ==================================================================

    @staticmethod
    def _inventario_rows(db: Session, inventario: Inventario) -> List[dict]:
        """Monta as linhas da ata de conferência (comuns ao CSV e ao PDF)."""
        inv = InventarioService.get_by_id(db, inventario.id) or inventario
        rows = []
        for item in inv.itens:
            asset = item.asset
            rows.append({
                "nao_previsto": bool(item.nao_previsto),
                "tag": asset.tag if asset else str(item.asset_id),
                "nome": asset.name if asset else "",
                "categoria": asset.category.label if asset and asset.category else "",
                "local_esperado": item.expected_location_name or "Estoque Central",
                "responsavel_esperado": item.expected_custodian_name or "Estoque / Livre",
                "resultado": item.status.label,
                "local_encontrado": item.found_location_name or "-",
                "conferido_em": item.checked_at.strftime("%d/%m/%Y %H:%M") if item.checked_at else "-",
                "conferido_por": item.checked_by_name or "-",
                "observacao": item.observation or "",
            })
        return rows

    @staticmethod
    def generate_inventario_csv(db: Session, inventario: Inventario) -> str:
        """Gera a ata comprobatória do inventário em CSV (delimitador ';', BOM handled by endpoint)."""
        rows = ReportService._inventario_rows(db, inventario)

        output = io.StringIO()
        writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_MINIMAL)

        # Bloco de comprovação (cabeçalho formal)
        writer.writerow(["ATA DE INVENTÁRIO PATRIMONIAL"])
        writer.writerow(["Código", inventario.code])
        writer.writerow(["Nome", inventario.name])
        writer.writerow(["Escopo", inventario.scope_filters or "Todo o acervo"])
        writer.writerow(["Status", inventario.status.label])
        writer.writerow(["Criado por", inventario.created_by_name or "-"])
        writer.writerow(["Criado em", inventario.created_at.strftime("%d/%m/%Y %H:%M") if inventario.created_at else "-"])
        if inventario.started_at:
            writer.writerow(["Conferência iniciada em", inventario.started_at.strftime("%d/%m/%Y %H:%M")])
        if inventario.closed_at:
            writer.writerow(["Encerrado em", inventario.closed_at.strftime("%d/%m/%Y %H:%M")])
            writer.writerow(["Encerrado por", inventario.closed_by_name or "-"])
        if inventario.closure_notes:
            writer.writerow(["Notas do encerramento", inventario.closure_notes])
        writer.writerow([])

        writer.writerow([
            "Tipo",
            "Tombamento",
            "Descrição",
            "Categoria",
            "Local Esperado",
            "Responsável Esperado",
            "Resultado",
            "Local Encontrado",
            "Conferido em",
            "Conferido por",
            "Observação",
        ])

        for r in rows:
            writer.writerow([
                "Bem não previsto" if r["nao_previsto"] else "Esperado",
                r["tag"],
                r["nome"],
                r["categoria"],
                r["local_esperado"],
                r["responsavel_esperado"],
                r["resultado"],
                r["local_encontrado"],
                r["conferido_em"],
                r["conferido_por"],
                r["observacao"],
            ])

        return output.getvalue()

    @staticmethod
    def generate_inventario_pdf(db: Session, inventario: Inventario) -> bytes:
        """Gera a ata comprobatória do inventário em PDF (paisagem A4, padrão dos relatórios existentes)."""
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.enums import TA_CENTER

        rows = ReportService._inventario_rows(db, inventario)
        summary = InventarioService.summary(db, inventario.id)

        output = io.BytesIO()
        page_size = landscape(A4)
        left_margin = 12 * mm
        right_margin = 12 * mm
        top_margin = 18 * mm
        bottom_margin = 15 * mm
        available_width = page_size[0] - left_margin - right_margin

        doc = SimpleDocTemplate(output, pagesize=page_size,
                                leftMargin=left_margin, rightMargin=right_margin,
                                topMargin=top_margin, bottomMargin=bottom_margin)

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('InvTitle', parent=styles['Heading1'], fontSize=14, alignment=TA_CENTER, spaceAfter=4)
        subtitle_style = ParagraphStyle('InvSubtitle', parent=styles['Normal'], fontSize=10, alignment=TA_CENTER, textColor=colors.grey, spaceAfter=10)
        meta_style = ParagraphStyle('InvMeta', parent=styles['Normal'], fontSize=9, spaceAfter=2)
        cell_style = ParagraphStyle('InvCell', parent=styles['Normal'], fontSize=7, leading=9)

        elements = [
            Paragraph("Ata de Inventário Patrimonial", title_style),
            Paragraph(f"{inventario.code} — {inventario.name}", subtitle_style),
            Paragraph(f"<b>Escopo:</b> {inventario.scope_filters or 'Todo o acervo'}", meta_style),
            Paragraph(f"<b>Status:</b> {inventario.status.label}", meta_style),
            Paragraph(
                f"<b>Criado por</b> {inventario.created_by_name or '-'} "
                f"em {inventario.created_at.strftime('%d/%m/%Y %H:%M') if inventario.created_at else '-'}",
                meta_style,
            ),
        ]
        if inventario.started_at:
            elements.append(Paragraph(f"<b>Conferência iniciada em</b> {inventario.started_at.strftime('%d/%m/%Y %H:%M')}", meta_style))
        if inventario.closed_at:
            elements.append(Paragraph(
                f"<b>Encerrado por</b> {inventario.closed_by_name or '-'} "
                f"em {inventario.closed_at.strftime('%d/%m/%Y %H:%M')}",
                meta_style,
            ))
        if inventario.closure_notes:
            elements.append(Paragraph(f"<b>Notas do encerramento:</b> {inventario.closure_notes}", meta_style))
        elements.append(Paragraph(
            f"<b>Consolidação:</b> {summary['expected']} esperados | "
            f"{summary['found']} encontrados | {summary['wrong_location']} em local diferente | "
            f"{summary['not_found']} não encontrados | {summary['unidentified']} sem identificação | "
            f"{summary['unlisted']} não previstos",
            ParagraphStyle('InvSummary', parent=styles['Normal'], fontSize=9, spaceBefore=4, spaceAfter=10),
        ))

        headers = [
            "Tipo", "Tombamento", "Descrição", "Categoria", "Local Esperado",
            "Responsável Esperado", "Resultado", "Local Encontrado",
            "Conferido em", "Conferido por", "Observação",
        ]
        table_data = [[Paragraph(h, cell_style) for h in headers]]
        for r in rows:
            table_data.append([
                Paragraph("Não previsto" if r["nao_previsto"] else "Esperado", cell_style),
                Paragraph(r["tag"], cell_style),
                Paragraph(r["nome"], cell_style),
                Paragraph(r["categoria"], cell_style),
                Paragraph(r["local_esperado"], cell_style),
                Paragraph(r["responsavel_esperado"], cell_style),
                Paragraph(r["resultado"], cell_style),
                Paragraph(r["local_encontrado"], cell_style),
                Paragraph(r["conferido_em"], cell_style),
                Paragraph(r["conferido_por"], cell_style),
                Paragraph(r["observacao"], cell_style),
            ])

        if len(table_data) > 1:
            column_weights = [4, 5, 7, 4, 6, 6, 5, 6, 4, 4, 8]
            total_weight = sum(column_weights)
            col_widths = [(available_width * w) / total_weight for w in column_weights]
            table = Table(table_data, colWidths=col_widths, repeatRows=1)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 7),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('LEFTPADDING', (0, 0), (-1, -1), 2),
                ('RIGHTPADDING', (0, 0), (-1, -1), 2),
                ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.HexColor('#f0f0f0')]),
            ]))
            elements.append(table)
        else:
            elements.append(Paragraph(
                "Nenhum bem registrado neste inventário.",
                ParagraphStyle('InvEmpty', parent=styles['Normal'], fontSize=11, textColor=colors.grey, spaceAfter=12),
            ))

        elements.append(Spacer(1, 10 * mm))
        elements.append(Paragraph(
            f"<b>Total de registros:</b> {len(rows)} | Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            ParagraphStyle('InvFooter', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER, textColor=colors.grey),
        ))

        doc.build(elements)
        output.seek(0)
        return output.getvalue()

    @staticmethod
    def generate_inventario_excel(db: Session, inventario: Inventario) -> bytes:
        """Gera a ata comprobatória do inventário em Excel (.xlsx)."""
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
        from openpyxl.utils import get_column_letter

        rows = ReportService._inventario_rows(db, inventario)
        summary = InventarioService.summary(db, inventario.id)

        wb = Workbook()
        ws = wb.active
        ws.title = f"Ata {inventario.code}"[:31]

        # Estilos (mesmo padrão do inventário geral)
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        title_font = Font(bold=True, size=14)
        meta_label_font = Font(bold=True)

        # Bloco de comprovação (cabeçalho formal)
        ws.cell(row=1, column=1, value="ATA DE INVENTÁRIO PATRIMONIAL").font = title_font
        meta = [
            ("Código", inventario.code),
            ("Nome", inventario.name),
            ("Escopo", inventario.scope_filters or "Todo o acervo"),
            ("Status", inventario.status.label),
            ("Criado por", inventario.created_by_name or "-"),
            ("Criado em", inventario.created_at.strftime("%d/%m/%Y %H:%M") if inventario.created_at else "-"),
        ]
        if inventario.started_at:
            meta.append(("Conferência iniciada em", inventario.started_at.strftime("%d/%m/%Y %H:%M")))
        if inventario.closed_at:
            meta.append(("Encerrado em", inventario.closed_at.strftime("%d/%m/%Y %H:%M")))
            meta.append(("Encerrado por", inventario.closed_by_name or "-"))
        if inventario.closure_notes:
            meta.append(("Notas do encerramento", inventario.closure_notes))
        meta.append((
            "Consolidação",
            f"{summary['expected']} esperados | {summary['found']} encontrados | "
            f"{summary['wrong_location']} em local diferente | {summary['not_found']} não encontrados | "
            f"{summary['unidentified']} sem identificação | {summary['unlisted']} não previstos",
        ))

        current_row = 2
        for label, value in meta:
            ws.cell(row=current_row, column=1, value=label).font = meta_label_font
            ws.cell(row=current_row, column=2, value=value)
            current_row += 1
        current_row += 1  # linha em branco antes da tabela

        headers = [
            "Tipo",
            "Tombamento",
            "Descrição",
            "Categoria",
            "Local Esperado",
            "Responsável Esperado",
            "Resultado",
            "Local Encontrado",
            "Conferido em",
            "Conferido por",
            "Observação",
        ]
        header_row = current_row
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=header_row, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border

        data_start = header_row + 1
        for i, r in enumerate(rows):
            r_idx = data_start + i
            values = [
                "Bem não previsto" if r["nao_previsto"] else "Esperado",
                r["tag"],
                r["nome"],
                r["categoria"],
                r["local_esperado"],
                r["responsavel_esperado"],
                r["resultado"],
                r["local_encontrado"],
                r["conferido_em"],
                r["conferido_por"],
                r["observacao"],
            ]
            for col, value in enumerate(values, 1):
                cell = ws.cell(row=r_idx, column=col, value=value)
                cell.border = thin_border

        if not rows:
            note = ws.cell(row=data_start, column=1, value="Nenhum bem registrado neste inventário.")
            note.font = Font(italic=True, color="808080")

        # Ajustar largura das colunas (mesma estratégia do inventário geral)
        for col in range(1, len(headers) + 1):
            max_length = len(str(ws.cell(row=header_row, column=col).value))
            for r_idx in range(data_start, data_start + max(len(rows), 1)):
                cell_value = ws.cell(row=r_idx, column=col).value
                if cell_value is not None:
                    max_length = max(max_length, len(str(cell_value)))
            ws.column_dimensions[get_column_letter(col)].width = min(max_length + 2, 50)

        # Rodapé com total
        footer_row = data_start + max(len(rows), 1) + 1
        footer = ws.cell(
            row=footer_row, column=1,
            value=f"Total de registros: {len(rows)} | Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        )
        footer.font = Font(bold=True, size=9, color="808080")

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output.getvalue()
