"""
Application factory. Building the Flask app through a function (instead
of a module-level `app = Flask(__name__)`) means tests can create fresh,
isolated app instances, and the dependency container is created once and
attached to `app.config` rather than living as ad-hoc module globals.
"""
from flask import Flask

from app.api.routes import bp as clipai_bp
from app.container import Container, build_container


def create_app(container: Container = None) -> Flask:
    """Build the Flask app.

    `container` is an optional seam for tests: pass a `Container` built
    from fakes (see tests/test_routes.py) to exercise routes without any
    real ffmpeg/Whisper/OpenRouter calls. Production code (run.py) always
    calls `create_app()` with no arguments, which builds the real
    container exactly as before.
    """
    flask_app = Flask(__name__)
    flask_app.config["CONTAINER"] = container or build_container()
    flask_app.register_blueprint(clipai_bp)
    return flask_app
