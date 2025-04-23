import re
import logging
from google.cloud import documentai_v1 as documentai

from .config import Config

logger = logging.getLogger(__name__)


def extract_from_document_ai(file_bytes: bytes):
    """
    Sends bytes to Document AI and returns (nombre, total, rmu).
    """
    try:
        client = documentai.DocumentProcessorServiceClient()
        name = (
            f"projects/{Config.DOCAI_PROJECT_ID}"
            f"/locations/{Config.DOCAI_LOCATION}"
            f"/processors/{Config.DOCAI_PROCESSOR_ID}"
        )
        request = documentai.ProcessRequest(
            name=name,
            raw_document={'content': file_bytes, 'mime_type': 'application/pdf'}
        )
        result = client.process_document(request=request)
        text = result.document.text or ""

        nombre = _extract_nombre(text)
        total = _extract_total(text)
        rmu = _extract_rmu(text)

        logger.info(f"Extracted: nombre={nombre}, total={total}, rmu={rmu}")
        return nombre, total, rmu

    except Exception:
        logger.exception("Document AI processing failed")
        return None, None, None


def _extract_nombre(text: str) -> str:
    match = re.search(r"Raz[oó]n Social\s*:\s*(.+)", text)
    if match:
        return match.group(1).strip()
    match = re.search(r"\n([A-ZÑ&\. ]{8,})\n.*C\.?P\.\d{5}", text)
    return match.group(1).strip() if match else None


def _extract_total(text: str) -> str:
    match = re.search(r"TOTAL A PAGAR:\s*\n?\s*(\$[\d,]+)", text)
    if not match:
        match = re.search(r"(\$[\d,]+)", text)
    return match.group(1).strip() if match else None


def _extract_rmu(text: str) -> str:
    match = re.search(r"RMU\s*[:]*\s*([\d]{5}(?:\s+\d{2}-\d{2}-\d{2}.*?)?CFE)", text)
    return match.group(1).strip() if match else None

