import io
import os

from werkzeug.datastructures import FileStorage

from app.services.document_service import DocumentService


class TestTemporaryUploads:
    """Temporary upload files must never collide between requests."""

    def test_each_request_gets_its_own_file(self):
        service = DocumentService()
        first = FileStorage(stream=io.BytesIO(b"first"), filename="a.pdf")
        second = FileStorage(stream=io.BytesIO(b"second"), filename="b.pdf")

        first_path = service._save(first, "pdf", "request-1")
        second_path = service._save(second, "pdf", "request-2")

        try:
            assert first_path != second_path
            with open(first_path, "rb") as f:
                assert f.read() == b"first"
            with open(second_path, "rb") as f:
                assert f.read() == b"second"
        finally:
            service._cleanup(first_path)
            service._cleanup(second_path)

        assert not os.path.exists(first_path)
        assert not os.path.exists(second_path)
