import json
import os

from PIL import Image

from app.helpers import debug_store
from app.helpers.debug_store import DebugStore


class TestDebugFolderPruning:
    """debug_mode keeps the most recent folders instead of wiping other requests' output."""

    def test_keeps_recent_folders_and_the_current_one(self, tmp_path, monkeypatch):
        monkeypatch.setattr(debug_store, "DEBUG_FOLDER", str(tmp_path))

        for i in range(15):
            folder = tmp_path / f"old-{i:02d}"
            folder.mkdir()
            os.utime(folder, (1_000_000 + i, 1_000_000 + i))
        current = tmp_path / "current-request"
        current.mkdir()
        os.utime(current, (1, 1))  # oldest on disk, but it belongs to the running request

        DebugStore("current-request")

        remaining = sorted(p.name for p in tmp_path.iterdir())
        assert "current-request" in remaining
        assert len(remaining) == debug_store.DEBUG_KEEP
        assert "old-14" in remaining and "old-00" not in remaining


class TestSnapshot:
    """Files land in the request folder; pages keep their real page number."""

    def test_saves_files_pages_text_and_json(self, tmp_path, monkeypatch):
        monkeypatch.setattr(debug_store, "DEBUG_FOLDER", str(tmp_path))
        source = tmp_path / "upload.pdf"
        source.write_bytes(b"%PDF fake")

        store = DebugStore("req-1")
        store.save_file(str(source), "original.pdf")
        store.save_pages([Image.new("RGB", (10, 10)), Image.new("RGB", (10, 10))], first_page=3)
        store.save_text("extractor_text.txt", "texto")
        store.save_json("request.json", {"document_type": "comprobante_domicilio"})

        folder = tmp_path / "req-1"
        assert sorted(p.name for p in folder.iterdir()) == [
            "extractor_text.txt", "original.pdf", "page_3.png", "page_4.png", "request.json",
        ]
        assert json.loads((folder / "request.json").read_text())["document_type"] == "comprobante_domicilio"
