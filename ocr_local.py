"""Optical character recognition for screenshots/photos, fully local via Tesseract."""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile


class OCRError(RuntimeError):
    pass


IMAGE_EXTS = {"png", "jpg", "jpeg", "webp", "tif", "tiff", "bmp", "heic", "heif"}


def recognize_image(filename: str, content: bytes) -> str:
    """Only operate on bytes explicitly uploaded by the local user."""
    extension = Path(filename).suffix.lower().lstrip(".")
    if extension not in IMAGE_EXTS:
        raise OCRError("Nieobsługiwany format zdjęcia.")
    if not content or len(content) > 12 * 1024 * 1024:
        raise OCRError("Zdjęcie powinno mieć od 1 bajta do 12 MB.")
    if not shutil.which("tesseract"):
        raise OCRError("Nie ma Tesseract. Uruchom 5_DOINSTALUJ_FISZKI.command.")
    with tempfile.TemporaryDirectory(prefix="olusia-ocr-") as temp:
        Path(temp).chmod(0o700)
        source = Path(temp) / f"zdjecie.{extension}"
        source.write_bytes(content)
        source.chmod(0o600)
        image = source
        if extension in {"heic", "heif"}:
            if not shutil.which("sips"):
                raise OCRError("Nie można odczytać zdjęcia HEIC — skonwertuj je na JPG.")
            image = Path(temp) / "converted.png"
            try:
                p = subprocess.run(["sips", "-s", "format", "png", str(source), "--out", str(image)],
                                   capture_output=True, text=True, timeout=90)
            except subprocess.TimeoutExpired as exc:
                raise OCRError("Konwersja zdjęcia trwała zbyt długo.") from exc
            if p.returncode != 0:
                raise OCRError("macOS nie może przekonwertować tego zdjęcia HEIC.")
        try:
            language_list = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True, timeout=15)
        except subprocess.TimeoutExpired as exc:
            raise OCRError("Nie udało się sprawdzić języków OCR.") from exc
        available = language_list.stdout + language_list.stderr
        languages = "pol+eng" if "pol" in available and "eng" in available else ("pol" if "pol" in available else "eng")
        try:
            p = subprocess.run(["tesseract", str(image), "stdout", "-l", languages, "--psm", "3"],
                               capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired as exc:
            raise OCRError("Odczyt zdjęcia trwał zbyt długo. Spróbuj wyraźniejszego zdjęcia.") from exc
        if p.returncode != 0:
            raise OCRError(f"Nie udało się odczytać tekstu: {(p.stderr or '')[-250:]}")
        result = p.stdout.strip()
        if not result:
            raise OCRError("Nie rozpoznano tekstu na zdjęciu. Spróbuj wyraźniejszego zdjęcia.")
        return result
