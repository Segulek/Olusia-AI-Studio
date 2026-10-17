# 🎧 Olusia AI Studio 2.2.0

Prywatna aplikacja na MacBooka: wyciąganie MP3, izolacja głosu, lokalny Whisper, generowanie fiszek ze zdjęć i tekstu oraz osobna zakładka **🧠 Olusia Learning Plus**.

## 🧠 Olusia Learning Plus — nowość

- Oddzielna zakładka w tej samej aplikacji — nie instalujesz drugiego programu.
- Przypisywanie istniejących zestawów do przedmiotów medycznych, np. anatomia, histologia, biochemia, fizjologia.
- Adaptacyjne powtórki FSRS z ocenami **Nie pamiętam / Trudne / Dobrze / Łatwe**.
- Zapamiętywanie kolejnych terminów powtórek, historia ocen i statystyki z ostatnich 7 dni.
- Wykrywanie trudnych pytań po co najmniej dwóch próbach.
- Bez API, abonamentu i przesyłania fiszek na serwer.

FSRS to algorytm oparty na modelu pamięci i historii odpowiedzi; w tej pierwszej wersji **nie trenujemy osobnego modelu ML Olusi**. Po zebraniu odpowiednio wielu powtórek będzie można dodać optymalizację parametrów pod jej historię.

## Aktualizacja ze starszych wersji

**Jeśli masz 2.1.1:**

1. Włącz Olusia AI Studio → **🔄 Aktualizacje → Sprawdź → Pobierz → Zainstaluj**.
2. Zamknij uruchomioną aplikację w Terminalu (`Ctrl+C`) i ponownie uruchom `2_URUCHOM.command`.
3. **Jednorazowo uruchom `5_DOINSTALUJ_FISZKI.command`**, aby doinstalować bezpłatną bibliotekę FSRS. Model fiszek Ollama pozostaje lokalny.

**Jeśli masz 1.0:** najpierw zrób kopię folderu, przeprowadź jednorazową migrację za pomocą `0_UAKTUALIZUJ_STARA_WERSJE.command` z pełnej paczki, doinstaluj moduły fiszek, a następnie korzystaj z GitHub Aktualizacje.

## Dane i bezpieczeństwo

Dotychczasowe zestawy pozostają w lokalnej bazie:
`~/Library/Application Support/Olusia AI Studio/fiszki.sqlite3`.

Nowe tabele FSRS są dodawane bez usuwania starych danych; dawne oznaczenia „Umiem” są zachowane, ale początkowo nie stanowią historii FSRS, więc wszystkie fiszki są gotowe do pierwszej powtórki Learning Plus. Zrób kopię ważnych danych przed aktualizacją.

To pomoc w nauce, **nie narzędzie diagnostyczne**. Pytania i odpowiedzi wygenerowane przez małe modele językowe mogą zawierać błędy — weryfikuj je w materiałach i podręcznikach. Statystyki nie przewidują wyniku egzaminu.

## Kanał darmowych aktualizacji

[GitHub Releases](https://github.com/Segulek/Olusia-AI-Studio/releases) · [GitHub Actions](https://github.com/Segulek/Olusia-AI-Studio/actions)

Po zmianie kodu należy ustawić nowy numer jednocześnie w `VERSION` i `updater.py`. Workflow `.github/workflows/publish-release.yml` uruchamia testy i publikuje paczkę ZIP. Repozytorium jest publiczne — nie przesyłaj notatek, zdjęć, baz danych, nagrań ani kluczy.

Wykorzystywane biblioteki: [py-fsrs](https://github.com/open-spaced-repetition/py-fsrs), Whisper, Demucs, Streamlit, Ollama. Instalacja wymaga internetu i lokalnego miejsca na modele, ale samo przetwarzanie nie wiąże się z opłatą za minutę.
