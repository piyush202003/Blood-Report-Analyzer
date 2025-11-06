from django.template.loader import render_to_string
from django.http import HttpResponse
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
import tempfile
from datetime import datetime


def generate_pdf_report(blood_report, recommendation, allergy_info):
    """
    Generate a professional PDF report from recommendations
    
    Args:
        blood_report: BloodReport instance
        recommendation: HealthRecommendation instance
        allergy_info: AllergyInfo instance
    
    Returns:
        HttpResponse with PDF content
    """
    
    # Parse recommendations into lists
    def parse_list(text):
        items = []
        for line in text.split('\n'):
            line = line.strip()
            if line and line.startswith('-'):
                item = line.lstrip('- ').strip()
                if item:
                    items.append(item)
        return items
    
    analysis_points = parse_list(recommendation.detailed_analysis)
    foods_to_eat = parse_list(recommendation.foods_to_eat)
    foods_to_avoid = parse_list(recommendation.foods_to_avoid)
    daily_habits = parse_list(recommendation.daily_habits)
    
    # Get allergies
    user_allergies = allergy_info.user_mentioned_allergies
    common_allergies = [
        k.replace('_', ' ').title() 
        for k, v in allergy_info.common_allergies_response.items() 
        if v
    ]
    
    # Prepare context
    context = {
        'blood_report': blood_report,
        'recommendation': recommendation,
        'allergy_info': allergy_info,
        'user': blood_report.user,
        'analysis_points': analysis_points,
        'foods_to_eat': foods_to_eat,
        'foods_to_avoid': foods_to_avoid,
        'daily_habits': daily_habits,
        'user_allergies': user_allergies,
        'common_allergies': common_allergies,
        'generated_date': datetime.now(),
    }
    
    # Render HTML template
    html_string = render_to_string('analyzer/pdf_report_template.html', context)
    
    # Create PDF
    font_config = FontConfiguration()
    html = HTML(string=html_string)
    
    # Generate PDF
    pdf = html.write_pdf(font_config=font_config)
    
    # Create response
    response = HttpResponse(pdf, content_type='application/pdf')
    filename = f'Health_Report_{blood_report.user.username}_{blood_report.uploaded_at.strftime("%Y%m%d")}.pdf'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response
