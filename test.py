import os
import django
import re
from typing import Optional

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "health_advisor.settings")
django.setup()

import pytesseract
from PIL import Image
from google import genai
from analyzer.models import BloodParameter, BloodReportValue, BloodReport
from django.conf import settings

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
NUMBER_PATTERN = re.compile(r"\b\d+(?:\.\d+)?\b")

def get_structured_data_from_ai(raw_text: str) -> str:
    """
    Uses Gemini to clean up OCR noise and return a clean key=value list.
    """
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    # IMPROVED PROMPT: Specifically asks for key=value and handles units
    prompt = """
    Analyze this OCR text from a blood report. Extract every lab parameter and its numeric result.
    Format your response EXACTLY like this (one per line):
    Parameter Name=Value Unit
    
    Example:
    Hemoglobin=14.2 g/dL
    RBC Count=4.5 million/cumm
    
    Ignore dates, patient IDs, and addresses. Only extract clinical values.
    """
    
    try:
        response = client.models.generate_content(
            model=settings.MODEL_NAME, 
            contents=[prompt, raw_text]
        )
        print(response.text.lower().strip())
        return response.text.lower().strip()
    except Exception as e:
        print(f"AI Extraction Error: {e}")
        return raw_text.lower()

def extract_and_save_report(report_id: int):
    report = BloodReport.objects.get(id=report_id)
    
    raw_text = report.extracted_text
    
    prompt = """
    Extract results from this blood report. Return ONLY a list in format 'Parameter:Value'. 
    Clean up aliases to standard names. Handle '<' or '>' signs by keeping only the number.
    Example: 'Vitamin B12:148'.
    """
    
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    response = client.models.generate_content(
        model=settings.MODEL_NAME,
        contents=[prompt, raw_text]
    )
    structured_text = response.text.lower()
    print(structured_text)
    parameters = BloodParameter.objects.all()
    
    for param in parameters:
        found_value = None
        
        for alias in param.aliases():
            pattern = rf"(?:^|\n){re.escape(alias.lower())}\s*[:=-]\s*(\d+(?:\.\d+)?)"
            matches = re.findall(pattern, structured_text, re.MULTILINE)
            
            if matches:
                found_value = float(matches[0])
                break 

        if found_value is not None:
            # BloodReportValue.objects.update_or_create(
            #     report=blood_report,
            #     parameter=param,
            #     defaults={'value': found_value, 'unit': param.unit}
            # )
            print(f"[OK] {param.name}: {found_value}")
        else:
            print(f"[MISS] {param.name}")

    return True

# To run:
extract_and_save_report(7)