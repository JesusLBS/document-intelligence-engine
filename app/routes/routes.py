from flask import Blueprint, jsonify

from app.controllers.document_controller import DocumentController

api = Blueprint("api", __name__)
document_controller = DocumentController()


@api.route("/health", methods=["GET"])
def health():
    return jsonify(document_controller.health()), 200


@api.route("/documents/process", methods=["POST"])
def process():
    result, status = document_controller.process()
    return jsonify(result), status