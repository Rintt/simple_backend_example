"""Download the HDF5 blobs from the public Azure container.

The container root URL itself returns 404 (it's not a blob). To see what's inside,
you have to call the List Blobs API: <container>?restype=container&comp=list

Usage (from the project root):
    python tools/download.py                  # the 9 files from INFO.md (prefix "users/") into data/
    python tools/download.py --prefix ""      # everything in the container
    python tools/download.py --list           # only print what's there
"""

import argparse
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

CONTAINER_URL = "https://divepublic.blob.core.windows.net/divers-license"


def list_blobs(prefix: str = "") -> list[tuple[str, int]]:
    """Return (name, size_in_bytes) for every blob under prefix, following pagination."""
    blobs, marker = [], ""
    while True:
        query = {"restype": "container", "comp": "list", "prefix": prefix}
        if marker:
            query["marker"] = marker
        with urllib.request.urlopen(f"{CONTAINER_URL}?{urllib.parse.urlencode(query)}") as resp:
            root = ET.fromstring(resp.read())
        for blob in root.iter("Blob"):
            blobs.append((blob.findtext("Name"), int(blob.findtext("Properties/Content-Length"))))
        marker = root.findtext("NextMarker") or ""
        if not marker:
            return blobs


def download(name: str, out_dir: Path) -> Path:
    target = out_dir / name
    target.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(f"{CONTAINER_URL}/{urllib.parse.quote(name)}", target)
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--prefix", default="users/", help='blob name prefix (default: "users/")')
    parser.add_argument("--out", default="data", help="output directory (default: ./data)")
    parser.add_argument("--list", action="store_true", help="only list blobs, don't download")
    args = parser.parse_args()

    blobs = list_blobs(args.prefix)
    total_mb = sum(size for _, size in blobs) / 1e6
    print(f"{len(blobs)} blobs, {total_mb:.1f} MB under prefix {args.prefix!r}")

    out_dir = Path(args.out)
    for name, size in blobs:
        if args.list:
            print(f"  {name}  ({size / 1e6:.2f} MB)")
            continue
        target = out_dir / name
        if target.exists() and target.stat().st_size == size:
            print(f"  skip   {name} (already downloaded)")
            continue
        download(name, out_dir)
        print(f"  saved  {target}")


if __name__ == "__main__":
    main()
