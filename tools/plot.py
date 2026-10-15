"""Plot the distributions and the per-output statistics of every part of one simulation.

Needs the files locally first: python tools/download.py
Usage (from the project root): python tools/plot.py data/users/0/simulations/dambreak
"""

import sys
from pathlib import Path

import h5py
import matplotlib.pyplot as plt
import numpy as np

sim = Path(sys.argv[1] if len(sys.argv) > 1 else "data/users/0/simulations/dambreak")
outputs = sorted(sim.glob("output_*.hdf5"), key=lambda p: int(p.stem.split("_")[1]))

# Load every dataset of every output once: data[output_name][part][attr]
data = {}
for path in outputs:
    with h5py.File(path, "r") as f:
        data[path.stem] = {part: {attr: f[part][attr][()] for attr in f[part]} for part in f}
names = list(data)
parts = list(data[names[0]])
rows = parts + ["all parts"]  # the API can combine several parts in one request
x = [int(n.split("_")[1]) for n in names]

# Every 1-D quantity that can be derived from a part
channels = {
    "pressure": lambda g: g["pressure"],
    "|velocity|": lambda g: np.linalg.norm(g["velocity"], axis=1),
    "velocity x": lambda g: g["velocity"][:, 0],
    "velocity y": lambda g: g["velocity"][:, 1],
    "velocity z": lambda g: g["velocity"][:, 2],
}

stats = {"min": np.min, "max": np.max, "average": np.mean, "median": np.median,
        "p95": lambda a: np.percentile(a, 95)}


def values(name, row, channel):
    fn = channels[channel]
    if row == "all parts":
        return np.concatenate([fn(data[name][p]) for p in parts])
    return fn(data[name][row])


def grid(title):
    fig, axes = plt.subplots(len(rows), len(channels), squeeze=False,
                            figsize=(4 * len(channels), 3 * len(rows)))
    fig.suptitle(f"{title} - {sim}")
    return fig, axes


# Figure 1: full distribution of every value, one curve per output
fig1, axes = grid("distributions")
for i, row in enumerate(rows):
    for j, channel in enumerate(channels):
        ax = axes[i, j]
        per_output = [values(n, row, channel) for n in names]
        bins = np.histogram_bin_edges(np.concatenate(per_output), bins=100)
        for n, v in zip(names, per_output):
            ax.hist(v, bins=bins, histtype="step", label=n)
        ax.set(title=f"{row} / {channel}", yscale="log")
        if i == len(rows) - 1:
            ax.set_xlabel(channel)
        if j == 0:
            ax.set_ylabel("count")
axes[0, 0].legend(fontsize="small")
fig1.tight_layout()

# Figure 2: every statistic the API offers, over all outputs
fig2, axes = grid("statistics over outputs")
for i, row in enumerate(rows):
    for j, channel in enumerate(channels):
        ax = axes[i, j]
        per_output = [values(n, row, channel) for n in names]
        for s, fn in stats.items():
            ax.plot(x, [fn(v) for v in per_output], marker="o", label=s)
        ax.set(title=f"{row} / {channel}")
        if i == len(rows) - 1:
            ax.set_xlabel("output")
axes[0, 0].legend(fontsize="small")
fig2.tight_layout()


plt.show()