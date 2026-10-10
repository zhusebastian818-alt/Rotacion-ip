"""Service for generating Excel reports (.xlsx) for traffic fine queries in CABA and Provincia de Buenos Aires."""

import io
import logging
from typing import List
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from app.models.fine import VehicleFinesResponse

logger = logging.getLogger(__name__)


class ExcelReportService:
    """Service to export aggregated accumulated traffic fines to Excel (.xlsx) format."""

    @staticmethod
    def generate_fines_excel(reports: List[VehicleFinesResponse]) -> bytes:
        """Generate a professionally styled Excel workbook containing cumulative fine details for CABA and PBA."""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Reporte de Multas"

        # Ensure gridlines are visible
        ws.views.sheetView[0].showGridLines = True

        # Styles
        font_family = "Segoe UI"
        
        title_font = Font(name=font_family, size=16, bold=True, color="1B365D")
        subtitle_font = Font(name=font_family, size=10, italic=True, color="555555")
        
        header_font = Font(name=font_family, size=11, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1B365D", end_color="1B365D", fill_type="solid")
        
        data_font = Font(name=font_family, size=10, color="333333")
        bold_data_font = Font(name=font_family, size=10, bold=True, color="333333")
        
        summary_fill = PatternFill(start_color="F2F5F9", end_color="F2F5F9", fill_type="solid")
        
        thin_border = Border(
            left=Side(style="thin", color="D3D3D3"),
            right=Side(style="thin", color="D3D3D3"),
            top=Side(style="thin", color="D3D3D3"),
            bottom=Side(style="thin", color="D3D3D3"),
        )
        
        summary_border = Border(
            left=Side(style="thin", color="1B365D"),
            right=Side(style="thin", color="1B365D"),
            top=Side(style="medium", color="1B365D"),
            bottom=Side(style="medium", color="1B365D"),
        )

        align_center = Alignment(horizontal="center", vertical="center")
        align_left = Alignment(horizontal="left", vertical="center")
        align_right = Alignment(horizontal="right", vertical="center")

        # Title Block
        ws.append(["REPORTE ACUMULADO DE INFRACCIONES - CABA Y PROVINCIA DE BUENOS AIRES"])
        ws.merge_cells("A1:H1")
        ws["A1"].font = title_font
        ws["A1"].alignment = align_left
        ws.row_dimensions[1].height = 25

        ws.append([f"Generado el: {reports[0].queried_at.strftime('%Y-%m-%d %H:%M:%S UTC') if reports else ''} | Motor B2B de Monitoreo"])
        ws.merge_cells("A2:H2")
        ws["A2"].font = subtitle_font
        ws["A2"].alignment = align_left
        ws.row_dimensions[2].height = 18

        ws.append([])  # Blank row
        ws.row_dimensions[3].height = 10

        # Table Headers
        headers = [
            "Dominio / Patente",
            "Jurisdicción / Autoridad",
            "ID Infracción",
            "Código",
            "Fecha Emisión",
            "Descripción",
            "Estado",
            "Monto (ARS)"
        ]
        ws.append(headers)
        ws.row_dimensions[4].height = 24

        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=4, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = align_center
            cell.border = thin_border

        row_idx = 5
        grand_total = 0.0
        total_infractions_count = 0

        for report in reports:
            plate = report.plate_number
            if not report.fines:
                # Add row indicating no fines found for this plate
                ws.append([plate, "Sin Infracciones", "-", "-", "-", "Sin multas registradas en CABA/PBA", "LIMPIO", 0.0])
                ws.row_dimensions[row_idx].height = 20
                for col_idx in range(1, 9):
                    c = ws.cell(row=row_idx, column=col_idx)
                    c.font = data_font
                    c.border = thin_border
                    if col_idx in [1, 3, 4, 5, 7]:
                        c.alignment = align_center
                    elif col_idx == 8:
                        c.alignment = align_right
                        c.number_format = "$#,##0.00"
                    else:
                        c.alignment = align_left
                row_idx += 1
            else:
                for fine in report.fines:
                    total_infractions_count += 1
                    grand_total += fine.amount
                    
                    ws.append([
                        plate,
                        fine.authority,
                        fine.fine_id,
                        fine.infraction_code,
                        fine.issue_date.strftime("%Y-%m-%d"),
                        fine.description,
                        fine.status.value,
                        fine.amount
                    ])
                    ws.row_dimensions[row_idx].height = 20

                    for col_idx in range(1, 9):
                        c = ws.cell(row=row_idx, column=col_idx)
                        c.font = data_font
                        c.border = thin_border
                        if col_idx in [1, 3, 4, 5, 7]:
                            c.alignment = align_center
                        elif col_idx == 8:
                            c.alignment = align_right
                            c.number_format = "$#,##0.00"
                        else:
                            c.alignment = align_left
                    row_idx += 1

        # Summary Row
        ws.append([])
        row_idx += 1

        ws.cell(row=row_idx, column=1, value="TOTAL GENERAL ACUMULADO").font = bold_data_font
        ws.cell(row=row_idx, column=1).alignment = align_left
        ws.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=7)

        total_cell = ws.cell(row=row_idx, column=8, value=grand_total)
        total_cell.font = bold_data_font
        total_cell.alignment = align_right
        total_cell.number_format = "$#,##0.00"

        for col_idx in range(1, 9):
            c = ws.cell(row=row_idx, column=col_idx)
            c.fill = summary_fill
            c.border = summary_border

        ws.row_dimensions[row_idx].height = 24

        # Auto-fit column widths
        col_widths = {
            "A": 18,  # Dominio
            "B": 45,  # Autoridad
            "C": 20,  # ID Infracción
            "D": 15,  # Código
            "E": 15,  # Fecha Emisión
            "F": 60,  # Descripción
            "G": 15,  # Estado
            "H": 18,  # Monto
        }
        for col_letter, width in col_widths.items():
            ws.column_dimensions[col_letter].width = width

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output.getvalue()
