import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from restore_full_backup import restore


class RestoreBackupTests(unittest.TestCase):
    def test_identical_archive_entries_restore_as_independent_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = root / 'assets'
            assets.mkdir()
            data = b'node,rank\n0,0.5\n1,0.5\n'
            digest = hashlib.sha256(data).hexdigest()
            packed = assets / 'vectors.tar.gz'
            with tarfile.open(packed, 'w:gz') as archive:
                regular = tarfile.TarInfo('results/first/ranks.csv')
                regular.size = len(data)
                archive.addfile(regular, io.BytesIO(data))
                duplicate = tarfile.TarInfo('results/second/ranks.csv')
                duplicate.type = tarfile.LNKTYPE
                duplicate.linkname = regular.name
                archive.addfile(duplicate)
            manifest = {'base_commit': 'test', 'files': [
                {'path': name, 'bytes': len(data), 'sha256': digest}
                for name in (regular.name, duplicate.name)], 'archives': [
                {'name': packed.name, 'parts': [{'name': packed.name,
                 'sha256': hashlib.sha256(packed.read_bytes()).hexdigest()}]}]}
            (assets / 'manifest.json').write_text(json.dumps(manifest))
            destination = root / 'restored'
            result = restore(assets, destination)
            first, second = destination / regular.name, destination / duplicate.name
            self.assertEqual(result['verified_files'], 2)
            self.assertEqual(first.read_bytes(), data)
            self.assertEqual(second.read_bytes(), data)
            self.assertNotEqual(first.stat().st_ino, second.stat().st_ino)
            first.write_bytes(b'changed')
            self.assertEqual(second.read_bytes(), data)


if __name__ == '__main__':
    unittest.main()
