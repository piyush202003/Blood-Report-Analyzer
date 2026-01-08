import os
import django
import re
from typing import Optional

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "health_advisor.settings")
django.setup()

import pytesseract
from PIL import Image
from google import genai
from analyzer.models import BloodParameter, BloodReportValue, BloodReport
from django.conf import settings
# Constants
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
        # Note: Updated model name to a current stable version
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
    """
    Main service function to extract data and save to BloodReportValue
    """
    report = BloodReport.objects.get(id=report_id)
    
    # Use OCR or File reading
    raw_text = report.extracted_text
    
    # 2. Use Gemini to structure the data
    # We ask Gemini to return strictly key:value pairs or 'None'
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

    # --- STEP 3: Smart Matching Logic ---
    parameters = BloodParameter.objects.all()
    
    for param in parameters:
        found_value = None
        
        for alias in param.aliases():
            # Improved Regex: Looks for alias followed by colon, then optional spaces, then the number.
            # Use ^ or \n to ensure we are matching the start of a line to avoid "foetal hb" matching "hb"
            pattern = rf"(?:^|\n){re.escape(alias.lower())}\s*[:=-]\s*(\d+(?:\.\d+)?)"
            matches = re.findall(pattern, structured_text, re.MULTILINE)
            
            if matches:
                # We take the FIRST match found (usually the main result), not the last
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