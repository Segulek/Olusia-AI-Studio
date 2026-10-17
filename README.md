# 🎧 Olusia AI Studio

Lokalna aplikacja na MacBooka: MP3 z wideo, separacja głosu, transkrypcja oraz fiszki AI ze zdjęć i tekstu. Przetwarzanie AI odbywa się lokalnie, bez opłat za minuty transkrypcji. Wymagane są lokalne narzędzia i pobranie modeli.

## Status v2.1.1

- ✅ Kod aplikacji v2.1.1 został zaimportowany do gałęzi `main` przez GitHub Actions.
- ✅ Testy importu zakończyły się pomyślnie, a archiwum `.bundle` zostało usunięte z repozytorium.
- ✅ Tag `v2.1.1` jest dostępny na GitHubie.
- 🔎 Dostępność **pliku ZIP w GitHub Releases** należy potwierdzić na stronie [Releases](https://github.com/Segulek/Olusia-AI-Studio/releases). Sam tag nie potwierdza obecności pliku do pobrania.

[Zobacz kod](https://github.com/Segulek/Olusia-AI-Studio) · [Sprawdź wydania](https://github.com/Segulek/Olusia-AI-Studio/releases) · [Historia automatyzacji](https://github.com/Segulek/Olusia-AI-Studio/actions)

## Aktualizowanie u Olusi

1. Otwórz lokalne **Olusia AI Studio → 🔄 Aktualizacje**.
2. W razie potrzeby zapisz źródło `Segulek/Olusia-AI-Studio` (w v2.1.1 jest już domyślne).
3. Kliknij **Sprawdź, czy jest nowa wersja**. Gdy jest nowsza od zainstalowanej, kliknij **Pobierz aktualizację z GitHuba**, a potem **Zainstaluj**.
4. Uruchom aplikację ponownie.

Ważne: użytkownik mający już **v2.1.1 nie zobaczy v2.1.1 jako nowej aktualizacji**. Kanał pobierania sprawdzimy w pełni przy pierwszym kolejnym wydaniu. W starszej aplikacji może być potrzebna jednorazowa aktualizacja lokalnym ZIP-em.

Zestawy fiszek są zapisane w `~/Library/Application Support/Olusia AI Studio/fiszki.sqlite3`, poza folderem źródeł. Aktualizacja kodu ma zachować te dane oraz pobrane modele. Ważne materiały warto regularnie kopiować na osobny nośnik.

## Publikowanie kolejnych wersji

1. Wprowadź zmiany w kodzie i testach.
2. Ustaw ten sam numer wersji w `VERSION` i `updater.py`.
3. Uruchom `python -m pytest -q tests/test_cards_and_update.py tests/test_processor.py`.
4. Zapisz zmiany na `main`. Workflow [publish-release.yml](.github/workflows/publish-release.yml) ma przetestować kod i utworzyć GitHub Release z paczką ZIP.

Nowy numer musi być **większy** niż poprzedni. Nie edytuj pliku archiwalnego importera; służył tylko do pierwszego importu.

## Bezpieczeństwo i koszty

Repozytorium jest **publiczne**. Nie umieszczaj w nim zdjęć, nagrań, transkrypcji, kluczy, bazy fiszek ani środowisk modeli. `.gitignore` ogranicza przypadkowe dodawanie takich danych, ale nie zastępuje kontroli przed commitem.

Aktualizacje pobieraj tylko z repozytorium, któremu ufasz. SHA-256 wykrywa uszkodzenia, nie stanowi samodzielnego podpisu kryptograficznego wydawcy. Lokalna transkrypcja i generowanie fiszek nie wymagają płatnego API; GitHub udostępnia bezpłatny zakres Actions/Releases, podlegający limitom usługi.

