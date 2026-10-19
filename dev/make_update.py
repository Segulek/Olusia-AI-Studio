"""Maintainer script: produce offline patch ZIP from a new version of Olusia AI Studio.

Example: python dev/make_update.py /path/to/output.zip
Change VERSION in updater.py and VERSION file before releasing.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from updater import ALLOWED_FILES, VERSION


def create(target: Path):
    declared_version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if declared_version != VERSION:
        raise ValueError(f"Wersja z pliku VERSION ({declared_version}) różni się od updater.py ({VERSION})")
    # Preserve compatibility with macOS 2.7 and older updaters: their strict
    # allowlist rejects *new* Windows .bat files. Windows users initially get
    # these files from the separate full Windows distribution archive.
    windows_only = {"1_INSTALL_WINDOWS.bat", "2_START_WINDOWS.bat",
                    "3_INSTALL_AI_WINDOWS.bat", "4_OPTIONAL_DEMUCS_WINDOWS.bat",
                    "WINDOWS_README.txt"}
    files = {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
             for name in sorted(ALLOWED_FILES)
             if name != "0_UAKTUALIZUJ_STARA_WERSJE.command"
             and name not in windows_only and (ROOT/name).is_file()}
    manifest = {"app_id": "olusia-ai-studio", "version": VERSION, "files": files}
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as out:
        out.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        for name in files:
            out.write(ROOT/name, f"payload/{name}")
    return target


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python dev/make_update.py /path/to/Olusia_AI_Studio_UPDATE_vX.Y.Z.zip")
    print(create(Path(sys.argv[1]).resolve()))
