"""Simple token authentication plus per-user authorization.

Each token belongs to one user. Requests send it as "Authorization: Bearer <token>" and may only
read that user's data. Only a SHA-256 hash of each token is stored, in the JSON file config.TOKENS_FILE.

Create a token:  python -m backend.auth <user_id>
"""

import hashlib
import json
import re
import secrets
import sys
from pathlib import Path
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from . import config
from .errors import api_error
from .models import UserId

bearer = HTTPBearer(auto_error=False)  # also adds the "Authorize" button to /docs


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def load_tokens() -> dict[str, str]:
    """{token hash: user id}. No file yet means no tokens."""
    path = Path(config.TOKENS_FILE)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def create_token(user_id: str) -> str:
    """Create a token for user_id and store its hash. The token itself is returned once and never stored."""
    token = secrets.token_urlsafe(32)
    tokens = load_tokens()
    tokens[hash_token(token)] = user_id
    Path(config.TOKENS_FILE).write_text(json.dumps(tokens, indent=2), encoding="utf-8")
    return token


def _unauthenticated(msg: str):
    return api_error(401, "not_authenticated", ["header", "Authorization"], msg,
                     headers={"WWW-Authenticate": "Bearer"})


def current_user(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> str:
    """Authentication: which user does this token belong to?"""
    if credentials is None:
        raise _unauthenticated("missing bearer token")
    user_id = load_tokens().get(hash_token(credentials.credentials))
    if user_id is None:
        raise _unauthenticated("invalid token")
    return user_id


def authorize(user_id: UserId, caller: Annotated[str, Depends(current_user)]) -> None:
    """Authorization: a token may only read its own user's data."""
    if caller != user_id:
        raise api_error(403, "forbidden", ["path", "user_id"],
                        f"this token may not read user {user_id!r}", user_id)


if __name__ == "__main__":
    if len(sys.argv) != 2 or not re.fullmatch(config.NAME_PATTERN, sys.argv[1]):
        sys.exit("usage: python -m backend.auth <user_id>")
    print(create_token(sys.argv[1]))
