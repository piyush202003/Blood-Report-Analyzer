import re
from analyzer.models import BloodParameter, BloodReportValue
from google import genai
from django.conf import settings

def normalize_text(text: str) -> str:
    prompt = """
    Extract results from this blood report. Return ONLY a list in format 'Parameter:Value'. 
    Clean up aliases to standard names. Handle '<' or '>' signs by keeping only the number.
    Example: 'Vitamin B12:148'.
    """

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    response = client.models.generate_content(
        model=settings.MODEL_NAME,
        contents=[prompt, text]
    )
    text = response.text
    text = text.lower()
    text=text.strip()

    replacements = {
        "gm/dl": "g/dl",
        "jul": "",
        "ful": "",
        "mill/comm": "million/cumm",
        "mill/emm": "million/cumm",
        "emm": "cumm",
        "/ul": "/cumm",
        "/u l": "/cumm",
        "per ul": "/cumm",
        "[h]": "",
        "[l]": "",
        "row":"rdw"
    }

    for k, v in replacements.items():
        text = text.replace(k, v)

    # Remove unwanted symbols but keep numbers and %
    text = re.sub(r"[^\w\s.%/:-]", " ", text)

    # Normalize spaces
    text = re.sub(r"\s+", " ", text)
    # print(text)

    
    return text

NUMBER_PATTERN = re.compile(r"\b\d+(?:\.\d+)?\b")

def extract_values_from_text(report):
    text = report.extracted_text.lower()


    text = normalize_text(text)
    parameters = BloodParameter.objects.all()

    for param in parameters:
        value_found = False

        for alias in param.aliases():
            pos = text.find(alias)
            if pos == -1:
                continue

            # Look ahead only (safe window)
            window = text[pos:pos + 120]

            numbers = NUMBER_PATTERN.findall(window)

            if numbers:
                value = float(numbers[0])

                BloodReportValue.objects.update_or_create(
                    report=report,
                    parameter=param,
                    defaults={
                        "value": value,
                        "unit": param.unit
                    }
                )

                print(f"[OK] {param.name} = {value}")
                value_found = True
                break

        if not value_found:
            print(f"[MISS] {param.name}")