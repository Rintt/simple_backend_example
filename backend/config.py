"""Settings. Values that differ per environment can be overridden with environment variables."""

import os

CONTAINER_URL = os.environ.get("CONTAINER_URL", "https://divepublic.blob.core.windows.net/divers-license")
TIMEOUT = 60  # seconds per HTTP call to blob storage
TOKENS_FILE = os.environ.get("TOKENS_FILE", "tokens.json")  # API token hashes; relative to where the server runs

NAME_PATTERN = r"^[A-Za-z0-9_-]+$"  # names go into blob paths, so this blocks "..", "/", etc.
MAX_OUTPUTS = 20  # every requested output is loaded into memory, so cap it per request
MAX_PARTS = 10
MAX_WORKERS = 8  # outputs downloaded in parallel, shared by all requests
