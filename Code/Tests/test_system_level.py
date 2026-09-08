import os

from system_level import FileOperations as fop


class TestReadPhrases:
    def test_simple_phrase(self, tmp_path):
        file = tmp_path / 'phrases.txt'
        file.write_text('hello || hola\n', encoding='utf-8')

        assert fop.read_phrases(str(file)) == {'hello': 'hola'}

    def test_comment_lines_are_ignored(self, tmp_path):
        file = tmp_path / 'phrases.txt'
        file.write_text('# comment || ignored\nhello || hola\n', encoding='utf-8')

        assert fop.read_phrases(str(file)) == {'hello': 'hola'}

    def test_multiple_english_variants(self, tmp_path):
        file = tmp_path / 'phrases.txt'
        file.write_text("I know || Lo se | Ya se | Yo sé\n", encoding='utf-8')

        assert fop.read_phrases(str(file)) == {'I know': ['Lo se', 'Ya se', 'Yo sé']}

    def test_multiple_native_variants(self, tmp_path):
        file = tmp_path / 'phrases.txt'
        file.write_text('Si | Yes || Sí\n', encoding='utf-8')

        assert fop.read_phrases(str(file)) == {'Si': 'Sí', 'Yes': 'Sí'}

    def test_too_many_separators_are_reported(self, tmp_path, capsys):
        file = tmp_path / 'phrases.txt'
        file.write_text('a || b || c\n', encoding='utf-8')

        assert fop.read_phrases(str(file)) == {}
        assert 'Error' in capsys.readouterr().out

    def test_empty_native_part_is_skipped_with_warning(self, tmp_path, capsys):
        file = tmp_path / 'phrases.txt'
        file.write_text('|| hola\nhello || hola\n', encoding='utf-8')

        assert fop.read_phrases(str(file)) == {'hello': 'hola'}
        assert 'Warning' in capsys.readouterr().out

    def test_empty_english_part_is_skipped_with_warning(self, tmp_path, capsys):
        file = tmp_path / 'phrases.txt'
        file.write_text('hello ||\nhello || hola\n', encoding='utf-8')

        assert fop.read_phrases(str(file)) == {'hello': 'hola'}
        assert 'Warning' in capsys.readouterr().out

    def test_empty_variant_among_many_is_dropped(self, tmp_path, capsys):
        file = tmp_path / 'phrases.txt'
        file.write_text('I know || Lo se | | Yo sé\n', encoding='utf-8')

        assert fop.read_phrases(str(file)) == {'I know': ['Lo se', 'Yo sé']}
        assert 'Warning' in capsys.readouterr().out

    def test_single_surviving_variant_is_stored_as_string(self, tmp_path):
        file = tmp_path / 'phrases.txt'
        file.write_text('I know || Lo se |\n', encoding='utf-8')

        assert fop.read_phrases(str(file)) == {'I know': 'Lo se'}


class TestJsonOperations:
    def test_read_missing_file_returns_empty_dict(self, tmp_path):
        assert fop.read_json_from_file(str(tmp_path / 'missing.json')) == {}

    def test_save_and_read_roundtrip(self, tmp_path):
        file = tmp_path / 'data.json'
        data = {'hello': {'translations': 'hola', 'attempts': [['2026.01.01 00:00:00', 1.0]]}}

        assert fop.save_json_to_file(str(file), data) is True

        assert fop.read_json_from_file(str(file)) == data


class TestSaveJsonToFile:
    """Issue 24 regression tests: a save must be atomic and must report its result"""

    def test_save_writes_a_temporary_file_in_the_target_directory_and_swaps_it_in(self, tmp_path, monkeypatch):
        file = tmp_path / 'data.json'
        replacements: list[tuple[str, str]] = []
        real_replace = os.replace

        def spy_replace(src, dst, **kwargs):
            replacements.append((src, dst))
            return real_replace(src, dst, **kwargs)

        monkeypatch.setattr('system_level.os.replace', spy_replace)

        assert fop.save_json_to_file(str(file), {'hello': 'hola'}) is True

        assert len(replacements) == 1
        temp_file_path, destination = replacements[0]
        assert destination == str(file)
        assert temp_file_path != str(file)  # The data is written to a temporary file first
        assert os.path.dirname(temp_file_path) == str(tmp_path)  # ... in the target directory, so the swap is atomic

    def test_missing_parent_directories_are_created(self, tmp_path):
        file = tmp_path / 'nested' / 'user data' / 'data.json'

        assert fop.save_json_to_file(str(file), {'hello': 'hola'}) is True

        assert fop.read_json_from_file(str(file)) == {'hello': 'hola'}

    def test_unicode_is_saved_without_escaping(self, tmp_path):
        file = tmp_path / 'data.json'

        fop.save_json_to_file(str(file), {'¿Qué tal?': 'Yo sé'})

        assert '¿Qué tal?' in file.read_text(encoding='utf-8')

    def test_no_temporary_file_is_left_after_successful_saves(self, tmp_path):
        file = tmp_path / 'data.json'

        fop.save_json_to_file(str(file), {'hello': 'hola'})
        fop.save_json_to_file(str(file), {'hello': 'adiós'})  # Overwrite, as flywheel does after every answer

        assert sorted(path.name for path in tmp_path.iterdir()) == ['data.json']
        assert fop.read_json_from_file(str(file)) == {'hello': 'adiós'}

    def test_failed_save_keeps_the_previous_complete_file(self, tmp_path, monkeypatch, capsys):
        file = tmp_path / 'data.json'
        fop.save_json_to_file(str(file), {'old': 'data'})

        def broken_dump(obj, fp, **kwargs):
            fp.write('{"new": ')  # Half of the new document, as an interrupted write would leave
            raise OSError('No space left on device')

        monkeypatch.setattr('system_level.json.dump', broken_dump)

        assert fop.save_json_to_file(str(file), {'new': 'data'}) is False

        assert 'Cannot save' in capsys.readouterr().out
        assert fop.read_json_from_file(str(file)) == {'old': 'data'}
        assert sorted(path.name for path in tmp_path.iterdir()) == ['data.json']  # No half-written temporary file

    def test_keyboard_interrupt_during_save_is_reported_instead_of_raised(self, tmp_path, monkeypatch):
        file = tmp_path / 'data.json'
        fop.save_json_to_file(str(file), {'old': 'data'})

        def interrupted_replace(src, dst, **kwargs):
            raise KeyboardInterrupt  # Ctrl+C exactly in the middle of saving

        monkeypatch.setattr('system_level.os.replace', interrupted_replace)

        assert fop.save_json_to_file(str(file), {'new': 'data'}) is False  # No traceback escapes from the save

        assert fop.read_json_from_file(str(file)) == {'old': 'data'}
        assert sorted(path.name for path in tmp_path.iterdir()) == ['data.json']

    def test_unserializable_data_does_not_create_a_broken_file(self, tmp_path, capsys):
        file = tmp_path / 'data.json'

        assert fop.save_json_to_file(str(file), {'bad': {1, 2}}) is False  # A set has no JSON representation

        assert 'Cannot save' in capsys.readouterr().out
        assert not file.exists()  # The non-atomic open(..., 'w') left an empty file here
        assert list(tmp_path.iterdir()) == []

    def test_unwritable_path_is_reported_as_a_failed_save(self, tmp_path):
        directory = tmp_path / 'data.json'
        directory.mkdir()  # A directory cannot be replaced by a file

        assert fop.save_json_to_file(str(directory), {'hello': 'hola'}) is False

        assert list(directory.iterdir()) == []


class TestFindOrCreateFile:
    def test_existing_file_in_current_directory(self, tmp_path, monkeypatch):
        (tmp_path / 'phrases.txt').write_text('hello || hola\n', encoding='utf-8')
        monkeypatch.chdir(tmp_path)

        assert fop.find_or_create_file('phrases.txt') == 'phrases.txt'

