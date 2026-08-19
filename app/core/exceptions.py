class AppError(Exception):
    """Base class for all errors this application raises."""

    status_code: int = 500

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):
    status_code = 409
    
class UnauthorizedError(AppError):
    status_code = 401
