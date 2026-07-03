"""Entry point. Run with `python run.py` (same as the original single-file app)."""
from app import create_app
from app.config import get_config

app = create_app()

if __name__ == "__main__":
    config = get_config()
    print(f"Starting ClipAI on port {config.port}")
    app.run(debug=False, host="0.0.0.0", port=config.port)
