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

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

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

class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    content = db.Column(db.LargeBinary, nullable=False)
    uploaded_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<File {self.filename}>'

    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'uploaded_at': self.uploaded_at.isoformat()
        }

with app.app_context():
    try:
        db.create_all()
        logger.info("Tablas creadas exitosamente")
    except Exception as e:
        logger.error(f"Error al crear las tablas: {str(e)}")

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

@app.route('/api/files', methods=['GET'])
def list_files():
    try:
        files = File.query.all()
        return jsonify([file.to_dict() for file in files])
    except Exception as e:
        logger.error(f"Error al listar archivos: {str(e)}")
        return jsonify({'error': f'Error al listar archivos: {str(e)}'}), 500

@app.route('/api/upload', methods=['POST', 'OPTIONS'])
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
            try:
                content = file.read()
                logger.info(f"Archivo {file.filename} leído correctamente")
                
                new_file = File(filename=file.filename, content=content)
                db.session.add(new_file)
                db.session.commit()
                logger.info(f"Archivo {file.filename} guardado en la base de datos")
                
                return jsonify({'message': 'Archivo subido exitosamente'}), 200
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error al guardar el archivo en la base de datos: {str(e)}")
                return jsonify({'error': f'Error al guardar el archivo: {str(e)}'}), 500
    except Exception as e:
        logger.error(f"Error general al procesar la solicitud: {str(e)}")
        return jsonify({'error': f'Error al procesar la solicitud: {str(e)}'}), 500

if __name__ == '__main__':
    logger.info("Iniciando servidor Flask...")
    app.run(host='0.0.0.0', port=5000, debug=True) 