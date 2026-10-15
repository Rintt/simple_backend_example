"""Integration tests for the API, against the real Azure blob storage.

Needs: internet access. Tokens are created in a temporary file, so your own tokens.json is never touched.
Run:   python -m pytest -v                            # all tests
       python -m pytest tests/test_calculations.py   # fast unit tests only
"""

import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend import auth, blob_storage, calculations, config
from backend.main import app

PART_SIZES = {"fluid": 57624, "housing": 72536, "obstacle": 748}  # dambreak particle counts


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def tokens(tmp_path_factory):
    """A token per user, stored in a temporary tokens file for the duration of this module."""
    original = config.TOKENS_FILE
    config.TOKENS_FILE = str(tmp_path_factory.mktemp("auth") / "tokens.json")
    created = {user: auth.create_token(user) for user in ("0", "1", "999")}
    yield created
    config.TOKENS_FILE = original


@pytest.fixture(scope="module")
def client(tokens):
    with TestClient(app, headers=auth_header(tokens["0"])) as c:  # acts as user 0 unless a test says otherwise
        yield c


def stats(client, attribute, stat, outputs, parts, user="0", sim="dambreak", headers=None):
    return client.get(
        f"/users/{user}/simulations/{sim}/stats",
        params={"attribute": attribute, "stat": stat, "outputs": outputs, "parts": parts},
        headers=headers,
    )


# ======================= endpoints =======================

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


@pytest.mark.parametrize("user, expected", [("0", ["dambreak", "moving_cube"]), ("1", ["dambreak"])])
def test_list_simulations(client, tokens, user, expected):
    r = client.get(f"/users/{user}/simulations", headers=auth_header(tokens[user]))
    assert r.status_code == 200
    assert r.json() == expected


def test_list_simulations_unknown_user(client, tokens):
    assert client.get("/users/999/simulations", headers=auth_header(tokens["999"])).status_code == 404


def test_list_simulations_invalid_user(client):
    assert client.get("/users/a.b/simulations").status_code == 422


def test_list_outputs(client):
    r = client.get("/users/0/simulations/dambreak/outputs")
    assert r.status_code == 200
    assert r.json() == [0, 1, 2]


def test_list_outputs_unknown_simulation(client):
    assert client.get("/users/0/simulations/nope/outputs").status_code == 404


@pytest.mark.parametrize("sim, expected", [
    ("dambreak", {"fluid", "housing", "obstacle"}),
    ("moving_cube", {"filling", "housing", "moving_square"}),
])
def test_list_parts(client, sim, expected):
    r = client.get(f"/users/0/simulations/{sim}/parts")
    assert r.status_code == 200
    assert set(r.json()) == expected


# Reference values computed directly from the HDF5 files with numpy
@pytest.mark.parametrize("attribute, stat, outputs, parts, value, count", [
    ("velocity", "max", "1", "fluid", 3.97931, 57624),
    ("velocity", "max", "0,1,2", "fluid", 4.50758, 172872),
    ("pressure", "max", "1", "fluid", 3571, 57624),
    ("pressure", "average", "0,1,2", "housing,obstacle", 427.7825, 219852),
])
def test_stats_reference_values(client, attribute, stat, outputs, parts, value, count):
    r = stats(client, attribute, stat, outputs, parts)
    assert r.status_code == 200
    body = r.json()
    assert body["value"] == pytest.approx(value, rel=1e-3)
    assert body["count"] == count


@pytest.mark.parametrize("stat", ["min", "max", "average", "median", "p95"])
def test_every_stat_returns_a_number(client, stat):
    r = stats(client, "pressure", stat, "0,1,2", "fluid")
    assert r.status_code == 200
    assert isinstance(r.json()["value"], float)


def test_repeated_and_comma_params_are_equal(client):
    comma = stats(client, "velocity", "average", "0,1", "fluid,housing").json()
    repeated = stats(client, "velocity", "average", ["0", "1"], ["fluid", "housing"]).json()
    assert comma["value"] == repeated["value"]
    assert comma["count"] == repeated["count"]


def test_duplicates_are_counted_once(client):
    body = stats(client, "pressure", "average", "1,1", "fluid,fluid").json()
    assert body["outputs"] == [1]
    assert body["parts"] == ["fluid"]
    assert body["count"] == PART_SIZES["fluid"]


def test_users_with_same_data_give_same_result(client, tokens):
    a = stats(client, "velocity", "max", "0,1,2", "fluid", user="0").json()
    b = stats(client, "velocity", "max", "0,1,2", "fluid", user="1", headers=auth_header(tokens["1"])).json()
    assert a["value"] == b["value"]


# ======================= validation and errors =======================

@pytest.mark.parametrize("params, status", [
    ({}, 422),                                                                                  # nothing given
    ({"attribute": "velocity", "stat": "mean", "outputs": "1", "parts": "fluid"}, 422),        # unknown stat
    ({"attribute": "speed", "stat": "max", "outputs": "1", "parts": "fluid"}, 422),            # unknown attribute
    ({"attribute": "velocity", "stat": "max", "outputs": "a", "parts": "fluid"}, 422),         # non-integer output
    ({"attribute": "velocity", "stat": "max", "outputs": ",", "parts": "fluid"}, 422),         # empty list
    ({"attribute": "velocity", "stat": "max", "outputs": "-1", "parts": "fluid"}, 422),        # negative output
    ({"attribute": "velocity", "stat": "max", "outputs": ",".join(map(str, range(21))), "parts": "fluid"}, 422),  # > MAX_OUTPUTS
    ({"attribute": "velocity", "stat": "max", "outputs": "1", "parts": "fluid", "foo": "x"}, 422),  # unknown parameter
    ({"attribute": "velocity", "stat": "max", "outputs": "7", "parts": "fluid"}, 404),         # missing output
    ({"attribute": "velocity", "stat": "max", "outputs": "1", "parts": "nope"}, 404),          # missing part
])
def test_stats_errors(client, params, status):
    assert client.get("/users/0/simulations/dambreak/stats", params=params).status_code == status


def test_stats_unknown_simulation(client):
    assert stats(client, "velocity", "max", "1", "fluid", sim="nope").status_code == 404


@pytest.mark.parametrize("url, status, loc", [
    ("/users/0/simulations/dambreak/stats?attribute=velocity&stat=max&outputs=7&parts=fluid", 404, ["query", "outputs"]),
    ("/users/0/simulations/dambreak/stats?attribute=velocity&stat=max&outputs=1&parts=nope", 404, ["query", "parts"]),
    ("/users/1/simulations", 403, ["path", "user_id"]),
    ("/users/0/simulations/dambreak/stats?attribute=velocity&stat=mean&outputs=1&parts=fluid", 422, ["query", "stat"]),
])
def test_errors_share_one_shape(client, url, status, loc):
    r = client.get(url)
    assert r.status_code == status
    error = r.json()["detail"][0]
    assert {"type", "loc", "msg"} <= error.keys()
    assert error["loc"] == loc


def test_openapi_documents_contract(client):
    spec = client.get("/openapi.json").json()
    assert "StatsResponse" in spec["components"]["schemas"]
    params = {p["name"] for p in spec["paths"]["/users/{user_id}/simulations/{simulation}/stats"]["get"]["parameters"]}
    assert params == {"user_id", "simulation", "attribute", "stat", "outputs", "parts"}


# ======================= authentication and authorization =======================

def test_health_needs_no_token():
    assert TestClient(app).get("/health").status_code == 200


def test_missing_token_is_rejected(tokens):
    r = TestClient(app).get("/users/0/simulations")
    assert r.status_code == 401
    assert r.headers["WWW-Authenticate"] == "Bearer"


def test_invalid_token_is_rejected(tokens):
    assert TestClient(app).get("/users/0/simulations", headers=auth_header("not-a-token")).status_code == 401


@pytest.mark.parametrize("path", [
    "/users/1/simulations",
    "/users/1/simulations/dambreak/outputs",
    "/users/1/simulations/dambreak/parts",
    "/users/1/simulations/dambreak/stats?attribute=velocity&stat=max&outputs=0&parts=fluid",
])
def test_token_cannot_read_another_user(client, path):
    assert client.get(path).status_code == 403  # client holds user 0's token


def test_tokens_are_stored_hashed(tokens):
    stored = auth.load_tokens()
    assert tokens["0"] not in stored
    assert stored[auth.hash_token(tokens["0"])] == "0"


# ======================= every statistic against the raw data =======================

@pytest.fixture(scope="module")
def raw_outputs():
    """The three dambreak outputs of user 0, downloaded once for the comparisons below."""
    return {n: blob_storage.load_output("0", "dambreak", n) for n in (0, 1, 2)}


@pytest.mark.parametrize("attribute, outputs, parts", [
    ("velocity", [0, 1, 2], ["fluid"]),
    ("pressure", [0, 1, 2], ["housing", "obstacle"]),
    ("pressure", [1], ["fluid", "housing", "obstacle"]),
])
@pytest.mark.parametrize("stat", ["min", "max", "average", "median", "p95"])
def test_api_matches_raw_data(client, raw_outputs, attribute, outputs, parts, stat):
    body = stats(client, attribute, stat, ",".join(map(str, outputs)), ",".join(parts)).json()

    arrays = [raw_outputs[n][part][attribute] for n in outputs for part in parts]
    if attribute == "velocity":
        arrays = [np.linalg.norm(a, axis=1) for a in arrays]  # independent of calculations.per_particle_values
    values = np.concatenate(arrays)

    assert body["count"] == values.size
    assert body["value"] == pytest.approx(float(calculations.STATS[stat](values)))
