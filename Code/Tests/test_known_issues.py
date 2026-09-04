"""Tests for known but not yet fixed bugs.

Each test is marked with ``xfail(strict=True)`` and references the issue
number from the review. While the bug exists, the test does not pass and is
reported as ``xfailed``. When the bug is fixed, the test will XPASS and fail
the suite - a reminder to remove the obsolete marker.
"""

import os
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from data_level import DataOperations as dop
from data_level import datetime_format
from system_level import FileOperations as fop
from ui_level import UiOperations as uop


def make_repetition(time_to_repeat: str) -> dict:
    return {'translations': 'hola',
            'time_to_repeat': time_to_repeat,
            'easiness_factor': 2.5,
            'repetition_number': 0,
            'attempts': []}


@pytest.mark.xfail(strict=True, reason="Issue 2: tabs are deleted by the symbol filter before replace('\\t', ' ') can do its job")
def test_cleanup_user_input_replaces_tab_with_space():
    assert dop._cleanup_user_input('a\tb') == 'a b'


@pytest.mark.xfail(strict=True, reason='Issue 3: SM-2 does not reschedule a phrase after a failed answer')
def test_failed_answer_reschedules_repetition():
    far_future = (datetime.now() + timedelta(days=300)).strftime(datetime_format)
    updated = dop._supermemo2(make_repetition(far_future), 0.0)
    new_time = datetime.strptime(updated['time_to_repeat'], datetime_format)
    assert new_time <= datetime.now() + timedelta(days=1)


@pytest.mark.xfail(strict=True, reason="Issue 7: merge() counts updated phrases as 'added'")
def test_merge_does_not_count_updates_as_added():
    repetitions = {'hello': make_repetition('2026.01.01 00:00:00')}
    _, message = dop.merge({'hello': 'hola amigo', 'bye': 'adios'}, repetitions)
    assert 'Added 2' not in message


@pytest.mark.xfail(strict=True, reason='Issue 9: determine_next_phrase raises ValueError on a corrupted repetitions record')
def test_corrupted_record_does_not_crash_next_phrase_selection():
    repetitions = {
        'good': make_repetition((datetime.now() - timedelta(days=1)).strftime(datetime_format)),
        'bad': {'attempts': [], 'time_to_repeat': 'not-a-date'},
    }
    assert dop.determine_next_phrase(repetitions) == 'good'


@pytest.mark.skipif(os.name != 'nt', reason='Issue 10 is specific to os.linesep on Windows')
@pytest.mark.xfail(strict=True, reason='Issue 10: ui_level prints os.linesep, doubling new lines on Windows')
def test_user_session_output_has_no_doubled_newlines(monkeypatch, capsys):
    monkeypatch.setattr('builtins.input', lambda prompt='': 'te kiero')
    uop.user_session('I love you', {'translations': ['te quiero']})
    assert '\r\n\n' not in capsys.readouterr().out


@pytest.mark.xfail(strict=True, reason='Issue 16: read_phrases does not recognize comment lines with leading whitespace')
def test_indented_comment_line_is_ignored(tmp_path):
    file = tmp_path / 'phrases.txt'
    file.write_text('   # comment || ignored\nhello || hola\n', encoding='utf-8')
    assert fop.read_phrases(str(file)) == {'hello': 'hola'}


@pytest.mark.xfail(strict=True, reason='Issue 21: find_user_mistakes never flags wrong punctuation')
def test_missing_punctuation_is_flagged():
    correction = dop.find_user_mistakes('tequiero', 'te,quiero')
    assert correction[2] is False  # The comma the user did not type


@pytest.mark.xfail(strict=True, reason='Issue 1: flywheel.py saves statistics by file name instead of the found path')
def test_flywheel_saves_statistics_by_path():
    source = (Path(__file__).parents[1] / 'flywheel.py').read_text(encoding='utf-8')
    assert 'save_json_to_file(user_statistics_file_path' in source
