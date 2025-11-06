import google.generativeai as genai
from django.conf import settings
import PyPDF2
from PIL import Image
import io
import json

# Configure Gemini API
genai.configure(api_key=settings.GEMINI_API_KEY)


def extract_text_from_pdf(pdf_file):
    """Extract text from PDF blood report"""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        return f"Error extracting PDF: {str(e)}"


def extract_text_from_image(image_file):
    """Extract text from image using Gemini Vision"""
    try:
        model = genai.GenerativeModel('gemini-2.5-pro')
        
        # Convert to PIL Image
        image = Image.open(image_file)
        
        prompt = """
        This is a blood test report. Extract all the test parameters, their values, 
        and reference ranges. Format the output clearly with:
        - Test name
        - Value
        - Unit
        - Reference range
        - Status (if mentioned)
        """
        
        response = model.generate_content([prompt, image])
        return response.text
    except Exception as e:
        return f"Error extracting from image: {str(e)}"


def analyze_blood_report(extracted_text, allergies_dict):
    """
    Analyze blood report and generate personalized health recommendations
    
    Args:
        extracted_text: Text extracted from blood report
        allergies_dict: Dictionary containing allergy information
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-pro')
        
        # Build allergy information string
        allergy_info = "User Allergies:\n"
        if allergies_dict.get('user_mentioned'):
            allergy_info += f"- Specific allergies: {allergies_dict['user_mentioned']}\n"
        
        common_allergies = []
        for allergy, has_it in allergies_dict.get('common', {}).items():
            if has_it:
                common_allergies.append(allergy.replace('_', ' ').title())
        
        if common_allergies:
            allergy_info += f"- Common allergies: {', '.join(common_allergies)}\n"
        else:
            allergy_info += "- No common allergies reported\n"
        
        prompt = f"""
        You are a healthcare AI assistant. Analyze this blood test report and provide SHORT, SIMPLE, POINT-WISE recommendations.

        BLOOD TEST REPORT:
        {extracted_text}

        {allergy_info}

        IMPORTANT INSTRUCTIONS:
        - Keep everything SHORT and SIMPLE
        - Use ONE LINE per point
        - Maximum 10 words per point
        - No long explanations
        - Direct and actionable advice only
        - Avoid all allergens mentioned above

        Provide your response in these 4 sections:

        1. DETAILED ANALYSIS:
        List 5-7 key findings in one line each. Example format:
        - High cholesterol: Risk of heart disease
        - Low Vitamin D: Affects bone health
        - Normal blood sugar: Good glucose control

        2. FOODS TO EAT:
        List exactly 12 foods in ONE LINE each. Format:
        - Food name: Brief benefit (max 5 words)
        Example: 
        - Spinach: Rich in iron
        - Almonds: Good for heart
        
        3. FOODS TO AVOID:
        List exactly 12 foods in ONE LINE each. Format:
        - Food name: Brief reason (max 5 words)
        Example:
        - Red meat: Increases cholesterol
        - Sugary drinks: Raises blood sugar

        4. DAILY HABITS:
        List exactly 10 habits in ONE LINE each. Format:
        - Action: Brief benefit (max 5 words)
        Example:
        - Walk 30 minutes daily: Improves cardiovascular health
        - Sleep 7-8 hours: Better recovery

        Keep it SIMPLE, SHORT, and ACTIONABLE. One line per point only.
        """
        
        response = model.generate_content(prompt)
        return parse_gemini_response(response.text)
    
    except Exception as e:
        return {
            'detailed_analysis': f"Error: {str(e)}",
            'foods_to_eat': "Unable to generate recommendations",
            'foods_to_avoid': "Unable to generate recommendations",
            'daily_habits': "Unable to generate recommendations"
        }



def parse_gemini_response(response_text):
    """Parse the Gemini response into structured sections"""
    sections = {
        'detailed_analysis': '',
        'foods_to_eat': '',
        'foods_to_avoid': '',
        'daily_habits': ''
    }
    
    current_section = None
    lines = response_text.split('\n')
    
    for line in lines:
        line_lower = line.lower()
        
        # Detect section headers
        if 'detailed analysis' in line_lower or 'analysis' in line_lower and current_section is None:
            current_section = 'detailed_analysis'
            continue
        elif 'foods to eat' in line_lower or 'recommended foods' in line_lower:
            current_section = 'foods_to_eat'
            continue
        elif 'foods to avoid' in line_lower or 'avoid' in line_lower and 'food' in line_lower:
            current_section = 'foods_to_avoid'
            continue
        elif 'daily habits' in line_lower or 'lifestyle' in line_lower:
            current_section = 'daily_habits'
            continue
        
        # Add content to current section
        if current_section and line.strip():
            sections[current_section] += line + '\n'
    
    return sections


def get_quick_summary(extracted_text):
    """Get a quick summary of the blood report"""
    try:
        model = genai.GenerativeModel('gemini-2.5-pro')
        
        prompt = f"""
        Provide a brief 3-4 sentence summary of this blood test report.
        Highlight any critical values or areas of concern.
        
        BLOOD TEST REPORT:
        {extracted_text}
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Unable to generate summary: {str(e)}"
