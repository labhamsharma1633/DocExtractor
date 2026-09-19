import os
import shutil
import uuid
from abc import ABC, abstractmethod
from typing import BinaryIO, Tuple
from app.core.config import settings
from app.core.exceptions import FileTooLargeException, InvalidFileTypeException


class StorageService(ABC):
    """Abstract interface for document file storage."""

    @abstractmethod
    def save_file(self, file_obj: BinaryIO, original_filename: str) -> Tuple[str, str, int]:
        """Saves a file stream and returns (stored_filename, mime_type, file_size_bytes)."""
        pass

    @abstractmethod
    def get_file_path(self, stored_filename: str) -> str:
        """Returns the absolute or reachable path to the stored file."""
        pass

    @abstractmethod
    def delete_file(self, stored_filename: str) -> bool:
        """Deletes a file from storage."""
        pass


class LocalStorageService(StorageService):
    """Local filesystem implementation of StorageService."""

    def __init__(self, base_dir: str = settings.UPLOAD_DIR):
        self.base_dir = os.path.abspath(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)

    def _detect_mime_type(self, file_bytes: bytes, filename: str) -> str:
        """Detects MIME type using magic byte inspection with extension fallback."""
        # Magic bytes inspection
        if file_bytes.startswith(b"%PDF"):
            return "application/pdf"
        elif file_bytes.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        elif file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"

        # Fallback to python-magic if installed
        try:
            import magic
            mime = magic.from_buffer(file_bytes, mime=True)
            if mime in settings.ALLOWED_MIME_TYPES:
                return mime
        except Exception:
            pass

        # Fallback to filename extension check
        ext = os.path.splitext(filename.lower())[1]
        if ext == ".pdf":
            return "application/pdf"
        elif ext in [".jpg", ".jpeg"]:
            return "image/jpeg"
        elif ext == ".png":
            return "image/png"

        return "application/octet-stream"

    def save_file(self, file_obj: BinaryIO, original_filename: str) -> Tuple[str, str, int]:
        # Read initial chunk for MIME detection and size check
        file_obj.seek(0, os.SEEK_END)
        file_size = file_obj.tell()
        file_obj.seek(0)

        if file_size > settings.MAX_UPLOAD_SIZE_BYTES:
            raise FileTooLargeException(settings.MAX_UPLOAD_SIZE_BYTES, file_size)

        sample_bytes = file_obj.read(2048)
        file_obj.seek(0)

        mime_type = self._detect_mime_type(sample_bytes, original_filename)
        if mime_type not in settings.ALLOWED_MIME_TYPES:
            raise InvalidFileTypeException(mime_type, settings.ALLOWED_MIME_TYPES)

        # Generate secure randomized filename
        ext = os.path.splitext(original_filename)[1].lower()
        if not ext:
            if mime_type == "application/pdf":
                ext = ".pdf"
            elif mime_type == "image/jpeg":
                ext = ".jpg"
            elif mime_type == "image/png":
                ext = ".png"

        stored_filename = f"{uuid.uuid4().hex}{ext}"
        destination_path = os.path.join(self.base_dir, stored_filename)

        with open(destination_path, "wb") as buffer:
            shutil.copyfileobj(file_obj, buffer)

        return stored_filename, mime_type, file_size

    def get_file_path(self, stored_filename: str) -> str:
        # Prevent directory traversal attacks
        safe_filename = os.path.basename(stored_filename)
        full_path = os.path.join(self.base_dir, safe_filename)
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"Stored file {stored_filename} not found.")
        return full_path

    def delete_file(self, stored_filename: str) -> bool:
        try:
            path = self.get_file_path(stored_filename)
            if os.path.exists(path):
                os.remove(path)
                return True
        except Exception:
            pass
        return False


def get_storage_service() -> StorageService:
    """Dependency / Factory providing the configured storage service."""
    return LocalStorageService()
