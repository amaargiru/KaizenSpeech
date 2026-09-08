"""End-to-end tests of the flywheel script.

Issue 24 regression tests: every save must be atomic and a failed save must stop the session with an
explicit error instead of being silently ignored.

Issue 28 regression tests: a long phrase must be answerable, and a phrase longer than the input limit
must never reach the session.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from data_level import max_phrase_len

flywheel_path: Path = Path(__file__).parents[1] / 'flywheel.py'
working_directory_content: list[str] = ['phrases.txt', 'repetitions.json', 'user_statistics.txt']
default_phrases_content: str = 'hello || hola\nI know || Lo sé\n'
# 224 symbols: longer than the old 200 symbol input limit, within the current one (the proof case of Issue 28)
long_phrase: str = ('el abuelo siempre cuenta historias interesantes sobre la vida en el pueblo ' * 3).strip()


def prepare_working_directory(tmp_path: Path, phrases_content: str = default_phrases_content) -> Path:
    """Create all three data files in the working directory of the session

    find_or_create_file() walks the parent repositories when a file is missing (Issue 22), so an absent
    file would point the session at the real data of the developer instead of the temporary directory.
    """
    (tmp_path / 'phrases.txt').write_text(phrases_content, encoding='utf-8')
    (tmp_path / 'repetitions.json').write_text('', encoding='utf-8')
    (tmp_path / 'user_statistics.txt').write_text('', encoding='utf-8')

    return tmp_path


def run_flywheel(working_directory: Path, user_input: str = '') -> subprocess.CompletedProcess:
    """Run a session with the answers fed through stdin"""
    # A redirected stdout is not UTF-8 by default on Windows (Issue 46), which would break the output
    environment: dict = dict(os.environ, PYTHONIOENCODING='utf-8')

    return subprocess.run([sys.executable, str(flywheel_path)], cwd=working_directory, input=user_input,
                          capture_output=True, text=True, encoding='utf-8', env=environment, timeout=60)


def make_repetitions_file_unwritable(working_directory: Path):
    """Replace the data file with a directory: a directory cannot be replaced by a file, so saves fail"""
    (working_directory / 'repetitions.json').unlink()
    (working_directory / 'repetitions.json').mkdir()


def read_json(file: Path) -> dict:
    return json.loads(file.read_text(encoding='utf-8'))


class TestFlywheelSavesData:
    def test_exit_command_finishes_the_session_with_saved_data(self, tmp_path):
        working_directory = prepare_working_directory(tmp_path)

        result = run_flywheel(working_directory, '/exit\n')

        assert result.returncode == 0, result.stdout + result.stderr
        assert 'Session finished. All data saved.' in result.stdout
        assert set(read_json(working_directory / 'repetitions.json')) == {'hello', 'I know'}

    def test_answer_is_saved_to_repetitions_and_statistics(self, tmp_path):
        working_directory = prepare_working_directory(tmp_path)

        result = run_flywheel(working_directory, 'hola\n/exit\n')

        assert result.returncode == 0, result.stdout + result.stderr

        repetitions = read_json(working_directory / 'repetitions.json')
        statistics = read_json(working_directory / 'user_statistics.txt')
        answered_phrases = [phrase for phrase, record in repetitions.items() if record['attempts']]

        assert len(answered_phrases) == 1
        assert repetitions[answered_phrases[0]]['repetition_number'] == 1
        assert statistics['attempts_num'] == 1

    def test_session_leaves_no_temporary_files(self, tmp_path):
        working_directory = prepare_working_directory(tmp_path)

        run_flywheel(working_directory, 'hola\n/exit\n')

        assert sorted(path.name for path in working_directory.iterdir()) == working_directory_content


class TestFlywheelReportsSaveErrors:
    def test_unwritable_file_stops_the_session_with_an_error(self, tmp_path):
        working_directory = prepare_working_directory(tmp_path)
        make_repetitions_file_unwritable(working_directory)

        result = run_flywheel(working_directory)  # No input: the session must not even ask for an answer

        assert result.returncode == 1, result.stdout + result.stderr
        assert 'Cannot save repetitions.json file:' in result.stdout
        assert 'repetitions.json WAS NOT saved' in result.stdout
        assert 'Enter phrase' not in result.stdout  # The answers of a session with a dead file would be lost
        assert 'Traceback' not in result.stderr

    def test_failed_save_leaves_no_temporary_files(self, tmp_path):
        working_directory = prepare_working_directory(tmp_path)
        make_repetitions_file_unwritable(working_directory)

        run_flywheel(working_directory)

        assert sorted(path.name for path in working_directory.iterdir()) == working_directory_content
        assert list((working_directory / 'repetitions.json').iterdir()) == []

    def test_other_data_is_still_saved_when_one_file_fails(self, tmp_path):
        working_directory = prepare_working_directory(tmp_path)
        make_repetitions_file_unwritable(working_directory)

        run_flywheel(working_directory)

        assert read_json(working_directory / 'user_statistics.txt') == {}  # Nothing was answered, but the file is valid


class TestFlywheelLongPhrase:
    """Issue 28 regression: a long phrase is answerable, an over-limit phrase never reaches the session"""

    def test_long_phrase_can_be_answered(self, tmp_path):
        assert len(long_phrase) == 224  # Longer than the old 200 symbol limit, which made it unanswerable
        working_directory = prepare_working_directory(tmp_path, f'hello || {long_phrase}\n')

        result = run_flywheel(working_directory, f'{long_phrase}\n/exit\n')

        assert result.returncode == 0, result.stdout + result.stderr
        assert 'Correct!' in result.stdout  # The full answer is accepted instead of the old 'Not bad'

        record = read_json(working_directory / 'repetitions.json')['hello']
        assert record['translations'] == long_phrase
        assert len(record['attempts']) == 1
        assert record['attempts'][0][1] == 1.0  # The full answer was scored as an exact match
        assert record['repetition_number'] == 1  # SM-2 counted the answer as a success, not as a failure

    def test_too_long_phrase_is_not_loaded_into_the_session(self, tmp_path):
        too_long_phrase = 'a' * (max_phrase_len + 1)
        working_directory = prepare_working_directory(tmp_path, f'hello || {too_long_phrase}\n')

        result = run_flywheel(working_directory, '/exit\n')

        assert 'Warning. Too long English phrase variant' in result.stdout
        assert 'Both structures have zero length' in result.stdout  # The unanswerable phrase is not a card
        assert 'Enter phrase' not in result.stdout  # ... so the user is never asked for it
        assert (working_directory / 'repetitions.json').read_text(encoding='utf-8') == ''  # No card was created

    def test_long_phrase_leaves_no_temporary_files(self, tmp_path):
        working_directory = prepare_working_directory(tmp_path, f'hello || {long_phrase}\n')

        run_flywheel(working_directory, f'{long_phrase}\n/exit\n')

        assert sorted(path.name for path in working_directory.iterdir()) == working_directory_content
