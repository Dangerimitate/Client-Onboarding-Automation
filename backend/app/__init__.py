import os
from pathlib import Path
from flask import Flask, send_from_directory, send_file
from .config import config_by_name
from .extensions import cors
from .models import init_db
from .controllers.client_controller import client_bp
from .controllers.message_controller import message_bp
from .controllers.ingestion_controller import ingestion_bp
from .controllers.stats_controller import stats_bp
from .controllers.inbox_controller import inbox_bp

def create_app(config_name: str = "default") -> Flask:
    """
    Industrial Application Factory for CA Firm Onboarding Backend.
    """
    app = Flask(__name__)
    config_obj = config_by_name.get(config_name, config_by_name["default"])
    app.config.from_object(config_obj)

    # Initialize extensions
    cors.init_app(app, resources={r"/*": {"origins": "*"}})

    # Ensure directories & DB exist
    app.config["UPLOAD_DIR"].mkdir(parents=True, exist_ok=True)
    init_db(app.config["DB_PATH"])

    # Register modular controllers
    app.register_blueprint(client_bp)
    app.register_blueprint(message_bp)
    app.register_blueprint(ingestion_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(inbox_bp)

    @app.route("/api/health", methods=["GET"])
    def health_check():
        return {"status": "healthy", "service": "CA Onboarding Backend (MVC)"}

    # Angular SPA static serving
    angular_dist = app.config["BASE_DIR"] / "frontend" / "dist" / "frontend" / "browser"

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_angular(path):
        if path != "" and (angular_dist / path).exists():
            return send_from_directory(str(angular_dist), path)
        if (angular_dist / "index.html").exists():
            return send_file(str(angular_dist / "index.html"))
        return {"error": "Angular frontend not built yet. Run 'npm run build' inside frontend/"}, 404

    return app
