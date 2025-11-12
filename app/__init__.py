from flask import Flask, jsonify
from flask_cors import CORS

from .extensions import db, jwt
from .config import Config

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
    def health():
        return jsonify({'status': 'ok'}), 200
    
    # 8. Return the configured app
    return app