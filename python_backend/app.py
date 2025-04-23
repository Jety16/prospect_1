import os
import sys
import time
import json
import logging
import re
from datetime import datetime

from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from google.cloud import documentai_v1 as documentai

# Load environment
load_dotenv()

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# Flask app & CORS
app = Flask(__name__)
CORS(app)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@"
    f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME')}"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Extensions
db = SQLAlchemy(app)

# Document AI client & settings
PROJECT_ID = os.getenv('GCP_PROJECT_ID', '227652139161')
LOCATION = os.getenv('GCP_LOCATION', 'us')
PROCESSOR_ID = os.getenv('GCP_PROCESSOR_ID', '1e60d3bd63a0d751')
AI_CLIENT = documentai.DocumentProcessorServiceClient()
PROCESSOR_NAME = f"projects/{PROJECT_ID}/locations/{LOCATION}/processors/{PROCESSOR_ID}"

# Regex patterns
PATTERNS = {
    'rmu': re.compile(r"RMU[:\s]+([\d]+(?:\s[\d-]+)*)", re.IGNORECASE),
    'total': re.compile(r"TOTAL A PAGAR[:\s]*\$?([\d,]+(?:\.\d{2})?)", re.IGNORECASE),
    'amounts': re.compile(r"\$\s*([\d,]+(?:\.\d{2})?)"),
    'rfc': re.compile(r"RFC[:\s]+([A-Z0-9]+)", re.IGNORECASE),
    'entity': re.compile(r"(Comisión Federal de Electricidad|CFE|BANJERCITO)", re.IGNORECASE),
    'cmo': re.compile(r"CMO[-:\s]+([A-Z0-9-]+)", re.IGNORECASE),
    'rmu_cmo': re.compile(r"RMU[:\s].*?CMO[-:\s]*([A-Z0-9-]+)", re.IGNORECASE),
}

# Models
class File(db.Model):
    __tablename__ = 'files'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    content = db.Column(db.LargeBinary, nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    nombre = db.Column(db.String(255))
    total = db.Column(db.Float)
    rmu = db.Column(db.String(100))
    cmo = db.Column(db.String(100))

    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'uploaded_at': self.uploaded_at.isoformat(),
            'nombre': self.nombre,
            'total': self.total,
            'rmu': self.rmu,
            'cmo': self.cmo,
        }

# Create tables
with app.app_context():
    db.create_all()
    logger.info("Database tables ensured.")

# Extraction logic — solo esta función ha cambiado

def extract_from_document_ai(file_bytes):
    try:
        # Procesar documento con Document AI
        request = documentai.ProcessRequest(
            name=PROCESSOR_NAME,
            raw_document={'content': file_bytes, 'mime_type': 'application/pdf'}
        )
        document = AI_CLIENT.process_document(request=request).document
        text = document.text or ''

        nombre = total = rmu = cmo = None

        # 1. Extraer RMU
        if match := PATTERNS['rmu'].search(text):
            rmu = match.group(1).strip()

        # 2. Extraer TOTAL (primario)
        if match := PATTERNS['total'].search(text):
            total = float(match.group(1).replace(',', ''))
        else:
            fallback = PATTERNS['amounts'].findall(text)
            if fallback:
                total = float(fallback[-1].replace(',', ''))

        # 3. Extraer NOMBRE (RFC o entidad)
        if match := PATTERNS['rfc'].search(text):
            nombre = match.group(1).strip()
        elif match := PATTERNS['entity'].search(text):
            nombre = match.group(1).upper()

        # 4. Extraer CMO
        if match := PATTERNS['cmo'].search(text):
            cmo = match.group(1).strip()
        elif match := PATTERNS['rmu_cmo'].search(text):
            cmo = match.group(1).strip()

        return nombre, total, rmu, cmo

    except Exception as e:
        logger.error("Document AI extraction failed: %s", e)
        return None, None, None, None

# SSE generator

def generate_events():
    last_ids = set()
    while True:
        try:
            all_files = File.query.all()
            current_ids = {f.id for f in all_files}
            if current_ids != last_ids:
                yield f"data: {json.dumps([f.to_dict() for f in all_files])}\n\n"
                last_ids = current_ids
            time.sleep(1)
        except GeneratorExit:
            logger.info("SSE client disconnected.")
            break
        except Exception as e:
            logger.error("Error in SSE: %s", e)
            time.sleep(1)

# Rutas, /events, /files, /upload, y punto de entrada siguen igual
