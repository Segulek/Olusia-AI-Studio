"""Build the small Windows x64 *source* ZIP, not a signed/executable .exe.

Usage: python dev/make_windows.py Olusia_AI_Studio_Windows_v2.8.0.zip
The installer only installs core libraries; Demucs and Qwen are opt-in.
"""
from __future__ import annotations

from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from updater import VERSION

FILES = (
    "VERSION", "WINDOWS_README.txt",
    "1_INSTALL_WINDOWS.bat", "2_START_WINDOWS.bat",
    "3_INSTALL_AI_WINDOWS.bat", "4_OPTIONAL_DEMUCS_WINDOWS.bat",
    "app.py", "cards.py", "flashcards_ui.py", "processor.py",
    "ocr_local.py", "updater.py", "updates_ui.py", "requirements-core.txt",
    ".streamlit/config.toml",
)


def create(target: Path) -> Path:
    if (ROOT / "VERSION").read_text(encoding="utf-8").strip() != VERSION:
        raise ValueError("VERSION and updater.py disagree")
    if not VERSION or len(FILES) != len(set(FILES)):
        raise ValueError("Invalid release manifest")
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as output:
        for name in FILES:
            source = ROOT / name
            if not source.is_file() or source.is_symlink():
                raise FileNotFoundError(name)
            raw = source.read_bytes()
            # Windows cmd.exe prefers CRLF for .bat files.
            if name.endswith(".bat"):
                raw = raw.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
            output.writestr(name, raw)
    return target


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python dev/make_windows.py output.zip")
    print(create(Path(sys.argv[1]).resolve()))
