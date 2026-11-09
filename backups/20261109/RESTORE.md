# Complete local project backup — 2026-11-09

Base source/results commit: `1dadf5d9982f28640070bef4a87ae5c756e4163a`.

The tagged Git tree contains all tracked project source, scripts, documents and result tables. Attachments add every local graph input, raw PageRank output, pinned Kokkos source and non-secret runtime snapshot.

**Scope:** complete local project only. Vanda-only raw files not downloaded to this Mac remain on Vanda. Credentials, private amgr accounting files, build caches, PID/lock files and nested Git history are excluded.

## Restore

Download every asset into one folder and verify the download:

```bash
shasum -a 256 -c SHA256SUMS
```

Clone the project or unpack the source archive into a fresh directory. Then restore:

```bash
python3 restore_backup.py --assets . --destination /path/to/DSA5208_PROJECT_3
```

Identical rank-vector contents are stored once in standard tar hardlink entries. The restore program expands each path into an **independent file**, preserving all original paths and bytes. It checks SHA-256 against `manifest.json`; it does not overwrite existing files. For verification without writing restored data:

```bash
python3 restore_backup.py --assets . --verify-only
```

Files archived: 3774; uncompressed original bytes: 15328102584; losslessly deduplicated compressed payload bytes: 960888737.

Kokkos revision: `175257a51ff29a0059ec48bcd233ee096b2c0438`.
