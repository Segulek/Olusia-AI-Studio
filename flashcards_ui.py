"""Streamlit flashcards panel of Olusia AI Studio."""
from __future__ import annotations

import json

import streamlit as st

from cards import (
    CardsError, Flashcard, cards_as_csv, delete_deck, generate_flashcards,
    get_cards, list_decks, ollama_models, save_deck, set_known,
)
from ocr_local import OCRError, recognize_image


def render_flashcards() -> None:
    st.markdown("### 📚 Fiszki AI")
    st.write("Wklej notatki albo dodaj zdjęcia stron zeszytu. Odczytaj tekst, utwórz fiszki za pomocą lokalnego AI, popraw je i zachowaj na MacBooku.")
    create_tab, browse_tab = st.tabs(["✨ Twórz fiszki", "🗂️ Moje zestawy i nauka"])

    with create_tab:
        st.markdown("#### 1. Materiał do fiszek")
        uploaded = st.file_uploader(
            "Dodaj zdjęcia notatek (opcjonalnie)",
            type=["png", "jpg", "jpeg", "webp", "tif", "tiff", "bmp", "heic", "heif"],
            accept_multiple_files=True, key="flashcards_images",
            help="Zdjęcia JPG, PNG, HEIC; maksymalnie 8 zdjęć po 20 MB. Drukowany tekst OCR odczytuje najlepiej.",
        )
        if uploaded:
            st.caption(f"Wybrano {len(uploaded)} zdjęć. Odczyt zdjęć działa lokalnie przez Tesseract (OCR).")
            if st.button("📷 Odczytaj tekst ze zdjęć", disabled=len(uploaded) > 8):
                try:
                    with st.spinner("Odczytuję zdjęcia…"):
                        texts = [recognize_image(file.name, file.getvalue()) for file in uploaded[:8]]
                    existing = st.session_state.get("flashcards_source", "").strip()
                    result = "\n\n".join(texts)
                    st.session_state["flashcards_source"] = (existing + "\n\n" + result).strip()
                    st.success("Tekst odczytany! Sprawdź poniżej, czy OCR nie pomylił słów.")
                except (OCRError, OSError) as exc:
                    st.error(str(exc))

        source = st.text_area(
            "Wpisz lub wklej tekst — możesz też poprawić wynik ze zdjęć",
            height=220, key="flashcards_source",
            placeholder="Np. Fotosynteza to proces, w którym rośliny wytwarzają…",
        )
        st.caption(f"{len(source):,} / 16 000 znaków. Najpierw sprawdź rozpoznany tekst. AI może popełnić błędy, więc przejrzyj fiszki.")
        st.markdown("#### 2. Wybierz rodzaj fiszek")
        left, center, right = st.columns(3)
        with left:
            count = st.slider("Liczba fiszek", 3, 30, 10)
        with center:
            level = st.selectbox("Poziom", ["Łatwy", "Standardowy", "Trudniejszy"], index=1)
        with right:
            model = st.selectbox("Lokalny model AI", ["qwen2.5:3b", "qwen2.5:1.5b"],
                                 help="3b zwykle jest lepszy. 1.5b wymaga mniej pamięci, ale może robić więcej błędów.")
        try:
            available = ollama_models()
            if model in available:
                st.caption("🟢 Lokalna Ollama jest gotowa; wybrany model został pobrany.")
            else:
                st.info(f"Model **{model}** nie został jeszcze pobrany. Uruchom `5_DOINSTALUJ_FISZKI.command` lub w Terminalu: `ollama pull {model}`.")
        except CardsError as exc:
            st.info(str(exc))

        if st.button("✨ Generuj fiszki AI", type="primary", disabled=len(source.strip()) < 35 or len(source) > 16000):
            try:
                with st.spinner("Lokalne AI przygotowuje pytania i odpowiedzi…"):
                    cards = generate_flashcards(source, count, level, model)
                    for key in list(st.session_state):
                        if key.startswith("draft_front_") or key.startswith("draft_back_"):
                            st.session_state.pop(key, None)
                    st.session_state["draft_flashcards"] = cards
                st.success(f"Przygotowano {len(st.session_state['draft_flashcards'])} fiszek. Sprawdź odpowiedzi przed zapisaniem.")
            except CardsError as exc:
                st.error(str(exc))

        draft = st.session_state.get("draft_flashcards", [])
        if draft:
            st.markdown("#### 3. Sprawdź i zapisz fiszki")
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
                    st.session_state["selected_deck"] = saved_id
                    st.success("Zapisano zestaw! Otwórz „Moje zestawy i nauka”, aby go powtarzać.")
                except CardsError as exc:
                    st.error(str(exc))
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

    subjects_tab, reviews_tab, stats_tab = st.tabs(
        ["📚 Przedmioty", "🎯 Powtórki na dziś", "📊 Postępy"]
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
