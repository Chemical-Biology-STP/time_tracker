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
    
    # Create tables and run migrations
    with app.app_context():
        from . import models  # noqa: F401
        db.create_all()
        
        # Auto-migrate: add missing columns to existing tables
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        
        if 'time_entries' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('time_entries')]
            if 'project_id' not in columns:
                db.session.execute(text(
                    'ALTER TABLE time_entries ADD COLUMN project_id INTEGER REFERENCES projects(id)'
                ))
                db.session.commit()

    # Register blueprints
    from . import routes
    app.register_blueprint(routes.bp)
    
    from . import api
    app.register_blueprint(api.api_bp)

    # Start auto-sync if configured
    try:
        from .sync import _load_config, start_auto_sync
        sync_config = _load_config()
        if sync_config.get('auto_sync') and sync_config.get('server_url') and sync_config.get('email'):
            start_auto_sync(app)
    except Exception:
        pass  # sync module may not be available (missing requests)

    return app
