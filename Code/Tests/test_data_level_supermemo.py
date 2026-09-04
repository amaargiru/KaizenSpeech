from datetime import datetime, timedelta

from data_level import DataOperations as dop
from data_level import datetime_format


def make_repetition(repetition_number=0, easiness_factor=2.5):
    return {'translations': 'hola',
            'time_to_repeat': datetime.now().strftime(datetime_format),
            'easiness_factor': easiness_factor,
            'repetition_number': repetition_number,
            'attempts': []}


class TestSupermemo2:
    def test_first_success_schedules_one_day(self):
        repetition = dop._supermemo2(make_repetition(repetition_number=0), 1.0)

        assert repetition['repetition_number'] == 1
        delta = datetime.strptime(repetition['time_to_repeat'], datetime_format) - datetime.now()
        assert timedelta(days=1) - timedelta(minutes=5) <= delta <= timedelta(days=1)

    def test_second_success_schedules_six_days(self):
        repetition = dop._supermemo2(make_repetition(repetition_number=1), 1.0)

        assert repetition['repetition_number'] == 2
        delta = datetime.strptime(repetition['time_to_repeat'], datetime_format) - datetime.now()
        assert timedelta(days=6) - timedelta(minutes=5) <= delta <= timedelta(days=6)

    def test_later_success_scales_with_easiness_factor(self):
        repetition = dop._supermemo2(make_repetition(repetition_number=5, easiness_factor=2.0), 1.0)

        delta = datetime.strptime(repetition['time_to_repeat'], datetime_format) - datetime.now()
        assert timedelta(days=12) - timedelta(minutes=5) <= delta <= timedelta(days=12)

    def test_success_raises_easiness_factor(self):
        repetition = dop._supermemo2(make_repetition(easiness_factor=2.5), 1.0)

        assert repetition['easiness_factor'] == 2.6

    def test_failure_resets_repetition_number(self):
        repetition = dop._supermemo2(make_repetition(repetition_number=3), 0.0)

        assert repetition['repetition_number'] == 0

    def test_failure_lowers_easiness_factor(self):
        repetition = dop._supermemo2(make_repetition(easiness_factor=2.5), 0.0)

        assert repetition['easiness_factor'] < 2.5

    def test_easiness_factor_never_below_1_3(self):
        repetition = make_repetition(easiness_factor=1.4)

        for _ in range(5):
            repetition = dop._supermemo2(repetition, 0.0)

        assert repetition['easiness_factor'] >= 1.3

