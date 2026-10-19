"""Offline media utilities used by Olusia AI Studio.

Only a local loopback Streamlit UI invokes these helpers.
"""
from __future__ import annotations

import json
import math
import os
import sqlite3
from pathlib import Path
import subprocess
from typing import Iterable


class ProcessingError(RuntimeError):
    """Readable description of a failed local media-processing step."""


def _run(cmd: list[str], *, timeout: int = 900) -> subprocess.CompletedProcess[str]:
    try:
        p = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        raise ProcessingError(f"Nie znaleziono programu: {cmd[0]}.") from exc
    except subprocess.TimeoutExpired as exc:
        raise ProcessingError("Przekroczono czas przetwarzania nagrania.") from exc
    if p.returncode != 0:
        diagnostics = (p.stderr or p.stdout or "Nieznany błąd")[-2200:].strip()
        raise ProcessingError(f"Nie udało się przetworzyć pliku.\n\n{diagnostics}")
    return p


def media_duration(path: Path) -> float | None:
    """Best-effort duration, in seconds."""
    try:
        result = _run([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "json", str(path)
        ], timeout=30)
        raw = json.loads(result.stdout)["format"]["duration"]
        duration = float(raw)
        return duration if math.isfinite(duration) and duration >= 0 else None
    except (ProcessingError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None


def extract_mp3(source: Path, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    _run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(source), "-map", "0:a:0", "-vn",
        "-codec:a", "libmp3lame", "-b:a", "192k", str(destination)
    ])
    if not destination.is_file() or destination.stat().st_size == 0:
        raise ProcessingError("Nie udało się utworzyć pliku MP3.")
    return destination


def make_wav(source: Path, destination: Path, *, sample_rate: int = 16000, channels: int = 1) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    _run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(source), "-map", "0:a:0", "-vn",
        "-ar", str(sample_rate), "-ac", str(channels),
        "-c:a", "pcm_s16le", str(destination)
    ])
    if not destination.is_file() or destination.stat().st_size == 0:
        raise ProcessingError("Nie udało się przygotować ścieżki audio.")
    return destination


def isolate_vocals(source: Path, job_folder: Path, stem_python: Path) -> Path:
    """Use a *separate virtualenv* for older Demucs and torchaudio dependencies."""
    if not stem_python.is_file():
        raise ProcessingError("Nie zainstalowano modułu izolacji. Doinstaluj moduł izolacji głosu (macOS: 1_ZAINSTALUJ.command, Windows: 4_OPTIONAL_DEMUCS_WINDOWS.bat).")
    prepared = make_wav(source, job_folder / "do_separacji.wav", sample_rate=44100, channels=2)
    stems_folder = job_folder / "separacja"
    _run([
        str(stem_python), "-m", "demucs", "--device", "cpu",
        "--two-stems", "vocals", "-n", "htdemucs",
        "--out", str(stems_folder), str(prepared)
    ], timeout=7200)
    vocals_wav = stems_folder / "htdemucs" / prepared.stem / "vocals.wav"
    if not vocals_wav.is_file():
        raise ProcessingError("Model zakończył pracę, lecz nie utworzył ścieżki z głosem.")
    return vocals_wav


def timestamp_srt(seconds: float) -> str:
    total_ms = max(0, round(seconds * 1000))
    hours, rest = divmod(total_ms, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    secs, ms = divmod(rest, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{ms:03}"


def timestamp_readable(seconds: float) -> str:
    return timestamp_srt(seconds).replace(",", ".")


def transcript_files(segments: Iterable[tuple[float, float, str]]) -> tuple[str, str, str]:
    """Plain text, timestamped text and SRT for Whisper segments."""
    plain: list[str] = []
    with_times: list[str] = []
    subtitles: list[str] = []
    for start, end, raw_text in segments:
        text = " ".join(raw_text.split()).strip()
        if not text:
            continue
        a = max(0.0, float(start))
        b = max(a + 0.001, float(end))
        plain.append(text)
        with_times.append(f"[{timestamp_readable(a)}] {text}")
        subtitles.append(f"{len(subtitles) + 1}\n{timestamp_srt(a)} --> {timestamp_srt(b)}\n{text}")
    return "\n".join(plain), "\n".join(with_times), "\n\n".join(subtitles) + ("\n" if subtitles else "")


# Local recording bookmarks: only time markers and notes, never audio files.
BOOKMARK_DB = (Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "Olusia AI Studio"
               if os.name == "nt" else Path.home() / "Library" / "Application Support" / "Olusia AI Studio") / "nagrania.sqlite3"


def filter_segments(segments, search: str, maximum: int = 30) -> list[tuple[float, float, str]]:
    """Find transcript chunks without network access; keep timestamps for seeking."""
    phrase = search.strip().casefold()
    return [(float(a), float(b), str(t)) for a, b, t in segments
            if not phrase or phrase in str(t).casefold()][:max(1, min(100, maximum))]


def clip_audio(source: Path, destination: Path, start: float, end: float) -> Path:
    """Create a short playable MP3 preview, with strictly bounded time range."""
    start, end = float(start), float(end)
    if not math.isfinite(start) or not math.isfinite(end) or start < 0 or end <= start or end - start > 300:
        raise ProcessingError("Wybierz poprawny fragment (maksymalnie 5 minut).")
    duration = media_duration(source)
    if duration is None or start >= duration or end > duration + 0.25:
        raise ProcessingError("Fragment wykracza poza długość nagrania.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
          "-ss", str(start), "-i", str(source), "-t", str(end-start),
          "-map", "0:a:0", "-vn", "-codec:a", "libmp3lame",
          "-b:a", "160k", str(destination)])
    if not destination.is_file() or destination.stat().st_size == 0:
        raise ProcessingError("Nie udało się wyciąć fragmentu nagrania.")
    return destination


def _bookmarks(db_path: Path):
    if db_path.is_symlink():
        raise ProcessingError("Niebezpieczna ścieżka bazy zakładek.")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path == BOOKMARK_DB:
        db_path.parent.chmod(0o700)
    connection = sqlite3.connect(db_path, timeout=5)
    db_path.chmod(0o600)
    connection.execute("""CREATE TABLE IF NOT EXISTS recording_bookmarks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recording_sha TEXT NOT NULL,
        title TEXT NOT NULL,
        start REAL NOT NULL,
        excerpt TEXT NOT NULL,
        note TEXT NOT NULL DEFAULT ''
    )""")
    return connection


def save_bookmark(recording_sha: str, title: str, start: float, excerpt: str,
                  note: str = "", db_path: Path = BOOKMARK_DB) -> int:
    import re
    if not re.fullmatch(r"[a-f0-9]{64}", recording_sha):
        raise ProcessingError("Niepoprawny identyfikator nagrania.")
    if not math.isfinite(float(start)) or start < 0:
        raise ProcessingError("Niepoprawny czas zakładki.")
    with _bookmarks(db_path) as db:
        cursor = db.execute("""INSERT INTO recording_bookmarks
            (recording_sha,title,start,excerpt,note) VALUES (?,?,?,?,?)""",
            (recording_sha, title[:150], float(start), excerpt[:1000], note[:250]))
        return int(cursor.lastrowid)


def get_bookmarks(recording_sha: str, db_path: Path = BOOKMARK_DB) -> list[dict]:
    import re
    if not re.fullmatch(r"[a-f0-9]{64}", recording_sha):
        raise ProcessingError("Niepoprawny identyfikator nagrania.")
    with _bookmarks(db_path) as db:
        db.row_factory = sqlite3.Row
        return [dict(row) for row in db.execute("""SELECT id,title,start,excerpt,note
            FROM recording_bookmarks WHERE recording_sha=? ORDER BY start,id""", (recording_sha,))]


def delete_bookmark(bookmark_id: int, recording_sha: str, db_path: Path = BOOKMARK_DB) -> None:
    with _bookmarks(db_path) as db:
        db.execute("DELETE FROM recording_bookmarks WHERE id=? AND recording_sha=?",
                   (bookmark_id, recording_sha))
