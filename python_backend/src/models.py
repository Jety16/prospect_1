from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class File(db.Model):
    __tablename__ = 'files'

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    content = db.Column(db.LargeBinary, nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    nombre = db.Column(db.String(255), nullable=True)
    total = db.Column(db.String(100), nullable=True)
    rmu = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return f"<File filename='{self.filename}' id={self.id}>"

    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'uploaded_at': self.uploaded_at.isoformat(),
            'nombre': self.nombre,
            'total': self.total,
            'rmu': self.rmu
        }

