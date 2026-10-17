"""Safe update UI: user decides when to check, download, and install."""
from __future__ import annotations

from pathlib import Path
import streamlit as st

from updater import (
    VERSION, UpdateError, apply_update, check_github_update,
    configured_repo, download_verified_update, read_manifest, set_repo,
)


def render_updates(root: Path) -> None:
    st.markdown("### 🔄 Aktualizacje aplikacji")
    st.markdown(f"Obecna wersja: **v{VERSION}**")
    st.write("Nowe wersje możesz instalować za darmo. Baza fiszek i pobrane modele AI zostają na Macu.")

    st.markdown("#### Sprawdź aktualizacje przez GitHub")
    try:
        saved = configured_repo()
    except UpdateError as exc:
        st.warning(str(exc))
        saved = ""

    st.caption("Oficjalne źródło aktualizacji: `Segulek/Olusia-AI-Studio` — tylko zweryfikowane wydania.")
    repo = "Segulek/Olusia-AI-Studio"
    if st.button("💾 Zapisz źródło aktualizacji"):
        try:
            set_repo(repo)
            st.session_state.pop("olusia_release", None)
            st.session_state.pop("olusia_downloaded_zip", None)
            st.success("Zapisano źródło aktualizacji na MacBooku. Pozostanie zapisane po kolejnych wersjach.")
        except UpdateError as exc:
            st.error(str(exc))

    if not saved:
        st.info("Kanał GitHub nie jest jeszcze skonfigurowany. Po opublikowaniu pierwszej wersji wpisz tu adres repozytorium. Poniżej nadal można wgrać ZIP ręcznie.")
    else:
        if st.button("🔎 Sprawdź, czy jest nowa wersja"):
            try:
                release = check_github_update(saved)
                st.session_state["olusia_release"] = release
                st.session_state.pop("olusia_downloaded_zip", None)
            except UpdateError as exc:
                st.session_state.pop("olusia_release", None)
                st.error(str(exc))

        release = st.session_state.get("olusia_release")
        if release is None:
            st.caption("Sprawdź aktualizacje przyciskiem. Aplikacja nie pobiera ani nie instaluje nic w tle.")
        else:
            st.success(f"Jest nowa wersja **v{release['version']}**!")
            if release.get("notes"):
                st.markdown(release["notes"])
            st.caption("Pobieraj aktualizacje tylko z repozytorium, którego właścicielowi ufasz.")
            if st.button("⬇️ Pobierz aktualizację z GitHuba"):
                try:
                    with st.spinner("Pobieram i sprawdzam integralność paczki…"):
                        st.session_state["olusia_downloaded_zip"] = download_verified_update(release)
                    st.success("Paczka została pobrana i sprawdzona. Teraz możesz zatwierdzić instalację.")
                except UpdateError as exc:
                    st.error(str(exc))
            downloaded = st.session_state.get("olusia_downloaded_zip")
            if downloaded:
                if st.button("✅ Zainstaluj pobraną aktualizację", type="primary"):
                    try:
                        version = apply_update(downloaded, root)
                        st.success(f"Zainstalowano v{version}. Zamknij studio (Ctrl+C w Terminalu), a następnie uruchom ponownie.")
                    except UpdateError as exc:
                        st.error(str(exc))

    st.divider()
    st.markdown("#### Ręczna aktualizacja (tryb zaawansowany)")
    st.warning("Instalacja pliku ZIP podmienia kod aplikacji. Używaj wyłącznie paczek wydanych przez Olusia AI Studio.")
    archive = st.file_uploader("Wybierz otrzymany plik Olusia_AI_Studio_UPDATE_vX.Y.Z.zip", type=["zip"], key="app_update_zip")
    if archive is not None:
        try:
            content = archive.getvalue()
            manifest = read_manifest(content)
            st.info(f"Paczka do wersji **{manifest['version']}**. Zanim zainstalujesz, sprawdź, od kogo pochodzi.")
            trusted = st.checkbox("Potwierdzam, że pobrałam ZIP z oficjalnego repozytorium", key="olusia_trusted_zip")
            if st.button("Zainstaluj aktualizację ZIP", type="primary", disabled=not trusted):
                version = apply_update(content, root)
                st.success(f"Zainstalowano v{version}. Uruchom aplikację ponownie.")
        except UpdateError as exc:
            st.error(str(exc))
    st.caption("Pobranie kodu z Internetu i uruchomienie aktualizacji wymaga zaufania do wydawcy. Zachowuj kopie ważnych materiałów.")
