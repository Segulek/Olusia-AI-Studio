"""Olusia AI Studio — local-only Streamlit interface."""
from __future__ import annotations

import hashlib
import atexit
import html
import os
from pathlib import Path
import shutil
import sys
import tempfile

import streamlit as st

from flashcards_ui import render_flashcards, render_learning_plus
from updates_ui import render_updates
from updater import VERSION

from processor import (
    ProcessingError, extract_mp3, isolate_vocals, make_wav,
    media_duration, transcript_files, filter_segments, clip_audio,
    save_bookmark, get_bookmarks, delete_bookmark, timestamp_readable,
)

ROOT = Path(__file__).resolve().parent
STEM_PYTHON = ROOT / ".venv-isolation" / "bin" / "python"
SUPPORTED = ["mp4", "mov", "m4v", "mkv", "webm", "avi", "mp3", "wav", "m4a", "aac", "flac", "ogg", "aiff"]

st.set_page_config(
    page_title="Olusia AI Studio • Twoja przestrzeń",
    page_icon="🌷", layout="wide", initial_sidebar_state="collapsed"
)
st.markdown("""
<style>
  :root { color-scheme: light; }
  html, body, [data-testid="stAppViewContainer"], .stApp {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    background: #FAF8FD; color: #30283D;
  }
  .block-container {max-width: 1100px; padding-top: 1.15rem; padding-bottom: 3.5rem;}
  #MainMenu, footer, [data-testid="stToolbar"] {visibility: hidden;}
  .hero {background: linear-gradient(110deg,#F0E7F9 0%,#F9EFF6 52%,#EAF5EF 100%);
    border: 1px solid #E3D6EE; border-radius: 25px; padding: 28px 32px;
    margin-bottom: 20px; box-shadow: 0 13px 30px rgba(95,67,119,.055);}
  .hero h1 {font-size: clamp(1.9rem,4vw,2.65rem);color:#432C58!important;
    letter-spacing:-.035em;margin:3px 0 5px;font-weight:750;}
  .hero p {font-size:1.04rem;color:#675A76;margin:0;max-width:700px;}
  .eyebrow {font-size:.81rem;text-transform:uppercase;letter-spacing:.095em;
    font-weight:750;color:#815FA6;}
  .glass-card {background:white; border:1px solid #EAE3F0; border-radius:19px;
    padding:21px 22px; box-shadow:0 5px 15px #705d8610; min-height:142px;}
  .glass-card h3 {margin:.6rem 0 .3rem;font-size:1.12rem;color:#3E3052!important;}
  .glass-card p {margin:0;font-size:.93rem;color:#6F627A;line-height:1.55;}
  .section-soft {font-weight:700;font-size:1.17rem;color:#443253;margin:16px 0;}
  div[data-testid="stFileUploader"] {background:white;border:1px dashed #AB90C5;
    border-radius:19px;padding:13px;}
  div[data-testid="stTabs"] button[role="tab"] {border-radius:12px;padding:10px 14px;
    color:#5A496C;font-weight:650;}
  div[data-testid="stTabs"] button[aria-selected="true"] {color:#65428E!important;}
  div.stButton > button[kind="primary"], div.stDownloadButton button[kind="primary"] {
    background:#8463AF;color:white;border:1px solid #8463AF;border-radius:13px;
    font-weight:700;min-height:43px;
  }
  div.stButton > button {border-radius:12px;min-height:42px;}
  [data-testid="stMetric"], [data-testid="stAlert"] {border-radius:14px;}
  .stTextInput input, .stTextArea textarea {border-radius:12px;}
  @media (max-width: 680px) {
    .hero {padding:20px 18px;border-radius:19px;}
    .block-container {padding-left:.85rem;padding-right:.85rem;}
    .glass-card {min-height:auto;}
  }
</style>
""", unsafe_allow_html=True)
st.markdown("""
<section class="hero">
  <div class="eyebrow">✦ Twoje prywatne miejsce do nauki</div>
  <h1>🌷 Olusia AI Studio</h1>
  <p>Ucz się we własnym rytmie. Zamieniaj nagrania w notatki,
  twórz fiszki i wracaj do tego, co najważniejsze.</p>
</section>
""", unsafe_allow_html=True)


def render_home() -> None:
    st.markdown("### Cześć, Myszko! ♡")
    st.write("Wybierz, od czego chcesz zacząć. Wszystkie materiały przetwarzamy na Twoim MacBooku.")
    st.markdown("""
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(215px,1fr));gap:14px;margin:20px 0">
      <div class="glass-card"><div>🎧 <b>Nagrania</b></div>
      <h3>Od wykładu do tekstu</h3><p>Wczytaj nagranie, pobierz MP3 lub przepisz wykład.</p></div>
      <div class="glass-card"><div>📚 <b>Fiszki</b></div>
      <h3>Ucz się w małych porcjach</h3><p>Wklej tekst albo dodaj zdjęcie notatek, a potem sprawdź odpowiedzi.</p></div>
      <div class="glass-card"><div>🧠 <b>Learning Plus</b></div>
      <h3>Twój plan powtórek</h3><p>Egzamin ustny, medyczne przedmioty i inteligentne powtórki.</p></div>
    </div>
    """, unsafe_allow_html=True)
    try:
        from cards import list_decks
        decks = list_decks()
        left, right = st.columns(2)
        left.metric("📖 Zapisane zestawy", len(decks))
        right.metric("✨ Przygotowane fiszki", sum(int(d["total"]) for d in decks))
    except (OSError, ValueError, RuntimeError):
        st.caption("Statystyki pojawią się po utworzeniu pierwszego zestawu.")
    st.info("🌿 **Wskazówka:** przed egzaminem zacznij od zakładki „Learning Plus”. Jeśli dopiero zbierasz materiały, wybierz „Audio” lub „Fiszki”.")
    st.caption("🔒 Działa lokalnie na tym MacBooku • bez konta • bez abonamentu za przetwarzanie")


def remove_old_job() -> None:
    previous = st.session_state.get("job_dir")
    if previous:
        shutil.rmtree(previous, ignore_errors=True)
    for key in ("input_file", "mp3", "vocals_wav", "vocals_mp3", "transcript", "edited_transcript", "job_dir", "source_signature", "source_name", "seek_seconds", "recording_clip", "recording_query", "recording_note"):
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

    if uploaded.size > 250 * 1024 * 1024:
        st.error("Ten plik jest zbyt duży (limit 250 MB). Podziel wykład na części.")
        return
    buffer = uploaded.getbuffer()
    fingerprint = hashlib.sha256(buffer).hexdigest()
    if st.session_state.get("source_signature") != fingerprint:
        remove_old_job()
        job_dir = Path(tempfile.mkdtemp(prefix="olusia-studio-"))
        job_dir.chmod(0o700)
        ext = Path(uploaded.name).suffix.lower()
        if ext.lstrip(".") not in SUPPORTED:
            st.error("Nieobsługiwany format pliku.")
            return
        source = job_dir / f"oryginal{ext}"
        with source.open("wb") as fp:
            fp.write(buffer)
        source.chmod(0o600)
        st.session_state.update({
            "job_dir": str(job_dir), "input_file": str(source),
            "source_signature": fingerprint, "source_name": uploaded.name,
        })

    del buffer
    job = Path(st.session_state["job_dir"])
    source = Path(st.session_state["input_file"])
    duration = media_duration(source)
    if duration is None or duration <= 0:
        st.error("Nie udało się odczytać prawidłowego pliku multimedialnego. Sprawdź, czy zawiera dźwięk.")
        return
    if duration > 3 * 60 * 60:
        st.error("Nagranie ma ponad 3 godziny. Podziel je na krótsze części.")
        return
    name = st.session_state["source_name"]
    st.success(f"✅ Dodano: **{html.escape(name)}** · {pretty_size(source.stat().st_size)}" +
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
                    st.session_state["transcript"] = {"plain": plain, "timed": timed, "srt": srt, "segments": rows}
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
        if transcript:
            render_smart_recording(source, job, fingerprint, transcript)
        if transcript and st.button("📚 Użyj transkrypcji do fiszek", key="transcript_to_cards"):
            st.session_state["flashcards_source"] = edited[:16000]
            st.success("Przeniesiono transkrypcję do zakładki „Fiszki AI”. Otwórz ją, aby wygenerować zestaw.")

    st.divider()
    st.caption("🔒 Prywatność: pliki są obrabiane na tym komputerze. Internet jest potrzebny do instalacji i jednorazowego pobrania modeli. Nie ma połączenia z OpenAI API.")




def render_smart_recording(source: Path, job: Path, recording_sha: str, transcript: dict) -> None:
    """Search Whisper segments and play or export short excerpts; no cloud service."""
    st.divider()
    st.markdown("### 🔎 Inteligentne nagrania")
    st.write("Wyszukaj słowo z transkrypcji, kliknij fragment, aby odsłuchać go od wybranego momentu, albo zachowaj zakładkę.")
    segments = transcript.get("segments", [])
    if not segments:
        st.info("Aby przeglądać znaczniki czasu, wykonaj nową transkrypcję w tej wersji aplikacji.")
        return
    query = st.text_input("Znajdź temat lub słowo w nagraniu", key="recording_query")
    matches = filter_segments(segments, query, maximum=40)
    st.caption(f"Znaleziono i pokazano {len(matches)} fragmentów (maks. 40). Wyszukiwanie działa lokalnie.")
    for i, (start, end, text) in enumerate(matches):
        a, b = st.columns([1, 7])
        if a.button(f"▶ {timestamp_readable(start)[:8]}", key=f"seek_{i}_{int(start*1000)}"):
            st.session_state['seek_seconds'] = max(0, float(start))
        b.write(text)
    selected = st.session_state.get('seek_seconds')
    bookmarks = get_bookmarks(recording_sha)
    if bookmarks:
        with st.expander(f"⭐ Zapisane zakładki ({len(bookmarks)})"):
            for saved in bookmarks:
                col_play, col_text, col_del = st.columns([2, 7, 1])
                if col_play.button("▶ " + timestamp_readable(saved['start'])[:8], key=f"bookmark_play_{saved['id']}"):
                    st.session_state['seek_seconds'] = saved['start']
                    selected = saved['start']
                col_text.write(f"{saved['excerpt']}  _{saved['note']}_")
                if col_del.button("✕", key=f"bookmark_delete_{saved['id']}"):
                    delete_bookmark(saved['id'], recording_sha)
                    st.rerun()
    if selected is None:
        st.caption("Wybierz ▶ przy fragmencie, żeby otworzyć odtwarzacz i funkcje zakładek.")
        return
    duration = media_duration(source)
    if duration is not None and selected >= duration:
        selected = 0.0
    start = max(0.0, float(selected))
    st.markdown(f"**Wybrany moment: {timestamp_readable(start)}**")
    note = st.text_input("Notatka do zakładki (opcjonalnie)", key="recording_note")
    nearby = next((text for a, b, text in segments if a <= start < b+0.02), "Ważny fragment nagrania")
    if st.button("⭐ Zapisz zakładkę", key="recording_save_bookmark"):
        save_bookmark(recording_sha, st.session_state.get('source_name', 'Nagranie'), start, nearby, note)
        st.success("Zakładka została zapisana na MacBooku. Po ponownym przesłaniu tego samego pliku znów się pojawi.")
        st.rerun()
    max_end = min(start + 90, duration) if duration else start + 90
    end = st.slider("Koniec fragmentu (sekunda nagrania)",
                    min_value=int(start+1), max_value=max(int(start+1), int(max_end)),
                    value=min(int(start+30), max(int(start+1), int(max_end))), key=f"clip_end_{int(start)}")
    if st.button("🎧 Odsłuchaj od tego momentu / przygotuj klip", key="recording_make_clip"):
        try:
            with st.spinner("Przygotowuję lokalny fragment audio…"):
                preview = clip_audio(source, job / f"fragment_{int(start*1000)}_{int(end*1000)}.mp3", start, float(end))
                st.session_state['recording_clip'] = str(preview)
        except ProcessingError as exc:
            st.error(str(exc))
    clip = st.session_state.get('recording_clip')
    if clip and Path(clip).is_file():
        st.audio(clip, format="audio/mpeg")
        st.download_button("⬇️ Pobierz ten fragment MP3", data=Path(clip).read_bytes(),
                           file_name=f"fragment_{int(start)}s.mp3", mime="audio/mpeg")
    st.caption("Zakładki zapisują tylko tekst, notatkę i czas. Samego nagrania aplikacja nie archiwizuje — po restarcie trzeba ponownie wgrać plik.")



tab_home, tabs_audio, tabs_flash, tabs_plus, tabs_updates = st.tabs(["🏡 Start", "🎧 Audio", "📚 Fiszki", "🧠 Learning Plus", "⚙️ Aktualizacje"])

with tab_home:
    render_home()

with tabs_audio:
    render_audio()

with tabs_flash:
    render_flashcards()

with tabs_plus:
    render_learning_plus()

with tabs_updates:
    render_updates(ROOT)
