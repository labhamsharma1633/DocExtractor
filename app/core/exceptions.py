from typing import Any, Dict, Optional
from fastapi import status


class AppException(Exception):
    """Base application exception."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class EntityNotFoundException(AppException):
    def __init__(self, entity_name: str, entity_id: Any):
        super().__init__(
            message=f"{entity_name} with identifier '{entity_id}' not found.",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"entity_name": entity_name, "entity_id": str(entity_id)},
        )


class UnauthorizedException(AppException):
    def __init__(self, message: str = "Could not validate credentials"):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details={"auth_error": True},
        )


class ForbiddenException(AppException):
    def __init__(self, message: str = "Access to the requested resource is forbidden"):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            details={"forbidden": True},
        )


class InvalidFileTypeException(AppException):
    def __init__(self, detected_mime: str, allowed_types: list):
        super().__init__(
            message=f"Unsupported media type '{detected_mime}'. Allowed formats: {allowed_types}",
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            details={"detected_mime": detected_mime, "allowed_types": allowed_types},
        )


class FileTooLargeException(AppException):
    def __init__(self, max_bytes: int, actual_bytes: int):
        super().__init__(
            message=f"Uploaded file size ({actual_bytes} bytes) exceeds maximum limit of {max_bytes} bytes.",
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            details={"max_bytes": max_bytes, "actual_bytes": actual_bytes},
        )


class DocumentProcessingException(AppException):
    def __init__(self, message: str, stage: str = "UNKNOWN"):
        super().__init__(
            message=f"Document processing failure at stage '{stage}': {message}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={"stage": stage},
        )
