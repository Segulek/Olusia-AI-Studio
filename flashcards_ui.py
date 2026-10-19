"""Streamlit flashcards panel of Olusia AI Studio."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile

import streamlit as st

from cards import (
    CardsError, Flashcard, cards_as_csv, delete_deck, generate_flashcards,
    get_cards, list_decks, ollama_models, save_deck, set_known,
    generate_visual_flashcards, STUDIO_MODEL, _require_english_cards,
)
from ocr_local import OCRError, recognize_image


def render_flashcards() -> None:
    st.markdown("### 📚 Fiszki AI")
    st.write("Dodaj zdjęcie odręcznych notatek albo wklej tekst. Jeden lokalny silnik AI przygotuje fiszki po angielsku.")
    st.caption("🇬🇧 English medical flashcards • One AI model • No manual model selection")
    create_tab, browse_tab = st.tabs(["✨ Create flashcards", "🗂️ Moje zestawy i nauka"])

    with create_tab:
        st.markdown("#### 1. Your study material")
        uploaded = st.file_uploader(
            "📷 Photo or screenshot of notes (optional)",
            type=["png", "jpg", "jpeg", "webp", "tif", "tiff", "bmp", "heic", "heif"],
            accept_multiple_files=True, key="flashcards_images",
            help="One or two pages at once, up to 12 MB each. AI also examines zoomed sections.",
        )
        source = st.text_area(
            "Notes in text (optional)",
            height=115, key="flashcards_source",
            placeholder="Add your own explanation if some handwriting is difficult to read.",
            help="You may add context, or use text on its own. Generated questions and answers remain English.",
        )
        picture_mode = bool(uploaded)
        if picture_mode:
            st.info("🧠 AI will analyze headings, relationships and zoomed sections one at a time. "
                    "Illegible words will not block cards from the rest of the page.")
            st.caption("Photographs are processed by Ollama on this Mac. The model may still make mistakes.")
        with st.expander("🛠️ AI troubleshooting (if a photo fails)"):
            st.write("If the same photo fails again, check that Ollama is running, "
                     "qwen3-vl:4b is installed, and your Mac has enough free RAM. "
                     "Run `ollama list` and `ollama --version` in Terminal, "
                     "then restart Ollama if necessary. "
                     "The error message will help distinguish model, RAM and response issues.")
        with st.expander("🔧 Advanced: classical OCR (optional)"):
            st.caption("For clear printed notes only. Not recommended for Olusia's handwriting.")
            if st.button("Extract plain text with OCR", disabled=not uploaded or len(uploaded)>2):
                try:
                    with st.spinner("Odczytuję tekst…"):
                        texts = [recognize_image(file.name, file.getvalue()) for file in uploaded]
                    st.session_state["flashcards_source"] = (source + "\n\n" + "\n\n".join(texts)).strip()[:16000]
                    st.success("OCR text is ready to review. You may remove the photos to generate only from text.")
                except (OCRError, OSError) as exc:
                    st.error(str(exc))

        st.markdown("#### 2. Create your cards")
        a, b = st.columns(2)
        with a:
            count = st.slider("Number of cards", 3, 30, 10)
        with b:
            level = st.selectbox("Difficulty", ["Łatwy", "Standardowy", "Trudniejszy"], index=1,
                                 format_func=lambda value: {"Łatwy": "Easy", "Standardowy": "Standard",
                                                            "Trudniejszy": "Challenging"}[value])
        try:
            available = ollama_models()
            if STUDIO_MODEL not in available:
                st.warning("One-time setup needed: install the local model with 5_DOINSTALUJ_FISZKI.command "
                           "or run: ollama pull " + STUDIO_MODEL + ". No other model is required.")
            else:
                st.caption("🟢 Olusia AI is ready on this computer.")
        except CardsError as exc:
            st.info(str(exc))

        invalid_photos = picture_mode and (
            len(uploaded) > 2 or any(file.size > 12 * 1024 * 1024 for file in uploaded))
        valid_text = len(source.strip()) >= 35 and len(source) <= 16000
        if st.button("✨ Create English flashcards", type="primary",
                     disabled=invalid_photos or not (picture_mode or valid_text)):
            try:
                with st.spinner("Reading what is clear, analyzing arrows and diagrams, preparing English cards…"):
                    if picture_mode:
                        result = generate_visual_flashcards(
                            [(file.name, file.getvalue()) for file in uploaded],
                            count, level, supplementary_text=source,
                        )
                        cards = result.cards
                        st.session_state["visual_note_structure"] = result.structure
                        st.session_state["visual_note_uncertainties"] = result.uncertainties
                        st.session_state["visual_note_review_flags"] = result.review_flags
                        st.session_state["visual_note_diagnostics"] = result.diagnostics
                        st.session_state["draft_needs_review"] = bool(cards)
                    else:
                        cards = generate_flashcards(source, count, level)
                        st.session_state.pop("visual_note_structure", None)
                        st.session_state.pop("visual_note_uncertainties", None)
                        st.session_state.pop("visual_note_review_flags", None)
                        st.session_state.pop("visual_note_diagnostics", None)
                        st.session_state["draft_needs_review"] = False
                for key in list(st.session_state):
                    if key.startswith("draft_front_") or key.startswith("draft_back_"):
                        st.session_state.pop(key, None)
                st.session_state["draft_flashcards"] = cards
                # A new picture needs a fresh explicit medical verification.
                st.session_state.pop("draft_medical_review_confirm", None)
                if cards:
                    st.success(f"Prepared {len(cards)} English flashcards. Review them before saving.")
                else:
                    st.error(
                        "The local AI returned no usable flashcards. This does NOT mean "
                        "your handwriting is unreadable. See AI Diagnostics below: "
                        "the model may have returned empty JSON or no text. "
                        "You can retry, restart Ollama or ask for help using the diagnostics."
                    )
            except CardsError as exc:
                st.error(str(exc))

        if "visual_note_structure" in st.session_state:
            with st.expander("🧩 What the AI understood", expanded=True):
                st.write(st.session_state.get("visual_note_structure") or
                         "The model could not recognize the page structure clearly.")
                for warning in st.session_state.get("visual_note_uncertainties", ()):
                    st.caption("🔎 " + warning)
                for warning in st.session_state.get("visual_note_review_flags", ()):
                    st.warning(warning)
                st.caption("Unclear details must be checked against your course notes. "
                           "The model's evidence descriptions are not an independent verification.")
            if st.session_state.get("visual_note_diagnostics"):
                with st.expander("🛠️ AI Diagnostics — copy these lines if the image fails"):
                    st.code("\\n".join(st.session_state["visual_note_diagnostics"]), language="text")
                    st.caption("The report contains only request counts and failure categories, "
                               "not your photo, private notes or model output.")

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
                save = st.form_submit_button("💾 Zapisz zestaw na komputerze", type="primary")
            review_ok = True
            if st.session_state.get("draft_needs_review"):
                review_ok = st.checkbox(
                    "I have checked the medical facts against my notes and corrected uncertain cards.",
                    key="draft_medical_review_confirm",
                )
            if save and not review_ok:
                st.warning("Please verify the medical facts and confirm before saving.")
            if save and review_ok:
                valid = [c for c in edits if c.front.strip() and c.back.strip()]
                try:
                    _require_english_cards(valid)
                    saved_id = save_deck(deck_name, valid)
                    st.session_state.pop("draft_flashcards", None)
                    st.session_state.pop("visual_note_structure", None)
                    st.session_state.pop("visual_note_uncertainties", None)
                    st.session_state.pop("visual_note_review_flags", None)
                    st.session_state.pop("visual_note_diagnostics", None)
                    st.session_state.pop("draft_needs_review", None)
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
                    segments, _ = _oral_whisper().transcribe(str(path), language="en", beam_size=5, vad_filter=True)
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
