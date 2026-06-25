from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import ListStyle
from io import BytesIO
from datetime import datetime


def generate_pdf_report(blood_report, recommendation, allergy_info):
    """
    Generate a professional PDF report using ReportLab
    """

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []

    styles = getSampleStyleSheet()
    normal_style = styles["Normal"]
    heading_style = styles["Heading1"]

    elements.append(Paragraph("Blood Health Report", heading_style))
    elements.append(Spacer(1, 0.3 * inch))

    elements.append(Paragraph(f"User: {blood_report.user.username}", normal_style))
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%d-%m-%Y')}", normal_style))
    elements.append(Spacer(1, 0.3 * inch))

    # Helper to parse list
    def parse_list(text):
        items = []
        for line in text.split('\n'):
            line = line.strip()
            if line and line.startswith('-'):
                items.append(line.lstrip('- ').strip())
        return items

    def add_section(title, content_list):
        elements.append(Paragraph(title, styles["Heading2"]))
        elements.append(Spacer(1, 0.2 * inch))
        list_items = [ListItem(Paragraph(item, normal_style)) for item in content_list]
        elements.append(ListFlowable(list_items, bulletType='bullet'))
        elements.append(Spacer(1, 0.3 * inch))

    add_section("Detailed Analysis", parse_list(recommendation.detailed_analysis))
    add_section("Foods To Eat", parse_list(recommendation.foods_to_eat))
    add_section("Foods To Avoid", parse_list(recommendation.foods_to_avoid))
    add_section("Daily Habits", parse_list(recommendation.daily_habits))

    # Allergies
    elements.append(Paragraph("Allergy Information", styles["Heading2"]))
    elements.append(Spacer(1, 0.2 * inch))
    elements.append(Paragraph(f"User Mentioned Allergies: {allergy_info.user_mentioned_allergies}", normal_style))

    doc.build(elements)

    buffer.seek(0)
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(pdf, content_type='application/pdf')
    filename = f'Health_Report_{blood_report.user.username}_{blood_report.uploaded_at.strftime("%Y%m%d")}.pdf'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    return response