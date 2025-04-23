import json
import logging
from flask import Blueprint, request, jsonify

from ..models import db, File
from ..document_ai import extract_from_document_ai

logger = logging.getLogger(__name__)

files_bp = Blueprint('files', __name__)

@files_bp.route('/files', methods=['GET'])
def list_files():
    try:
        files = File.query.all()
        return jsonify([f.to_dict() for f in files]), 200
    except Exception:
        logger.exception("Failed to list files")
        return jsonify({'error': 'Failed to list files'}), 500

@files_bp.route('/upload', methods=['POST', 'OPTIONS'])
def upload_file():
    if request.method == 'OPTIONS':
        return '', 200

    uploaded = request.files.get('file')
    if not uploaded or not uploaded.filename:
        return jsonify({'error': 'No file provided'}), 400

    try:
        content = uploaded.read()
        nombre, total, rmu = extract_from_document_ai(content)

        new_file = File(
            filename=uploaded.filename,
            content=content,
            nombre=nombre,
            total=total,
            rmu=rmu
        )
        db.session.add(new_file)
        db.session.commit()

        logger.info(f"Saved file: {uploaded.filename}")
        return jsonify({'message': 'File uploaded and processed'}), 201
    except Exception:
        db.session.rollback()
        logger.exception("Error during file upload")
        return jsonify({'error': 'Upload failed'}), 500