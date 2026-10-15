"""The statistics the API offers, as pure functions (no network, no database)."""

import numpy as np

STATS = {
    "min": np.min,
    "max": np.max,
    "average": np.mean,
    "median": np.median,
    "p95": lambda values: np.percentile(values, 95),
}

def per_particle_values(array: np.ndarray) -> np.ndarray:
    """One number per particle: vectors (N, 3) become their magnitude, scalars (N,) stay as they are."""
    return np.linalg.norm(array, axis=1) if array.ndim == 2 else array


def compute_statistic(arrays: list[np.ndarray], stat: str) -> tuple[float, int]:
    """Pool the arrays of all selected outputs and parts, then compute one statistic over every particle.

    Pooling, rather than averaging per-part results, weights every particle equally.
    Returns (value, number of values).
    """
    values = np.concatenate([per_particle_values(a) for a in arrays])
    return float(STATS[stat](values)), int(values.size)
