# 🌷 Olusia AI Studio 2.8.0 — macOS + Windows

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
