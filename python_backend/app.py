from flask import Flask, request, jsonify, Response, stream_with_context
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os, sys, time, json, logging, re
from datetime import datetime
from dotenv import load_dotenv
from google.cloud import documentai_v1 as documentai

load_dotenv()
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    stream=sys.stdout)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# DB
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

# Document AI
project_id = os.getenv('GCP_PROJECT_ID') or "227652139161"
location = "us"
processor_id = os.getenv('DOCAI_PROCESSOR_ID') or "1e60d3bd63a0d751"

class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    content = db.Column(db.LargeBinary, nullable=False)
    uploaded_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    nombre = db.Column(db.String(255))
    total = db.Column(db.String(100))
    rmu = db.Column(db.String(100))

    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'uploaded_at': self.uploaded_at.isoformat(),
            'nombre': self.nombre,
            'total': self.total,
            'rmu': self.rmu,
        }

with app.app_context():
    try:
        db.create_all()
        logger.info("Tablas creadas exitosamente")
    except Exception as e:
        logger.error(f"Error al crear tablas: {e}")

def extract_from_document_ai(file_bytes):
    try:
        client = documentai.DocumentProcessorServiceClient()
        name = f"projects/{project_id}/locations/{location}/processors/{processor_id}"
        document = {"content": file_bytes, "mime_type": "application/pdf"}
        request = documentai.ProcessRequest(name=name, raw_document=document)
        result = client.process_document(request=request)
        full_text = result.document.text

        # Regex básicos
        nombre = (re.search(r"RFC:\s*(.+?)\s", full_text) or [None, None])[1]
        total = (re.search(r"TOTAL A PAGAR:\s*\$?([\d,]+\.\d{2})", full_text) or [None, None])[1]
        rmu   = (re.search(r"RMU:\s*(.+)", full_text) or [None, None])[1]

        return nombre.strip() if nombre else None, total.strip() if total else None, rmu.strip() if rmu else None
    except Exception as e:
        logger.error(f"Document AI error: {e}")
        return None, None, None

def generate_events():
    yield "data: {}\n\n"
    seen = set()
    while True:
        with app.app_context():
            all_ids = {f.id for f in File.query.all()}
            if all_ids != seen:
                files = [f.to_dict() for f in File.query.order_by(File.uploaded_at.desc()).all()]
                yield f"data: {json.dumps(files)}\n\n"
                seen = all_ids
        time.sleep(1)

@app.route('/events')
def events():
    return Response(stream_with_context(generate_events()),
                    mimetype='text/event-stream',
                    headers={
                      'Cache-Control':'no-cache',
                      'Connection':'keep-alive',
                      'X-Accel-Buffering':'no'})
    
@app.route('/files', methods=['GET'])
def list_files():
    try:
        files = File.query.order_by(File.uploaded_at.desc()).all()
        return jsonify([f.to_dict() for f in files])
    except Exception as e:
        logger.error(f"Error list_files: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/upload', methods=['POST', 'OPTIONS'])
def upload_file():
    if request.method == 'OPTIONS':
        return '', 200
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No se encontró el archivo'}), 400
        file = request.files['file']
        if not file.filename:
            return jsonify({'error': 'No se seleccionó ningún archivo'}), 400

        content = file.read()
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
        return jsonify({'message': 'Archivo subido y procesado exitosamente'}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Upload error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
