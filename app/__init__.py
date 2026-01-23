"""Flask application factory for Time Tracker."""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app(config=None):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Default configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///time_tracker.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'dev-secret-key'
    
    # Override with custom config if provided
    if config:
        app.config.update(config)
    
    # Initialize extensions
    db.init_app(app)
    
    # Create tables
    with app.app_context():
        from . import models  # noqa: F401
        db.create_all()

    # Register blueprints
    from . import routes
    app.register_blueprint(routes.bp)
    
    from . import api
    app.register_blueprint(api.api_bp)

    return app
