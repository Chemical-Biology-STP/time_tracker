"""Entry point for running the Flask Time Tracker application."""
from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
