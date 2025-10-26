"""
Serviço de geração de relatórios
"""
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict

# Imports do ReportLab
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, Flowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
# --- CORREÇÃO AQUI ---
from reportlab.lib.units import cm, inch # Adiciona inch
# --- FIM CORREÇÃO ---
from reportlab.pdfgen import canvas # Importa canvas para generate_simple_pdf

# Imports do seu projeto
from ..models.entities import DetectionSession, DetectionEvent, ReportData, DailyReport
from ..utils.logger import log_system_event, log_error, log_user_action
from ..config.settings import config_manager

# --- Constantes de Estilo ---
COLOR_PRIMARY = colors.HexColor("#4A90A4")
COLOR_SECONDARY = colors.HexColor("#2C3E50")
COLOR_TEXT_DARK = colors.HexColor("#34495E")
COLOR_TEXT_LIGHT = colors.HexColor("#ECF0F1")
COLOR_GREY = colors.HexColor("#7F8C8D")
COLOR_LIGHT_GREY = colors.HexColor("#BDC3C7")
COLOR_TABLE_HEADER_BG = colors.HexColor("#34495E")
COLOR_TABLE_GRID = colors.lightgrey
COLOR_WHITE = colors.white


class ReportService:
    """Serviço de geração de relatórios aprimorado"""

    def __init__(self, reports_dir: Optional[str] = None):
        if reports_dir is None:
            try:
                 self.reports_dir = Path(getattr(config_manager.config, 'reports_dir', 'reports'))
            except AttributeError:
                 self.reports_dir = Path('reports')
        else:
             self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.styles = self._setup_styles()
        log_system_event(f"REPORT_SERVICE_INITIALIZED: Directory={self.reports_dir.resolve()}")

    def _setup_styles(self) -> Dict[str, ParagraphStyle]:
        """Define estilos de parágrafo para o relatório"""
        base_styles = getSampleStyleSheet()
        styles = {
            'Title': ParagraphStyle(name='Title', parent=base_styles['h1'], fontSize=20, alignment=TA_CENTER, spaceAfter=1*cm, textColor=COLOR_SECONDARY),
            'HeaderInfo': ParagraphStyle(name='HeaderInfo', parent=base_styles['Normal'], fontSize=9, alignment=TA_RIGHT, textColor=COLOR_GREY, rightIndent=0.5*cm),
            'SubHeader': ParagraphStyle(name='SubHeader', parent=base_styles['h2'], fontSize=14, alignment=TA_LEFT, spaceBefore=0.8*cm, spaceAfter=0.4*cm, textColor=COLOR_PRIMARY, borderPadding=(2, 2, 4, 2)),
            'BodyText': ParagraphStyle(name='BodyText', parent=base_styles['Normal'], fontSize=10, alignment=TA_LEFT, spaceAfter=3, textColor=COLOR_TEXT_DARK),
            'Footer': ParagraphStyle(name='Footer', parent=base_styles['Normal'], fontSize=8, alignment=TA_CENTER, textColor=COLOR_GREY),
            'TableCellLabel': ParagraphStyle(name='TableCellLabel', parent=base_styles['Normal'], fontSize=10, alignment=TA_LEFT, textColor=COLOR_TEXT_LIGHT, fontName='Helvetica-Bold'),
            'TableCellValue': ParagraphStyle(name='TableCellValue', parent=base_styles['Normal'], fontSize=10, alignment=TA_LEFT, textColor=COLOR_TEXT_DARK),
            'TableCellValueBold': ParagraphStyle(name='TableCellValueBold', parent=base_styles['Normal'], fontSize=10, alignment=TA_LEFT, textColor=COLOR_TEXT_DARK, fontName='Helvetica-Bold'),
        }
        return styles

    def _add_page_elements(self, canvas, doc):
        """Adiciona cabeçalho (logo, data) e rodapé (nome, página) em cada página"""
        canvas.saveState()
        page_width = doc.pagesize[0]; page_height = doc.pagesize[1]
        try: # Logo
            logo_path = "logo.png"
            if Path(logo_path).exists():
                max_logo_w = 3*cm; max_logo_h = 1.5*cm
                img = Image(logo_path); img_w, img_h = img._img.getSize()
                ratio = min(max_logo_w / img_w, max_logo_h / img_h) if img_w > 0 and img_h > 0 else 1
                logo_w, logo_h = img_w * ratio, img_h * ratio
                canvas.drawImage(logo_path, doc.leftMargin, page_height - doc.topMargin - logo_h + 0.5*cm, width=logo_w, height=logo_h, mask='auto')
        except Exception: pass
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S") # Data/Hora Geração
        canvas.setFont('Helvetica', 8); canvas.setFillColor(COLOR_GREY)
        canvas.drawRightString(page_width - doc.rightMargin, page_height - doc.topMargin + 0.5*cm, f"Gerado em: {now}")
        page_num = canvas.getPageNumber() # Rodapé
        text = f"LAS Cams System v2.0 | Contagem Automática | Página {page_num}"
        canvas.setFont('Helvetica', 8); canvas.setFillColor(COLOR_GREY)
        canvas.drawCentredString(page_width / 2.0, doc.bottomMargin / 2.0, text)
        canvas.restoreState()

    def generate_daily_report(
            self,
            report_data: DailyReport,
            filename: Optional[str] = None
        ) -> Optional[str]:
        """Gera um relatório PDF aprimorado para uma sessão usando Platypus."""
        if filename is None:
            ts = report_data.horaInicio.strftime("%Y%m%d_%H%M%S")
            safe_cam_name = "".join(c if c.isalnum() else "_" for c in report_data.camera_name)
            filename = f"Relatorio_{safe_cam_name}_{ts}.pdf"
        filepath = self.reports_dir / filename
        log_system_event(f"GENERATING_ENHANCED_REPORT: {filepath}")

        try:
            doc = SimpleDocTemplate(str(filepath), pagesize=A4, leftMargin=1.5*cm, rightMargin=1.5*cm, topMargin=2.5*cm, bottomMargin=2.0*cm)
            Story: List[Flowable] = []
            Story.append(Paragraph("Relatório de Sessão de Contagem", self.styles['Title']))
            Story.append(Paragraph("Resumo da Sessão", self.styles['SubHeader']))

            start_time_str = report_data.horaInicio.strftime("%d/%m/%Y %H:%M:%S")
            end_time_str = report_data.horaTermino.strftime("%H:%M:%S")
            duration_delta = report_data.horaTermino - report_data.horaInicio
            hours, remainder = divmod(int(max(0, duration_delta.total_seconds())), 3600) # Garante não negativo
            minutes, seconds = divmod(remainder, 60)
            duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

            table_data = [
                [Paragraph('Câmera:', self.styles['TableCellLabel']), Paragraph(report_data.camera_name, self.styles['TableCellValue'])],
                [Paragraph('Tipo de Carga:', self.styles['TableCellLabel']), Paragraph(report_data.tipo.value, self.styles['TableCellValue'])],
                [Paragraph('Início da Sessão:', self.styles['TableCellLabel']), Paragraph(start_time_str, self.styles['TableCellValue'])],
                [Paragraph('Fim da Sessão:', self.styles['TableCellLabel']), Paragraph(end_time_str, self.styles['TableCellValue'])],
                [Paragraph('Duração Total:', self.styles['TableCellLabel']), Paragraph(duration_str, self.styles['TableCellValue'])],
                [Paragraph('Contagem Total:', self.styles['TableCellLabel']), Paragraph(str(report_data.total), self.styles['TableCellValueBold'])],
            ]
            table = Table(table_data, colWidths=[4*cm, None])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), COLOR_TABLE_HEADER_BG),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, COLOR_LIGHT_GREY),
                ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 8), ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ]))
            Story.append(table)
            Story.append(Spacer(1, 1*cm))

            doc.build(Story, onFirstPage=self._add_page_elements, onLaterPages=self._add_page_elements)
            log_system_event(f"ENHANCED_REPORT_GENERATED: {filepath}")
            return str(filepath)
        except Exception as e:
            log_error("ReportService", e, f"Erro crítico ao gerar relatório PDF aprimorado: {filepath}")
            return None

    def generate_simple_pdf(self, user: str, camera_id: int, session: DetectionSession) -> Optional[str]:
        """Gera relatório simples em PDF (compatibilidade ou fallback)"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"Relatorio_Simples_Cam{camera_id}_{timestamp}.pdf"
            filepath = self.reports_dir / filename

            # Usa a instância de canvas importada
            c = canvas.Canvas(str(filepath), pagesize=A4)
            width, height = A4

            # Título Simples
            c.setFont("Helvetica-Bold", 18)
            c.drawCentredString(width / 2.0, height - 1 * inch, f"Relatório Simples - Câmera {camera_id}") # Usa inch

            # Informações Básicas
            c.setFont("Helvetica", 11)
            textobject = c.beginText(1 * inch, height - 2 * inch) # Usa inch
            textobject.textLine(f"Usuário: {user}")
            textobject.textLine(f"Câmera ID: {camera_id}")
            textobject.textLine(f"Tipo de Carga: {session.cargo_type.value}")
            textobject.textLine(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
            textobject.textLine(f"Início Sessão: {session.start_time.strftime('%d/%m/%Y %H:%M:%S')}")
            if session.end_time:
                textobject.textLine(f"Fim Sessão: {session.end_time.strftime('%H:%M:%S')}")
                duration = session.get_duration()
                textobject.textLine(f"Duração: {str(duration).split('.')[0]}")
            else:
                 textobject.textLine("Fim Sessão: (Ainda ativa)")
                 textobject.textLine("Duração: (Em andamento)")

            textobject.setFont("Helvetica-Bold", 12)
            textobject.moveCursor(0, 14)
            textobject.textLine(f"Contagem Total: {session.detection_count}")

            c.drawText(textobject)
            c.save()

            log_system_event(f"SIMPLE_REPORT_GENERATED: {filepath}")
            return str(filepath)
        except Exception as e:
            log_error("ReportService", e, f"Erro ao gerar relatório PDF simples para câmera {camera_id}")
            return None

    def get_reports_list(self) -> List[dict]:
        """Retorna lista de relatórios gerados (arquivos PDF)"""
        reports = []
        try:
            for file_path in self.reports_dir.glob("*.pdf"):
                try:
                    stat = file_path.stat()
                    reports.append({
                        'filename': file_path.name,
                        'filepath': str(file_path.resolve()),
                        'size_kb': round(stat.st_size / 1024, 2),
                        'created': datetime.fromtimestamp(stat.st_ctime),
                        'modified': datetime.fromtimestamp(stat.st_mtime)
                    })
                except Exception as file_e:
                     log_error("ReportService", file_e, f"Erro ao processar arquivo de relatório: {file_path.name}")
                     continue
        except Exception as e:
            log_error("ReportService", e, f"Erro ao listar diretório de relatórios: {self.reports_dir}")
        return sorted(reports, key=lambda x: x['created'], reverse=True)

    def delete_report(self, filename: str) -> bool:
        """Remove um arquivo de relatório pelo nome"""
        try:
            file_path = self.reports_dir / filename
            if file_path.exists() and file_path.is_file():
                file_path.unlink()
                log_system_event(f"REPORT_DELETED: {filename}")
                return True
            else:
                 log_error("ReportService", None, f"Tentativa de deletar relatório não encontrado: {filename}")
                 return False
        except Exception as e:
            log_error("ReportService", e, f"Erro ao deletar relatório {filename}")
            return False