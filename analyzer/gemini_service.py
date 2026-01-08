from django.conf import settings
from google import genai
import PyPDF2
from PIL import Image
import pytesseract


client = genai.Client(api_key=settings.GEMINI_API_KEY)
MODEL_NAME = settings.MODEL_NAME


def extract_text_from_pdf(pdf_file):
    """Extract text from PDF blood report"""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        return text.strip()
    except Exception as e:
        return f"Error extracting PDF: {str(e)}"


def extract_text_from_image(image_file):
    """Extract text from image using Gemini Vision"""
    try:
        image = Image.open(image_file)

        # prompt = """
        # This is a blood test report.
        # Extract all test parameters with:
        # - Test name
        # - Value
        # - Unit
        # - Reference range
        # - Status (if mentioned)
        # """

        # response = client.models.generate_content(
        #     model=MODEL_NAME,
        #     contents=[prompt, image]
        # )
        pytesseract.pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"

        text = pytesseract.image_to_string(image)

        return text

    except Exception as e:
        return f"Error extracting from image: {str(e)}"


def analyze_blood_report(extracted_text, allergies_dict):
    """Analyze blood report and generate recommendations"""
    try:
        allergy_info = "User Allergies:\n"

        if allergies_dict.get("user_mentioned"):
            allergy_info += f"- Specific allergies: {allergies_dict['user_mentioned']}\n"

        common_allergies = [
            a.replace("_", " ").title()
            for a, has_it in allergies_dict.get("common", {}).items()
            if has_it
        ]

        if common_allergies:
            allergy_info += f"- Common allergies: {', '.join(common_allergies)}\n"
        else:
            allergy_info += "- No common allergies reported\n"

        prompt = f"""
        You are a healthcare AI assistant.
        Keep everything SHORT, SIMPLE, and POINT-WISE.

        BLOOD TEST REPORT:
        {extracted_text}

        {allergy_info}

        RULES:
        - One line per point
        - Max 10 words per line
        - No medical diagnosis
        - Avoid all allergens

        SECTIONS REQUIRED:

        1. DETAILED ANALYSIS (5–7 points)
        2. FOODS TO EAT (12 items)
        3. FOODS TO AVOID (12 items)
        4. DAILY HABITS (10 items)
        """

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )

        return parse_gemini_response(response.text)

    except Exception as e:
        return {
            "detailed_analysis": f"Error: {str(e)}",
            "foods_to_eat": "",
            "foods_to_avoid": "",
            "daily_habits": ""
        }


def parse_gemini_response(response_text):
    """Parse Gemini response into structured sections"""
    sections = {
        "detailed_analysis": "",
        "foods_to_eat": "",
        "foods_to_avoid": "",
        "daily_habits": ""
    }

    current_section = None

    for line in response_text.splitlines():
        l = line.lower()

        if "detailed analysis" in l:
            current_section = "detailed_analysis"
            continue
        if "foods to eat" in l:
            current_section = "foods_to_eat"
            continue
        if "foods to avoid" in l:
            current_section = "foods_to_avoid"
            continue
        if "daily habits" in l:
            current_section = "daily_habits"
            continue

        if current_section and line.strip():
            sections[current_section] += line.strip() + "\n"

    return sections


def get_quick_summary(extracted_text):
    """Generate short summary of blood report"""
    try:
        prompt = f"""
        Give a 3–4 sentence summary.
        Highlight critical abnormalities only.

        REPORT:
        {extracted_text}
        """

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )

        return response.text

    except Exception as e:
        return f"Unable to generate summary: {str(e)}"
