"""Read-only access to the public Azure blob container (List Blobs API and plain downloads)."""

import io
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

import h5py
import numpy as np

from .config import CONTAINER_URL, TIMEOUT
from .errors import api_error

OutputData = dict[str, dict[str, np.ndarray]]  # {part: {attribute: array}}


def list_blobs(prefix: str) -> list[str]:
    """Names of all blobs under prefix (List Blobs API, follows pagination)."""
    names, marker = [], ""
    while True:
        query = {"restype": "container", "comp": "list", "prefix": prefix}
        if marker:
            query["marker"] = marker
        try:
            with urllib.request.urlopen(f"{CONTAINER_URL}?{urllib.parse.urlencode(query)}", timeout=TIMEOUT) as resp:
                root = ET.fromstring(resp.read())
        except (urllib.error.URLError, TimeoutError) as e:
            raise api_error(502, "blob_storage_error", ["blob_storage"], f"blob storage unreachable: {e}")
        names += [b.findtext("Name") for b in root.iter("Blob")]
        marker = root.findtext("NextMarker") or ""
        if not marker:
            return names


def blob_name(user_id: str, simulation: str, output: int) -> str:
    return f"users/{user_id}/simulations/{simulation}/output_{output}.hdf5"


def open_blob(name: str) -> h5py.File:
    """Download one blob into memory and open it as an HDF5 file."""
    try:
        with urllib.request.urlopen(f"{CONTAINER_URL}/{urllib.parse.quote(name)}", timeout=TIMEOUT) as resp:
            return h5py.File(io.BytesIO(resp.read()), "r")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise api_error(404, "not_found", ["blob_storage"], f"{name} not found", name)
        raise api_error(502, "blob_storage_error", ["blob_storage"], f"blob storage error: {e}")
    except (urllib.error.URLError, TimeoutError) as e:
        raise api_error(502, "blob_storage_error", ["blob_storage"], f"blob storage unreachable: {e}")


def load_output(user_id: str, simulation: str, output: int) -> OutputData:
    """Download one output and read all its arrays as {part: {attribute: array}}."""
    with open_blob(blob_name(user_id, simulation, output)) as f:
        return {part: {attr: f[part][attr][()] for attr in f[part]} for part in f}


def output_numbers(user_id: str, simulation: str) -> list[int]:
    """Sorted output numbers of a simulation; 404 if it has none."""
    prefix = f"users/{user_id}/simulations/{simulation}/"
    numbers = []
    for name in list_blobs(prefix):
        m = re.fullmatch(r"output_(\d+)\.hdf5", name.removeprefix(prefix))
        if m:
            numbers.append(int(m.group(1)))
    if not numbers:
        raise api_error(404, "not_found", ["path", "simulation"],
                        f"simulation {simulation!r} not found for user {user_id!r}", simulation)
    return sorted(numbers)
