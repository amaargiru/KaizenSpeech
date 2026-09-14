"""The verdict on the screen and the verdict of SM-2 must agree (Issue 3.1).

'Correct!' and 'Almost correct' are the successes, 'Not bad' and 'Wrong' are the failures: the interface
and the scheduler read one and the same level_good boundary. An answer typed without diacritics used to be
shown as 'Not bad' and recorded as a failure, although it is a correct answer.
"""

from datetime import datetime

import pytest

from data_level import DataOperations as dop
from data_level import datetime_format
from ui_level import UiOperations as uop


def answer_once(monkeypatch, capsys, user_input: str, translations) -> tuple[str, dict]:
    """Ask the phrase, feed the answer and return the printed text with the SM-2 record after it"""
    monkeypatch.setattr('builtins.input', lambda prompt='': user_input)
    distance, _ = uop.user_session('I love you', {'translations': translations})

    repetition = {'translations': translations,
                  'time_to_repeat': datetime.now().strftime(datetime_format),
                  'easiness_factor': dop.default_easiness_factor,
                  'repetition_number': 0,
                  'interval': 0,
                  'attempts': []}

    return capsys.readouterr().out, dop._supermemo2(repetition, distance)


class TestVerdictMatchesSupermemo:
    @pytest.mark.parametrize('user_input, translations, verdict, is_success', [
        ('te quiero', ['te quiero'], 'Correct!', True),
        ('Te, QUIERO!', 'te quiero', 'Correct!', True),
        ('Y que?', ['Y qué?'], 'Correct!', True),  # No accent is not a mistake
        ('Lo esta', ['Lo es', 'Lo está'], 'Correct!', True),  # The accented variant is the best one
        ('te qiero', ['te quiero'], 'Almost correct', True),  # A single typo is still a known phrase
        ('te odio mucho', ['te quiero mucho'], 'Not bad', False),
        ('Lo esta', ['Lo está bien'], 'Not bad', False),  # A dropped word
        ('nada', ['te quiero'], 'Wrong', False),
        ('', ['te quiero'], 'Wrong', False),
    ])
    def test_verdict_and_supermemo_agree(self, monkeypatch, capsys, user_input, translations, verdict, is_success):
        printed, repetition = answer_once(monkeypatch, capsys, user_input, translations)

        assert verdict in printed
        assert (repetition['repetition_number'] == 1) is is_success
        assert (repetition['interval'] > dop.failed_interval_days) is is_success

    def test_a_successful_answer_pushes_the_card_into_the_future(self, monkeypatch, capsys):
        _, repetition = answer_once(monkeypatch, capsys, 'te quiero', ['te quiero'])

        assert datetime.strptime(repetition['time_to_repeat'], datetime_format) > datetime.now()

    def test_a_failed_answer_keeps_the_card_due(self, monkeypatch, capsys):
        _, repetition = answer_once(monkeypatch, capsys, 'nada', ['te quiero'])

        assert datetime.strptime(repetition['time_to_repeat'], datetime_format) <= datetime.now()
