"""Unit tests for the calculation itself. No network or database needed."""

from typing import get_args

import numpy as np
import pytest

from backend.calculations import STATS, compute_statistic, per_particle_values
from backend.models import Stat


def test_vectors_become_magnitudes():
    velocity = np.array([[3.0, 4.0, 0.0], [0.0, 0.0, 2.0]])
    assert per_particle_values(velocity).tolist() == [5.0, 2.0]


def test_scalars_stay_unchanged():
    pressure = np.array([-1.0, 2.0])
    assert per_particle_values(pressure).tolist() == [-1.0, 2.0]


@pytest.mark.parametrize("stat, expected", [
    ("min", 1.0), ("max", 4.0), ("average", 2.5), ("median", 2.5), ("p95", 3.85),
])
def test_values_are_pooled_across_arrays(stat, expected):
    value, count = compute_statistic([np.array([1.0, 2.0]), np.array([3.0, 4.0])], stat)
    assert count == 4
    assert value == pytest.approx(expected)


def test_average_weights_every_particle_equally():
    # 3 particles at 0 and 1 particle at 10: the pooled mean is 2.5, not the mean of the two means (5.0)
    value, _ = compute_statistic([np.zeros(3), np.array([10.0])], "average")
    assert value == 2.5


def test_every_offered_stat_has_a_function():
    assert set(get_args(Stat)) == set(STATS)
