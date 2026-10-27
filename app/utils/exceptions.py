from typing import Any


class AppBaseException(Exception):
    def __init__(
        self, message: str, status_code: int, error_code: str, content: dict[str, Any]
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.error_code = error_code

        super().__init__(message, status_code, error_code)

        self.content = content or {}


class UnauthorizedException(AppBaseException):
    def __init__(self, message: str, status_code: int, error_code: str, content: dict):
        super().__init__(
            message=message,
            status_code=status_code,
            error_code=error_code,
            content=content,
        )


class UnAvailableService(AppBaseException):
    def __init__(self, message: str, status_code: int, error_code: str, content: dict):
        super().__init__(
            message=message,
            status_code=status_code,
            error_code=error_code,
            content=content,
        )


class KeycloakAdminError(AppBaseException):
    def __init__(self, message: str, status_code: int, error_code: str, content: dict):
        super().__init__(
            message=message,
            status_code=status_code,
            error_code=error_code,
            content=content,
        )
