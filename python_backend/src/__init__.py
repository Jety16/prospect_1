from flask import Flask
from flask_cors import CORS

from .config import Config
from .models import db
from .routes.files import files_bp
from .routes.sse import sse_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app)

    db.init_app(app)
    with app.app_context():
        db.create_all()

    app.register_blueprint(files_bp, url_prefix='/api')
    app.register_blueprint(sse_bp,   url_prefix='/api')

    return app