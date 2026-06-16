from app.validators.base_validator import validate
from app.schemas.process_document import ProcessDocumentSchema

validate_process_document = validate(ProcessDocumentSchema())