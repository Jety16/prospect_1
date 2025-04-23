from datetime import datetime
import os
import sys
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from dotenv import load_dotenv
from src.routes import register_routes

load_dotenv()

db = SQLAlchemy()

def configure_database(app):
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME')}"
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    content = db.Column(db.LargeBinary, nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

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

def configure_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )

def create_app():
    app = Flask(__name__)
    CORS(app, resources={r"/*": {"origins": "*"}})

    configure_logging()
    configure_database(app)
    db.init_app(app)

    register_routes(app)

    with app.app_context():
        db.create_all()

    return app