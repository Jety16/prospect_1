import re
import logging
from google.cloud import documentai_v1beta3 as documentai

logger = logging.getLogger(__name__)

PROJECT_ID = "227652139161"
LOCATION = "us"
PROCESSOR_ID = "1e60d3bd63a0d751"

def extract_from_document_ai(file_bytes):
    try:
        client = documentai.DocumentProcessorServiceClient()
        name = f"projects/{PROJECT_ID}/locations/{LOCATION}/processors/{PROCESSOR_ID}"

        document = {"content": file_bytes, "mime_type": "application/pdf"}
        result = client.process_document(request=documentai.ProcessRequest(name=name, raw_document=document))
        full_text = result.document.text

        nombre = extract_nombre(full_text)
        total = extract_total(full_text)
        rmu = extract_rmu(full_text)

        return nombre, total, rmu, None
    except Exception as e:
        logger.error(f"Error en Document AI: {str(e)}")
        return None, None, None, None

def extract_nombre(text):
    match = re.search(r"Raz[oó]n Social\s*:\s*(.+)", text)
    if match:
        return match.group(1).strip()
    match = re.search(r"\n([A-ZÑ&\. ]{8,})\n.*C\.?P\.\d{5}", text)
    return match.group(1).strip() if match else None

def extract_total(text):
    match = re.search(r"TOTAL A PAGAR:\s*\n?\s*(\$\d[\d,]*)", text)
    if not match:
        match = re.search(r"(\$\d[\d,]*)", text)
    return match.group(1).strip() if match else None

def extract_rmu(text):
    match = re.search(r"RMU\s*[:]*\s*([\d]{5}(?:\s+\d{2}-\d{2}-\d{2}.*?)?CFE)", text)
    return match.group(1).strip() if match else None
