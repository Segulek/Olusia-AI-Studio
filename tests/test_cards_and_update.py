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
        with sqlite3.connect(db) as con:
            con.execute('CREATE TABLE IF NOT EXISTS learning_reviews (id INTEGER PRIMARY KEY, card_id INTEGER, rating INTEGER, reviewed_at TEXT, next_due_at TEXT)')
            con.execute('INSERT INTO learning_reviews VALUES (1,?,?,?,?)',(cid,2,'2026-10-18T10:00:00Z','2026-10-19T10:00:00Z'))
        save_bookmark('a'*64,'Wykład',30,'Nerwy czaszkowe','ważne',root/'nagrania.sqlite3')
        backup=create_data_backup(root)
        assert set(validate_data_backup(backup))=={'fiszki.sqlite3','nagrania.sqlite3'}
        delete_deck(did,db)
        with sqlite3.connect(root/'nagrania.sqlite3') as con:
            con.execute('DELETE FROM recording_bookmarks')
        restored=restore_data_backup(backup,root)
        assert restored['safety_backup'] is not None
        assert len(get_cards(did,db))==1
        with sqlite3.connect(db) as con:
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
        with sqlite3.connect(db) as con:
            con.execute('CREATE TRIGGER bad_trigger AFTER INSERT ON cards BEGIN DELETE FROM decks; END')
        with pytest.raises(BackupError):
            create_data_backup(root)
        with sqlite3.connect(db) as con:
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
        upgraded=apply_update(_pack('2.6.0'),installed,current_version='2.5.0')
        assert upgraded=='2.6.0'
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
