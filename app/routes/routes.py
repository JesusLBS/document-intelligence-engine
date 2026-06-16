from flask import Blueprint

from app.controllers.document_controller import DocumentController
from app.validators.document_validator import validate_process_document

api = Blueprint("api", __name__)
document_controller = DocumentController()


@api.route("/health", methods=["GET"])
def health():
    return document_controller.health()


@api.route("/documents/process", methods=["POST"])
@validate_process_document
def process():
    return document_controller.process()