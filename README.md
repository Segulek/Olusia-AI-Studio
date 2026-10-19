# 🌷 Olusia AI Studio 2.7.0 — jeden silnik AI do fiszek

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
