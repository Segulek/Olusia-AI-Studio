# Olusia AI Studio — darmowe aktualizacje przez GitHub

Źródło: https://github.com/Segulek/Olusia-AI-Studio

## Pierwsze wydanie (jednorazowo)

Użyj pliku `Olusia_AI_Studio_GitHub_v2.1.1.bundle` przygotowanego w rozmowie. Paczka jest archiwum ZIP z rozszerzeniem `.bundle`, aby uniknąć pomyłki z gotową aktualizacją. Publikujemy źródła bez prywatnych nagrań ani fiszek.

1. Dodaj plik do gałęzi `main` przez https://github.com/Segulek/Olusia-AI-Studio/upload/main
2. Workflow `.github/workflows/import-source.yml` porównuje SHA-256 paczki, rozpakowuje wyłącznie dozwolone pliki i uruchamia testy.
3. Jeśli testy przejdą, workflow zapisze kod w repozytorium, usunie plik `.bundle` i utworzy GitHub Release `v2.1.1`.
4. Plik wydania `Olusia_AI_Studio_UPDATE_v2.1.1.zip` to aktualizacja z manifestem SHA-256 dla aplikacji Myszy.

Kontroluj status w zakładce **Actions**. Do czasu zakończenia pracy nie ma jeszcze opublikowanego wydania.

## Kolejne wersje

Po uruchomieniu projektu zmień pliki w repozytorium i podnieś wersję równocześnie w `VERSION` i w `updater.py`. Przetestuj zmiany, a następnie wypchnij commit do `main`. Workflow `publish-release.yml` uruchomi testy i wystawi nowe wydanie. Istniejącego wydania nie nadpisuje.

**W aplikacji:** zakładka **Aktualizacje** → **Sprawdź** → **Pobierz** → **Zainstaluj**, a potem ponowne uruchomienie.

## Ważne

- Modele AI, środowiska lokalne oraz zapisane fiszki nie są dołączane do repozytorium ani paczek aktualizacji.
- GitHub Releases nie są niezależnym systemem podpisywania kodu; instaluj wyłącznie z zaufanego źródła.
- Repozytorium jest publiczne. Nie przesyłaj sekretów ani danych osobowych.
- GitHub udostępnia bezpłatny zakres usług, ale limity mogą się zmieniać.
