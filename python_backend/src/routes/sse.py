import json
import time
import logging
from flask import Blueprint, Response, stream_with_context
from src.models import File
from src import db

sse_blueprint = Blueprint('sse', __name__)
logger = logging.getLogger(__name__)

def generate_events():
    last_files = set()
    while True:
        try:
            current_files = {f.id for f in File.query.all()}
            if current_files != last_files:
                files = [f.to_dict() for f in File.query.all()]
                yield f"data: {json.dumps(files)}\n\n"
                last_files = current_files
            time.sleep(1)
        except Exception as e:
            logger.error(f"Error en SSE: {str(e)}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            time.sleep(1)

@sse_blueprint.route('/events')
def events():
    logger.info("Conexión SSE iniciada")
    response = Response(stream_with_context(generate_events()), mimetype='text/event-stream')
    response.headers.update({
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'X-Accel-Buffering': 'no',
        'Access-Control-Allow-Origin': '*'
    })
    return response
