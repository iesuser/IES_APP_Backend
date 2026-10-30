from flask import Flask, request

from app.commands import init_db, populate_db, upgrade_db
from app.config import get_config
from app.extensions import api as restx_api
from app.extensions import db, migrate

COMMANDS = [init_db, upgrade_db, populate_db]


def create_app(config_object=None):
    app = Flask(__name__)
    app.config.from_object(config_object or get_config())

    register_extensions(app)
    register_commands(app)
    register_error_handlers(app)
    return app


def register_extensions(app):
    """Initialize Flask extensions."""
    db.init_app(app)
    migrate.init_app(app, db)

    # Namespaces register themselves on import, before RESTX is attached.
    from app import api as api_package  # noqa: F401

    restx_api.init_app(app)


def register_commands(app):
    for command in COMMANDS:
        app.cli.add_command(command)


def _is_api_request():
    return request.path == "/api" or request.path.startswith("/api/") or request.path == "/docs" or request.path.startswith("/docs/")


def register_error_handlers(app):
    @app.errorhandler(404)
    def page_not_found(_error):
        if _is_api_request():
            return {"error": "not_found", "message": "The requested API URL was not found."}, 404
        return {"error": "not_found", "message": "The requested URL was not found."}, 404

    @app.errorhandler(500)
    def server_error(_error):
        app.logger.exception("An exception occurred during a request.")
        return {"error": "server_error", "message": "Internal server error."}, 500
