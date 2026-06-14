from flask import Blueprint

from app.controllers.document_controller import DocumentController

api = Blueprint("api", __name__)

document_controller = DocumentController()


@api.route("/health", methods=["GET"])
def health():
    return document_controller.health()