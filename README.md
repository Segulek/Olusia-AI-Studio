# 🎧 Olusia AI Studio

Prywatna aplikacja lokalna dla macOS: MP3 z filmów, izolacja głosu, transkrypcja i fiszki z tekstu lub zdjęć. Modele AI działają lokalnie, bez opłat API za przetworzone nagrania. Uruchomienie wymaga własnego MacBooka oraz lokalnie zainstalowanych narzędzi.

## Status publikacji

- ✅ Repozytorium i zapis zmian przez GitHub zostały skonfigurowane.
- ✅ Workflow `import-source.yml` został dodany do repozytorium.
- ⏳ Pliki aplikacji 2.1.1 **nie są jeszcze zaimportowane**.
- ⏳ GitHub Release v2.1.1 pojawi się **dopiero po pomyślnym imporcie i testach**.

## Jednorazowe uruchomienie kanału aktualizacji

1. Pobierz z rozmowy plik **`Olusia_AI_Studio_GitHub_v2.1.1.bundle`**. Jest to archiwum ZIP z kodem, pod innym rozszerzeniem.
2. Otwórz [Upload files](https://github.com/Segulek/Olusia-AI-Studio/upload/main).
3. Prześlij ten **jeden plik .bundle**, wpisz opis `Import Olusia AI Studio v2.1.1` i zatwierdź commit do `main`.
4. Otwórz [GitHub Actions](https://github.com/Segulek/Olusia-AI-Studio/actions/workflows/import-source.yml) i sprawdź przebieg działania **Importuj Olusia AI Studio**.
5. Po zielonym zakończeniu sprawdź [Releases](https://github.com/Segulek/Olusia-AI-Studio/releases). Powinna pojawić się paczka `Olusia_AI_Studio_UPDATE_v2.1.1.zip`.

Import uruchamia testy przed zapisaniem źródeł i publikacją. Paczka jest porównywana z zapisanym w workflow SHA-256 — przypadkowa lub zmieniona zawartość zostanie odrzucona. Import usuwa archiwum z repozytorium po rozpakowaniu.

Jeśli GitHub Actions nie wystartuje automatycznie, w workflow `import-source.yml` można wybrać **Run workflow**, dopóki archiwum jest dostępne na `main`.

## Kolejne wydania

Po pierwszym imporcie w repozytorium będzie plik `VERSION` oraz skrypt `dev/make_update.py` i workflow `.github/workflows/publish-release.yml`. Aby wydać następną wersję, zmień kod, zaktualizuj numer w `VERSION` i `updater.py`, uruchom testy i opublikuj commit. GitHub Actions utworzy paczkę aktualizacji, którą Olusia może pobrać z poziomu aplikacji.

## Prywatność i bezpieczeństwo

Nie umieszczaj na GitHubie nagrań, zdjęć, baz fiszek, haseł ani modeli. Repozytorium jest publiczne. Sprawdzanie aktualizacji wymaga internetu; lokalne przetwarzanie plików nie wymaga klucza OpenAI.

Podstawowe przetwarzanie jest bezpłatne per użycie; moc obliczeniową zapewnia MacBook. Dostępność i limity usług GitHub mogą ulegać zmianie.
