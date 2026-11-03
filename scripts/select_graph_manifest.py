"""Write the one-graph manifest used by one scheduled matrix job."""
import argparse
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("source", type=Path)
parser.add_argument("graph")
parser.add_argument("output", type=Path)
args = parser.parse_args()

rows = [line for line in args.source.read_text(encoding="utf-8").splitlines()
        if line.split() and line.split()[0] == args.graph]
assert len(rows) == 1, f"Expected one graph named {args.graph}, found {len(rows)}"
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(rows[0] + "\n", encoding="utf-8")
