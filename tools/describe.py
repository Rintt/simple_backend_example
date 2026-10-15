"""Print everything inside an HDF5 output file: groups, datasets, attributes and statistics.

Usage (from the project root, after python tools/download.py):
    python tools/describe.py data/users/0/simulations/dambreak/output_1.hdf5
    python tools/describe.py <file> --values           # also print every value (long!)
    python tools/describe.py <file> --csv out          # export each dataset as CSV
"""

import argparse
from pathlib import Path

import h5py
import numpy as np


def describe(name: str, obj, show_values: bool, csv_dir: Path | None) -> None:
    path = "/" + name if name else "/"
    attrs = dict(obj.attrs)
    if isinstance(obj, h5py.Group):
        print(f"GROUP   {path}  members={list(obj.keys())}  attrs={attrs}")
        return

    data = obj[()]
    print(f"DATASET {path}")
    print(f"    shape={data.shape} dtype={data.dtype} chunks={obj.chunks} compression={obj.compression} attrs={attrs}")
    print(f"    nan={int(np.isnan(data).sum())} inf={int(np.isinf(data).sum())} unique={np.unique(data).size}")

    values = np.linalg.norm(data, axis=1) if data.ndim == 2 else data
    label = "magnitude" if data.ndim == 2 else "values"
    print(f"    {label}: min={values.min():.6g} max={values.max():.6g} mean={values.mean():.6g} "
          f"median={np.median(values):.6g} p95={np.percentile(values, 95):.6g}")
    if data.ndim == 2:
        for i, axis in enumerate("xyz"[: data.shape[1]]):
            col = data[:, i]
            print(f"    {axis}: min={col.min():.6g} max={col.max():.6g} mean={col.mean():.6g}")

    if show_values:
        with np.printoptions(threshold=np.inf, linewidth=120):
            print(data)
    if csv_dir:
        csv_dir.mkdir(parents=True, exist_ok=True)
        out = csv_dir / (name.replace("/", "_") + ".csv")
        header = "x,y,z" if data.ndim == 2 else name.split("/")[-1]
        np.savetxt(out, data, delimiter=",", header=header, comments="")
        print(f"    -> wrote {out}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("file", type=Path)
    parser.add_argument("--values", action="store_true", help="print every value of every dataset")
    parser.add_argument("--csv", type=Path, help="directory to export each dataset as CSV")
    args = parser.parse_args()

    print(f"FILE    {args.file}  ({args.file.stat().st_size:,} bytes)")
    with h5py.File(args.file, "r") as f:
        print(f"ROOT    attrs={dict(f.attrs)}  members={list(f.keys())}")
        f.visititems(lambda name, obj: describe(name, obj, args.values, args.csv))


if __name__ == "__main__":
    main()
