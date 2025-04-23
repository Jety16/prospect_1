import logging
from flask import Blueprint, request, jsonify
from app.models import File
from app import db
from app.services.document_ai import extract_from_document_ai

files_blueprint = Blueprint('files', __name__)

logger = logging.getLogger(__name__)

@files_blueprint.route('/files', methods=['GET'])
def list_files():
    try:
        files = File.query.all()
        return jsonify([file.to_dict() for file in files])
    except Exception as e:
        logger.error(f"Error al listar archivos: {str(e)}")
        return jsonify({'error': str(e)}), 500

@files_blueprint.route('/upload', methods=['POST', 'OPTIONS'])
def upload_file():
    if request.method == 'OPTIONS':
        return '', 200

    try:
        file = request.files.get('file')
        if not file or file.filename == '':
            return jsonify({'error': 'Archivo no válido'}), 400

        content = file.read()
        nombre, total, rmu, _ = extract_from_document_ai(content)

        new_file = File(filename=file.filename, content=content,
                        nombre=nombre, total=total, rmu=rmu)
        db.session.add(new_file)
        db.session.commit()

        return jsonify({'message': 'Archivo subido y procesado'}), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al subir archivo: {str(e)}")
        return jsonify({'error': str(e)}), 500
