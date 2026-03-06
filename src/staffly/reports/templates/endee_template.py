"""Endee Engineers salary slip template using ReportLab."""

from decimal import Decimal
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from staffly.database.models import MonthlyPayroll
from .base_template import BaseSlipTemplate, to_decimal, format_currency, number_to_words


class EndeeTemplate(BaseSlipTemplate):
    """
    Salary slip template for ENDEE ENGINEERS PVT. LTD. using ReportLab.
    
    Layout based on the company's standard format.
    """
    
    name = "Endee"
    description = "ENDEE ENGINEERS PVT. LTD. template"
    
    # Colors - muted except for specific sections
    HEADER_BLUE = colors.Color(30/255, 45/255, 100/255)
    GREEN_HEADER = colors.Color(198/255, 224/255, 180/255)  # Muted green for Earnings
    RED_HEADER = colors.Color(248/255, 203/255, 173/255)    # Muted salmon for Deductions
    YELLOW_BG = colors.Color(255/255, 242/255, 204/255)     # Light yellow for amount in words
    BLUE_BG = colors.Color(221/255, 235/255, 247/255)       # Light blue for net payable
    
    def _register_fonts(self):
        """Register Calibri font if available, fallback to Helvetica."""
        try:
            # Try to register Calibri font
            pdfmetrics.registerFont(TTFont('Calibri', 'C:/Windows/Fonts/calibri.ttf'))
            pdfmetrics.registerFont(TTFont('Calibri-Bold', 'C:/Windows/Fonts/calibrib.ttf'))
            return 'Calibri', 'Calibri-Bold'
        except Exception:
            # Fallback to Helvetica
            return 'Helvetica', 'Helvetica-Bold'
    
    def generate(
        self,
        payroll: MonthlyPayroll,
        output_path: Path,
        company_name: str,
        company_address: str,
    ) -> Path:
        """Generate the Endee format salary slip using ReportLab."""
        width, height = A4
        margin = 15 * mm
        content_width = width - 2 * margin
        
        # Register fonts
        font_regular, font_bold = self._register_fonts()
        
        c = canvas.Canvas(str(output_path), pagesize=A4)
        
        employee = payroll.employee
        period = payroll.payroll_period
        
        # Border padding from content
        border_padding = 5 * mm
        
        # Track top of content for border
        y_start = height - 12 * mm
        y = y_start
        
        # ═══════════════════════════════════════════════════════════════════
        # HEADER SECTION
        # ═══════════════════════════════════════════════════════════════════
        # Company Name - Calibri 13, Blue
        c.setFillColor(self.HEADER_BLUE)
        c.setFont(font_bold, 13)
        c.drawCentredString(width / 2, y, company_name)
        y -= 4 * mm
        
        # Address - Calibri 7, Black
        c.setFillColor(colors.black)
        c.setFont(font_regular, 7)
        c.drawCentredString(width / 2, y, company_address)
        y -= 5 * mm
        
        # Monthly Salary Slip - Calibri 9, Black
        c.setFont(font_bold, 9)
        c.drawCentredString(width / 2, y, "Monthly Salary Slip")
        y -= 2 * mm
        
        # Dividing line after header
        c.setStrokeColor(colors.black)
        c.setLineWidth(0.5)
        c.line(margin, y, width - margin, y)
        y -= 1 * mm
        
        # ═══════════════════════════════════════════════════════════════════
        # EMPLOYEE INFO SECTION (No borders, text wrapping)
        # ═══════════════════════════════════════════════════════════════════
        month_str = f"{self._get_month_name(period.month)}-{period.year}"
        joining_date = employee.date_of_joining.strftime("%d-%m-%y") if employee.date_of_joining else "-"
        
        # Create paragraph style for wrapping
        wrap_style = ParagraphStyle(
            'wrap',
            fontName=font_regular,
            fontSize=7,
            leading=7,
            spaceBefore=0,
            spaceAfter=0,
        )
        wrap_style_bold = ParagraphStyle(
            'wrap_bold',
            fontName=font_bold,
            fontSize=7,
            leading=7,
            spaceBefore=0,
            spaceAfter=0,
        )
        
        # Employee info - 8 columns layout
        # Label | Value | Label | Value | Label | Value | Label | Value
        col_widths = [24*mm, 48*mm, 18*mm, 30*mm, 18*mm, 10*mm, 18*mm, 10*mm]
        
        info_data = [
            [Paragraph("Employee Code:", wrap_style), 
             Paragraph(employee.employee_code or "-", wrap_style),
             Paragraph("Month:", wrap_style), 
             Paragraph(month_str, wrap_style_bold),
             Paragraph("Present Days:", wrap_style), 
             Paragraph(str(payroll.present_days or 0), wrap_style),
             Paragraph("<u>Leaves Record:</u>", wrap_style), ""],
            
            [Paragraph("Name of Employee:", wrap_style), 
             Paragraph(employee.full_name or "-", wrap_style),
             Paragraph("Paid Days:", wrap_style), 
             Paragraph(str(payroll.paid_days or 0), wrap_style),
             Paragraph("PL Adjusted:", wrap_style), 
             Paragraph("0", wrap_style),
             Paragraph("PL Balance:", wrap_style), 
             Paragraph("0", wrap_style)],
            
            [Paragraph("Designation:", wrap_style), 
             Paragraph(employee.designation or "-", wrap_style),
             Paragraph("PF (UAN) No.:", wrap_style), 
             Paragraph(employee.uan_number or "NA", wrap_style),
             Paragraph("SL Adjusted:", wrap_style), 
             Paragraph("0", wrap_style),
             Paragraph("SL Balance:", wrap_style), 
             Paragraph("4", wrap_style)],
            
            [Paragraph("Department:", wrap_style), 
             Paragraph(employee.department or "-", wrap_style),
             Paragraph("ESIC No.:", wrap_style), 
             Paragraph(employee.esi_number or "NA", wrap_style),
             Paragraph("CL Adjusted:", wrap_style), 
             Paragraph("0", wrap_style),
             Paragraph("CL Balance:", wrap_style), 
             Paragraph("7", wrap_style)],
            
            [Paragraph("Branch/ Factory:", wrap_style), 
             Paragraph(employee.branch or "-", wrap_style),
             "", "",
             Paragraph("Absent Days:", wrap_style), 
             Paragraph(str(payroll.absent_days or 0), wrap_style),
             "", ""],
            
            [Paragraph("Date of Joining:", wrap_style), 
             Paragraph(joining_date, wrap_style),
             "", "",
             Paragraph("Late Marks:", wrap_style), 
             Paragraph(str(payroll.late_marks or 0), wrap_style),
               "", ""],
        ]
        
        info_table = Table(
            info_data,
            colWidths=col_widths,
            rowHeights=[8] * len(info_data),
        )
        info_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('ALIGN', (4, 0), (4, -1), 'RIGHT'),
            ('ALIGN', (6, 0), (6, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('ALIGN', (3, 0), (3, -1), 'LEFT'),
            ('ALIGN', (5, 0), (5, -1), 'LEFT'),
            ('ALIGN', (7, 0), (7, -1), 'LEFT'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0.25 * mm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0.25 * mm),
        ]))
        
        tw, th = info_table.wrap(content_width, y)
        info_table.drawOn(c, margin, y - th)
        y = y - th - 2.5*mm
        
        # ═══════════════════════════════════════════════════════════════════
        # EARNINGS & DEDUCTIONS SECTION
        # ═══════════════════════════════════════════════════════════════════
        
        # Header row with colored backgrounds
        ed_header = [["Earnings", "Amount", "Deductions", "Amount"]]
        ed_col_widths = [60*mm, 30*mm, 60*mm, 30*mm]
        
        header_table = Table(ed_header, colWidths=ed_col_widths)
        header_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), font_bold),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('BACKGROUND', (0, 0), (1, 0), self.GREEN_HEADER),
            ('BACKGROUND', (2, 0), (3, 0), self.RED_HEADER),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('ALIGN', (3, 0), (3, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('LINEABOVE', (0, 0), (-1, 0), 0.5, colors.black),
            ('LINEBELOW', (0, 0), (-1, 0), 0.5, colors.black),
        ]))
        
        hw, hh = header_table.wrap(content_width, y)
        header_table.drawOn(c, margin, y - hh)
        y = y - hh - 1*mm
        
        # Earnings and Deductions data
        earnings = [
            ("Basic Salary", to_decimal(payroll.basic_salary)),
            ("House Rent Allowance (HRA)", to_decimal(payroll.hra)),
            ("CCA Allowance", to_decimal(payroll.cca)),
            ("Other Allowance", to_decimal(payroll.other_allowance)),
        ]
        
        deductions = [
            ("PF (Employee)", to_decimal(payroll.pf_employee)),
            ("ESIC (Employee)", to_decimal(payroll.esi_employee)),
            ("Professional Tax", to_decimal(payroll.professional_tax)),
        ]
        
        # Build ED rows
        max_rows = max(len(earnings), len(deductions))
        ed_rows = []
        for i in range(max_rows):
            left_name = ""
            left_amt = ""
            right_name = ""
            right_amt = ""
            if i < len(earnings):
                left_name = earnings[i][0]
                left_amt = format_currency(earnings[i][1]) if earnings[i][1] > 0 else "-"
            if i < len(deductions):
                right_name = deductions[i][0]
                right_amt = format_currency(deductions[i][1]) if deductions[i][1] > 0 else "-"
            ed_rows.append([left_name, left_amt, right_name, right_amt])

        # Distinct sub-section for Employer PF and Bonus (same table)
        ed_rows.append(["", "", "", ""])
        special_start_idx = len(ed_rows)
        ed_rows.append([
            "PF (Employer-contribution)",
            format_currency(to_decimal(payroll.pf_employer)) if to_decimal(payroll.pf_employer) > 0 else "-",
            "PF (Employer-contribution)",
            format_currency(to_decimal(payroll.pf_employer)) if to_decimal(payroll.pf_employer) > 0 else "-",
        ])
        ed_rows.append([
            "Bonus",
            format_currency(to_decimal(payroll.bonus)) if to_decimal(payroll.bonus) > 0 else "-",
            "",
            "",
        ])
        special_end_idx = len(ed_rows) - 1
        ed_rows.append(["", "", "", ""])
        
        row_heights = [8] * len(ed_rows)
        row_heights[special_start_idx - 1] = 3
        row_heights[special_end_idx + 1] = 3

        data_table = Table(
            ed_rows,
            colWidths=ed_col_widths,
            rowHeights=row_heights,
        )
        data_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), font_regular),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 0 * mm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0 * mm),
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('LINEABOVE', (0, special_start_idx), (-1, special_start_idx), 0.5, colors.black),
            ('LINEBELOW', (0, special_end_idx + 1), (-1, special_end_idx + 1), 0.5, colors.black),
        ]))
        
        dw, dh = data_table.wrap(content_width, y)
        data_table.drawOn(c, margin, y - dh)
        y = y - dh -1*mm
        
        # ═══════════════════════════════════════════════════════════════════
        # TOTALS ROW
        # ═══════════════════════════════════════════════════════════════════
        gross = (
            to_decimal(payroll.basic_salary)
            + to_decimal(payroll.hra)
            + to_decimal(payroll.cca)
            + to_decimal(payroll.other_allowance)
            + to_decimal(payroll.bonus)
            + to_decimal(payroll.pf_employer)
        )
        deductions_total = (
            to_decimal(payroll.pf_employee)
            + to_decimal(payroll.pf_employer)
            + to_decimal(payroll.esi_employee)
            + to_decimal(payroll.professional_tax)
        )
        net = gross - deductions_total
        
        totals_data = [["Total Earnings:", format_currency(gross), "Total Deductions:", format_currency(deductions_total)]]
        
        totals_table = Table(totals_data, colWidths=ed_col_widths)
        totals_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), font_bold),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('BACKGROUND', (0, 0), (1, 0), self.GREEN_HEADER),
            ('BACKGROUND', (2, 0), (3, 0), self.RED_HEADER),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('ALIGN', (3, 0), (3, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('LINEABOVE', (0, 0), (-1, 0), 0.5, colors.black),
            ('LINEBELOW', (0, 0), (-1, 0), 0.5, colors.black),
        ]))
        
        tw2, th2 = totals_table.wrap(content_width, y)
        totals_table.drawOn(c, margin, y - th2)
        y = y - th2
        
        # ═══════════════════════════════════════════════════════════════════
        # NET PAYABLE ROW
        # ═══════════════════════════════════════════════════════════════════
        net_words = number_to_words(float(net))
        net_data = [[net_words, "Net Payable:", format_currency(net)]]
        
        net_col_widths = [90*mm, 50*mm, 40*mm]
        net_table = Table(net_data, colWidths=net_col_widths)
        net_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), font_bold),
            ('FONTSIZE', (0, 0), (0, 0), 7),
            ('FONTSIZE', (1, 0), (2, 0), 8),
            ('BACKGROUND', (0, 0), (0, 0), self.YELLOW_BG),
            ('BACKGROUND', (1, 0), (2, 0), self.BLUE_BG),
            ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('LINEABOVE', (0, 0), (-1, 0), 0.5, colors.black),
            ('LINEBELOW', (0, 0), (-1, 0), 0.5, colors.black),
        ]))
        
        nw, nh = net_table.wrap(content_width, y)
        net_table.drawOn(c, margin, y - nh)
        y = y - nh - 2*mm
        
        # ═══════════════════════════════════════════════════════════════════
        # FOOTER
        # ═══════════════════════════════════════════════════════════════════
        c.setFillColor(self.HEADER_BLUE)
        c.setFont(font_regular, 7)
        c.drawString(margin, y, "This is computer generated memo and requires no signature")
        y -= 2 * mm  # Space below footer text
        
        # ═══════════════════════════════════════════════════════════════════
        # OUTER BORDER - Draw around content only
        # ═══════════════════════════════════════════════════════════════════
        y_end = y
        c.setStrokeColor(self.HEADER_BLUE)
        c.setLineWidth(1.5)
        # Border rectangle: x, y, width, height
        # Equal padding on all sides
        c.rect(
            margin - border_padding,  # left
            y_end,  # bottom
            content_width + 2 * border_padding,  # width
            y_start - y_end + border_padding,  # height
            stroke=1, fill=0
        )
        
        # Save
        c.save()
        return output_path
