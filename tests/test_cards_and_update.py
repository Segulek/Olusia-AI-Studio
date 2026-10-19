from __future__ import annotations

from io import BytesIO
import sqlite3
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import tempfile
import zipfile
from unittest.mock import patch

import pytest

from cards import Flashcard, CardsError, cards_as_csv, get_cards, list_decks, save_deck, set_known, delete_deck, generate_flashcards
from updater import UpdateError, read_manifest, apply_update


@contextmanager
def _test_db(path):
    """Commit and CLOSE test connections so Windows can delete temp files."""
    con = sqlite3.connect(path)
    try:
        with con:
            yield con
    finally:
        con.close()


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
        {"front": "What is photosynthesis?", "back": "Production of organic compounds using light energy."},
        {"front": "What is photosynthesis?", "back": "Duplicate"},
        {"front": "What do plants need for photosynthesis?", "back": "Light and water."},
    ]}, ensure_ascii=False)}}
    with patch('cards.urlopen', return_value=BytesIO(json.dumps(response).encode('utf-8'))) as mock_url:
        cards = generate_flashcards('Fotosynteza zachodzi w liściach roślin, wymaga światła oraz wody.', 10, 'Łatwy')
    assert len(cards) == 2
    assert 'photosynthesis' in cards[0].front.lower()
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
        version = apply_update(_pack('2.9.0'), root)
        assert version == '2.9.0'
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
    payload = _pack('2.9.0', content=b'fresh')
    asset = {
        'name': 'Olusia_AI_Studio_UPDATE_v2.9.0.zip',
        'browser_download_url': 'https://github.com/Segulek/Olusia-AI-Studio/releases/download/v2.9.0/Olusia_AI_Studio_UPDATE_v2.9.0.zip',
        'digest': 'sha256:' + hashlib.sha256(payload).hexdigest(),
    }
    result = {'tag_name':'v2.9.0', 'assets':[asset], 'body':'Nowa wersja'}
    with patch('updater.urlopen', return_value=BytesIO(json.dumps(result).encode('utf-8'))):
        latest = check_github_update('Segulek/Olusia-AI-Studio')
    assert latest['version'] == '2.9.0'
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
            'app_id':'olusia-ai-studio','version':'2.9.0',
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
            'app_id':'olusia-ai-studio','version':'2.9.0',
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
            'app_id':'olusia-ai-studio','version':'2.9.0',
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
    if os.name == "nt":
        pytest.skip("Windows NTFS ACLs are not represented by POSIX permission bits.")
    with tempfile.TemporaryDirectory() as tmp:
        db=Path(tmp)/'data'/'fiszki.sqlite3'
        save_deck('Anatomia',[Flashcard('Czym jest komórka?','Podstawowa jednostka.')],db)
        assert os.stat(db).st_mode & 0o077 == 0


def test_missing_release_digest_is_rejected():
    from updater import download_verified_update
    v={'url':'https://github.com/Segulek/Olusia-AI-Studio/releases/download/v2.9.0/Olusia_AI_Studio_UPDATE_v2.9.0.zip',
       'version':'2.9.0', 'sha256':''}
    with patch('updater.urlopen',return_value=BytesIO(_pack('2.9.0'))):
        with pytest.raises(UpdateError):
            download_verified_update(v)



def test_backups_snapshot_roundtrip_and_restore_fsrs_history():
    from updater import (create_data_backup, validate_data_backup,
                         restore_data_backup, list_data_backups)
    from processor import save_bookmark, get_bookmarks
    import sqlite3
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)/'local-data'
        root.mkdir()
        db=root/'fiszki.sqlite3'
        did=save_deck('Anatomia',[Flashcard('Który nerw?', 'Nerw VII')],db)
        cid=get_cards(did,db)[0]['id']
        with _test_db(db) as con:
            con.execute('CREATE TABLE IF NOT EXISTS learning_reviews (id INTEGER PRIMARY KEY, card_id INTEGER, rating INTEGER, reviewed_at TEXT, next_due_at TEXT)')
            con.execute('INSERT INTO learning_reviews VALUES (1,?,?,?,?)',(cid,2,'2026-10-18T10:00:00Z','2026-10-19T10:00:00Z'))
        save_bookmark('a'*64,'Wykład',30,'Nerwy czaszkowe','ważne',root/'nagrania.sqlite3')
        backup=create_data_backup(root)
        assert set(validate_data_backup(backup))=={'fiszki.sqlite3','nagrania.sqlite3'}
        delete_deck(did,db)
        with _test_db(root/'nagrania.sqlite3') as con:
            con.execute('DELETE FROM recording_bookmarks')
        restored=restore_data_backup(backup,root)
        assert restored['safety_backup'] is not None
        assert len(get_cards(did,db))==1
        with _test_db(db) as con:
            assert con.execute('SELECT rating FROM learning_reviews').fetchone()==(2,)
        assert len(get_bookmarks('a'*64,root/'nagrania.sqlite3'))==1
        assert any('before-restore' in item['name'] for item in list_data_backups(root))


def test_daily_backup_is_idempotent_and_preupdate_backup_kept():
    from updater import ensure_daily_backup, save_data_backup, list_data_backups
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)/'local-data'
        save_deck('Anatomia',[Flashcard('B?','C')],root/'fiszki.sqlite3')
        first=ensure_daily_backup(root)
        assert first is not None and first.is_file()
        assert first==ensure_daily_backup(root)
        manual=save_data_backup('manual',root)
        before=save_data_backup('before-update',root)
        assert manual is not None and before is not None
        assert len(list_data_backups(root))==3


def test_data_backup_rejects_tampering_zip_traversal_and_wrong_structure():
    from updater import create_data_backup, validate_data_backup, BackupError
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)
        save_deck('Anatomia',[Flashcard('a?','b')],root/'fiszki.sqlite3')
        good=create_data_backup(root)
        assert 'fiszki.sqlite3' in validate_data_backup(good)
        damaged=BytesIO()
        with zipfile.ZipFile(BytesIO(good)) as original, zipfile.ZipFile(damaged,'w') as target:
            for name in original.namelist():
                contents=original.read(name)
                if name=='databases/fiszki.sqlite3':
                    contents += b'not-correct'
                target.writestr(name,contents)
        with pytest.raises(BackupError):
            validate_data_backup(damaged.getvalue())
        altered=BytesIO()
        with zipfile.ZipFile(BytesIO(good)) as original, zipfile.ZipFile(altered,'w') as target:
            for name in original.namelist():
                target.writestr(name,original.read(name))
            target.writestr('../escaped.sqlite3',b'evil')
        with pytest.raises(BackupError):
            validate_data_backup(altered.getvalue())
        # Old data may not be overwritten with malformed backups.
        assert list_decks(root/'fiszki.sqlite3')[0]['total']==1


def test_restore_refuses_sqlite_triggers_without_touching_current_db():
    from updater import create_data_backup, restore_data_backup, BackupError
    import sqlite3
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)
        db=root/'fiszki.sqlite3'
        saved=save_deck('Nauka',[Flashcard('x','y')],db)
        with _test_db(db) as con:
            con.execute('CREATE TRIGGER bad_trigger AFTER INSERT ON cards BEGIN DELETE FROM decks; END')
        with pytest.raises(BackupError):
            create_data_backup(root)
        with _test_db(db) as con:
            con.execute('DROP TRIGGER bad_trigger')
        good=create_data_backup(root)
        assert restore_data_backup(good,root)['restored']==['fiszki.sqlite3']
        assert get_cards(saved,db)[0]['front']=='x'


def test_backup_must_be_created_before_app_code_update(monkeypatch):
    import updater
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)
        data=root/'private'
        save_deck('Nerwy',[Flashcard('X?','XI')],data/'fiszki.sqlite3')
        installed=root/'program'
        installed.mkdir()
        (installed/'app.py').write_text('old')
        (installed/'processor.py').write_text('old')
        monkeypatch.setattr(updater,'DATA_DIR',data)
        upgraded=apply_update(_pack('2.9.0'),installed,current_version='2.5.0')
        assert upgraded=='2.9.0'
        assert any(p.name.startswith('olusia-before-update-') for p in (data/'backups').iterdir())
        assert get_cards(1,data/'fiszki.sqlite3')[0]['front']=='X?'



def test_automatic_backups_expire_after_seven_calendar_days_but_manual_remain():
    from datetime import datetime, timezone, timedelta
    from updater import _prune_automatic_backups
    now = datetime(2026, 10, 18, 12, 0, tzinfo=timezone.utc)
    with tempfile.TemporaryDirectory() as temp:
        directory = Path(temp)
        for age in range(12):
            day = (now.date() - timedelta(days=age)).isoformat()
            for kind in ('daily', 'before-update', 'before-restore'):
                suffix = '' if kind == 'daily' else '_12-00-00-123456'
                (directory / f'olusia-{kind}-{day}{suffix}.zip').write_bytes(b'archive')
        manual = directory / 'olusia-manual-2026-08-01_12-00-00-123456.zip'
        manual.write_bytes(b'my manual copy')
        unrelated = directory / 'olusia-daily-not-a-date.zip'
        unrelated.write_bytes(b'unrelated')
        _prune_automatic_backups(directory, now)
        assert manual.read_bytes() == b'my manual copy'
        assert unrelated.read_bytes() == b'unrelated'
        for kind in ('daily', 'before-update', 'before-restore'):
            assert len(list(directory.glob(f'olusia-{kind}-2026-10-*.zip'))) == 7
            old = (now.date() - timedelta(days=7)).isoformat()
            assert not list(directory.glob(f'olusia-{kind}-{old}*.zip'))


def test_automatic_backup_keeps_no_more_than_seven_each_kind():
    from datetime import datetime, timezone
    from updater import _prune_automatic_backups
    now = datetime(2026, 10, 18, 12, tzinfo=timezone.utc)
    with tempfile.TemporaryDirectory() as temp:
        directory = Path(temp)
        for i in range(10):
            for kind in ('before-update', 'before-restore'):
                (directory / f'olusia-{kind}-2026-10-18_12-00-{i:02}-123456.zip').write_bytes(b'test')
        _prune_automatic_backups(directory, now)
        assert len(list(directory.glob('olusia-before-update-*.zip'))) == 7
        assert len(list(directory.glob('olusia-before-restore-*.zip'))) == 7
        for kind in ('before-update', 'before-restore'):
            assert (directory / f'olusia-{kind}-2026-10-18_12-00-09-123456.zip').is_file()


def test_backup_zip_deflate_max_compression_and_compact_without_touching_live_db():
    from updater import create_data_backup, validate_data_backup
    import sqlite3
    with tempfile.TemporaryDirectory() as temp:
        directory = Path(temp)
        db = directory / 'fiszki.sqlite3'
        did = save_deck(
            'Anatomia',
            [Flashcard(f'Nerw {i}?', 'Powtarzalna odpowiedź ' * 42) for i in range(100)],
            db,
        )
        delete_deck(did, db)
        save_deck('Fizjologia', [Flashcard('ATP?', 'Energia')], db)
        live_size = db.stat().st_size
        compressed = create_data_backup(directory)
        assert db.stat().st_size == live_size
        with zipfile.ZipFile(BytesIO(compressed)) as archive:
            item = archive.getinfo('databases/fiszki.sqlite3')
            assert item.compress_type == zipfile.ZIP_DEFLATED
            assert item.compress_size < item.file_size
            assert item.file_size < live_size
        assert validate_data_backup(compressed)['fiszki.sqlite3'][:16].startswith(b'SQLite format 3')



def test_generated_flashcards_must_be_english():
    from cards import _require_english_cards
    assert _require_english_cards([Flashcard("What is the axial skeleton?", "Skull, ribs and vertebrae.")])
    with pytest.raises(CardsError):
        _require_english_cards([Flashcard("Jakie kości?", "Skull.")])
    with pytest.raises(CardsError):
        _require_english_cards([Flashcard("What is the sternum?", "Mostek jest kością.")])
    response = {"message":{"content":json.dumps({"cards":[
        {"front":"Jakie elementy?", "back":"Czaszka i żebra"}]})}}
    with patch('cards.urlopen',return_value=BytesIO(json.dumps(response).encode('utf-8'))):
        with pytest.raises(CardsError):
            generate_flashcards("The axial skeleton has a skull and rib cage, forming the central framework.", 10, "Standardowy")


def test_visual_notes_examine_actual_image_and_return_english_flashcards():
    from PIL import Image
    from cards import generate_visual_flashcards
    photo=BytesIO()
    Image.new("RGB", (500,500), "white").save(photo,"PNG")
    calls=[]
    def fake(req, **kwargs):
        payload=json.loads(req.data); calls.append(payload)
        if len(calls)==1:
            assert payload["messages"][1]["images"]
            assert payload["model"]=="qwen3-vl:4b-instruct"
            assert "format" not in payload
            return BytesIO(json.dumps({"message":{"content":
                "- The axial skeleton contains the skull, vertebral column, ribs and sternum.\n"
                "- The appendicular skeleton contains the limbs and girdles.\n"
                "- Bone marrow produces blood cells."},"done_reason":"stop","eval_count":91}).encode())
        assert "format" in payload and not payload["messages"][1].get("images")
        return BytesIO(json.dumps({"message":{"content":json.dumps({"cards":[
          {"front":"What structures form the axial skeleton?",
           "back":"Skull, vertebral column, ribs and sternum."},
          {"front":"Which skeletal division includes the limbs?",
           "back":"The appendicular skeleton."},
          {"front":"Where are blood cells produced?",
           "back":"In bone marrow."}
        ]})}}).encode())
    with patch("cards.urlopen",side_effect=fake):
        result=generate_visual_flashcards([("skeleton.png",photo.getvalue())],10,"Standardowy")
    assert len(result.cards)==3
    assert len(calls)==2
    assert "Readable English medical facts" in result.structure
    assert any("done_reason=stop" in detail for detail in result.diagnostics)


def test_visual_notes_reject_bad_images_and_unsupported_claims():
    from PIL import Image
    from cards import generate_visual_flashcards
    with pytest.raises(CardsError):
        generate_visual_flashcards([("notes.txt",b"not an image")],10,"Standardowy")
    with pytest.raises(CardsError):
        generate_visual_flashcards([("notes.png",b"\\x89PNG\\r\\nfake")],10,"Standardowy")
    with pytest.raises(CardsError):
        generate_visual_flashcards([("notes.jpg",b"0"*13_000_000)],10,"Standardowy")
    with pytest.raises(CardsError):
        generate_visual_flashcards([("note.png",b"x")]*3,10,"Standardowy")


def test_text_generator_prompt_explicit_english_only():
    response={"message":{"content":json.dumps({"cards":[{"front":"What is a rib?", "back":"A bone forming part of the thoracic cage."}]})}}
    with patch("cards.urlopen",return_value=BytesIO(json.dumps(response).encode())) as mocked:
        generate_flashcards("The rib cage forms the bony frame around the thorax and protects the organs.",3,"Standardowy")
    prompt=json.loads(mocked.call_args.args[0].data)["messages"][1]["content"]
    assert "entirely in English" in prompt
    assert "Do not include Polish" in prompt



def test_single_model_handles_text_images_and_oral_answers():
    from cards import STUDIO_MODEL, SUPPORTED_MODELS, VISION_MODELS, oral_feedback
    assert STUDIO_MODEL == "qwen3-vl:4b-instruct"
    assert SUPPORTED_MODELS == VISION_MODELS == (STUDIO_MODEL, "qwen3-vl:4b")
    text_response = {"message": {"content": json.dumps({"cards": [
        {"front":"What forms the axial skeleton?", "back":"Skull, vertebral column, ribs and sternum."}]})}}
    with patch("cards.urlopen", return_value=BytesIO(json.dumps(text_response).encode())) as call:
        generate_flashcards("The axial skeleton includes the skull, vertebral column, ribs and sternum.", 3, "Standardowy")
        assert json.loads(call.call_args.args[0].data)["model"] == STUDIO_MODEL
    oral_response = {"message":{"content":json.dumps({"ocena":"zgodna","komentarz":"Good."})}}
    with patch("cards.urlopen", return_value=BytesIO(json.dumps(oral_response).encode())) as call:
        oral_feedback("What forms the axial skeleton?", "Skull.", "Skull.")
        assert json.loads(call.call_args.args[0].data)["model"] == STUDIO_MODEL


def test_handwritten_page_is_split_into_full_image_and_magnified_halves():
    from PIL import Image
    from cards import generate_visual_flashcards
    photo=BytesIO()
    Image.new("RGB",(1173,1311),"white").save(photo,"PNG")
    seen=[]
    def fake(request, **kwargs):
        payload=json.loads(request.data);seen.append(payload)
        if payload["messages"][1].get("images"):
            return BytesIO(json.dumps({"message":{"content":
              "- The axial skeleton includes the vertebral column and ribs."},
              "done_reason":"stop","eval_count":83}).encode())
        return BytesIO(json.dumps({"message":{"content":json.dumps({"cards":[
            {"front":"Which skeleton includes the vertebral column?",
             "back":"The axial skeleton."}]})}}).encode())
    with patch("cards.urlopen",side_effect=fake):
        result=generate_visual_flashcards(
            [("notes.png",photo.getvalue())],6,"Standardowy",
            supplementary_text="This handwritten note describes the axial skeleton.")
    assert len(result.cards)==1
    assert sum(bool(p["messages"][1].get("images")) for p in seen)==3
    assert all(len(p["messages"][1]["images"])==1
               for p in seen if p["messages"][1].get("images"))
    assert all(p["think"] is False for p in seen)
    assert any("output_tokens=83" in x for x in result.diagnostics)


def test_vision_only_disclaimer_retries_once_and_salvages_partial_notes():
    from PIL import Image
    from cards import generate_visual_flashcards
    photo=BytesIO()
    Image.new("RGB",(1200,1200),"white").save(photo,"PNG")
    seen=[]
    def fake(request, **kwargs):
        data=json.loads(request.data);seen.append(data)
        if len(seen)==1:
            return BytesIO(json.dumps({"message":{"content":""},
                                       "done_reason":"length",
                                       "eval_count":1024}).encode())
        if data["messages"][1].get("images"):
            return BytesIO(json.dumps({"message":{"content":
                 "- Blood cell formation occurs in bone marrow."},
                 "done_reason":"stop"}).encode())
        return BytesIO(json.dumps({"message":{"content":json.dumps({"cards":[
             {"front":"Where are blood cells formed?","back":"In bone marrow."}]})}}).encode())
    with patch("cards.urlopen",side_effect=fake):
        result=generate_visual_flashcards([("note.png",photo.getvalue())],5,"Standardowy")
    assert len(result.cards)==1
    assert any("done_reason=length" in d for d in result.diagnostics)
    assert len(seen)==4


def test_vision_polish_one_card_does_not_block_english_cards():
    from PIL import Image
    from cards import _vision_facts_with_diagnostics
    response={"message":{"content":
        "- Jakie kości są w szkielecie?\n"
        "- The nutrient foramen transmits nutrient vessels."},
        "done_reason":"stop"}
    with patch("cards.urlopen",return_value=BytesIO(json.dumps(response).encode())):
        facts,_=_vision_facts_with_diagnostics("qwen3-vl:4b","test-image")
    assert facts == ["The nutrient foramen transmits nutrient vessels."]


def test_empty_page_does_not_trigger_infinite_attempts_or_invent_cards():
    from PIL import Image
    from cards import generate_visual_flashcards
    photo=BytesIO()
    Image.new("RGB",(500,500),"white").save(photo,"PNG")
    reply={"message":{"content":"NO LEGIBLE FACTS"},"done_reason":"stop"}
    with patch("cards.urlopen",return_value=BytesIO(json.dumps(reply).encode())) as call:
        result=generate_visual_flashcards([("page.png",photo.getvalue())],10,"Standardowy")
    assert call.call_count==1
    assert not result.cards
    assert "No reliable facts" in result.structure
    assert any("readable_facts=0" in d for d in result.diagnostics)


def test_handwritten_notes_photo_size_is_processed_one_image_per_request():
    import base64
    from PIL import Image
    from cards import generate_visual_flashcards
    photo=BytesIO()
    Image.new("RGB",(1121,1584),"white").save(photo,"WEBP")
    seen=[]
    def fake(req, **kwargs):
        data=json.loads(req.data);seen.append(data)
        if data["messages"][1].get("images"):
            assert len(data["messages"][1]["images"])==1
            assert base64.b64decode(data["messages"][1]["images"][0]).startswith(b"\xff\xd8")
            return BytesIO(json.dumps({"message":{"content":
               "- The nucleus is enclosed by a double-membrane nuclear envelope."},
               "done_reason":"stop","eval_count":70}).encode())
        return BytesIO(json.dumps({"message":{"content":json.dumps({"cards":[
            {"front":"What surrounds the nucleus?",
             "back":"A double-membrane nuclear envelope."}]})}}).encode())
    with patch("cards.urlopen",side_effect=fake):
        result=generate_visual_flashcards([("notes.webp",photo.getvalue())],9,"Standardowy")
    assert len(result.cards)==1
    assert 1<=sum(bool(x["messages"][1].get("images")) for x in seen)<=3


def test_local_vision_accepts_code_fenced_json_and_empty_thinking_response():
    from cards import _vision_call, STUDIO_MODEL
    good={"message":{"content":chr(96)*3 + "json\n" + json.dumps({
        "structure":"Nucleus", "uncertainties":[],
        "cards":[{"front":"What is chromatin?", "back":"DNA and protein.",
                  "evidence":"Top of page"}]}) + "\n" + chr(96)*3}}
    with patch("cards.urlopen", return_value=BytesIO(json.dumps(good).encode())) as mocked:
        result = _vision_call(STUDIO_MODEL, ["base64photobytes"], "Use English")
        payload=json.loads(mocked.call_args.args[0].data)
        assert payload["think"] is False
        assert payload["keep_alive"] == "2m"
    assert len(result["cards"]) == 1
    empty={"message":{"content":"", "thinking":"There is an unclear note."}, "done_reason":"stop"}
    with patch("cards.urlopen", return_value=BytesIO(json.dumps(empty).encode())):
        result = _vision_call(STUDIO_MODEL, ["base64photobytes"], "Use English")
    assert result["cards"] == []
    assert "empty" in result["uncertainties"][0].lower()


def test_malformed_whole_page_does_not_discard_readable_zoom_cards():
    from PIL import Image
    from cards import generate_visual_flashcards
    photo=BytesIO()
    Image.new("RGB",(1121,1584),"white").save(photo,"WEBP")
    calls=[]
    def fake(req, **kwargs):
        payload=json.loads(req.data);calls.append(payload)
        if len(calls)==1:
            return BytesIO(b"broken json")
        if payload["messages"][1].get("images"):
            return BytesIO(json.dumps({"message":{"content":
               "- The nucleus contains chromatin made of DNA and proteins."},
               "done_reason":"stop"}).encode())
        return BytesIO(json.dumps({"message":{"content":json.dumps({"cards":[
            {"front":"What is chromatin made of?","back":"DNA and proteins."}]})}}).encode())
    with patch("cards.urlopen",side_effect=fake):
        result=generate_visual_flashcards([("notes.webp",photo.getvalue())],8,"Standardowy")
    assert len(result.cards)==1
    assert any("invalid_model_response" in x for x in result.diagnostics)


def test_vision_partial_photo_does_not_require_model_to_decode_all_handwriting():
    from PIL import Image
    from cards import generate_visual_flashcards
    photo=BytesIO()
    Image.new("RGB",(500,500),"white").save(photo,"PNG")
    response={"message":{"content":"- A gene is a functional segment of DNA."},
              "done_reason":"stop"}
    cards={"message":{"content":json.dumps({"cards":[
        {"front":"What is a gene?", "back":"A functional segment of DNA."}]})}}
    with patch("cards.urlopen",side_effect=[
        BytesIO(json.dumps(response).encode()),
        BytesIO(json.dumps(cards).encode())]):
        result=generate_visual_flashcards([("nucleus.png",photo.getvalue())],5,"Standardowy")
    assert len(result.cards)==1
    assert "gene" in result.cards[0].front


def test_vision_fallback_recovers_cards_using_same_local_model():
    from PIL import Image
    from cards import generate_visual_flashcards, STUDIO_MODEL
    photo=BytesIO()
    Image.new("RGB",(500,500),"white").save(photo,"PNG")
    calls=[]
    def fake(req, **kwargs):
        payload=json.loads(req.data);calls.append(payload)
        assert payload["model"]==STUDIO_MODEL
        if payload["messages"][1].get("images"):
            return BytesIO(json.dumps({"message":{"content":
              "- The nucleus is surrounded by a double-membrane nuclear envelope.\n"
              "- Chromatin is composed of DNA and proteins."},"done_reason":"stop"}).encode())
        return BytesIO(json.dumps({"message":{"content":json.dumps({"cards":[
            {"front":"What surrounds the nucleus?",
             "back":"The double-membrane nuclear envelope."},
            {"front":"What is chromatin composed of?", "back":"DNA and proteins."}
        ]})}}).encode())
    with patch("cards.urlopen",side_effect=fake):
        result=generate_visual_flashcards([("notes.png",photo.getvalue())],9,"Standardowy")
    assert len(result.cards)==2
    assert len(calls)==2
    assert any("produced=2" in d for d in result.diagnostics)
    assert all(payload["model"]==STUDIO_MODEL for payload in calls)


def test_vision_empty_reply_reports_real_reason_not_handwriting_quality():
    from PIL import Image
    from cards import generate_visual_flashcards
    photo=BytesIO()
    Image.new("RGB",(500,500),"white").save(photo,"PNG")
    response={"message":{"content":"","thinking":"analysis only"},
              "done_reason":"length","eval_count":1024}
    with patch("cards.urlopen",return_value=BytesIO(json.dumps(response).encode())):
        result=generate_visual_flashcards([("nucleus.png",photo.getvalue())],8,"Standardowy")
    assert not result.cards
    assert any("done_reason=length" in d for d in result.diagnostics)
    assert any("thinking_chars=13" in d for d in result.diagnostics)


def test_vision_accepts_common_model_aliases_for_flashcards():
    from cards import _interpret_vision_result
    data={"structure":"Nucleus","uncertainties":[],
          "flashcards":[{"question":"What is a gene?",
                         "answer":"A functional segment of DNA.",
                         "evidence":"Pink handwritten line"}]}
    result=_interpret_vision_result(data,5)
    assert len(result.cards)==1
    assert result.cards[0].front=="What is a gene?"



def test_vision_fact_reader_salvages_complete_sentences_after_token_limit():
    from cards import _vision_facts_with_diagnostics, STUDIO_MODEL
    response={"message":{"content":
       "- The nucleus is enclosed by a double-membrane nuclear envelope.\n"
       "- Chromatin is composed of DNA and proteins.\n"
       "- The unfinished line contains"},
       "thinking":"private reasoning","done_reason":"length","eval_count":1024}
    with patch("cards.urlopen",return_value=BytesIO(json.dumps(response).encode())) as call:
        facts,stats=_vision_facts_with_diagnostics(STUDIO_MODEL,"base64-photo",5)
    assert len(facts)==2
    assert stats["done_reason"]=="length"
    assert stats["output_tokens"]=="1024"
    assert "format" not in json.loads(call.call_args.args[0].data)


def test_vision_text_generation_failure_shows_readable_facts():
    from PIL import Image
    from cards import generate_visual_flashcards
    photo=BytesIO()
    Image.new("RGB",(500,500),"white").save(photo,"PNG")
    replies=[
        {"message":{"content":"- The nucleus controls the cell cycle."}},
        {"message":{"content":"invalid JSON"}},
    ]
    with patch("cards.urlopen",side_effect=[BytesIO(json.dumps(v).encode()) for v in replies]):
        result=generate_visual_flashcards([("nucleus.png",photo.getvalue())],5,"Standardowy")
    assert result.cards==[]
    assert "nucleus controls" in result.structure
    assert any("Text-to-cards: failed" in x for x in result.diagnostics)



def test_studio_model_selection_prefers_installed_instruct_without_user_choice():
    from cards import (select_studio_model, STUDIO_MODEL, LEGACY_STUDIO_MODEL,
                       generate_flashcards, oral_feedback, SUPPORTED_MODELS)
    assert select_studio_model([STUDIO_MODEL]) == STUDIO_MODEL
    assert select_studio_model([LEGACY_STUDIO_MODEL]) == LEGACY_STUDIO_MODEL
    assert select_studio_model([LEGACY_STUDIO_MODEL, STUDIO_MODEL]) == STUDIO_MODEL
    assert select_studio_model(["some-other-model:latest"]) is None
    assert SUPPORTED_MODELS == (STUDIO_MODEL, LEGACY_STUDIO_MODEL)

    fake_cards = {"message": {"content": json.dumps({"cards":[
        {"front":"What is chromatin?", "back":"DNA associated with proteins."}
    ]})}}
    with patch("cards.urlopen", return_value=BytesIO(json.dumps(fake_cards).encode())) as call:
        generate_flashcards("Chromatin comprises DNA and proteins inside the eukaryotic nucleus.",
                            3, "Standardowy", model=LEGACY_STUDIO_MODEL)
        assert json.loads(call.call_args.args[0].data)["model"] == LEGACY_STUDIO_MODEL
    with patch("cards.urlopen", return_value=BytesIO(json.dumps(fake_cards).encode())) as call:
        generate_flashcards("Chromatin comprises DNA and proteins inside the eukaryotic nucleus.",
                            3, "Standardowy", model=STUDIO_MODEL)
        assert json.loads(call.call_args.args[0].data)["model"] == STUDIO_MODEL
