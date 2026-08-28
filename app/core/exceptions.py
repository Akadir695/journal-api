class AppError(Exception):
    """Base class for all errors this application raises."""

    status_code: int = 500
    title: str = "Internal server error"
    type: str = "about:blank"

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class NotFoundError(AppError):
    status_code = 404
    title = "Not found"
    type = "https://journal.api/errors/not-found"


class ConflictError(AppError):
    status_code = 409
    title = "Conflict"
    type = "https://journal.api/errors/conflict"


class UnauthorizedError(AppError):
    status_code = 401
    title = "Unauthorized"
    type = "https://journal.api/errors/unauthorized"
