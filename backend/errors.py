"""One error format for every error, the same shape as FastAPI's own validation errors:
{"detail": [{"type": ..., "loc": [...], "msg": ..., "input": ...}]}
"""

from fastapi import HTTPException


def api_error(status: int, type_: str, loc: list[str], msg: str, input=None,
              headers: dict[str, str] | None = None) -> HTTPException:
    return HTTPException(status, [{"type": type_, "loc": loc, "msg": msg, "input": input}], headers=headers)
