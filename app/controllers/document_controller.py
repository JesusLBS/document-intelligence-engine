from app.services.document_service import DocumentService


class DocumentController:
    """
    Handle document requests.
    """

    def __init__(self):
        self.document_service = DocumentService()

    def health(self):
        """
        Health endpoint.

        Returns:
            tuple
        """
        return self.document_service.health(), 200