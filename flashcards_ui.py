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
