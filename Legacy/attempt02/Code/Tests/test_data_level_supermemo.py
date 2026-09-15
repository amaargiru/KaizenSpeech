"""Tests of the SM-2 scheduler.

Issue 3.2 regression: the interval must be recurrent - I(1) = 1 day, I(2) = 6 days, I(n) = I(n-1) * EF -
so the intervals really grow instead of staying at '6 * EF' days forever.

Issue 3 regression: a failed answer must reschedule the card at once, otherwise it keeps its old far
future time and the user never gets another try.
"""

from datetime import datetime, timedelta

from data_level import DataOperations as dop
from data_level import datetime_format


def make_repetition(repetition_number=0, easiness_factor=2.5, interval=0, days=0.0):
    """A card as it is stored in repetitions.json, 'days' shifts its time_to_repeat from now"""
    return {'translations': 'hola',
            'time_to_repeat': (datetime.now() + timedelta(days=days)).strftime(datetime_format),
            'easiness_factor': easiness_factor,
            'repetition_number': repetition_number,
            'interval': interval,
            'attempts': []}


def scheduled_in_days(repetition: dict) -> float:
    """How far from now the card is scheduled, in days"""
    delta = datetime.strptime(repetition['time_to_repeat'], datetime_format) - datetime.now()

    return delta.total_seconds() / 86400


class TestSupermemo2Intervals:
    def test_first_success_schedules_one_day(self):
        repetition = dop._supermemo2(make_repetition(repetition_number=0), 1.0)

        assert repetition['repetition_number'] == 1
        assert repetition['interval'] == dop.first_interval_days
        assert dop.first_interval_days - 0.01 <= scheduled_in_days(repetition) <= dop.first_interval_days

    def test_second_success_schedules_six_days(self):
        repetition = dop._supermemo2(make_repetition(repetition_number=1, interval=1), 1.0)

        assert repetition['repetition_number'] == 2
        assert repetition['interval'] == dop.second_interval_days
        assert dop.second_interval_days - 0.01 <= scheduled_in_days(repetition) <= dop.second_interval_days

    def test_later_success_multiplies_the_previous_interval(self):
        # I(n) = I(n-1) * EF, and not '6 * EF' as before: that formula froze the interval at about 16 days
        repetition = dop._supermemo2(make_repetition(repetition_number=2, easiness_factor=2.5, interval=6), 1.0)

        assert repetition['interval'] == 15  # round(6 * 2.5)
        assert 15 - 0.01 <= scheduled_in_days(repetition) <= 15

    def test_a_bigger_easiness_factor_gives_a_bigger_step(self):
        easy_card = dop._supermemo2(make_repetition(repetition_number=2, easiness_factor=2.5, interval=10), 1.0)
        hard_card = dop._supermemo2(make_repetition(repetition_number=2, easiness_factor=1.3, interval=10), 1.0)

        assert easy_card['interval'] == 25  # round(10 * 2.5)
        assert hard_card['interval'] == 13  # round(10 * 1.3)

    def test_intervals_grow_from_answer_to_answer(self):
        repetition = make_repetition()
        intervals: list = []

        for _ in range(6):  # Six perfect answers in a row
            repetition = dop._supermemo2(repetition, 1.0)
            intervals.append(repetition['interval'])

        assert intervals == sorted(set(intervals))  # Every next interval is longer than the previous one
        assert intervals[:4] == [1, 6, 16, 45]
        # The old implementation could not go beyond '6 * EF' days (about 18 days here)
        assert intervals[-1] > 6 * repetition['easiness_factor']

    def test_a_hard_card_still_grows_at_the_easiness_factor_floor(self):
        repetition = make_repetition(repetition_number=2, easiness_factor=dop.min_easiness_factor, interval=6)

        repetition = dop._supermemo2(repetition, dop.level_good)  # A barely passing answer

        assert repetition['interval'] == 8  # round(6 * 1.3): the interval grows even at the floor EF
        assert repetition['easiness_factor'] >= dop.min_easiness_factor


class TestSupermemo2Failure:
    def test_failure_resets_repetition_number(self):
        repetition = dop._supermemo2(make_repetition(repetition_number=3, interval=16), 0.0)

        assert repetition['repetition_number'] == 0

    def test_failed_answer_reschedules_the_card_at_once(self):
        # Issue 3: the card was scheduled 300 days ahead and stayed there after a failure
        repetition = dop._supermemo2(make_repetition(repetition_number=4, interval=90, days=300), 0.0)

        assert repetition['interval'] == dop.failed_interval_days
        assert scheduled_in_days(repetition) <= 1.0  # Due again, so the next session retries it

    def test_success_after_a_failure_starts_the_sequence_over(self):
        repetition = dop._supermemo2(make_repetition(repetition_number=4, interval=90, days=300), 0.0)

        repetition = dop._supermemo2(repetition, 1.0)

        assert repetition['interval'] == dop.first_interval_days  # 1 day, not the old 90 * EF

    def test_failure_lowers_easiness_factor(self):
        repetition = dop._supermemo2(make_repetition(easiness_factor=2.5), 0.0)

        assert repetition['easiness_factor'] < 2.5

    def test_easiness_factor_never_below_the_floor(self):
        repetition = make_repetition(easiness_factor=1.4)

        for _ in range(5):
            repetition = dop._supermemo2(repetition, 0.0)

        assert repetition['easiness_factor'] >= dop.min_easiness_factor


class TestSupermemo2EasinessFactor:
    def test_success_raises_easiness_factor(self):
        repetition = dop._supermemo2(make_repetition(easiness_factor=2.5), 1.0)

        assert repetition['easiness_factor'] == 2.6


class TestSupermemo2PassBoundary:
    """Issue 3.1: level_good is the one boundary between an SM-2 success and an SM-2 failure"""

    def test_level_good_itself_is_a_success(self):
        repetition = dop._supermemo2(make_repetition(), dop.level_good)

        assert repetition['repetition_number'] == 1
        assert repetition['interval'] == dop.first_interval_days

    def test_just_below_level_good_is_a_failure(self):
        repetition = dop._supermemo2(make_repetition(), dop.level_good - 0.001)

        assert repetition['repetition_number'] == 0
        assert repetition['interval'] == dop.failed_interval_days


class TestSupermemo2LegacyRecords:
    """repetitions.json is user data: records saved before the 'interval' key existed must keep working"""

    def make_legacy_repetition(self):
        return {'translations': 'hola',
                'time_to_repeat': datetime.now().strftime(datetime_format),
                'easiness_factor': 2.0,
                'repetition_number': 5,
                'attempts': []}

    def test_record_without_interval_is_accepted(self):
        repetition = dop._supermemo2(self.make_legacy_repetition(), 1.0)

        assert repetition['interval'] == 12  # round(6 * EF): the last value the old formula could give
        assert repetition['repetition_number'] == 6

    def test_recurrence_starts_from_the_next_answer(self):
        repetition = dop._supermemo2(self.make_legacy_repetition(), 1.0)

        repetition = dop._supermemo2(repetition, 1.0)

        assert repetition['interval'] == 25  # round(12 * 2.1), the recurrent step

    def test_record_without_any_sm2_field_is_accepted(self):
        repetition = dop._supermemo2({'translations': 'hola'}, 1.0)

        assert repetition['repetition_number'] == 1
        assert repetition['interval'] == dop.first_interval_days
        assert repetition['easiness_factor'] == dop.default_easiness_factor + 0.1

