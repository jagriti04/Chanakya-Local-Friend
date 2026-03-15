"""
Flask application factory and configuration.

Creates the Flask app instance with CORS, template/static paths, and logging.
"""

import os
import logging
from flask import Flask
from flask_cors import CORS
from .. import config

app = Flask(
    __name__,
    template_folder=os.path.join(config.PROJECT_ROOT, "src", "frontend", "templates"),
    static_folder=os.path.join(config.PROJECT_ROOT, "src", "frontend", "static"),
)
CORS(app)
app.secret_key = config.APP_SECRET_KEY

log_handler = logging.StreamHandler()
log_handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
log_handler.setFormatter(formatter)

if not app.logger.handlers:
    app.logger.addHandler(log_handler)

app.logger.setLevel(logging.INFO)
app.logger.info("Flask app initialized and logger configured.")
