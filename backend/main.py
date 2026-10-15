"""Diver's License: Statistics API.

Downloads the requested HDF5 outputs from the public Azure blob storage and computes one statistic
of one attribute over the selected outputs and parts. Every /users/{user_id}/... route needs that
user's bearer token (see auth.py).

Run:  python -m backend.auth 0     # prints a token for user 0
      uvicorn backend.main:app --reload
Docs: http://127.0.0.1:8000/docs
"""

from concurrent.futures import ThreadPoolExecutor
from typing import Annotated

from fastapi import Depends, FastAPI, Query

from .auth import authorize
from .blob_storage import list_blobs, load_output, output_numbers
from .calculations import compute_statistic
from .config import MAX_WORKERS
from .errors import api_error
from .models import Health, Simulation, StatsQuery, StatsResponse, UserId

executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)  # downloads outputs in parallel, shared by all requests

app = FastAPI(title="Diver's License: Statistics API")


@app.get("/health")
def health() -> Health:
    """Liveness check."""
    return Health(status="ok")


@app.get("/users/{user_id}/simulations", dependencies=[Depends(authorize)])
def list_simulations(user_id: UserId) -> list[str]:
    """List the simulations of a user, e.g. ["dambreak", "moving_cube"]."""
    prefix = f"users/{user_id}/simulations/"
    sims = sorted({name.removeprefix(prefix).split("/")[0] for name in list_blobs(prefix)})
    if not sims:
        raise api_error(404, "not_found", ["path", "user_id"], f"user {user_id!r} not found", user_id)
    return sims


@app.get("/users/{user_id}/simulations/{simulation}/outputs", dependencies=[Depends(authorize)])
def list_outputs(user_id: UserId, simulation: Simulation) -> list[int]:
    """List the available output numbers of a simulation, e.g. [0, 1, 2]."""
    return output_numbers(user_id, simulation)


@app.get("/users/{user_id}/simulations/{simulation}/parts", dependencies=[Depends(authorize)])
def list_parts(user_id: UserId, simulation: Simulation) -> list[str]:
    """List the parts of a simulation, e.g. ["fluid", "housing", "obstacle"]."""
    first = output_numbers(user_id, simulation)[0]
    return list(load_output(user_id, simulation, first))


@app.get("/users/{user_id}/simulations/{simulation}/stats", dependencies=[Depends(authorize)])
def get_statistic(
    user_id: UserId,
    simulation: Simulation,
    query: Annotated[StatsQuery, Query()],
) -> StatsResponse:
    """One statistic of one attribute, over the selected outputs and parts (values pooled).

    Example: /users/0/simulations/dambreak/stats?attribute=velocity&stat=max&outputs=0,1,2&parts=fluid
    """
    available = output_numbers(user_id, simulation)
    missing = [n for n in query.outputs if n not in available]
    if missing:
        raise api_error(404, "not_found", ["query", "outputs"],
                        f"outputs not found: {missing}, available: {available}", missing)

    # Download all requested outputs in parallel; an error in any worker (e.g. a 502) is re-raised here
    loaded = list(executor.map(lambda n: load_output(user_id, simulation, n), query.outputs))

    arrays = []
    for data in loaded:
        unknown = [p for p in query.parts if p not in data]
        if unknown:
            raise api_error(404, "not_found", ["query", "parts"],
                            f"parts not found: {unknown}, available: {list(data)}", unknown)
        arrays += [data[part][query.attribute] for part in query.parts]

    value, count = compute_statistic(arrays, query.stat)
    return StatsResponse(
        user_id=user_id,
        simulation=simulation,
        attribute=query.attribute,
        stat=query.stat,
        outputs=query.outputs,
        parts=query.parts,
        count=count,
        value=value,
    )
