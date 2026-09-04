from pydantic import BaseModel


class ProblemDetail(BaseModel):
    type: str
    title: str
    status: int
    detail: str
    instance: str
    request_id: str | None = None


AUTH_ERRORS = {
    401: {"model": ProblemDetail, "description": "Missing or invalid credentials"},
    403: {"model": ProblemDetail, "description": "Email address not verified"},
}

NOT_FOUND = {
    404: {
        "model": ProblemDetail,
        "description": "Not found, or belongs to another user",
    }
}

CONFLICT = {409: {"model": ProblemDetail, "description": "Conflict"}}
