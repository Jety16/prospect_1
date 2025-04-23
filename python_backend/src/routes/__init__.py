from .files import files_blueprint
from .sse import sse_blueprint

def register_routes(app):
    app.register_blueprint(files_blueprint)
    app.register_blueprint(sse_blueprint)
