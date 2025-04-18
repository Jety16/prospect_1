from flask import Flask, request, jsonify, Response, stream_with_context
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os
from datetime import datetime
import logging
import sys
import time
import json
from dotenv import load_dotenv

from google.cloud import documentai_v1 as documentai

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Configuración de DB
db_host = os.getenv('DB_HOST')
db_port = os.getenv('DB_PORT', '5432')
db_name = os.getenv('DB_NAME')
db_user = os.getenv('DB_USER')
db_password = os.getenv('DB_PASSWORD')

app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Configuración de Document AI
project_id = "227652139161"
location = "us"
processor_id = "1e60d3bd63a0d751"

# Modelo
class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    content = db.Column(db.LargeBinary, nullable=False)
    uploaded_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    nombre = db.Column(db.String(255))
    total = db.Column(db.String(100))
    rmu = db.Column(db.String(100))

    def __repr__(self):
        return f'<File {self.filename}>'

    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'uploaded_at': self.uploaded_at.isoformat(),
            'nombre': self.nombre,
            'total': self.total,
            'rmu': self.rmu
        }

# Crear tablas
with app.app_context():
    try:
        db.create_all()
        logger.info("Tablas creadas exitosamente")
    except Exception as e:
        logger.error(f"Error al crear las tablas: {str(e)}")

# Función Document AI
import re

def extract_from_document_ai(file_bytes):
    try:
        client = documentai.DocumentProcessorServiceClient()
        name = f"projects/{project_id}/locations/{location}/processors/{processor_id}"

        document = {"content": file_bytes, "mime_type": "application/pdf"}
        request = documentai.ProcessRequest(name=name, raw_document=document)
        result = client.process_document(request=request)
        doc = result.document

        full_text = doc.text
        logger.info("Texto completo extraído del documento")

        # 💡 Imprimir para debug
        # print(full_text)

        # 🔍 Buscar datos usando regex o patrones simples
        nombre = None
        total = None
        rmu = None

        # Ejemplo: encontrar línea que contiene "RMU:"
        rmu_match = re.search(r"RMU:\s*(.+)", full_text)
        if rmu_match:
            rmu = rmu_match.group(1).strip()

        # Total (más robusto si usamos patrón de dinero en MXN)
        total_match = re.search(r"TOTAL A PAGAR:\s*\$?([\d,]+\.\d{2})", full_text)
        if total_match:
            total = total_match.group(1).strip()

        # Nombre de compañía o entidad (ej: CFE o Banjercito)
        # Buscar algo con "RFC:" seguido de nombre
        nombre_match = re.search(r"RFC:\s*(.+?)\s", full_text)
        if nombre_match:
            nombre = nombre_match.group(1).strip()

        logger.info(f"Nombre extraído: {nombre}")
        logger.info(f"Total extraído: {total}")
        logger.info(f"RMU extraído: {rmu}")

        return nombre, total, rmu

    except Exception as e:
        logger.error(f"Error en Document AI: {str(e)}")
        return None, None, None


# SSE
def generate_events():
    try:
        yield "data: {}\n\n"
        last_files = set()
        while True:
            try:
                with app.app_context():
                    current_files = {f.id for f in File.query.all()}
                    if current_files != last_files:
                        files = [f.to_dict() for f in File.query.all()]
                        yield f"data: {json.dumps(files)}\n\n"
                        last_files = current_files
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error en generate_events: {str(e)}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                time.sleep(1)
    except GeneratorExit:
        logger.info("Cliente desconectado")

@app.route('/events')
def events():
    logger.info("Nueva conexión SSE recibida")
    response = Response(
        stream_with_context(generate_events()),
        mimetype='text/event-stream'
    )
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['Connection'] = 'keep-alive'
    response.headers['X-Accel-Buffering'] = 'no'
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

@app.route('/files', methods=['GET'])
def list_files():
    try:
        files = File.query.all()
        return jsonify([file.to_dict() for file in files])
    except Exception as e:
        logger.error(f"Error al listar archivos: {str(e)}")
        return jsonify({'error': f'Error al listar archivos: {str(e)}'}), 500

@app.route('/upload', methods=['POST', 'OPTIONS'])
def upload_file():
    if request.method == 'OPTIONS':
        return '', 200

    try:
        if 'file' not in request.files:
            logger.error("No se encontró el archivo en la solicitud")
            return jsonify({'error': 'No se encontró el archivo'}), 400
        
        file = request.files['file']
        if file.filename == '':
            logger.error("Nombre de archivo vacío")
            return jsonify({'error': 'No se seleccionó ningún archivo'}), 400
        
        if file:
            content = file.read()
            logger.info(f"Archivo {file.filename} leído correctamente")

            # Procesar con Document AI
            nombre, total, rmu = extract_from_document_ai(content)

            new_file = File(
                filename=file.filename,
                content=content,
                nombre=nombre,
                total=total,
                rmu=rmu
            )
            db.session.add(new_file)
            db.session.commit()
            logger.info(f"Archivo {file.filename} guardado y procesado")

            return jsonify({'message': 'Archivo subido y procesado exitosamente'}), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error general al procesar la solicitud: {str(e)}")
        return jsonify({'error': f'Error al procesar la solicitud: {str(e)}'}), 500

if __name__ == '__main__':
    logger.info("Iniciando servidor Flask...")
    app.run(host='0.0.0.0', port=5000, debug=True)
