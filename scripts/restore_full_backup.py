"""Verify and restore the local project data attached to a GitHub backup release."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tarfile


class PartsReader:
    def __init__(self, paths):
        self.paths = iter(paths)
        self.current = None

    def read(self, size):
        blocks = []
        remaining = size
        while remaining:
            if self.current is None:
                try:
                    self.current = next(self.paths).open('rb')
                except StopIteration:
                    break
            block = self.current.read(remaining)
            if block:
                blocks.append(block)
                remaining -= len(block)
            else:
                self.current.close()
                self.current = None
        return b''.join(blocks)

    def close(self):
        if self.current:
            self.current.close()


def restore(assets, destination, verify_only=False):
    manifest = json.loads((assets / 'manifest.json').read_text())
    expected = {entry['path']: entry for entry in manifest['files']}
    verified = {}
    for archive in manifest['archives']:
        paths = [assets / part['name'] for part in archive['parts']]
        for path, part in zip(paths, archive['parts']):
            digest = hashlib.sha256()
            with path.open('rb') as source:
                for block in iter(lambda: source.read(8 * 1024 * 1024), b''):
                    digest.update(block)
            assert digest.hexdigest() == part['sha256'], path.name
        reader = PartsReader(paths)
        try:
            with tarfile.open(fileobj=reader, mode='r|gz') as packed:
                for member in packed:
                    relative = Path(member.name)
                    assert not relative.is_absolute() and '..' not in relative.parts
                    item = expected[member.name]
                    target = destination / relative
                    if not verify_only:
                        target.parent.mkdir(parents=True, exist_ok=True)
                    if member.isfile():
                        digest = hashlib.sha256()
                        size = 0
                        output = None if verify_only else target.open('xb')
                        try:
                            with packed.extractfile(member) as source:
                                for block in iter(lambda: source.read(8 * 1024 * 1024), b''):
                                    digest.update(block)
                                    size += len(block)
                                    if output:
                                        output.write(block)
                        finally:
                            if output:
                                output.close()
                        assert size == item['bytes'] and digest.hexdigest() == item['sha256'], member.name
                    elif member.islnk():
                        assert member.linkname in verified
                        assert verified[member.linkname] == item['sha256'], member.name
                        if not verify_only:
                            # Independent copies preserve the original output-file semantics.
                            with (destination / member.linkname).open('rb') as source, target.open('xb') as output:
                                shutil.copyfileobj(source, output, length=8 * 1024 * 1024)
                    else:
                        raise ValueError('Unexpected archive entry: ' + member.name)
                    verified[member.name] = item['sha256']
                    if not verify_only:
                        os.chmod(target, member.mode)
                        os.utime(target, (member.mtime, member.mtime))
        finally:
            reader.close()
        print(('Verified ' if verify_only else 'Restored ') + archive['name'], flush=True)
    assert set(verified) == set(expected)
    return {'verified_files': len(verified), 'source_files': len(expected),
            'all_file_checksums_match': True, 'base_commit': manifest['base_commit'],
            'verified_archives': [a['name'] for a in manifest['archives']]}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets', type=Path, default=Path('.'))
    parser.add_argument('--destination', type=Path, default=Path('.'))
    parser.add_argument('--verify-only', action='store_true')
    parser.add_argument('--verification-json', type=Path)
    args = parser.parse_args()
    result = restore(args.assets, args.destination, args.verify_only)
    if args.verification_json:
        args.verification_json.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)
