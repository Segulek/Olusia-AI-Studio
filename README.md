# 🌷 Olusia AI Studio 2.9.0 — nawet 30 fiszek ze zdjęcia

Olusia może teraz wybrać **od 3 do 30 fiszek** zarówno z tekstu, jak i ze zdjęcia notatek. Wcześniej tryb fotograficzny tworzył maksymalnie 5 fiszek niezależnie od ustawienia suwaka.

## Jak to działa

- Lokalny **Qwen3-VL 4B Instruct** (lub już zainstalowany starszy wariant 4B) najpierw odczytuje krótkie fakty medyczne **w porcjach maksymalnie po 5**, bez proszenia od razu o duży JSON.
- Jeśli jedna porcja nie wystarcza, aplikacja przegląda kolejne powiększenia i w razie potrzeby wykonuje drugie podejście z listą faktów, które już zna, aby ograniczyć powtórzenia.
- Następnie tworzy angielskie fiszki **partiami po maksymalnie 5 pytań**. Jest to ważne, bo wcześniejsze duże odpowiedzi potrafiły wyczerpać limit tokenów i zablokować wynik.
- Program usuwa dosłowne duplikaty faktów i pytań. Gdy jedna partia się nie powiedzie, wcześniejsze prawidłowo wygenerowane fiszki pozostają.
- Żądana liczba to **maksimum**, nie obietnica: ze strony zawierającej tylko 6 czytelnych faktów model nie powinien wymyślać 20 kolejnych. **Olusia sprawdza fakty medyczne przed zapisem.**
- Dla wielu fiszek przetwarzanie potrwa dłużej. Liczba wywołań analizy obrazu jest ograniczona, żeby nie utknąć w nieskończonych próbach.
- Jedno AI do tekstu, zdjęć i porównania odpowiedzi ustnych, fiszki wyłącznie po angielsku. Bez nowych modeli ani dużych bibliotek.

## Aktualizacja Windows i macOS

Jeśli działa już wersja 2.x, wybierz w aplikacji **Aktualizacje → Sprawdź → Pobierz → Zainstaluj**, a następnie uruchom ją ponownie. Zachowane zostaną stare fiszki, baza FSRS, nagrania i kopie danych.

Na Windows lokalny model `qwen3-vl:4b-instruct` pozostaje wystarczający. Nie trzeba instalować modeli 8B ani ponownie pobierać Ollamy.

---
**Fixes the flashcard blocker after uninstalling the old Qwen model.** The app now automatically checks local Ollama models and prefers **`qwen3-vl:4b-instruct`**, but also accepts the older **`qwen3-vl:4b`** if that's the only model installed. The interface never asks Olusia to select between them.

- Works for handwritten photo notes, text flashcards and oral exam feedback.
- **No re-download needed** if either of those two models is already installed.
- The installer now downloads `qwen3-vl:4b-instruct` only when explicitly run. It does not delete older models or stored cards.
- To temporarily unblock Olusia Studio 2.8.3 before updating, use `ollama cp qwen3-vl:4b-instruct qwen3-vl:4b` if Instruct is present (an Ollama model alias; not a new 3.3GB download).
- For a clean installation: `ollama pull qwen3-vl:4b-instruct`.
- `ollama list` shows installed models. Never remove the only installed model without checking the app after upgrading.
- English-language medical flashcards, FSRS and seven-day compressed backups remain unchanged.

**Windows:** Update from inside the app (Updates → Check → Download → Install), restart `2_START_WINDOWS.bat`. Mac users can update the same way. No mandatory downloads, no added AI models.

---
## Dlaczego poprzedni odczyt mógł zawodzić?

Na Windowsie potwierdzono Ollama 0.40.6 i prawidłowo zainstalowany model `qwen3-vl:4b` (3,3 GB). Raport `output_limit=3` oznaczał, że podczas bezpośredniego tworzenia dużych odpowiedzi JSON model dochodził do limitu generowania — nie świadczy o nieczytelnym piśmie.

## Zmiana w 2.8.3

- Zdjęcie jest analizowane przez ten sam Qwen3-VL 4B, **bez JSON w pierwszym kroku**.
- Model ma krótko wypisać maksymalnie **5 czytelnych faktów w języku angielskim**; następnie ten sam model zamienia je w maksymalnie 5 fiszek po angielsku.
- Jeśli pełna strona daje mało faktów, aplikacja próbuje dwóch zachodzących na siebie powiększeń. Każde wywołanie obsługuje **tylko jeden obraz**.
- Gdy model zakończy pracę z `done_reason=length`, już wygenerowane, kompletne zdania nie przepadają.
- Jeśli nie uda się zbudować fiszek, panel pokaże **czytelne fakty**, które model jednak odczytał. Dzięki temu można je poprawić i ponowić tworzenie z tekstu.
- Sekcja **AI Diagnostics** zawiera teraz typ zakończenia odpowiedzi, liczbę znaków tekstu, liczbę znaków rozumowania i liczbę tokenów. Raport nie zawiera zdjęć ani tekstu notatek.
- Nie trzeba ponownie pobierać Ollamy, Qwena, Whispera ani Demucsa. Kompatybilne z macOS i Windows.

**Uwaga:** to rozwiązanie ogranicza złożoność żądania modelu, lecz nie gwarantuje odczytu wszystkich odręcznych notatek. W szczególności nie wolno bez sprawdzenia używać wygenerowanych informacji medycznych — wszystkie propozycje wymagają akceptacji Olusi.

### Instalacja

W działającej wersji 2.x wybierz **Aktualizacje → Sprawdź → Pobierz → Zainstaluj**, a następnie uruchom aplikację ponownie. Na Windows lub macOS wymagany jest nadal tylko `qwen3-vl:4b`. Jeśli Myszka wciąż korzysta z pakietu 1.0, najpierw trzeba przeprowadzić migrację do wersji z aktualizatorem.

---
If the local vision model generates zero cards, the application now tries a **second method using the SAME qwen3-vl:4b**: it first reads short, clearly visible English medical facts as ordinary text without forcing a JSON flashcard response, then turns those statements into English flashcards. No second model, cloud service or new large download.

- Handles common alternative fields in model results: `flashcards`, `question`, `answer`.
- Displays counts of model responses, JSON errors and empty results under **AI Diagnostics**, instead of incorrectly claiming the student's handwriting is unreadable.
- Shows a medical review warning when fallback flashcards come from an AI-extracted interpretation. Never silently saves generated cards.
- Still uses sequential photo crops, `think: false`, and a local model on `127.0.0.1:11434`.
- Keeps old decks and the macOS/Windows local backup database unchanged.

**Privacy:** diagnostic details contain counts and error categories only, not student pictures, text or answers. The photo is never added to GitHub.

**Limitation:** CI simulates Ollama responses; it does not run the 3.3 GB model on Olusia's Mac. If the new fallback also returns no cards, share the short text from the **AI Diagnostics** expander, plus `ollama --version` and `ollama list`, so we can identify the actual cause.

---
Poprawiliśmy błędy analizy zdjęć w jednym lokalnym modelu **qwen3-vl:4b**. Obsługa zdjęć jest nadal prywatna, bez chmury, a **fiszki są w całości po angielsku**.

- Model Ollama otrzymuje teraz jawne **`think: false`**. Wcześniej odpowiedzi modeli zdolnych do reasoning mogły pojawiać się jako puste pole `message.content`.
- Zdjęcie trafia do Ollama jako **jeden obraz na żądanie** zamiast całej strony plus dwa zbliżenia jednocześnie. To zmniejsza chwilowe zużycie RAM na słabszych MacBookach.
- Jeśli cała strona nie daje poprawnego wyniku, aplikacja próbuje powiększonych fragmentów i zachowuje te fiszki, które da się uzyskać z czytelnych informacji.
- Obsługiwane są odpowiedzi JSON z dodatkowymi znacznikami oraz puste/ucięte wiadomości Ollamy.
- Dodatkowe komunikaty pomagają odróżnić problemy z modelem, pamięcią RAM, Ollamą i niespójnym JSON.
- Testy obejmują obraz WebP o wymiarach **1121 × 1584** (jak przesłane zdjęcie z notatkami), bez dołączania prywatnego zdjęcia studentki do publicznego repozytorium.

**Ograniczenie:** automatyczne testy symulują odpowiedzi modelu. Nie gwarantują, że rzeczywisty Qwen poprawnie przeczyta każde pismo. Jeśli na komputerze nadal jest błąd, potrzebny jest dokładny komunikat i dane diagnostyczne z lokalnej Ollamy. Nie trzeba usuwać fiszek ani zmieniać silnika.

Po aktualizacji uruchom aplikację ponownie. Jeśli model nie działa, sprawdź `ollama list`, `ollama --version` i `ollama pull qwen3-vl:4b`.

---
**Nowość: instalacja na Windows 10/11 (x64).** Te same fiszki medyczne po angielsku, Learning Plus, lokalny Qwen3-VL 4B, FSRS, kopie danych, Whisper i narzędzia audio. Na Windows program działa w przeglądarce pod prywatnym adresem \`127.0.0.1:8501\`, a nie jako podpisany instalator \`.exe\`.

## 🪟 Windows: uruchomienie

1. Pobierz z [GitHub Releases](https://github.com/Segulek/Olusia-AI-Studio/releases) plik **Olusia_AI_Studio_Windows_v2.8.0.zip** i rozpakuj go.
2. Uruchom **\`1_INSTALL_WINDOWS.bat\`** (wymaga Python 3.11 x64 i FFmpeg; skrypt wyświetla dokładne instrukcje jeśli ich nie ma).
3. Do fiszek i analiz zdjęć uruchom **\`3_INSTALL_AI_WINDOWS.bat\`**. Wymagane Ollama dla Windows (oficjalna instalacja) oraz jeden model **\`qwen3-vl:4b\`**, około 3,3 GB. Model nie jest instalowany automatycznie z pakietem.
4. Uruchom **\`2_START_WINDOWS.bat\`** — otworzy lokalną aplikację. Jeżeli chcesz izolować głos z nagrań, osobno uruchom **\`4_OPTIONAL_DEMUCS_WINDOWS.bat\`**.

Pełna instrukcja znajduje się w pliku \`WINDOWS_README.txt\` w ZIP. Windows może wyświetlić ostrzeżenie SmartScreen dla niepodpisanych plików .bat — pobieraj tylko oficjalne wydania i w razie wątpliwości sprawdź ich treść. Instalator nie zawiera modeli i wymaga internetu przy pierwszym pobieraniu.

**Folder danych:** Windows: \`%LOCALAPPDATA%\Olusia AI Studio\`; macOS: \`~/Library/Application Support/Olusia AI Studio\`. Kopie SQLite ZIP z zakładki \`💾 Kopie danych\` można eksportować i przywracać między platformami. Kopie automatyczne pozostają przez 7 dni; ręczne zachowujemy.

**Windows: uwagi:** HEIC/HEIF najlepiej skonwertować do JPG/PNG przed analizą. Demucs jest opcjonalny i na CPU może działać wolno. Uruchamianie lokalnych modeli może wymagać kilku dodatkowych GB RAM i miejsca na dysku.

## 🍎 macOS i aktualizacje

Użytkownicy macOS mogą pozostać przy dotychczasowym instalatorze .command i aktualizować studio w zakładce \`Aktualizacje\`. Od wersji 2.8.0 automatyczny ZIP z GitHub Releases może uzupełniać także pliki .bat na Windows — nie modyfikuje folderów środowiska AI ani baz SQLite.

---

**Olusia studiuje medycynę po angielsku — wszystkie nowo generowane pytania i odpowiedzi są po angielsku.**

## Nowość: jeden przycisk, jeden model

W zakładce **📚 Fiszki → Create flashcards** Myszka dodaje **zdjęcie notatek albo tekst** i naciska **Create English flashcards**. Nie wybiera modelu ani metody przetwarzania.

Cały moduł edukacyjny (zdjęcia, tekst, porównanie odpowiedzi ustnych z fiszkami) korzysta z **jednego, lokalnego modelu Qwen3-VL 4B** (`qwen3-vl:4b`). Model zajmuje około 3,3 GB na dysku i wymaga Ollama 0.12.7+. Żadne notatki i zdjęcia nie trafiają do zewnętrznego API.

**Uwaga:** transkrypcje mowy wciąż używają osobnego silnika Whisper, a separacja dźwięku Demucs. To niezależne narzędzia audio, nie dodatkowe modele generujące fiszki.

### Pismo odręczne

- Zdjęcie jest analizowane jako całość oraz w **dwóch zachodzących na siebie powiększonych częściach** (jeśli jest dostatecznie duże).
- Nawet przy częściowo nieczytelnym piśmie model powinien tworzyć fiszki z **czytelnych fragmentów**, zamiast odrzucać całą stronę.
- Jeśli najpierw zwróci tylko zastrzeżenie, aplikacja wykonuje **jedną dodatkową próbę** na powiększonych fragmentach.
- Obok fiszek pokazujemy strukturę notatek, niepewne elementy i ostrzeżenia przy pytaniach bez jasnego wskazania źródła.
- Wszystkie fiszki są **wersjami roboczymi do zatwierdzenia**. Przy zdjęciach użytkowniczka potwierdza sprawdzenie faktów medycznych przed zapisem.
- Można dopisać krótkie objaśnienie nieczytelnego słowa lub związku w tym samym formularzu, bez wybierania innego modelu.

## Pierwsze uruchomienie

Jeśli program został zaktualizowany z wcześniejszej wersji, uruchom ponownie **`5_DOINSTALUJ_FISZKI.command`**. Instalator sprawdzi niezbędne zależności i pobierze tylko jeden model generatywny:

```bash
ollama pull qwen3-vl:4b
```

Program nie usuwa starych modeli samodzielnie. Po sprawdzeniu, że nowy tryb działa, nieużywane modele można zobaczyć poleceniem `ollama list` i odinstalować ręcznie, np. `ollama rm qwen2.5:3b` lub `ollama rm qwen3-vl:2b`. **Nie usuwaj modelu `qwen3-vl:4b`**.

## Pozostałe funkcje i prywatność

Learning Plus, FSRS, nagrania, egzamin ustny, aktualizator oraz kompresowane kopie zapasowe z limitem 7 dni pozostają bez zmian. Limit zdjęć: 2 na raz, 12 MB każde. Przechowywane zestawy fiszek nie są automatycznie modyfikowane.

Nie da się zagwarantować bezbłędnego odczytania drobnego pisma na każdym zdjęciu ani medycznej poprawności każdego pytania. **Zweryfikuj fakty w materiałach uczelni**, zwłaszcza fiszki oznaczone jako wymagające sprawdzenia.

[Wydania](https://github.com/Segulek/Olusia-AI-Studio/releases) · [Kod](https://github.com/Segulek/Olusia-AI-Studio)
