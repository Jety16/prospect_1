import json
import time
import logging
from flask import Blueprint, Response, stream_with_context

from ..models import File

logger = logging.getLogger(__name__)
sse_bp = Blueprint('sse', __name__)


def generate_events(poll_interval: float = 1.0):
    last_ids = set()
    yield "data: []\n\n"
    while True:
        try:
            current_ids = {f.id for f in File.query.all()}
            if current_ids != last_ids:
                payload = [f.to_dict() for f in File.query.all()]
                yield f"data: {json.dumps(payload)}\n\n"
                last_ids = current_ids
            time.sleep(poll_interval)
        except GeneratorExit:
            logger.info("SSE client disconnected")
            break
        except Exception:
            logger.exception("Error in SSE generator")
            yield f"data: {{'error':'stream error'}}\n\n"
            time.sleep(poll_interval)

@sse_bp.route('/events')
def sse_events():
    logger.info("SSE connection initiated")
    return Response(
        stream_with_context(generate_events()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
            'Access-Control-Allow-Origin': '*'
        }
    )
