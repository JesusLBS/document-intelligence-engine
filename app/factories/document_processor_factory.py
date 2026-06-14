class DocumentProcessorFactory:
    """
    Factory responsible for selecting processors.
    """

    @staticmethod
    def get_processor(file_type: str):
        """
        Resolve processor by file type.

        Args:
            file_type (str)

        Returns:
            object
        """
        raise NotImplementedError(
            f"Processor not implemented for [{file_type}]"
        )