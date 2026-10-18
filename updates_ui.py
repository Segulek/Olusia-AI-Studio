"""Safe update UI: user decides when to check, download, and install."""
from __future__ import annotations

from pathlib import Path
import streamlit as st

from updater import (
    VERSION, UpdateError, apply_update, check_github_update,
    configured_repo, download_verified_update, read_manifest, set_repo,
    BackupError, save_data_backup, list_data_backups, validate_data_backup,
    restore_data_backup,
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



def render_backups() -> None:
    """Local-only export, restore and overview of private data backups."""
    st.markdown("### 💾 Moje kopie zapasowe")
    st.write("Zabezpiecz swoje fiszki, wyniki Learning Plus, historię powtórek i zakładki w nagraniach.")
    st.info("🌷 Raz dziennie przy uruchomieniu studia zapisujemy lokalną, skompresowaną kopię ZIP. "
            "Tworzymy ją także przed aktualizacją i przywracaniem danych. "
            "Automatyczne kopie zachowujemy przez 7 dni (maksymalnie 7 każdego rodzaju). Ręczne kopie pozostają do samodzielnego usunięcia. Nie wysyłamy niczego na GitHub ani do chmury.")

    if st.button("💜 Zrób kopię zapasową teraz", type="primary", key="backup_save_now"):
        try:
            with st.spinner("Bezpiecznie zapisuję fiszki i zakładki…"):
                path = save_data_backup("manual")
            if path is None:
                st.info("Nie ma jeszcze zapisanych fiszek ani zakładek. Dodaj pierwszy zestaw.")
            else:
                st.session_state["olusia_last_backup_name"] = path.name
                st.success("Zapisano kopię danych na MacBooku. Możesz pobrać ją niżej.")
        except (BackupError, OSError) as exc:
            st.error(f"Nie udało się zrobić kopii: {exc}")

    backups = list_data_backups()
    st.markdown("#### Twoje zapisane kopie")
    if backups:
        names = {item["name"]: item for item in backups}
        preferred = st.session_state.get("olusia_last_backup_name", "")
        idx = list(names).index(preferred) if preferred in names else 0
        choice = st.selectbox("Wybierz kopię", options=list(names), index=idx, key="olusia_backup_choice")
        selected = names[choice]
        st.caption(f"Rozmiar kopii: {selected['bytes'] / 1024 / 1024:.2f} MB · plik tylko na tym komputerze.")
        if selected["bytes"] <= 96 * 1024 * 1024:
            try:
                st.download_button(
                    "⬇️ Pobierz wybraną kopię na dysk zewnętrzny",
                    data=selected["path"].read_bytes(),
                    file_name=choice, mime="application/zip", key="backup_download")
            except OSError:
                st.warning("Nie można odczytać kopii. Spróbuj wybrać inną.")
    else:
        st.caption("Nie ma jeszcze kopii. Użyj przycisku powyżej po zapisaniu pierwszych fiszek.")

    st.divider()
    st.markdown("#### Przywróć fiszki i postępy")
    st.warning("Przywrócenie ZASTĘPUJE obecne fiszki i zakładki wersją z wybranej kopii. "
               "Najpierw zapisywana jest oddzielna kopia ratunkowa. "
               "Pozostałe bazy, których nie ma w archiwum, zostaną bez zmian.")
    source = st.radio("Skąd przywrócić?", ["Z kopii na MacBooku", "Z pliku ZIP"],
                      horizontal=True, key="backup_restore_source")
    data = None
    if source == "Z kopii na MacBooku":
        if backups:
            selected_name = st.selectbox("Wybierz kopię do przywrócenia",
                                         options=[item["name"] for item in backups],
                                         key="backup_restore_choice")
            try:
                data = next(item for item in backups if item["name"] == selected_name)["path"].read_bytes()
            except OSError:
                st.error("Nie mogę odczytać tej kopii.")
    else:
        archive = st.file_uploader("Wybierz własną kopię Olusia (ZIP)",
                                   type=["zip"], key="backup_restore_upload")
        if archive is not None:
            if archive.size > 96 * 1024 * 1024:
                st.error("Kopia jest zbyt duża (ponad 96 MB).")
            else:
                data = archive.getvalue()
    if data is not None:
        try:
            content = validate_data_backup(data)
            labels = {
                "fiszki.sqlite3": "fiszki i historia powtórek",
                "nagrania.sqlite3": "zakładki w nagraniach",
            }
            st.success("Kopia jest poprawna i zawiera: " +
                       ", ".join(labels[name] for name in content))
            approved = st.checkbox("Rozumiem, że aktualne dane zostaną zastąpione danymi z kopii.",
                                   key="backup_restore_confirm")
            typed = st.text_input("Aby potwierdzić, wpisz PRZYWRÓĆ",
                                  key="backup_restore_phrase")
            if st.button("♻️ Przywróć moje dane", type="primary",
                         disabled=not (approved and typed == "PRZYWRÓĆ"),
                         key="backup_restore_execute"):
                with st.spinner("Tworzę kopię ratunkową i przywracam dane…"):
                    restored = restore_data_backup(data)
                st.success("Przywrócono: " + ", ".join(labels[name] for name in restored["restored"]) +
                           ". Uruchom studio ponownie, żeby odświeżyć wszystkie widoki.")
                if restored["safety_backup"]:
                    st.caption("Kopia ratunkowa sprzed przywrócenia: " +
                               Path(restored["safety_backup"]).name)
        except BackupError as exc:
            st.error(f"Nie mogę przywrócić tej kopii: {exc}")

    st.caption("🔐 Kopie nie są zaszyfrowane. Jeśli przenosisz ZIP na pendrive lub dysk, "
               "użyj nośnika chronionego hasłem (np. FileVault). "
               "Kopie w tym samym MacBooku nie chronią przed awarią ani utratą całego komputera.")
