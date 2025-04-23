from flask import Blueprint

# Import blueprints from route modules
from .files import files_bp
from .sse import sse_bp

# Create a parent blueprint for versioning or grouping if desired
api_bp = Blueprint('api', __name__)

# Register child blueprints under the parent
api_bp.register_blueprint(files_bp, url_prefix='')
api_bp.register_blueprint(sse_bp,   url_prefix='')