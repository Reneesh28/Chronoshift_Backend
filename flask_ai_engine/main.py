import os
import sys
from pathlib import Path

# Resolve absolute service folder and insert into sys.path to prevent import errors in nested folders
SERVICE_DIR = Path(__file__).resolve().parent
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))

from flask import Flask, jsonify
from flask_cors import CORS
from routes import ai_blueprint

def create_app():
    """
    Application factory pattern for the ChronoShift AI Microservice.
    """
    app = Flask(__name__)
    
    # Enable Cross-Origin Resource Sharing (CORS) for external frontend consumption
    CORS(app, resources={r"/*": {"origins": "*"}})
    
    # Register core routing blueprints
    app.register_blueprint(ai_blueprint)
    
    # Root entrypoint
    @app.route("/", methods=["GET"])
    def index():
        return jsonify({
            "service": "chronoshift_ai_engine",
            "status": "active",
            "docs": "/ai/health"
        }), 200

    # Global handler for unexpected application crashes
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            "error": True,
            "message": "Global application environment error intercepted.",
            "code": "AI_ENGINE_ERROR"
        }), 500

    # Global handler for missing routes
    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({
            "error": True,
            "message": "The requested API endpoint was not found.",
            "code": "INVALID_REQUEST"
        }), 404

    return app

# Expose global app handle for web server imports (e.g. gunicorn main:app)
app = create_app()

if __name__ == "__main__":
    # Deploy local service on port 8003
    port = int(os.getenv("AI_PORT", 8003))
    print(f"\n[BOOT] Initializing ChronoShift Flask AI Microservice...")
    print(f"[BOOT] Server listening on: http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=True)
