"""Read immutable measurement records directly from the published ZIP archives."""
from functools import lru_cache
from pathlib import Path
import zipfile
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=8)
def archive(path):
    return zipfile.ZipFile(ROOT / path)


def result_file(location):
    filename, member = str(location).split('::', 1)
    return zipfile.Path(archive(filename), at=member)


def verify_archives():
    for item in json.loads((ROOT/'results/manifests/archives.json').read_text()):
        assert hashlib.sha256((ROOT/item['archive']).read_bytes()).hexdigest() == item['sha256'], item['archive']
