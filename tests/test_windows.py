"""Windows package and cross-platform data checks (executed on Windows CI)."""
from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import zipfile

from cards import APP_DIR, Flashcard, save_deck, list_decks
from processor import BOOKMARK_DB, save_bookmark
from updater import DATA_DIR, SETTINGS_PATH, VERSION, ALLOWED_FILES
from dev.make_windows import ROOT, FILES, create


def test_user_data_path_platform_specific():
    if os.name == "nt":
        target = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "Olusia AI Studio"
    else:
        target = Path.home() / "Library" / "Application Support" / "Olusia AI Studio"
    assert APP_DIR == DATA_DIR == target
    assert BOOKMARK_DB == target / "nagrania.sqlite3"
    assert SETTINGS_PATH == target / "updates.json"


def test_windows_executables_present_in_update_allowlist():
    for name in ("1_INSTALL_WINDOWS.bat", "2_START_WINDOWS.bat",
                 "3_INSTALL_AI_WINDOWS.bat", "4_OPTIONAL_DEMUCS_WINDOWS.bat",
                 "WINDOWS_README.txt"):
        assert name in FILES
        assert name in ALLOWED_FILES
    assert VERSION == (ROOT / "VERSION").read_text().strip()


def test_windows_portable_zip_contains_source_without_models_and_has_crlf():
    with tempfile.TemporaryDirectory() as temp:
        dest = Path(temp) / f"Olusia_AI_Studio_Windows_v{VERSION}.zip"
        create(dest)
        with zipfile.ZipFile(dest) as packed:
            assert set(packed.namelist()) == set(FILES)
            assert not any(".venv" in path or ".ollama" in path or path.endswith(".exe")
                           for path in packed.namelist())
            for name in FILES:
                contents = packed.read(name)
                assert contents
                if name.endswith(".bat"):
                    assert b"\r\n" in contents
                    assert b"\n" not in contents.replace(b"\r\n", b"")


def test_windows_userdata_sqlite_still_works():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        db = root / "data" / "fiszki.sqlite3"
        save_deck("Anatomy", [Flashcard("What is a rib?", "Part of the thoracic cage.")], db)
        assert list_decks(db)[0]["total"] == 1
        bookmark = root / "data" / "nagrania.sqlite3"
        assert save_bookmark("a"*64, "Lecture", 8.0, "Sternum", db_path=bookmark) == 1


def test_windows_scripts_require_local_access_not_cloud():
    launcher = (ROOT / "2_START_WINDOWS.bat").read_text(encoding="utf-8")
    assert "--server.address=127.0.0.1" in launcher
    assert "--server.port=8501" in launcher
    ai = (ROOT / "3_INSTALL_AI_WINDOWS.bat").read_text(encoding="utf-8")
    assert "ollama pull qwen3-vl:4b-instruct" in ai
    assert "qwen2.5:" not in ai
    installer = (ROOT / "1_INSTALL_WINDOWS.bat").read_text(encoding="utf-8")
    assert "3_INSTALL_AI_WINDOWS.bat" in installer



def test_universal_update_keeps_older_macos_versions_compatible():
    from dev.make_update import create as make_universal_update
    windows_only = {"1_INSTALL_WINDOWS.bat", "2_START_WINDOWS.bat",
                    "3_INSTALL_AI_WINDOWS.bat", "4_OPTIONAL_DEMUCS_WINDOWS.bat",
                    "WINDOWS_README.txt"}
    with tempfile.TemporaryDirectory() as temp:
        zip_file = Path(temp) / "universal.zip"
        make_universal_update(zip_file)
        with zipfile.ZipFile(zip_file) as archive:
            import json
            manifest = json.loads(archive.read("manifest.json"))
            assert not windows_only.intersection(manifest["files"])
            assert {"app.py","updater.py","cards.py","VERSION"}.issubset(manifest["files"])
