import json
import os
import shutil

from PIL import Image

from app.helpers.logger import Logger


DEBUG_FOLDER = "storage/debug"
# Debug folders kept on disk (one per request with debug_mode=true); older ones are pruned.
DEBUG_KEEP = 10


class DebugStore:
    """
    Snapshot of one request with debug_mode=true, for any document and file type.

    Everything lands in storage/debug/{request_id}/: the uploaded file, the page images of the
    requested range, the file and text each extractor received, and the request/result as JSON.
    It holds document data (git-ignored, local only, last DEBUG_KEEP requests), unlike the logs.
    """

    def __init__(self, request_id: str):
        """
        Create the request folder and prune older ones.

        Args:
            request_id (str): Request id, used as folder name.
        """
        self.request_id = request_id
        self.folder = os.path.join(DEBUG_FOLDER, request_id)
        self._prune_folders(keep=request_id)
        os.makedirs(self.folder, exist_ok=True)

    def save_file(self, source_path: str, name: str) -> None:
        """
        Copy a file (upload, exported pages) into the debug folder.

        Args:
            source_path (str): File to copy.
            name (str): File name inside the debug folder.
        """
        shutil.copyfile(source_path, os.path.join(self.folder, name))

    def save_pages(self, pages: list[Image.Image], first_page: int = 1) -> None:
        """
        Save page images named after their real page number in the document.

        Args:
            pages (list[Image.Image]): Rendered pages of the requested range.
            first_page (int): Page number of the first image (from_page).
        """
        for offset, page in enumerate(pages):
            page.save(os.path.join(self.folder, f"page_{first_page + offset}.png"))

    def save_text(self, name: str, text: str) -> None:
        """
        Save a text file (e.g. the text sent to the extractor).

        Args:
            name (str): File name inside the debug folder.
            text (str): Content.
        """
        with open(os.path.join(self.folder, name), "w", encoding="utf-8") as f:
            f.write(text)

    def save_json(self, name: str, data: dict) -> None:
        """
        Save a JSON file (request summary, extraction result).

        Args:
            name (str): File name inside the debug folder.
            data (dict): JSON-serializable content.
        """
        with open(os.path.join(self.folder, name), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    def log_saved(self) -> None:
        """Log where the snapshot is (path only, never its content)."""
        Logger.info("Debug snapshot saved", path=self.folder, files=len(os.listdir(self.folder)))

    @staticmethod
    def _prune_folders(keep: str) -> None:
        """
        Keep only the most recent debug folders so storage/debug does not grow forever.

        Unlike wiping everything, this never deletes the folder of a request that is
        still running (its own, or a concurrent one among the most recent).

        Args:
            keep (str): Request id whose folder must survive regardless of age.
        """
        if not os.path.isdir(DEBUG_FOLDER):
            return

        folders = [
            os.path.join(DEBUG_FOLDER, name)
            for name in os.listdir(DEBUG_FOLDER)
            if name != keep and os.path.isdir(os.path.join(DEBUG_FOLDER, name))
        ]
        folders.sort(key=os.path.getmtime, reverse=True)

        # The current request adds one more folder, so keep DEBUG_KEEP - 1 previous ones.
        for folder in folders[DEBUG_KEEP - 1:]:
            shutil.rmtree(folder, ignore_errors=True)
