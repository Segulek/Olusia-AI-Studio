"""Streamlit flashcards panel of Olusia AI Studio."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile

import streamlit as st

from cards import (
    CardsError, Flashcard, cards_as_csv, delete_deck, generate_flashcards,
    get_cards, list_decks, ollama_models, save_deck, set_known,
    generate_visual_flashcards, VISION_MODELS,
)
from ocr_local import OCRError, recognize_image


def render_flashcards() -> None:
    st.markdown("### 📚 Fiszki AI")
    st.write("Fiszki do nauki medycyny po angielsku. AI może analizować **cały układ strony**: diagramy, strzałki, podpisy i zależności — nie tylko pojedyncze litery.")
    st.caption("🇬🇧 All newly generated flashcard questions and answers are in English.")
    create_tab, browse_tab = st.tabs(["✨ Twórz fiszki", "🗂️ Moje zestawy i nauka"])

    with create_tab:
        st.markdown("#### 1. Jak chcesz przygotować materiał?")
        mode = st.radio(
            "Sposób tworzenia fiszek",
            ["🧠 Zrozum zdjęcie (Vision AI)", "✍️ Tekst i notatki", "📷 Klasyczny OCR"],
            key="flashcard_generation_mode", horizontal=True,
            help="Vision AI interpretuje strukturę notatek. OCR rozpoznaje głównie litery i może pomylić pismo odręczne.",
        )
        is_visual = mode.startswith("🧠")
        is_ocr = mode.startswith("📷")
        uploaded = None
        if is_visual or is_ocr:
            allowed_count = 2 if is_visual else 6
            uploaded = st.file_uploader(
                "Dodaj zdjęcia swoich notatek",
                type=["png", "jpg", "jpeg", "webp", "tif", "tiff", "bmp", "heic", "heif"],
                accept_multiple_files=True, key="flashcards_images",
                help=f"Maksymalnie {allowed_count} zdjęcia po 12 MB każde. W razie długiej strony warto dodać 2 czytelne zbliżenia.",
            )
            if uploaded:
                st.caption(f"Zdjęć: {len(uploaded)} / {allowed_count}. Wzory, strzałki i podpisy powinny być czytelne.")
            if is_visual:
                st.info("✨ Model Vision otrzymuje obraz i analizuje hierarchię, powiązania i diagramy. Nie korzystamy tu z błędnego tekstu OCR. Każda fiszka będzie po angielsku.")
                st.caption("Tryb wymaga osobnego, opcjonalnego modelu obrazu Ollama. Najlżejszy zajmuje około 1.9 GB. Nie pobieramy go automatycznie.")
            else:
                if st.button("📷 Odczytaj sam tekst (OCR)", disabled=not uploaded or len(uploaded)>6 or any(file.size>12*1024*1024 for file in uploaded)):
                    try:
                        with st.spinner("Odczytuję tekst lokalnie…"):
                            texts = [recognize_image(file.name, file.getvalue()) for file in uploaded[:6]]
                        old_text = st.session_state.get("flashcards_source", "").strip()
                        st.session_state["flashcards_source"] = (old_text + "\n\n" + "\n\n".join(texts)).strip()[:16000]
                        st.success("Przeczytaj tekst poniżej, popraw błędy OCR i dopiero wtedy twórz fiszki.")
                    except (OCRError, OSError) as exc:
                        st.error(str(exc))

        if not is_visual:
            source = st.text_area(
                "Źródło do fiszek (możesz też poprawić wynik OCR)",
                height=200, key="flashcards_source",
                placeholder="e.g. The axial skeleton includes the skull, vertebral column, ribs and sternum.",
            )
            st.caption(f"{len(source):,}/16 000 znaków. Fiszki będą po angielsku, nawet gdy źródło jest dwujęzyczne.")
        else:
            source = ""

        st.markdown("#### 2. Jakie fiszki przygotować?")
        left, center, right = st.columns(3)
        with left:
            count = st.slider("Liczba fiszek", 3, 30, 10)
        with center:
            level = st.selectbox("Poziom", ["Łatwy", "Standardowy", "Trudniejszy"], index=1)
        with right:
            if is_visual:
                model = st.selectbox(
                    "Model do rozumienia obrazów", VISION_MODELS,
                    format_func=lambda name: {"qwen3-vl:2b": "Oszczędny — 2B (~1.9 GB)",
                                              "qwen3-vl:4b": "Dokładniejszy — 4B (~3.3 GB)"}[name],
                    help="Model 2B zajmuje mniej miejsca; 4B może lepiej czytać drobne diagramy.",
                )
            else:
                model = st.selectbox(
                    "Lokalny model AI", ["qwen2.5:3b", "qwen2.5:1.5b"],
                    help="Modele tekstowe nie rozumieją układu zdjęcia. Użyj Vision AI do diagramów.",
                )
        try:
            available = ollama_models()
            if model in available or any(name.startswith(model + "-") for name in available):
                st.caption("🟢 Model gotowy — lokalna Ollama odpowiada.")
            else:
                st.warning(f"Model {model} nie jest jeszcze pobrany. Zainstaluj go w Terminalu: ollama pull {model}. " +
                           ("Dla trybu obrazowego Ollama musi mieć wersję 0.12.7 lub nowszą." if is_visual else ""))
        except CardsError as exc:
            st.info(str(exc))

        if is_visual:
            too_many = not uploaded or len(uploaded) > 2 or any(file.size > 12*1024*1024 for file in uploaded)
            if st.button("🧠 Zrozum notatkę i utwórz English flashcards", type="primary", disabled=too_many):
                try:
                    with st.spinner("AI analizuje schematy, hierarchię i związki między pojęciami… Na starszym MacBooku może to potrwać kilka minut."):
                        result = generate_visual_flashcards(
                            [(file.name, file.getvalue()) for file in uploaded],
                            count, level, model,
                        )
                    for key in list(st.session_state):
                        if key.startswith("draft_front_") or key.startswith("draft_back_"):
                            st.session_state.pop(key, None)
                    st.session_state["draft_flashcards"] = result.cards
                    st.session_state["visual_note_structure"] = result.structure
                    st.session_state["visual_note_uncertainties"] = result.uncertainties
                    st.success(f"Prepared {len(result.cards)} English flashcards. Review them before saving.")
                except CardsError as exc:
                    st.error(str(exc))
        else:
            if st.button("✨ Generate English flashcards", type="primary",
                         disabled=len(source.strip()) < 35 or len(source) > 16000):
                try:
                    with st.spinner("Creating English questions and answers with local AI…"):
                        cards = generate_flashcards(source, count, level, model)
                    for key in list(st.session_state):
                        if key.startswith("draft_front_") or key.startswith("draft_back_"):
                            st.session_state.pop(key, None)
                    st.session_state["draft_flashcards"] = cards
                    st.session_state.pop("visual_note_structure", None)
                    st.session_state.pop("visual_note_uncertainties", None)
                    st.success(f"Prepared {len(cards)} English flashcards. Review them before saving.")
                except CardsError as exc:
                    st.error(str(exc))

        if st.session_state.get("visual_note_structure"):
            with st.expander("🧩 What the AI understood about your notes", expanded=True):
                st.write(st.session_state["visual_note_structure"])
                if st.session_state.get("visual_note_uncertainties"):
                    st.warning("**Unclear details — verify in your textbook:**")
                    for note in st.session_state["visual_note_uncertainties"]:
                        st.write("• " + note)

        draft = st.session_state.get("draft_flashcards", [])
        if draft:
            st.markdown("#### 3. Review and save your English flashcards")
            deck_name = st.text_input("Nazwa zestawu", value="Moje nowe fiszki", key="draft_deck_name")
            with st.form("edit_flashcards"):
                edits = []
                for index, card in enumerate(draft):
                    with st.expander(f"Fiszka {index+1}: {card.front[:75]}", expanded=index < 2):
                        front = st.text_input("Przód (pytanie)", value=card.front, key=f"draft_front_{index}")
                        back = st.text_area("Tył (odpowiedź)", value=card.back, height=82, key=f"draft_back_{index}")
                    edits.append(Flashcard(front=front, back=back))
                save = st.form_submit_button("💾 Zapisz zestaw na MacBooku", type="primary")
            if save:
                valid = [c for c in edits if c.front.strip() and c.back.strip()]
                try:
                    saved_id = save_deck(deck_name, valid)
                    st.session_state.pop("draft_flashcards", None)
                    st.session_state.pop("visual_note_structure", None)
                    st.session_state.pop("visual_note_uncertainties", None)
                    st.session_state["selected_deck"] = saved_id
                    st.success("Zapisano zestaw! Otwórz „Moje zestawy i nauka”, aby go powtarzać.")
                except CardsError as exc:
                    st.error(str(exc))
            st.caption("Check every medical statement against your class material before saving.")
            st.download_button("⬇️ Pobierz wersję roboczą CSV (Anki)",
                               data=cards_as_csv([{"front": c.front, "back": c.back} for c in draft]),
                               file_name="olusia_fiszki_robocze.csv", mime="text/csv")

    with browse_tab:
        decks = list_decks()
        if not decks:
            st.info("Nie masz jeszcze zapisanych fiszek. Wygeneruj pierwszy zestaw w zakładce „Twórz fiszki”.")
            return
        deck_index = {f"{d['name']} · {d['known']}/{d['total']} opanowane · zestaw #{d['id']}": d["id"] for d in decks}
        selected = st.selectbox("Wybierz zestaw", list(deck_index), key="browse_deck_choice")
        deck_id = deck_index[selected]
        flashcards = get_cards(deck_id)
        st.progress(sum(1 for c in flashcards if c["known"]) / len(flashcards) if flashcards else 0)
        st.caption(f"Opanowane: {sum(c['known'] for c in flashcards)} / {len(flashcards)}. Zestawy są trwale przechowywane poza folderem aplikacji.")
        if flashcards:
            index_key = f"study_index_{deck_id}"
            st.session_state.setdefault(index_key, 0)
            idx = min(st.session_state[index_key], len(flashcards)-1)
            card = flashcards[idx]
            st.markdown(f"#### Fiszka {idx+1} z {len(flashcards)}")
            st.info(card["front"])
            visible_key = f"answer_visible_{deck_id}"
            if st.session_state.get(visible_key, False):
                st.success(card["back"])
            if st.button("👁️ Pokaż / ukryj odpowiedź", key="reveal_card"):
                st.session_state[visible_key] = not st.session_state.get(visible_key, False)
                st.rerun()
            c1,c2,c3,c4 = st.columns(4)
            with c1:
                if st.button("⬅️ Poprzednia", disabled=idx == 0):
                    st.session_state[index_key] -= 1
                    st.session_state[visible_key] = False
                    st.rerun()
            with c2:
                if st.button("➡️ Następna", disabled=idx == len(flashcards) - 1):
                    st.session_state[index_key] += 1
                    st.session_state[visible_key] = False
                    st.rerun()
            with c3:
                if st.button("✅ Umiem"):
                    set_known(card["id"], True)
                    st.session_state[index_key] = (idx+1) % len(flashcards)
                    st.session_state[visible_key] = False
                    st.rerun()
            with c4:
                if st.button("🔁 Powtórz"):
                    set_known(card["id"], False)
                    st.session_state[index_key] = (idx+1) % len(flashcards)
                    st.session_state[visible_key] = False
                    st.rerun()
        st.divider()
        st.download_button("⬇️ Pobierz CSV do Anki", data=cards_as_csv(flashcards),
                           file_name=f"fiszki_zestaw_{deck_id}.csv", mime="text/csv")
        st.download_button("⬇️ Pobierz kopię zestawu JSON",
                           data=json.dumps({"name": selected, "cards": flashcards}, ensure_ascii=False, indent=2).encode("utf-8"),
                           file_name=f"fiszki_zestaw_{deck_id}.json", mime="application/json")
        with st.expander("🗑️ Usuń zestaw"):
            st.warning("Usunięcie jest nieodwracalne. Najpierw pobierz kopię JSON, jeśli chcesz zachować fiszki.")
            if st.checkbox("Rozumiem i chcę usunąć ten zestaw", key=f"confirm_delete_{deck_id}"):
                if st.button("Usuń zestaw", type="secondary"):
                    delete_deck(deck_id)
                    st.success("Zestaw usunięty.")
                    st.rerun()



def render_learning_plus() -> None:
    """Learning Plus in its own tab; only existing flashcard decks are used."""
    from cards import (
        MEDICAL_SUBJECTS, RATING_LABELS, assign_medical_subject,
        due_learning_cards, learning_summary, medical_decks, review_learning_card,
    )
    st.markdown("## 🧠 Olusia Learning Plus")
    st.caption("Osobisty asystent nauki na lekarski • lokalne powtórki FSRS")
    st.info("To narzędzie do nauki, nie do diagnozowania ani leczenia. Sprawdzaj treść fiszek z materiałami z uczelni.")
    decks = medical_decks()
    if not decks:
        st.warning("Brak zestawów. Najpierw przygotuj i zapisz fiszki w zakładce **Fiszki AI**.")
        return

    subjects_tab, reviews_tab, oral_tab, stats_tab = st.tabs(
        ["📚 Przedmioty", "🎯 Powtórki na dziś", "🎙️ Egzamin ustny", "📊 Postępy"]
    )

    with subjects_tab:
        st.markdown("#### Organizuj zestawy do nauki")
        options = {f"{d['name']} · {d['subject']} · {d['total']} fiszek · #{d['id']}": d for d in decks}
        key = st.selectbox("Wybierz zestaw", list(options), key="plus_deck")
        deck = options[key]
        subject = st.selectbox(
            "Przedmiot", MEDICAL_SUBJECTS,
            index=MEDICAL_SUBJECTS.index(deck["subject"]),
            key=f"plus_subject_{deck['id']}"
        )
        if st.button("💾 Przypisz przedmiot", key="plus_assign"):
            try:
                assign_medical_subject(deck["id"], subject)
                st.success("Zapisano. Zestaw jest dostępny do nauki z tego przedmiotu.")
                st.rerun()
            except CardsError as exc:
                st.error(str(exc))
        st.caption("Przedmioty porządkują już istniejące fiszki. Niczego nie usuwamy.")

    with reviews_tab:
        filter_name = st.selectbox(
            "Wybierz materiał do powtórek",
            ["Wszystkie przedmioty", *MEDICAL_SUBJECTS],
            key="plus_review_subject"
        )
        filter_subject = None if filter_name == "Wszystkie przedmioty" else filter_name
        summary = learning_summary(filter_subject)
        a, b, c = st.columns(3)
        a.metric("Do powtórzenia", summary["due"])
        b.metric("Już ćwiczone", summary["studied"])
        c.metric("Wszystkie fiszki", summary["total"])

        due_cards = due_learning_cards(filter_subject, limit=100)
        if not due_cards:
            st.success("Dobra robota! Na razie nie masz zaległych powtórek. 🌱")
        else:
            card = due_cards[0]
            st.caption(f"{card['subject']} · {card['deck_name']} · do {len(due_cards)} fiszek w kolejce")
            st.markdown("#### Pytanie")
            st.info(card["front"])
            reveal_key = f"plus_revealed_{card['id']}"
            if not st.session_state.get(reveal_key, False):
                if st.button("👁️ Pokaż odpowiedź", key="plus_reveal"):
                    st.session_state[reveal_key] = True
                    st.rerun()
            else:
                st.success(card["back"])
                st.markdown("**Oceń, jak zapamiętałaś odpowiedź:**")
                cols = st.columns(4)
                for index, (rating, label) in enumerate(RATING_LABELS.items()):
                    if cols[index].button(label, key=f"plus_grade_{rating}", use_container_width=True):
                        try:
                            next_due = review_learning_card(card["id"], rating)
                            st.session_state.pop(reveal_key, None)
                            st.session_state["plus_latest"] = (label, next_due)
                            st.rerun()
                        except CardsError as exc:
                            st.error(str(exc))
                st.caption("FSRS obliczy termin kolejnej powtórki według Twojej historii odpowiedzi.")
            latest = st.session_state.get("plus_latest")
            if latest:
                st.caption(f"Poprzednia ocena: {latest[0]}. Następna powtórka: {latest[1][:16].replace('T', ' ')} UTC.")
            try:
                import fsrs  # noqa: F401
            except ImportError:
                st.warning("Doinstaluj FSRS plikiem **5_DOINSTALUJ_FISZKI.command** i uruchom aplikację ponownie.")

    with oral_tab:
        render_oral_exam(decks)

    with stats_tab:
        filter_name = st.selectbox(
            "Wybierz przedmiot",
            ["Wszystkie przedmioty", *MEDICAL_SUBJECTS],
            key="plus_stats_subject"
        )
        filter_subject = None if filter_name == "Wszystkie przedmioty" else filter_name
        stats = learning_summary(filter_subject)
        a, b, c = st.columns(3)
        a.metric("Powtórki w 7 dni", stats["reviews_week"])
        percent = round(100 * stats["remembered_week"] / stats["reviews_week"]) if stats["reviews_week"] else None
        b.metric("Odpowiedzi Dobrze / Łatwe", f"{percent}%" if percent is not None else "—")
        c.metric("Fiszki do powtórki", stats["due"])
        if stats["daily_reviews"]:
            rows = [{"Dzień": d, "Powtórki": n} for d, n in sorted(stats["daily_reviews"].items())]
            st.bar_chart(rows, x="Dzień", y="Powtórki")
        st.markdown("#### Najtrudniejsze pytania")
        if stats["weak_questions"]:
            for item in stats["weak_questions"]:
                st.write(f"• **{item['front']}** — {item['difficult']}/{item['attempts']} trudnych odpowiedzi")
        else:
            st.caption("Trudne pytania pokażą się po co najmniej dwóch odpowiedziach na każdą fiszkę.")
        st.caption("To tylko analiza powtórek, a nie ocena kompetencji klinicznych ani gwarancja zdania egzaminu.")


@st.cache_resource(show_spinner=False)
def _oral_whisper():
    """Use the installed local Whisper, without sending recorded voice to a cloud API."""
    from faster_whisper import WhisperModel
    return WhisperModel("base", device="cpu", compute_type="int8")


def render_oral_exam(decks: list[dict]) -> None:
    from cards import oral_feedback, review_learning_card, RATING_LABELS
    st.markdown("#### 🎙️ Odpytaj mnie, Myszko!")
    st.write("Wybierz zestaw, odpowiedz **głosem** lub tekstem, sprawdź swoją odpowiedź i ocenę AI na podstawie zapisanej fiszki.")
    st.caption("Nagranie jest przetwarzane przez lokalny Whisper. Mikrofon wymaga zgody przeglądarki. AI może się mylić, szczególnie przy terminach medycznych.")
    choices = {f"{d['subject']} · {d['name']} (#{d['id']})": d['id'] for d in decks if d['total']}
    if not choices:
        st.info("Dodaj najpierw fiszki w zakładce Fiszki AI.")
        return
    label = st.selectbox("Zestaw do egzaminu ustnego", choices, key="oral_deck_select")
    deck_id = choices[label]
    items = get_cards(deck_id)
    if not items:
        return
    index_key = f"oral_question_idx_{deck_id}"
    index = st.session_state.get(index_key, 0) % len(items)
    card = items[index]
    card_id = card['id']
    st.caption(f"Pytanie {index+1} z {len(items)}. Odpowiedzi pozostają na tym MacBooku.")
    st.info(card['front'])
    if st.button("➡️ Kolejne pytanie", key="oral_next"):
        st.session_state[index_key] = (index+1) % len(items)
        st.session_state.pop("oral_feedback_result", None)
        st.rerun()

    recorded = st.audio_input("🎙️ Nagraj odpowiedź", key=f"oral_record_{card_id}")
    answer_key = f"oral_answer_{card_id}"
    if recorded is not None and st.button("📝 Przepisz nagraną odpowiedź", key="oral_transcribe"):
        with st.spinner("Lokalny Whisper rozpoznaje wypowiedź…"):
            try:
                with tempfile.TemporaryDirectory(prefix="olusia-oral-") as folder:
                    path = Path(folder) / "odpowiedz.wav"
                    path.write_bytes(recorded.getvalue())
                    if path.stat().st_size > 12 * 1024 * 1024:
                        raise ValueError("Odpowiedź jest za duża (limit 12 MB). Nagraj krótszy fragment.")
                    segments, _ = _oral_whisper().transcribe(str(path), language="pl", beam_size=5, vad_filter=True)
                    st.session_state[answer_key] = " ".join(piece.text.strip() for piece in segments).strip()
                st.session_state.pop("oral_feedback_result", None)
                st.rerun()
            except (OSError, ValueError, RuntimeError, ImportError) as exc:
                st.error(f"Nie udało się rozpoznać mowy: {exc}")
    answer = st.text_area("Twoja odpowiedź (możesz ją poprawić lub wpisać ręcznie)", key=answer_key, height=120)
    if st.button("🧠 Porównaj odpowiedź z fiszką", disabled=not answer.strip(), key="oral_compare"):
        try:
            with st.spinner("Lokalne AI porównuje odpowiedź ze wzorcem…"):
                result = oral_feedback(card['front'], card['back'], answer)
                st.session_state['oral_feedback_result'] = {"card_id": card_id, **result}
        except CardsError as exc:
            st.warning(str(exc))
    feedback = st.session_state.get('oral_feedback_result')
    if feedback and feedback['card_id'] == card_id:
        st.write(f"**Ocena orientacyjna AI:** {feedback['ocena']}")
        st.write(feedback['komentarz'])
    with st.expander("👁️ Pokaż poprawną odpowiedź z fiszki"):
        st.success(card['back'])
    st.markdown("**Oceń swoją pamięć, aby zaplanować powtórkę FSRS:**")
    cols = st.columns(4)
    for i, (rating, rating_label) in enumerate(RATING_LABELS.items()):
        if cols[i].button(rating_label, key=f"oral_review_{rating}", use_container_width=True):
            try:
                review_learning_card(card_id, rating)
                st.session_state[index_key] = (index+1) % len(items)
                st.session_state.pop('oral_feedback_result', None)
                st.success("Zapisano powtórkę.")
                st.rerun()
            except CardsError as exc:
                st.error(str(exc))
    st.caption("Porównanie AI jest wskazówką, a nie automatycznym zaliczeniem. Sprawdzaj informacje medyczne w wiarygodnych materiałach.")
