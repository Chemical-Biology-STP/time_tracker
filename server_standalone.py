#!/usr/bin/env python3
"""Standalone Flask server entry point for PyInstaller bundling."""
import os
import sys

# When running as a bundled app, set the instance path to a writable location
if getattr(sys, 'frozen', False):
    # Running as bundled executable
    bundle_dir = os.path.dirname(sys.executable)
    # Use Application Support for the database
    app_support = os.path.expanduser('~/Library/Application Support/TimeTrackerCompanion')
    os.makedirs(app_support, exist_ok=True)
    instance_path = app_support
else:
    # Running in development
    bundle_dir = os.path.dirname(os.path.abspath(__file__))
    instance_path = os.path.join(bundle_dir, 'instance')

# Set environment variable for Flask instance path
os.environ['INSTANCE_PATH'] = instance_path

from app import create_app

# Create app with custom instance path
app = create_app({
    'SQLALCHEMY_DATABASE_URI': f'sqlite:///{os.path.join(instance_path, "time_tracker.db")}'
})

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Time Tracker Server')
    parser.add_argument('--port', type=int, default=5001, help='Port to run on')
    parser.add_argument('--host', type=str, default='127.0.0.1', help='Host to bind to')
    args = parser.parse_args()
    
    print(f"Starting Time Tracker server on {args.host}:{args.port}")
    print(f"Database location: {instance_path}")
    
    # Use waitress for production-ready serving (or fallback to Flask dev server)
    try:
        from waitress import serve
        serve(app, host=args.host, port=args.port)
    except ImportError:
        app.run(host=args.host, port=args.port, debug=False)
