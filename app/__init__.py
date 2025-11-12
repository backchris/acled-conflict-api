from flask import Flask, jsonify
from flask_cors import CORS # security mechanism to control which websites access API 

from .extensions import db, jwt, celery
from .config import DevelopmentConfig

def create_app(config = DevelopmentConfig):
    """
    Create Flask App instance
    
    Arguments:
        config -- configuration class to use (Config, DevelopmentConfig, TestingConfig - default: DevelopmentConfig)
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

    #4. Configure Celery - use so user doesn't have to wait by running background tasks asynchronously
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery.Task = ContextTask

    # 5. Register blueprints (routes)
    try:
        from .routes import auth_bp, conflict_bp
        if auth_bp is not None:
            app.register_blueprint(auth_bp, url_prefix='/auth')
        if conflict_bp is not None:
            app.register_blueprint(conflict_bp, url_prefix='/conflictdata')
    except ImportError:
        # Routes don't exist yet - that's ok for now
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