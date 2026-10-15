"""Load test: REQUESTS authenticated requests at the same moment against a real uvicorn server.

Needs internet access. Skip it with: python -m pytest -m "not load"

The requests go to the listing endpoints. Without a cache, every /stats request downloads its files,
so many simultaneous /stats requests would pull GBs from the data provider's storage.
"""

import json
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from backend import auth, config

REQUESTS = 3000
CASES = [  # (user, path, expected answer)
    ("0", "/users/0/simulations", ["dambreak", "moving_cube"]),
    ("1", "/users/1/simulations", ["dambreak"]),
    ("0", "/users/0/simulations/dambreak/outputs", [0, 1, 2]),
    ("1", "/users/1/simulations/dambreak/outputs", [0, 1, 2]),
]
PROJECT_ROOT = Path(__file__).resolve().parent.parent

pytestmark = pytest.mark.load


@pytest.fixture(scope="module")
def tokens_file(tmp_path_factory):
    """A temporary tokens file with one token per user; returns (path, {user: token})."""
    path = str(tmp_path_factory.mktemp("auth") / "tokens.json")
    original = config.TOKENS_FILE
    config.TOKENS_FILE = path
    tokens = {user: auth.create_token(user) for user in ("0", "1")}
    config.TOKENS_FILE = original
    return path, tokens


@pytest.fixture(scope="module")
def server_url(tokens_file):
    """Start the API with uvicorn on a free port, like in production, and stop it afterwards."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--port", str(port), "--log-level", "warning"],
        cwd=PROJECT_ROOT,
        env={**os.environ, "TOKENS_FILE": tokens_file[0]},  # the server reads the test's tokens
    )
    url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(100):
            if proc.poll() is not None:
                pytest.fail("uvicorn exited during startup")
            try:
                urllib.request.urlopen(f"{url}/health", timeout=1)
                break
            except OSError:
                time.sleep(0.2)
        else:
            pytest.fail("uvicorn did not start")
        yield url
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def get_json(url: str, token: str, attempts: int = 5) -> tuple[int, object]:
    """GET with the user's token. Refused connections are retried with a short backoff:
    Windows caps the server's queue of waiting connections at about 200, so a burst of
    thousands of new connections gets some refused before uvicorn can accept them."""
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=180) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")
        except urllib.error.URLError as e:
            if not isinstance(e.reason, ConnectionRefusedError) or attempt == attempts - 1:
                raise
            time.sleep(0.1 * 2 ** attempt)  # 0.1 s, 0.2 s, 0.4 s, 0.8 s


def test_simultaneous_requests(server_url, tokens_file):
    _, tokens = tokens_file
    requests = [CASES[i % len(CASES)] for i in range(REQUESTS)]
    start = threading.Barrier(REQUESTS)  # releases all threads at the same moment

    def fire(case):
        user, path, _ = case
        start.wait(timeout=60)
        return get_json(server_url + path, tokens[user])

    began = time.perf_counter()
    with ThreadPoolExecutor(max_workers=REQUESTS) as pool:
        results = list(pool.map(fire, requests))
    print(f"\n{REQUESTS} simultaneous requests answered in {time.perf_counter() - began:.1f}s")

    statuses = Counter(status for status, _ in results)
    assert statuses == {200: REQUESTS}, statuses

    # Every request got the right answer, not just a 200
    wrong = [path for (_, body), (_, path, expected) in zip(results, requests) if body != expected]
    assert not wrong, Counter(wrong)
