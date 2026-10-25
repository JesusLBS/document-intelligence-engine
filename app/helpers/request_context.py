import uuid

from flask import Flask, g, has_request_context


def current_request_id() -> str | None:
    """
    Return the id of the request being handled.

    Returns:
        str | None: Request id, or None outside a request (CLI, tests calling services directly).
    """
    if has_request_context():
        return g.get("request_id")
    return None


def register_request_id(app: Flask) -> None:
    """
    Give every request a single id shared by the response, the logs and the processing pipeline.

    The id is returned in `meta.request_id` and in the `X-Request-ID` header, so a client
    report can be matched to its log lines and temp files.

    Args:
        app (Flask): Flask application instance.
    """

    @app.before_request
    def assign_request_id() -> None:
        """Generate the request id before any handler runs."""
        g.request_id = str(uuid.uuid4())

    @app.after_request
    def expose_request_id(response):
        """Echo the request id in a response header."""
        request_id = current_request_id()
        if request_id:
            response.headers["X-Request-ID"] = request_id
        return response
