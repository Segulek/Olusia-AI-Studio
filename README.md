# 🌷 Olusia AI Studio 2.5.1 — Kopie danych

Lokalna aplikacja na macOS: audio, transkrypcje, fiszki AI, adaptacyjna nauka medycyny i Learning Plus. Wersja 2.5 dodaje nową zakładkę **💾 Kopie danych**.

## Co nowego

- **Kopia dzienna:** przy uruchomieniu aplikacja tworzy najwyżej jedną kopię dziennie, o ile są zapisane fiszki lub zakładki.
- **Kopia przed aktualizacją:** od wersji 2.5 każde kolejne instalowanie aktualizacji wykonuje kopię przed podmianą kodu. Ważne: przy przejściu z 2.4 do 2.5 stary aktualizator nie tworzy jeszcze automatycznej kopii; zrób ją ręcznie przed pierwszą aktualizacją.
- **Kopia przed przywróceniem:** aplikacja zapisuje wersję ratunkową przed nadpisaniem istniejących danych.
- **Zapisz i pobierz:** jeden przycisk do utworzenia kopii oraz pobranie ZIP na zewnętrzny nośnik.
- **Przywróć:** wybór zapisanej kopii lub ZIP, kontrola sum SHA-256, formatu i integralności SQLite oraz świadome potwierdzenie operacji.
- **Oszczędność miejsca od 2.5.1:** automatyczne kopie dzienne, sprzed aktualizacji i sprzed przywrócenia przechowywane są **tylko z ostatnich 7 dni kalendarzowych UTC** (maksymalnie po 7 plików każdego rodzaju). Starsze automatyczne archiwa są usuwane po pomyślnym wykonaniu kolejnej kopii. Ręcznych kopii nie usuwamy automatycznie.
- **Kompresja:** kopie SQLite są wykonywane bezpiecznym mechanizmem SQLite backup, porządkowane przez `VACUUM` wyłącznie w kopii tymczasowej i kompresowane jako ZIP (DEFLATE, poziom 9). Baza Olusi pozostaje bez zmian. W zależności od danych oszczędność miejsca może być różna.

## Co jest zabezpieczane

Kopia zawiera tylko lokalne bazy danych: `fiszki.sqlite3` (zestawy, przedmioty, harmonogram FSRS, historia powtórek) i `nagrania.sqlite3` (znaczniki czasu i notatki). Nie zawiera nagrań, zdjęć, pobranych modeli, aplikacji ani danych z innych folderów.

Archiwa są zapisywane lokalnie w `~/Library/Application Support/Olusia AI Studio/backups/` z uprawnieniami tylko dla bieżącego użytkownika. Nie są wysyłane na serwer. **ZIP nie ma hasła i nie jest szyfrowany** — jeśli przenosisz go poza MacBook, wykorzystuj zaszyfrowany dysk lub nośnik. Kopie na tym samym komputerze nie chronią przed utratą lub awarią całego dysku.

## Przywracanie

W **💾 Kopie danych** wybierz archiwum lokalne lub ZIP. Aplikacja zweryfikuje zawartość przed przywróceniem. Następnie potwierdź operację i kliknij **Przywróć moje dane**. Przywracane są wyłącznie bazy, które znajdują się w archiwum. Po zakończeniu uruchom studio ponownie. Nie przywracaj danych przy równocześnie uruchomionych innych kopiach aplikacji.

## Instalacja

Z wersji 2.1.1+ wybierz **⚙️ Aktualizacje → Sprawdź → Pobierz → Zainstaluj**, potem uruchom ponownie. Z wersji 1.0 najpierw wykonaj jednorazową migrację. **Przed pierwszym przejściem na 2.5 wykonaj ręczną kopię folderu danych** w Finderze (aplikacja nie miała wcześniej wbudowanego narzędzia do kopii).

## Bezpieczeństwo i ograniczenia

Całość działa lokalnie na `127.0.0.1`. ZIP kopii jest sprawdzany przed zapisem baz danych, a wcześniejszy stan zabezpieczamy osobno. Kopie przywracaj wyłącznie ze sprawdzonego źródła. Sumy SHA-256 nie stanowią podpisu cyfrowego. Testy automatyczne nie zastępują próby przywrócenia na MacBooku Olusi. Wiedzę medyczną generowaną przez AI należy weryfikować w podręcznikach.

[Wydania](https://github.com/Segulek/Olusia-AI-Studio/releases) · [Kod](https://github.com/Segulek/Olusia-AI-Studio)
