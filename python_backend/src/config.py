
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Database
    DB_HOST = os.getenv('DB_HOST')
    DB_PORT = os.getenv('DB_PORT', '5432')
    DB_NAME = os.getenv('DB_NAME')
    DB_USER = os.getenv('DB_USER')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    SQLALCHEMY_DATABASE_URI = (
        f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Document AI
    DOCAI_PROJECT_ID = os.getenv('DOCAI_PROJECT_ID', '227652139161')
    DOCAI_LOCATION = os.getenv('DOCAI_LOCATION', 'us')
    DOCAI_PROCESSOR_ID = os.getenv('DOCAI_PROCESSOR_ID', '1e60d3bd63a0d751')