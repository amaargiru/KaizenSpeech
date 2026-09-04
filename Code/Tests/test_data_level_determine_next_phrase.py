from datetime import datetime, timedelta

from data_level import DataOperations as dop
from data_level import datetime_format


def make_entry(attempts=(), days=0.0):
    return {'translations': 'hola',
            'time_to_repeat': (datetime.now() + timedelta(days=days)).strftime(datetime_format),
            'easiness_factor': 2.5,
            'repetition_number': 0,
            'attempts': list(attempts)}


class TestDetermineNextPhrase:
    def test_due_started_phrase_wins(self):
        repetitions = {
            'a': make_entry(attempts=[(datetime.now().strftime(datetime_format), 1.0)], days=-1),
            'b': make_entry(days=-1),
        }

        assert dop.determine_next_phrase(repetitions) == 'a'

    def test_not_started_phrase_with_minimal_time(self):
        repetitions = {
            'a': make_entry(days=1),
            'b': make_entry(days=2),
        }

        assert dop.determine_next_phrase(repetitions) == 'a'

    def test_future_started_phrase_loses_to_continuing(self):
        repetitions = {
            'a': make_entry(attempts=[(datetime.now().strftime(datetime_format), 1.0)], days=2),
            'b': make_entry(days=1),
        }

        assert dop.determine_next_phrase(repetitions) == 'b'


class TestUpdateRepetitions:
    def test_attempt_is_appended(self):
        repetitions = {'hello': make_entry()}

        dop.update_repetitions(repetitions, 'hello', 1.0)

        attempts = repetitions['hello']['attempts']
        assert len(attempts) == 1
        assert attempts[0][1] == 1.0
        assert repetitions['hello']['repetition_number'] == 1

    def test_attempts_list_is_capped(self):
        repetitions = {'hello': make_entry()}

        for _ in range(15):
            dop.update_repetitions(repetitions, 'hello', 0.5)

        assert len(repetitions['hello']['attempts']) == 10


class TestUpdateStatistics:
    def test_first_attempt(self):
        statistics = dop.update_statistics({}, 'What is it?', 'Que es?')

        assert statistics['attempts_num'] == 1
        assert statistics['native_words'] == ['is', 'it', 'what']
        assert statistics['english_words'] == ['es', 'que']

    def test_words_accumulate(self):
        statistics = dop.update_statistics({}, 'What is it?', 'Que es?')
        statistics = dop.update_statistics(statistics, 'Hello there', 'Hola')

        assert statistics['attempts_num'] == 2
        assert set(statistics['native_words']) == {'what', 'is', 'it', 'hello', 'there'}
        assert set(statistics['english_words']) == {'que', 'es', 'hola'}

