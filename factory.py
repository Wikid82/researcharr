# -*- coding: utf-8 -*-
"""Flask application factory for researcharr."""
from flask import Flask

def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY="dev",
    )
    if test_config is not None:
        app.config.update(test_config)
    # Register blueprints, routes, error handlers, etc. here
    # Example: from . import webui; webui.init_app(app)
    return app
