"""SHA-256 integrity check for every file in data/raw/ (line endings normalized; see sha256()).

  python scripts/verify_checksums.py --write   create/refresh checksums.sha256 (after acquiring data)
  python scripts/verify_checksums.py           verify files against checksums.sha256

Verification writes results/quality/checksum_report.txt and exits non-zero on any mismatch,
missing file, or file in data/raw/ that has no recorded checksum.
"""
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
SUMS = ROOT / "checksums.sha256"
REPORT = ROOT / "results" / "quality" / "checksum_report.txt"


def sha256(path):
    """SHA-256 of the file content with Windows line endings (CRLF) read as LF.

    Git on Windows may convert line endings when files are checked out, which would change a
    byte-for-byte hash on that machine only. Normalizing CRLF -> LF makes the hash identical on
    Windows, macOS and Linux while still detecting any change to the data itself.
    """
    data = Path(path).read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def raw_files():
    return sorted(
        p for p in RAW.rglob("*")
        if p.is_file() and not any(part.startswith(".") for part in p.relative_to(RAW).parts)
    )


def rel(path):
    return path.relative_to(ROOT).as_posix()


def write_mode():
    files = raw_files()
    if not files:
        sys.exit("ERROR: no files found in data/raw/ (run the acquire_*.py scripts first)")
    lines = [f"{sha256(p)}  {rel(p)}" for p in files]
    SUMS.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"verify_checksums: wrote {len(lines)} checksums to {SUMS.name}")


def verify_mode():
    if not SUMS.exists():
        sys.exit("ERROR: checksums.sha256 not found (run: python scripts/verify_checksums.py --write)")
    expected = {}
    for line in SUMS.read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, _, name = line.partition("  ")
            expected[name.strip()] = digest.strip()

    report, ok = ["SHA-256 verification of data/raw/"], True
    for name, digest in sorted(expected.items()):
        path = ROOT / name
        if not path.exists():
            report.append(f"MISSING   {name}")
            ok = False
        elif sha256(path) != digest:
            report.append(f"MISMATCH  {name}")
            ok = False
        else:
            report.append(f"OK        {name}")
    for p in raw_files():
        if rel(p) not in expected:
            report.append(f"UNLISTED  {rel(p)} (no recorded checksum)")
            ok = False
    report.append(f"RESULT: {'all files verified' if ok else 'FAILED'}")

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report))
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    write_mode() if "--write" in sys.argv[1:] else verify_mode()
