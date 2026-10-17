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

SETTINGS_PATH = Path.home() / "Library" / "Application Support" / "Olusia AI Studio" / "updates.json"

VERSION = "2.1.1"
DEFAULT_REPO = "Segulek/Olusia-AI-Studio"
ALLOWED_FILES = {
    "app.py", "processor.py", "cards.py", "flashcards_ui.py", "ocr_local.py",
    "updater.py", "updates_ui.py", "requirements-core.txt", "README.md",
    "START_TUTAJ.html", "1_ZAINSTALUJ.command", "2_URUCHOM.command",
    "3_DIAGNOSTYKA.command", "4_AKTUALIZUJ.command",
    "5_DOINSTALUJ_FISZKI.command", "6_UTWORZ_APLIKACJE.command",
    "0_UAKTUALIZUJ_STARA_WERSJE.command", ".streamlit/config.toml",
    "VERSION",
}


class UpdateError(RuntimeError):
    pass


def _parse_version(value: str) -> tuple[int, ...]:
    if not re.fullmatch(r"\d+(?:\.\d+){0,3}", value):
        raise UpdateError("Nieprawidłowy numer wersji w paczce aktualizacji.")
    return tuple(int(x) for x in value.split("."))


def read_manifest(data: bytes) -> dict:
    if len(data) > 15 * 1024 * 1024:
        raise UpdateError("Paczka aktualizacji jest zbyt duża (>15 MB).")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as pack:
            metadata = json.loads(pack.read("manifest.json"))
            if metadata.get("app_id") != "olusia-ai-studio":
                raise UpdateError("To nie jest aktualizacja Olusia AI Studio.")
            _parse_version(metadata["version"])
            files = metadata["files"]
            if not isinstance(files, dict) or not files or set(files) - ALLOWED_FILES:
                raise UpdateError("Paczka zawiera niedozwolone ścieżki.")
            if len(pack.namelist()) != len(files) + 1:
                raise UpdateError("Paczka zawiera nieoczekiwane pliki.")
            for name, expected in files.items():
                if name.startswith("/") or ".." in Path(name).parts or not re.fullmatch("[a-f0-9]{64}", expected):
                    raise UpdateError("Niepoprawny manifest aktualizacji.")
                target = f"payload/{name}"
                if target not in pack.namelist():
                    raise UpdateError(f"Brak pliku {name} w paczce.")
                member = pack.getinfo(target)
                if member.file_size > 4 * 1024 * 1024 or member.is_dir() or ((member.external_attr >> 16) & 0o170000) == 0o120000:
                    raise UpdateError(f"Niebezpieczny typ lub rozmiar pliku: {name}")
                if hashlib.sha256(pack.read(target)).hexdigest() != expected:
                    raise UpdateError(f"Uszkodzony plik aktualizacji: {name}")
            return metadata
    except (zipfile.BadZipFile, KeyError, ValueError, TypeError, UnicodeDecodeError, AttributeError) as exc:
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
    with tempfile.TemporaryDirectory(prefix="olusia-upgrade-") as temp:
        temp_dir = Path(temp)
        backup = temp_dir / "backup"
        backup.mkdir()
        replaced: list[tuple[Path, Path | None]] = []
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as pack:
                for index, name in enumerate(metadata["files"]):
                    target = folder / name
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
    repo = repo.strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise UpdateError("Podaj repozytorium w formacie właściciel/nazwa, np. przyklad/Olusia-AI-Studio.")
    return repo


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
