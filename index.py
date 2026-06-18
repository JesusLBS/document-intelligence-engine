from flask import Flask
from dotenv import load_dotenv

from app.routes.routes import api
from app.config.logging import configure_logging
from app.helpers.logger import Logger
from app.exceptions.handler import register_error_handlers

configure_logging()
load_dotenv()

app = Flask(__name__)
app.json.sort_keys = False
register_error_handlers(app)

app.register_blueprint(
    api,
    url_prefix="/api/v1"
)

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
    )