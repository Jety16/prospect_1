import re
import logging
from google.cloud import documentai_v1 as documentai

from .config import Config

logger = logging.getLogger(__name__)

def extract_from_document_ai(file_bytes: bytes) -> tuple[str | None, str | None, str | None]:
    """
    Sends bytes to Document AI, processes the document, and extracts key fields.
    Returns a tuple (nombre, total, rmu); any value may be None on failure.
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
            raw_document={"content": file_bytes, "mime_type": "application/pdf"}
        )
        result = client.process_document(request=request)
        full_text = result.document.text or ""

        logger.info("Documento procesado con éxito")

        nombre = _extract_nombre(full_text)
        total  = _extract_total(full_text)
        rmu    = _extract_rmu(full_text)

        logger.debug(f"Extracciones → nombre: {nombre!r}, total: {total!r}, rmu: {rmu!r}")
        return nombre, total, rmu

    except Exception:
        logger.exception("Error durante el procesamiento con Document AI")
        return None, None, None


def _extract_nombre(text: str) -> str | None:
    """Busca primero 'Razón Social', luego RFC, luego una línea en mayúsculas."""
    if match := re.search(r"Raz[oó]n Social\s*:\s*(.+)", text):
        return match.group(1).strip()
    if match := re.search(r"RFC\s*:\s*([A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3})", text):
        return match.group(1)
    if match := re.search(r"\n([A-ZÑ&\. ]{8,})\n.*C\.?P\.\d{5}", text):
        return match.group(1).strip()
    return None


def _extract_total(text: str) -> str | None:
    """Extrae el importe tras 'TOTAL A PAGAR' o cualquier '$123,456'."""
    if match := re.search(r"TOTAL A PAGAR:\s*\n?\s*(\$[\d,]+)", text):
        return match.group(1).strip()
    if match := re.search(r"(\$[\d,]+)", text):
        return match.group(1).strip()
    return None


def _extract_rmu(text: str) -> str | None:
    """Captura códigos RMU que terminan en 'CFE'."""
    if match := re.search(r"RMU\s*:?\\s*([\d]{5}(?:\s+\d{2}-\d{2}-\d{2}.*?)?CFE)", text):
        return match.group(1).strip()
    return None