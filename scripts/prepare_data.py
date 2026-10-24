"""Generate reproducible Uniform and Hub graphs and fetch SNAP web-Google."""
import gzip
from pathlib import Path
import random
import shutil
import urllib.request

ROOT = Path(__file__).resolve().parents[1]

SYNTHETIC_NODES = 100000
SYNTHETIC_EDGES = 1000000
SEED = 5208
DOWNLOAD_URL = "https://snap.stanford.edu/data/web-Google.txt.gz"


def write_graph(folder, name, nodes, edges):
    folder.mkdir(parents=True, exist_ok=True)
    node_path, edge_path = folder / (name + ".nodes"), folder / (name + ".edges")
    with node_path.open("w", encoding="utf-8", newline="\n") as f:
        f.write("# Authoritative node list, including isolated vertices\n")
        f.writelines(f"{v}\n" for v in nodes)
    with edge_path.open("w", encoding="utf-8", newline="\n") as f:
        f.write("# Directed unweighted edges: source destination\n")
        f.writelines(f"{u} {v}\n" for u, v in edges)
    print(edge_path)


def synthetic(n, m, seed, kind):
    rng = random.Random(seed)
    edges = set()
    # In the hub graph, 80% of candidate destinations come from the first 1% of nodes.
    hubs = max(1, n // 100)
    # Fixed edge count; duplicate candidates are resampled.
    while len(edges) < m:
        u = rng.randrange(n)
        v = rng.randrange(hubs) if kind == "hub" and rng.random() < 0.8 else rng.randrange(n)
        edges.add((u, v))
    write_graph(ROOT / "data" / "synthetic", kind, range(n), sorted(edges))


def download(url):
    folder = ROOT / "data" / "raw"
    folder.mkdir(parents=True, exist_ok=True)
    compressed, expanded = folder / "web-Google.txt.gz", folder / "web-Google.txt"
    # Reuse files that were already downloaded or extracted.
    if not compressed.exists():
        print(f"Downloading {url}", flush=True)
        urllib.request.urlretrieve(url, compressed)
    if not expanded.exists():
        with gzip.open(compressed, "rb") as source, expanded.open("wb") as out:
            shutil.copyfileobj(source, out)
    print(expanded)


def main():
    for kind in ("uniform", "hub"):
        synthetic(SYNTHETIC_NODES, SYNTHETIC_EDGES, SEED, kind)
    download(DOWNLOAD_URL)


if __name__ == "__main__":
    main()
