# 🌷 Olusia AI Studio 2.6.0 — Visual Notes for Medical English

## 🧠 Understand Notes — nowy generator fiszek ze zdjęć

Olusia studiuje **medycynę po angielsku**. Od wersji 2.6.0 **WSZYSTKIE NOWO GENEROWANE FISZKI** — pytania i odpowiedzi — muszą być po angielsku, zarówno ze zdjęć, jak i z tekstu. Dotychczasowe zapisane zestawy nie są zmieniane.

W zakładce **📚 Fiszki → ✨ Twórz fiszki** dostępne są trzy tryby:

- **🧠 Zrozum zdjęcie (Vision AI)** — zalecany do ręcznych notatek, strzałek, schematów, kolumn i zdjęć z diagramami. Model dostaje **obraz**, a nie błędny tekst OCR; wyjaśnia relacje i tworzy pytania medyczne w języku angielskim.
- **✍️ Tekst i notatki** — generuje angielskie pytania i odpowiedzi na podstawie wklejonego źródła.
- **📷 Klasyczny OCR** — stary tryb odczytu liter, przydatny do czytelnego druku; tekst należy poprawić przed generowaniem fiszek.

Tryb Vision wymaga lokalnego modelu obrazu Ollama. W celu oszczędzania miejsca **nie pobiera się automatycznie** żadnego nowego dużego modelu. Po zainstalowaniu Ollamy **0.12.7 lub nowszej** wybierz:

- **Oszczędny:** w Terminalu uruchom \`ollama pull qwen3-vl:2b\` (około **1,9 GB**).
- **Mocniejszy:** opcjonalnie \`ollama pull qwen3-vl:4b\` (około **3,3 GB**).

Instalator \`5_DOINSTALUJ_FISZKI.command\` pyta o zgodę na pobranie modelu Vision; bez zgody pozostaje niepobrany. Maksymalnie **2 zdjęcia** na jedną analizę obrazu, do **12 MB** każde. Zdjęcia są lokalnie weryfikowane, orientowane i skalowane, a następnie przesyłane wyłącznie na lokalny serwer Ollama \`127.0.0.1:11434\`, nie do zewnętrznego API.

**Zasady bezpieczeństwa:** AI musi opierać fiszki na widocznych elementach obrazu i wskazywać uzasadnienie. Nieczytelne dopiski powinno pomijać i zgłaszać niepewność, jednak małe lokalne modele mogą błędnie odczytać ręczne pismo lub pomylić relacje. Olusia musi sprawdzić każdą fiszkę z materiałami z uczelni przed zapisaniem; to nie jest narzędzie diagnostyczne. Walidacja wykrywa typowe polskie słowa i litery, ale nie gwarantuje absolutnej poprawności języka ani medycyny.

**Ważne dla wersji 1.0:** najpierw wykonaj migrację starej aplikacji do nowszej wersji. Sam plik ZIP aktualizacji nie jest przeznaczony do instalowania bezpośrednio w 1.0.

---

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
