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


class TestJsonOperations:
    def test_read_missing_file_returns_empty_dict(self, tmp_path):
        assert fop.read_json_from_file(str(tmp_path / 'missing.json')) == {}

    def test_save_and_read_roundtrip(self, tmp_path):
        file = tmp_path / 'data.json'
        data = {'hello': {'translations': 'hola', 'attempts': [['2026.01.01 00:00:00', 1.0]]}}

        fop.save_json_to_file(str(file), data)

        assert fop.read_json_from_file(str(file)) == data


class TestFindOrCreateFile:
    def test_existing_file_in_current_directory(self, tmp_path, monkeypatch):
        (tmp_path / 'phrases.txt').write_text('hello || hola\n', encoding='utf-8')
        monkeypatch.chdir(tmp_path)

        assert fop.find_or_create_file('phrases.txt') == 'phrases.txt'

