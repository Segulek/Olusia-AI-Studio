from __future__ import annotations

from io import BytesIO
import hashlib
import json
from pathlib import Path
import tempfile
import zipfile
from unittest.mock import patch

import pytest

from cards import Flashcard, CardsError, cards_as_csv, get_cards, list_decks, save_deck, set_known, delete_deck, generate_flashcards
from updater import UpdateError, read_manifest, apply_update


def test_save_study_export_delete():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "userdata" / "fiszki.sqlite3"
        did = save_deck("Historia Polski", [Flashcard('Kiedy?', '966'), Flashcard('Co oznacza "test"?', 'wynik; dwa')], db)
        assert list_decks(db)[0]["total"] == 2
        cards = get_cards(did, db)
        assert 'Co oznacza "test"?' in cards[1]['front']
        set_known(cards[0]['id'], True, db)
        assert list_decks(db)[0]["known"] == 1
        export = cards_as_csv(get_cards(did, db)).decode('utf-8-sig')
        assert '"wynik; dwa"' in export
        delete_deck(did, db)
        assert not list_decks(db)


def test_local_generation_json():
    response = {"message": {"content": json.dumps({"cards": [
        {"front": "Co to jest fotosynteza?", "back": "Proces wytwarzania substancji organicznych."},
        {"front": "Co to jest fotosynteza?", "back": "Duplikat"},
        {"front": "Co jest potrzebne roślinom?", "back": "Światło i woda."},
    ]}, ensure_ascii=False)}}
    with patch('cards.urlopen', return_value=BytesIO(json.dumps(response).encode('utf-8'))) as mock_url:
        cards = generate_flashcards('Fotosynteza zachodzi w liściach roślin, wymaga światła oraz wody.', 10, 'Łatwy')
    assert len(cards) == 2
    assert 'fotosynteza' in cards[0].front.lower()
    assert mock_url.call_args.args[0].full_url == 'http://127.0.0.1:11434/api/chat'


def _pack(version: str, content: bytes = b'updated'):
    meta = {"app_id": "olusia-ai-studio", "version": version,
            "files": {"app.py": hashlib.sha256(content).hexdigest()}}
    out = BytesIO()
    with zipfile.ZipFile(out, 'w') as z:
        z.writestr('manifest.json', json.dumps(meta))
        z.writestr('payload/app.py', content)
    return out.getvalue()


def test_updates_preserve_venvs_and_reject_older():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / 'app.py').write_text('old')
        (root / 'processor.py').write_text('core')
        (root / '.venv-core').mkdir()
        (root / '.venv-core' / 'secret').write_text('keep')
        version = apply_update(_pack('2.6.0'), root)
        assert version == '2.6.0'
        assert (root / 'app.py').read_bytes() == b'updated'
        assert (root / '.venv-core' / 'secret').read_text() == 'keep'
        with pytest.raises(UpdateError):
            apply_update(_pack('1.9.0'), root)
        assert (root / 'app.py').read_bytes() == b'updated'


def test_update_rejects_tampered_files_and_extra_files():
    damaged = BytesIO()
    data = _pack('2.4.0')
    with zipfile.ZipFile(BytesIO(data)) as original, zipfile.ZipFile(damaged, 'w') as out:
        for name in original.namelist():
            content = original.read(name)
            if name == 'payload/app.py':
                content += b'bad'
            out.writestr(name, content)
    with pytest.raises(UpdateError):
        read_manifest(damaged.getvalue())


def test_repo_settings_remain_outside_app_folder():
    from updater import set_repo, configured_repo, UpdateError
    with tempfile.TemporaryDirectory() as temp:
        where = Path(temp) / 'appdata' / 'updates.json'
        set_repo('Segulek/Olusia-AI-Studio', where)
        assert configured_repo(where) == 'Segulek/Olusia-AI-Studio'
        with pytest.raises(UpdateError):
            set_repo('https://evil.test/anything', where)
        assert configured_repo(where) == 'Segulek/Olusia-AI-Studio'


def test_check_and_download_release_mocked():
    from updater import check_github_update, download_verified_update, UpdateError
    from unittest.mock import patch
    payload = _pack('2.6.0', content=b'fresh')
    asset = {
        'name': 'Olusia_AI_Studio_UPDATE_v2.6.0.zip',
        'browser_download_url': 'https://github.com/Segulek/Olusia-AI-Studio/releases/download/v2.6.0/Olusia_AI_Studio_UPDATE_v2.6.0.zip',
        'digest': 'sha256:' + hashlib.sha256(payload).hexdigest(),
    }
    result = {'tag_name':'v2.6.0', 'assets':[asset], 'body':'Nowa wersja'}
    with patch('updater.urlopen', return_value=BytesIO(json.dumps(result).encode('utf-8'))):
        latest = check_github_update('Segulek/Olusia-AI-Studio')
    assert latest['version'] == '2.6.0'
    with patch('updater.urlopen', return_value=BytesIO(payload)):
        assert download_verified_update(latest) == payload
    latest['sha256'] = 'sha256:' + '0'*64
    with patch('updater.urlopen', return_value=BytesIO(payload)):
        with pytest.raises(UpdateError):
            download_verified_update(latest)



def test_learning_plus_preserves_old_cards_and_filters_subjects():
    from cards import (assign_medical_subject, due_learning_cards, learning_summary,
                       medical_decks)
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / 'fiszki.sqlite3'
        anatomy = save_deck("Anatomia", [Flashcard("Nerw?", "VII")], db)
        histology = save_deck("Histologia", [Flashcard("Komórka?", "Neuron")], db)
        set_known(get_cards(anatomy, db)[0]["id"], True, db)
        assert len(due_learning_cards(db_path=db)) == 2
        assign_medical_subject(anatomy, "Anatomia", db)
        assign_medical_subject(histology, "Histologia", db)
        assert len(due_learning_cards("Anatomia", db)) == 1
        assert {row["subject"] for row in medical_decks(db)} == {"Anatomia", "Histologia"}
        assert learning_summary("Anatomia", db)["due"] == 1
        # Existing old 'Umiem' data remains intact.
        assert get_cards(anatomy, db)[0]["known"] == 1
        delete_deck(anatomy, db)
        assert learning_summary("Anatomia", db)["total"] == 0


def test_real_fsrs_when_installed():
    pytest.importorskip("fsrs")
    from datetime import datetime, timezone
    from cards import due_learning_cards, review_learning_card, learning_summary
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "fiszki.sqlite3"
        did = save_deck("Biochemia", [Flashcard("ATP?", "Trifosforan adenozyny")], db)
        card_id = get_cards(did, db)[0]["id"]
        now = datetime(2026, 10, 18, 12, 0, tzinfo=timezone.utc)
        due = review_learning_card(card_id, 3, db, now)
        assert datetime.fromisoformat(due) > now
        assert due_learning_cards(db_path=db, now=now) == []
        assert learning_summary(db_path=db, now=now)["reviews_week"] == 1



def test_oral_feedback_from_local_ollama_and_no_automatic_rating():
    from cards import oral_feedback
    good = {'message':{'content':json.dumps({'ocena':'częściowa','komentarz':'Brakuje fragmentu o unerwieniu.'})}}
    with patch('cards.urlopen', return_value=BytesIO(json.dumps(good).encode('utf-8'))) as transport:
        result = oral_feedback('Jak unerwione?', 'Nerw twarzowy', 'Nerw')
    assert result['ocena']=='częściowa'
    request=transport.call_args.args[0]
    assert request.full_url.startswith('http://127.0.0.1:11434/')
    assert 'WZORZEC' in request.data.decode()
    with pytest.raises(CardsError):
        oral_feedback('Pytanie','Wzorzec','  ')



def test_update_rejects_duplicate_members_and_symlinks():
    raw = BytesIO()
    with zipfile.ZipFile(raw, 'w') as archive:
        data=b'test'
        archive.writestr('manifest.json', json.dumps({
            'app_id':'olusia-ai-studio','version':'2.6.0',
            'files':{'app.py':hashlib.sha256(data).hexdigest()}
        }))
        archive.writestr('payload/app.py',data)
        archive.writestr('payload/app.py',data)
    with pytest.raises(UpdateError):
        read_manifest(raw.getvalue())

    raw=BytesIO()
    with zipfile.ZipFile(raw,'w') as archive:
        data=b'bad'
        archive.writestr('manifest.json', json.dumps({
            'app_id':'olusia-ai-studio','version':'2.6.0',
            'files':{'app.py':hashlib.sha256(data).hexdigest()}
        }))
        info=zipfile.ZipInfo('payload/app.py')
        info.create_system=3
        info.external_attr=(0o120777 << 16)
        archive.writestr(info,data)
    with pytest.raises(UpdateError):
        read_manifest(raw.getvalue())


def test_update_rejects_directory_symlink_escape():
    data=b'[server]\naddress="127.0.0.1"\n'
    packed=BytesIO()
    with zipfile.ZipFile(packed,'w') as archive:
        archive.writestr('manifest.json',json.dumps({
            'app_id':'olusia-ai-studio','version':'2.6.0',
            'files':{'.streamlit/config.toml':hashlib.sha256(data).hexdigest()}
        }))
        archive.writestr('payload/.streamlit/config.toml',data)
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)/'install'
        root.mkdir()
        (root/'app.py').write_text('original')
        (root/'processor.py').write_text('original')
        outside=Path(tmp)/'outside'
        outside.mkdir()
        (root/'.streamlit').symlink_to(outside,target_is_directory=True)
        with pytest.raises(UpdateError):
            apply_update(packed.getvalue(),root)
        assert not (outside/'config.toml').exists()


def test_update_publisher_is_pinned_and_csv_formula_safe():
    from updater import validate_repo
    assert validate_repo('Segulek/Olusia-AI-Studio')=='Segulek/Olusia-AI-Studio'
    with pytest.raises(UpdateError):
        validate_repo('untrusted/Olusia-AI-Studio')
    exported=cards_as_csv([{'front':'=1+1','back':'@formula'}]).decode('utf-8-sig')
    assert "'=1+1" in exported and "'@formula" in exported


def test_database_file_permissions_are_private():
    import os
    with tempfile.TemporaryDirectory() as tmp:
        db=Path(tmp)/'data'/'fiszki.sqlite3'
        save_deck('Anatomia',[Flashcard('Czym jest komórka?','Podstawowa jednostka.')],db)
        assert os.stat(db).st_mode & 0o077 == 0


def test_missing_release_digest_is_rejected():
    from updater import download_verified_update
    v={'url':'https://github.com/Segulek/Olusia-AI-Studio/releases/download/v2.6.0/Olusia_AI_Studio_UPDATE_v2.6.0.zip',
       'version':'2.6.0', 'sha256':''}
    with patch('updater.urlopen',return_value=BytesIO(_pack('2.6.0'))):
        with pytest.raises(UpdateError):
            download_verified_update(v)
