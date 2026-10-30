from flask_migrate import Migrate
from flask_restx import Api
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
migrate = Migrate()

api = Api(
    title="IES App API",
    version="1.0",
    description="IES earthquake application API",
    doc="/docs/",
    mask_swagger=False,
    error_404_help=False,
)
