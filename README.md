# 🌷 Olusia AI Studio 2.4.0 — nowy wygląd i bezpieczeństwo

Nowa wersja ma jasny lawendowo-kremowy interfejs, kartę **🏡 Start** i uproszczoną nawigację. Zachowuje audio, MP3, lokalne transkrypcje, fiszki, Learning Plus, egzamin ustny, FSRS oraz inteligentne nagrania.

## Co zmienia się w 2.4.0?

- **Nowy interfejs:** delikatne kolory, czytelne sekcje, responsywne karty, logiczna nawigacja.
- **Audio:** maks. 250 MB, 3 godziny na nagranie; kontrola formatu i długości, limit czasu obliczeń, tymczasowe pliki z ograniczonym dostępem.
- **Zdjęcia:** maks. 6 plików po 12 MB; lokalny OCR z limitami czasu przetwarzania.
- **Fiszki:** lokalne bazy SQLite z uprawnieniami właściciela, limity długości pytań i odpowiedzi, ochrona eksportu CSV przed wykonywaniem formuł w arkuszach.
- **Ustny egzamin:** bez wysyłania nagrań na zewnętrzne API; ocena AI tylko pomocnicza, bez automatycznego zaliczania i modyfikowania FSRS.
- **Zakładki nagrań:** lokalna baza dostępna właścicielowi, weryfikacja identyfikatora nagrania i zakresu odtwarzanego klipu.
- **Aktualizacje:** wyłącznie z `Segulek/Olusia-AI-Studio`, kontrola SHA-256 i manifestu ZIP, odrzucanie nieznanych plików, duplikatów, dowiązań symbolicznych i podejrzanych rozmiarów.

**Jak zainstalować:** w aplikacji 2.1.1+ otwórz **⚙️ Aktualizacje → Sprawdź → Pobierz → Zainstaluj**, a potem uruchom ją ponownie. Jeśli masz 1.0, skorzystaj najpierw z migratora starszej wersji. Zrób kopię folderu i bazy fiszek przed pierwszą aktualizacją.

## Prywatność i ograniczenia

Aplikacja nasłuchuje na **127.0.0.1**, ma włączone zabezpieczenia CORS i XSRF oraz używa lokalnych modeli. Nie jest jednak przeznaczona do udostępniania publicznie w internecie; osoby z dostępem do konta macOS mogą mieć dostęp do jej lokalnych danych. Przeglądarka utrzymuje pliki przesłane w bieżącej sesji, a zatrzymanie komputera podczas pracy może pozostawić pliki w systemowym katalogu tymczasowym. Warto regularnie czyścić pliki tymczasowe i robić kopie danych.

Sumy SHA-256 sprawdzają integralność pobranych aktualizacji, **nie zastępują podpisu cyfrowego wydawcy ani pełnego audytu bezpieczeństwa**. Nie instaluj ZIP-ów z nieznanych źródeł. Model medyczny może generować błędne odpowiedzi — weryfikuj wiedzę w podręcznikach i materiałach uczelnianych. To narzędzie edukacyjne, a nie diagnostyczne.

Zapisane fiszki: `~/Library/Application Support/Olusia AI Studio/fiszki.sqlite3`. Zakładki nagrań: `~/Library/Application Support/Olusia AI Studio/nagrania.sqlite3`. Przesłanych nagrań aplikacja nie archiwizuje automatycznie.

## Rozwój i testy

Repozytorium: https://github.com/Segulek/Olusia-AI-Studio

Wydania: https://github.com/Segulek/Olusia-AI-Studio/releases

Przed aktualizacją uruchom: `python -m pytest -q tests/test_cards_and_update.py tests/test_processor.py`.

