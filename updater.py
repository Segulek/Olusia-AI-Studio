"""Conservative, local ZIP updater for Olusia AI Studio.

Updates only a fixed list of source files, never installed environments or user data.
Accept ZIPs with a manifest and exact SHA-256 per payload file. Hashes detect accidental
corruption, NOT authenticity: download only from the trusted project publisher.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import zipfile

DATA_DIR = (Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "Olusia AI Studio"
            if os.name == "nt" else Path.home() / "Library" / "Application Support" / "Olusia AI Studio")
SETTINGS_PATH = DATA_DIR / "updates.json"

VERSION = "2.8.3"
DEFAULT_REPO = "Segulek/Olusia-AI-Studio"
ALLOWED_FILES = {
    "app.py", "processor.py", "cards.py", "flashcards_ui.py", "ocr_local.py",
    "updater.py", "updates_ui.py", "requirements-core.txt", "README.md",
    "START_TUTAJ.html", "1_ZAINSTALUJ.command", "2_URUCHOM.command",
    "3_DIAGNOSTYKA.command", "4_AKTUALIZUJ.command",
    "5_DOINSTALUJ_FISZKI.command", "6_UTWORZ_APLIKACJE.command",
    "0_UAKTUALIZUJ_STARA_WERSJE.command", ".streamlit/config.toml",
    "VERSION", "1_INSTALL_WINDOWS.bat", "2_START_WINDOWS.bat",
    "3_INSTALL_AI_WINDOWS.bat", "4_OPTIONAL_DEMUCS_WINDOWS.bat",
    "WINDOWS_README.txt",
}


class UpdateError(RuntimeError):
    pass


def _parse_version(value: str) -> tuple[int, ...]:
    if not re.fullmatch(r"\d+(?:\.\d+){0,3}", value):
        raise UpdateError("Nieprawidłowy numer wersji w paczce aktualizacji.")
    return tuple(int(x) for x in value.split("."))


def read_manifest(data: bytes) -> dict:
    """Reject oversized, duplicate, nonregular or unlisted ZIP members."""
    if not isinstance(data, bytes) or len(data) > 15 * 1024 * 1024:
        raise UpdateError("Paczka aktualizacji jest nieprawidłowa lub za duża.")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as pack:
            names = pack.namelist()
            if len(names) != len(set(names)) or "manifest.json" not in names:
                raise UpdateError("Powtarzające się lub brakujące pliki w paczce.")
            manifest_info = pack.getinfo("manifest.json")
            if manifest_info.file_size > 128 * 1024:
                raise UpdateError("Manifest aktualizacji jest zbyt duży.")
            metadata = json.loads(pack.read("manifest.json"))
            if not isinstance(metadata, dict) or metadata.get("app_id") != "olusia-ai-studio":
                raise UpdateError("To nie jest aktualizacja Olusia AI Studio.")
            _parse_version(metadata["version"])
            files = metadata["files"]
            if not isinstance(files, dict) or not files or set(files) - ALLOWED_FILES:
                raise UpdateError("Paczka zawiera niedozwolone ścieżki.")
            expected_names = {"manifest.json"} | {f"payload/{name}" for name in files}
            if set(names) != expected_names:
                raise UpdateError("Paczka zawiera nieoczekiwane pliki.")
            total = 0
            for name, expected in files.items():
                if (name.startswith("/") or ".." in Path(name).parts or
                        not re.fullmatch(r"[a-f0-9]{64}", expected)):
                    raise UpdateError("Niepoprawny manifest aktualizacji.")
                entry = pack.getinfo(f"payload/{name}")
                # macOS/UNIX ZIP metadata: permit regular files, reject symlinks.
                mode = (entry.external_attr >> 16) & 0o170000
                if (entry.is_dir() or mode not in (0, 0o100000) or
                        entry.file_size > 4 * 1024 * 1024):
                    raise UpdateError(f"Niedozwolony typ lub rozmiar pliku: {name}")
                total += entry.file_size
                if total > 18 * 1024 * 1024:
                    raise UpdateError("Paczka zawiera zbyt dużo rozpakowanych danych.")
                if hashlib.sha256(pack.read(entry)).hexdigest() != expected:
                    raise UpdateError(f"Uszkodzony plik aktualizacji: {name}")
            return metadata
    except UpdateError:
        raise
    except (zipfile.BadZipFile, KeyError, ValueError, TypeError, UnicodeDecodeError,
            AttributeError, OSError, RuntimeError) as exc:
        raise UpdateError("Nieprawidłowe archiwum aktualizacji.") from exc


def apply_update(data: bytes, folder: Path, current_version: str = VERSION) -> str:
    """Apply validated files with rollback on failure; requires restart of running app."""
    metadata = read_manifest(data)
    new_version = metadata["version"]
    if _parse_version(new_version) <= _parse_version(current_version):
        raise UpdateError(f"Ta aktualizacja (v{new_version}) nie jest nowsza niż zainstalowana v{current_version}.")
    folder = folder.resolve()
    if not (folder / "app.py").is_file() or not (folder / "processor.py").is_file():
        raise UpdateError("Nie znaleziono zainstalowanej aplikacji w tym folderze.")
    # A snapshot of the user databases is mandatory before touching program files.
    try:
        save_data_backup("before-update")
    except BackupError as exc:
        raise UpdateError("Nie udało się zrobić kopii danych przed aktualizacją: " + str(exc)) from exc
    with tempfile.TemporaryDirectory(prefix="olusia-upgrade-") as temp:
        temp_dir = Path(temp)
        backup = temp_dir / "backup"
        backup.mkdir()
        replaced: list[tuple[Path, Path | None]] = []
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as pack:
                for index, name in enumerate(metadata["files"]):
                    target = folder / name
                    # Do not traverse symlinks inside an installation.
                    if target.is_symlink() or any(p.is_symlink() for p in [target.parent, folder]):
                        raise UpdateError("Folder aktualizacji zawiera dowiązanie symboliczne.")
                    if target.parent.resolve() != folder and folder not in target.parent.resolve().parents:
                        raise UpdateError("Niebezpieczna ścieżka aktualizacji.")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    old = backup / str(index) if target.exists() else None
                    if old is not None:
                        shutil.copy2(target, old)
                    # Atomic replacement on same filesystem.
                    candidate = target.with_name(target.name + ".olusia-new")
                    try:
                        candidate.write_bytes(pack.read(f"payload/{name}"))
                        if target.suffix == ".command":
                            candidate.chmod(0o755)
                        os.replace(candidate, target)
                    finally:
                        candidate.unlink(missing_ok=True)
                    replaced.append((target, old))
        except Exception as exc:
            for target, old in reversed(replaced):
                if old is not None:
                    shutil.copy2(old, target)
                else:
                    target.unlink(missing_ok=True)
            raise UpdateError("Instalacja nie powiodła się. Cofnięto podmienione pliki.") from exc
    return new_version


def validate_repo(repo: str) -> str:
    """Updates are executable code: accept only the trusted publisher."""
    if repo.strip().casefold() != DEFAULT_REPO.casefold():
        raise UpdateError("Ze względów bezpieczeństwa aktualizacje pochodzą tylko z oficjalnego repozytorium Olusia AI Studio.")
    return DEFAULT_REPO


def configured_repo(settings: Path = SETTINGS_PATH) -> str:
    if not settings.exists():
        return DEFAULT_REPO
    try:
        config = json.loads(settings.read_text(encoding="utf-8"))
        repo = str(config.get("github_repo", "")).strip()
        return validate_repo(repo) if repo else ""
    except (ValueError, OSError, TypeError) as exc:
        raise UpdateError("Uszkodzony plik konfiguracji aktualizacji.") from exc


def set_repo(repo: str, settings: Path = SETTINGS_PATH) -> None:
    repo = validate_repo(repo)
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(json.dumps({"github_repo": repo}, ensure_ascii=False), encoding="utf-8")


def check_github_update(repo: str) -> dict | None:
    """Look up the latest *public* GitHub Release from the configured repository."""
    repo = validate_repo(repo)
    req = Request(f"https://api.github.com/repos/{repo}/releases/latest",
                  headers={"Accept": "application/vnd.github+json", "User-Agent": "OlusiaAIStudio/2"})
    try:
        with urlopen(req, timeout=8) as response:
            release = json.load(response)
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        raise UpdateError("Nie udało się sprawdzić wersji na GitHub. Sprawdź internet lub repozytorium.") from exc
    tag = str(release.get("tag_name", "")).removeprefix("v")
    _parse_version(tag)
    if _parse_version(tag) <= _parse_version(VERSION):
        return None
    prefix = f"https://github.com/{repo}/releases/download/"
    assets = release.get("assets", [])
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        name = str(asset.get("name", ""))
        url = str(asset.get("browser_download_url", ""))
        if name == f"Olusia_AI_Studio_UPDATE_v{tag}.zip" and url.startswith(prefix) and url.endswith(".zip"):
            return {
                "version": tag,
                "url": url,
                "sha256": str(asset.get("digest", "")),
                "notes": str(release.get("body", ""))[:1200],
            }
    raise UpdateError(f"Wydanie v{tag} istnieje, ale nie ma właściwego pliku aktualizacji ZIP.")


def download_verified_update(release: dict) -> bytes:
    """Download explicitly requested release from GitHub, with size and digest checks."""
    url = str(release.get("url", ""))
    if not url.startswith("https://github.com/") or "/releases/download/" not in url or not url.endswith(".zip"):
        raise UpdateError("Nieprawidłowy adres paczki aktualizacyjnej.")
    req = Request(url, headers={"User-Agent": "OlusiaAIStudio/2"})
    try:
        with urlopen(req, timeout=45) as response:
            size = 0
            blocks = []
            while True:
                chunk = response.read(65536)
                if not chunk:
                    break
                size += len(chunk)
                if size > 15 * 1024 * 1024:
                    raise UpdateError("Paczka aktualizacji przekroczyła limit 15 MB.")
                blocks.append(chunk)
        contents = b"".join(blocks)
        digest = str(release.get("sha256", ""))
        if not digest:
            raise UpdateError("Wydanie GitHub nie ma sumy kontrolnej SHA-256. Nie instaluję niezweryfikowanego pliku.")
        if digest:
            if not re.fullmatch("sha256:[a-f0-9]{64}", digest):
                raise UpdateError("GitHub zwrócił nierozpoznawalny format sumy kontrolnej.")
            if hashlib.sha256(contents).hexdigest() != digest.removeprefix("sha256:"):
                raise UpdateError("Suma kontrolna paczki nie zgadza się z sumą z GitHuba.")
        manifest = read_manifest(contents)
        if manifest["version"] != release["version"]:
            raise UpdateError("Numer wersji w ZIP nie zgadza się z wydaniem GitHub.")
        return contents
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise UpdateError("Nie udało się pobrać aktualizacji. Sprawdź internet.") from exc


# Private, offline backups. Keep these helpers in updater.py so old installed
# versions can receive them through the existing allowlisted ZIP updater.
from datetime import datetime, timezone, timedelta
import sqlite3
from urllib.parse import quote

DATABASE_NAMES = ("fiszki.sqlite3", "nagrania.sqlite3")
MAX_DATABASE_BYTES = 64 * 1024 * 1024
MAX_BACKUP_BYTES = 96 * 1024 * 1024
BACKUP_FORMAT = "olusia-data-backup-v1"
_ALLOWED_TABLES = {
    "fiszki.sqlite3": {"decks", "cards", "learning_subjects", "learning_schedule",
                       "learning_reviews", "sqlite_sequence"},
    "nagrania.sqlite3": {"recording_bookmarks", "sqlite_sequence"},
}


class BackupError(RuntimeError):
    """A recoverable error shown to the user without exposing file contents."""


def _private_folder(folder: Path) -> None:
    if folder.is_symlink() or folder.parent.is_symlink():
        raise BackupError("Folder danych ma niebezpieczne dowiązanie symboliczne.")
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    folder.chmod(0o700)


def _check_file(path: Path) -> None:
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise BackupError("Nieobsługiwany lub niebezpieczny plik danych.")
    if path.exists() and path.stat().st_size > MAX_DATABASE_BYTES:
        raise BackupError("Baza danych jest zbyt duża do bezpiecznego archiwum.")


def _open_database(path: Path, readonly: bool = False) -> sqlite3.Connection:
    if readonly:
        encoded = quote(path.resolve().as_posix(), safe="/:")
        return sqlite3.connect(f"file:{encoded}?mode=ro", uri=True, timeout=8)
    return sqlite3.connect(str(path), timeout=8)


def _check_database(path: Path, name: str) -> None:
    """Validate contents as small, ordinary databases used by this application."""
    if not path.is_file() or path.stat().st_size > MAX_DATABASE_BYTES:
        raise BackupError("Baza danych w kopii ma nieprawidłowy rozmiar.")
    try:
        con = _open_database(path, readonly=True)
        try:
            con.execute("PRAGMA trusted_schema=OFF")
            if con.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise BackupError("Kopia zawiera uszkodzoną bazę danych.")
            objects = con.execute("SELECT type, name, sql FROM sqlite_master").fetchall()
            if any(kind not in ("table", "index") for kind, _, _ in objects):
                raise BackupError("Baza ma niedozwolone elementy schematu.")
            tables = {name_in_db for kind, name_in_db, _ in objects if kind == "table"}
            mandatory = {"decks", "cards"} if name == "fiszki.sqlite3" else {"recording_bookmarks"}
            if not mandatory.issubset(tables) or tables - _ALLOWED_TABLES[name]:
                raise BackupError("Nieprawidłowa struktura bazy danych.")
            if any((sql or "").upper().lstrip().startswith("CREATE VIRTUAL TABLE")
                   for _, _, sql in objects):
                raise BackupError("Baza zawiera niedozwolone wirtualne tabele.")
            if con.execute("PRAGMA foreign_key_check").fetchone() is not None:
                raise BackupError("Niespójne powiązania w bazie fiszek.")
        finally:
            con.close()
    except BackupError:
        raise
    except sqlite3.Error as exc:
        raise BackupError("Nie można otworzyć lub zweryfikować bazy danych.") from exc


def _snapshot_database(source: Path, target: Path, name: str) -> None:
    """SQLite online backup safely includes data present in any WAL journal."""
    source_con = _open_database(source, readonly=True)
    dest_con = _open_database(target)
    try:
        source_con.backup(dest_con, pages=128, sleep=0.05)
    finally:
        dest_con.close()
        source_con.close()
    target.chmod(0o600)
    _check_database(target, name)
    # Repack the *snapshot*, never the original database. VACUUM removes
    # unused SQLite pages, making the ZIP smaller after deleting cards.
    try:
        snapshot = sqlite3.connect(target, timeout=8)
        try:
            snapshot.execute("VACUUM")
        finally:
            snapshot.close()
    except sqlite3.Error as exc:
        raise BackupError("Nie można skompaktować kopii danych.") from exc
    _check_database(target, name)


def _available_databases(folder: Path) -> list[str]:
    found = []
    for name in DATABASE_NAMES:
        source = folder / name
        _check_file(source)
        if source.exists():
            found.append(name)
    return found


def create_data_backup(data_dir: Path | None = None) -> bytes:
    """Create a consistent backup. No networks, models, passwords or audio files."""
    folder = Path(data_dir) if data_dir is not None else DATA_DIR
    names = _available_databases(folder)
    if not names:
        raise BackupError("Nie ma jeszcze zapisanych fiszek ani zakładek do zabezpieczenia.")
    with tempfile.TemporaryDirectory(prefix="olusia-snapshot-") as temporary:
        output = io.BytesIO()
        recorded = {}
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name in names:
                snapshot = Path(temporary) / name
                try:
                    _snapshot_database(folder / name, snapshot, name)
                except (sqlite3.Error, OSError) as exc:
                    raise BackupError("Nie można utworzyć spójnej kopii bazy danych.") from exc
                size = snapshot.stat().st_size
                payload = snapshot.read_bytes()
                recorded[name] = {"sha256": hashlib.sha256(payload).hexdigest(), "size": size}
                archive.writestr("databases/" + name, payload)
            manifest = {
                "format": BACKUP_FORMAT,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "databases": recorded,
            }
            archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False))
        if output.tell() > MAX_BACKUP_BYTES:
            raise BackupError("Kopia przekracza limit 96 MB.")
        return output.getvalue()


def validate_data_backup(data: bytes) -> dict[str, bytes]:
    """Validate the complete archive before any restoration takes place."""
    if not isinstance(data, bytes) or not 0 < len(data) <= MAX_BACKUP_BYTES:
        raise BackupError("Kopia jest pusta albo ma ponad 96 MB.")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)) or "manifest.json" not in names:
                raise BackupError("Kopia ma powtarzające się lub brakujące pliki.")
            if archive.getinfo("manifest.json").file_size > 32_768:
                raise BackupError("Manifest kopii jest zbyt duży.")
            manifest = json.loads(archive.read("manifest.json"))
            if not isinstance(manifest, dict) or manifest.get("format") != BACKUP_FORMAT:
                raise BackupError("To nie jest kopia danych Olusia AI Studio.")
            declared = manifest.get("databases")
            if (not isinstance(declared, dict) or not declared or
                    set(declared) - set(DATABASE_NAMES)):
                raise BackupError("Kopia zawiera niedozwolone bazy.")
            expected = {"manifest.json"} | {"databases/" + n for n in declared}
            if set(names) != expected:
                raise BackupError("Kopia zawiera nieoczekiwane pliki.")
            total, result = 0, {}
            for name, record in declared.items():
                if (not isinstance(record, dict) or
                        not isinstance(record.get("size"), int) or
                        not isinstance(record.get("sha256"), str)):
                    raise BackupError("Nieprawidłowy manifest kopii.")
                info = archive.getinfo("databases/" + name)
                mode = (info.external_attr >> 16) & 0o170000
                if (info.is_dir() or mode not in (0, 0o100000) or
                        info.file_size <= 0 or info.file_size > MAX_DATABASE_BYTES or
                        info.file_size != record["size"]):
                    raise BackupError("Niedozwolony typ lub rozmiar bazy.")
                total += info.file_size
                if total > 2 * MAX_DATABASE_BYTES:
                    raise BackupError("Zbyt dużo rozpakowanych danych.")
                raw = archive.read(info)
                if hashlib.sha256(raw).hexdigest() != record["sha256"]:
                    raise BackupError("Kopia nie przeszła kontroli integralności.")
                result[name] = raw
        with tempfile.TemporaryDirectory(prefix="olusia-verify-") as tmp:
            for name, contents in result.items():
                path = Path(tmp) / name
                path.write_bytes(contents)
                _check_database(path, name)
        return result
    except BackupError:
        raise
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile, RuntimeError) as exc:
        raise BackupError("Nie udało się odczytać lub sprawdzić kopii zapasowej.") from exc


def _backup_directory(data_dir: Path) -> Path:
    target = data_dir / "backups"
    _private_folder(data_dir)
    _private_folder(target)
    return target


def _prune_automatic_backups(backups: Path, now: datetime) -> None:
    """Keep the latest 7 UTC calendar dates, at most 7 archives per kind.

    Never touch manually created copies or names that do not exactly match
    our naming convention. Pruning happens only after a successful backup.
    """
    cutoff = now.astimezone(timezone.utc).date() - timedelta(days=6)
    for kind in ("daily", "before-update", "before-restore"):
        copies: list[tuple[datetime, Path]] = []
        for path in backups.glob(f"olusia-{kind}-*.zip"):
            if path.is_symlink() or not path.is_file():
                continue
            match = re.fullmatch(
                rf"olusia-{kind}-(\d{{4}}-\d{{2}}-\d{{2}})"
                + (r"" if kind == "daily" else r"_\d{2}-\d{2}-\d{2}-\d{6}")
                + r"\.zip",
                path.name,
            )
            if not match:
                continue
            try:
                day = datetime.strptime(match.group(1), "%Y-%m-%d")
            except ValueError:
                continue
            copies.append((day, path))
        copies.sort(key=lambda pair: pair[1].name, reverse=True)
        retained = 0
        for day, path in copies:
            if day.date() >= cutoff and retained < 7:
                retained += 1
            else:
                path.unlink(missing_ok=True)


def save_data_backup(kind: str = "manual", data_dir: Path | None = None) -> Path | None:
    """Keep all manual backups; automated backups only from the last 7 UTC dates."""
    if kind not in {"manual", "daily", "before-update", "before-restore"}:
        raise BackupError("Nieprawidłowy typ kopii.")
    root = Path(data_dir) if data_dir is not None else DATA_DIR
    if not _available_databases(root):
        return None
    backups = _backup_directory(root)
    date = datetime.now(timezone.utc)
    stamp = date.strftime("%Y-%m-%d") if kind == "daily" else date.strftime("%Y-%m-%d_%H-%M-%S-%f")
    destination = backups / f"olusia-{kind}-{stamp}.zip"
    if kind == "daily" and destination.exists():
        _prune_automatic_backups(backups, date)
        return destination
    payload = create_data_backup(root)
    try:
        with destination.open("xb") as f:
            destination.chmod(0o600)
            f.write(payload)
        # Confirm on disk; avoid reporting a success for a damaged file.
        validate_data_backup(destination.read_bytes())
    except (BackupError, OSError) as exc:
        destination.unlink(missing_ok=True)
        raise BackupError("Nie udało się bezpiecznie zapisać kopii na dysku.") from exc
    _prune_automatic_backups(backups, date)
    return destination


def ensure_daily_backup(data_dir: Path | None = None) -> Path | None:
    """Runs during local app startup, at most once per UTC day."""
    root = Path(data_dir) if data_dir is not None else DATA_DIR
    return save_data_backup("daily", root)


def list_data_backups(data_dir: Path | None = None) -> list[dict]:
    root = Path(data_dir) if data_dir is not None else DATA_DIR
    backup_dir = root / "backups"
    if backup_dir.is_symlink() or not backup_dir.is_dir():
        return []
    found = []
    for path in sorted(backup_dir.glob("olusia-*.zip"), reverse=True)[:60]:
        if path.is_file() and not path.is_symlink():
            found.append({"name": path.name, "path": path, "bytes": path.stat().st_size})
    return found


def restore_data_backup(data: bytes, data_dir: Path | None = None) -> dict:
    """Restore safely from a validated backup, with a local pre-restore copy."""
    validated = validate_data_backup(data)
    root = Path(data_dir) if data_dir is not None else DATA_DIR
    _private_folder(root)
    for name in validated:
        _check_file(root / name)
    # Abort if the safety backup cannot be persisted.
    safety = save_data_backup("before-restore", root)
    with tempfile.TemporaryDirectory(prefix="olusia-restore-") as temp:
        stage = Path(temp)
        old = {}
        for name in validated:
            if (root / name).exists():
                old[name] = stage / ("original-" + name)
                _snapshot_database(root / name, old[name], name)
            candidate = stage / name
            candidate.write_bytes(validated[name])
            candidate.chmod(0o600)
            _check_database(candidate, name)
        replaced = []
        try:
            for name in validated:
                target = root / name
                # Track the currently-changing database too, in case SQLite
                # raises after writing some pages.
                replaced.append(name)
                src = _open_database(stage / name, readonly=True)
                try:
                    dest = _open_database(target)
                    try:
                        src.backup(dest, pages=128, sleep=0.05)
                    finally:
                        dest.close()
                finally:
                    src.close()
                target.chmod(0o600)
                _check_database(target, name)
        except (OSError, sqlite3.Error, BackupError) as exc:
            rollback_failed = False
            for name in reversed(replaced):
                try:
                    if name in old:
                        src = _open_database(old[name], readonly=True)
                        try:
                            dest = _open_database(root / name)
                            try:
                                src.backup(dest)
                            finally:
                                dest.close()
                        finally:
                            src.close()
                    else:
                        (root / name).unlink(missing_ok=True)
                except (sqlite3.Error, OSError):
                    rollback_failed = True
            if rollback_failed:
                raise BackupError("Przywracanie przerwane. Sprawdź kopię ratunkową; automatyczne cofnięcie było niepełne.") from exc
            raise BackupError("Przywracanie przerwane. Cofnięto zmiany; sprawdź kopię ratunkową.") from exc
    return {"restored": sorted(validated), "safety_backup": str(safety) if safety else None}
