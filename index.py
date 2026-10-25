from flask import Flask

from app.config import Config
from app.routes.routes import api
from app.config.logging import configure_logging
from app.exceptions.handler import register_error_handlers
from app.helpers.request_context import register_request_id

# Multipart framing and other form fields add a little on top of the file itself.
MULTIPART_OVERHEAD_BYTES = 1024 * 1024

configure_logging()

app = Flask(__name__)
app.json.sort_keys = False

# Reject oversized uploads (413) before Flask reads them; the schema still gives the exact per-file message.
app.config["MAX_CONTENT_LENGTH"] = Config.MAX_FILE_SIZE_MB * 1024 * 1024 + MULTIPART_OVERHEAD_BYTES

register_request_id(app)
register_error_handlers(app)

app.register_blueprint(
    api,
    url_prefix="/api/v1"
)

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        # APP_DEBUG drives the auto-reloader. The interactive Werkzeug debugger stays off:
        # every error is answered as JSON by the global handler, and it must never be reachable.
        debug=Config.APP_DEBUG,
        use_debugger=False,
    )
