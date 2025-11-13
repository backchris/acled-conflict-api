from flask import Flask, jsonify
from flask_cors import CORS
from flasgger import Flasgger, swag_from
import os

from .extensions import db, jwt
from .config import Config

# Store specs_dir for use by @swag_from decorators
_specs_dir = None

def get_specs_path(filename):
    """Get absolute path to a spec file"""
    global _specs_dir
    if _specs_dir is None:
        # This is set during app creation
        return os.path.join(os.path.dirname(__file__), 'specs', filename)
    return os.path.join(_specs_dir, filename)

def create_app(config=Config):
    """
    Create Flask App instance
    
    Arguments:
        config -- configuration class to use (default: Config)
    Returns:
        Configured Flask app instance
    """
    #1. Create Flask app instance
    app = Flask(__name__)

    #2. Load configuration passed from argument or default to DevelopmentConfig
    app.config.from_object(config)

    #3. Initialize extensions with app instance
    db.init_app(app)
    jwt.init_app(app)
    CORS(app)  # Enable CORS for all routes

    #3.5. Initialize Flasgger for Swagger UI
    global _specs_dir
    _specs_dir = os.path.join(os.path.dirname(__file__), 'specs')
    Flasgger(app)

    # 4. Register blueprints (routes)
    try:
        from .routes.auth import auth_bp
        app.register_blueprint(auth_bp, url_prefix='/auth')
    except ImportError:
        pass
    
    try:
        from .routes.conflict import conflict_bp
        app.register_blueprint(conflict_bp, url_prefix='/conflictdata')
    except ImportError:
        pass
    
    # 6. Import models so SQLAlchemy registers them, then create tables
    with app.app_context():
        from . import models  # noqa: F401 - import to register models
        db.create_all()
    
    # 7. Health check endpoint
    @app.route('/health', methods=['GET'])
    @swag_from(os.path.join(os.path.dirname(__file__), 'specs', 'health.yaml'))
    def health():
        """Health check endpoint"""
        return jsonify({'status': 'ok'}), 200
    
    # 8. Return the configured app
    return app