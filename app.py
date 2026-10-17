"""Olusia AI Studio — local-only Streamlit interface."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import sys
import tempfile

import streamlit as st

from flashcards_ui import render_flashcards
from updates_ui import render_updates
from updater import VERSION

from processor import (
    ProcessingError, extract_mp3, isolate_vocals, make_wav,
    media_duration, transcript_files,
)

ROOT = Path(__file__).resolve().parent
STEM_PYTHON = ROOT / ".venv-isolation" / "bin" / "python"
SUPPORTED = ["mp4", "mov", "m4v", "mkv", "webm", "avi", "mp3", "wav", "m4a", "aac", "flac", "ogg", "aiff"]

st.set_page_config(page_title="Olusia AI Studio", page_icon="🎧", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
  :root { color-scheme: dark; }
  #MainMenu, footer {visibility: hidden;}
  .block-container {padding-top: 2.0rem; padding-bottom: 3rem; max-width: 1120px;}
  .hero {background:linear-gradient(120deg,#34224f,#211c3d 57%,#142a3a);border:1px solid #5e4a73;
         border-radius:24px;padding:29px 34px;margin-bottom:22px;box-shadow:0 10px 38px #00000022;}
  .hero h1 {color:#fff !important;font-size:2.5rem;letter-spacing:-.045em; margin:0 0 6px 0;}
  .hero p {color:#dacde8;font-size:1.05rem;margin:0;}
  .chip {display:inline-block; padding:5px 11px; border-radius:80px; background:#1d443d;
         color:#a8f2c7; font-size:.79rem; border:1px solid #396459; margin-bottom:12px;}
  .section-title {font-weight:700;font-size:1.1rem;margin:12px 0 2px;}
  div[data-testid="stFileUploader"] {background:#22213a;border:1px dashed #a287c2;border-radius:16px;padding:10px;}
  div.stButton > button[kind="primary"] {background:linear-gradient(95deg,#a855f7,#6366f1); color:white;
      border:0; border-radius:11px; font-weight:700; padding:9px 22px;}
  div.stDownloadButton button {border-radius:10px; border:1px solid #655985;}
  [data-testid="stTabs"] [role="tab"] {font-weight:600;}
  .note {color:#aeb4cf;font-size:.87rem;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <div class="chip">● Prywatne studio • AI na Twoim MacBooku</div>
  <h1>🎧 Olusia AI Studio</h1>
  <p>Audio, transkrypcje i fiszki ze zdjęć lub tekstu. Prywatnie, na Twoim MacBooku.</p>
</div>
""", unsafe_allow_html=True)


def remove_old_job() -> None:
    previous = st.session_state.get("job_dir")
    if previous:
        shutil.rmtree(previous, ignore_errors=True)
    for key in ("input_file", "mp3", "vocals_wav", "vocals_mp3", "transcript", "edited_transcript", "job_dir", "source_signature", "source_name"):
        st.session_state.pop(key, None)


@st.cache_resource(show_spinner=False)
def whisper_model(name: str):
    from faster_whisper import WhisperModel
    return WhisperModel(name, device="cpu", compute_type="int8", cpu_threads=min(8, os.cpu_count() or 4))


def pretty_size(n: int) -> str:
    return f"{n / (1024 * 1024):.1f} MB"


def download_audio(label: str, path: Path | None, suffix: str, *, mime: str = "audio/mpeg") -> None:
    if path and path.is_file():
        st.download_button(label, data=path.read_bytes(), file_name=f"olusia_{suffix}.mp3", mime=mime,
                           use_container_width=True, key=f"download_{suffix}")


with st.sidebar:
    st.markdown("### ℹ️ O aplikacji")
    st.markdown("Nagrania są przetwarzane **lokalnie**. Po pierwszym pobraniu modeli Whisper i Demucs można korzystać z AI offline.")
    st.markdown("**Co robią moduły?**")
    st.markdown("- MP3: wyciąga całą ścieżkę audio z filmu.\n- Izoluj głos: oddziela wokal/głos od podkładu.\n- Transkrypcja: rozpoznaje mowę i przygotowuje TXT i SRT.")
    st.caption("Demucs nie jest narzędziem do idealnego usuwania każdego szumu lub rozdzielania wielu mówiących osób.")
    st.markdown("- Fiszki AI: zdjęcie → OCR → pytania i odpowiedzi (Ollama).")
    st.caption(f"Wersja v{VERSION} • tylko ten Mac • bez API i abonamentu.")

def render_audio() -> None:
    st.markdown("#### 1. Dodaj film lub nagranie")
    uploaded = st.file_uploader("Przeciągnij plik lub kliknij, aby wybrać", type=SUPPORTED,
                                help="MP4, MOV, MP3, WAV, M4A i inne popularne formaty. Limit: 400 MB.")

    if uploaded is None:
        st.info("👆 Wybierz plik, a poniżej pojawią się trzy narzędzia.")
        st.markdown("<div class='note'>💡 Wskazówka: możesz najpierw wyciągnąć MP3, następnie odizolować głos, a na końcu zrobić transkrypcję.</div>", unsafe_allow_html=True)
        return

    buffer = uploaded.getbuffer()
    fingerprint = hashlib.sha256(buffer).hexdigest()
    if st.session_state.get("source_signature") != fingerprint:
        remove_old_job()
        job_dir = Path(tempfile.mkdtemp(prefix="olusia-studio-"))
        ext = Path(uploaded.name).suffix.lower()
        if ext.lstrip(".") not in SUPPORTED:
            st.error("Nieobsługiwany format pliku.")
            return
        source = job_dir / f"oryginal{ext}"
        with source.open("wb") as fp:
            fp.write(buffer)
        st.session_state.update({
            "job_dir": str(job_dir), "input_file": str(source),
            "source_signature": fingerprint, "source_name": uploaded.name,
        })

    del buffer
    job = Path(st.session_state["job_dir"])
    source = Path(st.session_state["input_file"])
    duration = media_duration(source)
    name = st.session_state["source_name"]
    st.success(f"✅ Dodano: **{name}** · {pretty_size(source.stat().st_size)}" +
               (f" · {duration / 60:.1f} min" if duration is not None else ""))

    st.markdown("#### 2. Wybierz, co chcesz zrobić")
    tab_mp3, tab_voice, tab_text = st.tabs(["🎵 Wyciągnij MP3", "🎤 Izoluj głos", "📝 Transkrypcja AI"])

    with tab_mp3:
        st.markdown("##### 🎵 Film → MP3")
        st.write("Zapisz ścieżkę dźwiękową filmu jako plik MP3 (192 kb/s). Nie wymaga modelu AI.")
        if st.button("🎵 Utwórz MP3", type="primary", key="make_mp3"):
            try:
                with st.spinner("Konwertuję plik…"):
                    result = extract_mp3(source, job / "audio.mp3")
                    st.session_state["mp3"] = str(result)
                st.success("MP3 jest gotowe!")
            except ProcessingError as e:
                st.error(str(e))
        mp3 = Path(st.session_state["mp3"]) if st.session_state.get("mp3") else None
        if mp3 and mp3.is_file():
            st.audio(str(mp3))
            download_audio("⬇️ Pobierz MP3", mp3, "audio")

    with tab_voice:
        st.markdown("##### 🎤 Oddziel głos od podkładu")
        st.write("Demucs spróbuje wyodrębnić głos i wokal z muzyki oraz innych dźwięków. Dobre np. do filmów z muzycznym tłem.")
        if not STEM_PYTHON.is_file():
            st.warning("Brakuje modułu Demucs. Uruchom plik **1_ZAINSTALUJ.command** z folderu aplikacji.")
        st.caption("Pierwsze użycie pobierze model do komputera; na CPU separacja dłuższych filmów może potrwać sporo czasu.")
        if st.button("🎙️ Odizoluj głos", type="primary", key="make_voice", disabled=not STEM_PYTHON.is_file()):
            try:
                with st.spinner("Oddzielam głos. Przy dłuższych nagraniach proces może być powolny…"):
                    vocals = isolate_vocals(source, job, STEM_PYTHON)
                    voice_mp3 = extract_mp3(vocals, job / "sam_glos.mp3")
                    st.session_state["vocals_wav"] = str(vocals)
                    st.session_state["vocals_mp3"] = str(voice_mp3)
                st.success("Głos został wyodrębniony!")
            except ProcessingError as e:
                st.error(str(e))
        voice_mp3 = Path(st.session_state["vocals_mp3"]) if st.session_state.get("vocals_mp3") else None
        if voice_mp3 and voice_mp3.is_file():
            st.audio(str(voice_mp3))
            download_audio("⬇️ Pobierz wyizolowany głos (MP3)", voice_mp3, "glos")
            st.info("Wyizolowany głos można wybrać też jako źródło transkrypcji w ostatniej zakładce.")

    with tab_text:
        st.markdown("##### 📝 Automatyczna transkrypcja")
        st.write("Whisper zamieni mowę na tekst. Działa na MacBooku, bez opłat za minuty nagrań.")
        c1, c2, c3 = st.columns(3)
        with c1:
            model_name = st.selectbox("Dokładność", ["base", "small", "tiny", "medium"],
                                      format_func=lambda x: {"tiny":"Szybka (tiny)", "base":"Standard (base)",
                                                             "small":"Dokładniejsza (small)", "medium":"Wysoka (medium)"}[x],
                                      index=0, help="Większy model jest zwykle dokładniejszy, ale działa wolniej.")
        with c2:
            lang = st.selectbox("Język", ["pl", "auto", "en", "de"],
                                format_func=lambda x: {"pl":"Polski", "auto":"Wykryj automatycznie", "en":"Angielski", "de":"Niemiecki"}[x])
        with c3:
            sources = ["Oryginalne nagranie"]
            if st.session_state.get("vocals_wav"):
                sources.append("Wyizolowany głos")
            chosen_source = st.selectbox("Źródło", sources)
        st.caption("Przy pierwszej transkrypcji wybrany model pobierze się z internetu. Kolejne użycia są lokalne.")
        if st.button("✨ Transkrybuj nagranie", type="primary", key="make_transcript"):
            try:
                with st.spinner("Przygotowuję audio i rozpoznaję wypowiedzi…"):
                    selected = (Path(st.session_state["vocals_wav"])
                                if chosen_source == "Wyizolowany głos" else source)
                    wav = make_wav(selected, job / "do_transkrypcji.wav", sample_rate=16000, channels=1)
                    model = whisper_model(model_name)
                    segments, _ = model.transcribe(
                        str(wav), language=None if lang == "auto" else lang,
                        beam_size=5, vad_filter=True, condition_on_previous_text=False,
                    )
                    rows = [(seg.start, seg.end, seg.text) for seg in segments]
                    plain, timed, srt = transcript_files(rows)
                    st.session_state["transcript"] = {"plain": plain, "timed": timed, "srt": srt}
                    st.session_state.pop("edited_transcript", None)
                if rows:
                    st.success(f"Gotowe! Rozpoznano {len(rows)} fragmentów wypowiedzi.")
                else:
                    st.warning("Nie znaleziono rozpoznawalnej mowy. Spróbuj nagrania z wyraźniejszym głosem.")
            except ProcessingError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Nie udało się wykonać transkrypcji: {e}")
        transcript = st.session_state.get("transcript")
        if transcript:
            st.markdown("###### Edytuj i zapisz tekst")
            edited = st.text_area("Treść transkrypcji", value=transcript["plain"], height=255,
                                  key="edited_transcript", help="Możesz poprawić tekst przed pobraniem TXT.")
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.download_button("⬇️ Pobierz TXT", data=edited.encode("utf-8"),
                                   file_name="olusia_transkrypcja.txt", mime="text/plain", use_container_width=True)
            with col_b:
                st.download_button("⬇️ Pobierz SRT (napisy)", data=transcript["srt"].encode("utf-8"),
                                   file_name="olusia_napisy.srt", mime="text/plain", use_container_width=True)
            with col_c:
                st.download_button("⬇️ Tekst z czasami", data=transcript["timed"].encode("utf-8"),
                                   file_name="olusia_znaczniki_czasu.txt", mime="text/plain", use_container_width=True)
            st.caption("TXT zawiera Twoje poprawki. SRT i znaczniki czasu są generowane z pierwotnego wyniku AI.")
        if st.button("📚 Użyj transkrypcji do fiszek", key="transcript_to_cards"):
            st.session_state["flashcards_source"] = edited[:16000]
            st.success("Przeniesiono transkrypcję do zakładki „Fiszki AI”. Otwórz ją, aby wygenerować zestaw.")

    st.divider()
    st.caption("🔒 Prywatność: pliki są obrabiane na tym komputerze. Internet jest potrzebny do instalacji i jednorazowego pobrania modeli. Nie ma połączenia z OpenAI API.")


tabs_audio, tabs_flash, tabs_updates = st.tabs(["🎙️ Audio i transkrypcje", "📚 Fiszki AI", "🔄 Aktualizacje"])

with tabs_audio:
    render_audio()

with tabs_flash:
    render_flashcards()

with tabs_updates:
    render_updates(ROOT)
