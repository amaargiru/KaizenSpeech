from data_level import DataOperations as dop


def make_entry(translations='hola'):
    return {'translations': translations,
            'time_to_repeat': '2026.01.01 00:00:00',
            'easiness_factor': 2.5,
            'repetition_number': 0,
            'attempts': []}


class TestDataAssessment:
    def test_both_structures_empty(self):
        can_work, message = dop.data_assessment({}, {})
        assert can_work is False
        assert message == 'Both structures have zero length'

    def test_only_phrases_present(self):
        can_work, _ = dop.data_assessment({'hello': 'hola'}, {})
        assert can_work is True

    def test_only_repetitions_present(self):
        can_work, _ = dop.data_assessment({}, {'hello': make_entry()})
        assert can_work is True


class TestMerge:
    def test_merge_new_phrase(self):
        repetitions: dict = {}

        is_merged, message = dop.merge({'hello': 'hola'}, repetitions)

        assert is_merged is True
        assert message == 'Added 1 new phrases'
        assert repetitions['hello']['translations'] == 'hola'
        assert repetitions['hello']['easiness_factor'] == 2.5
        assert repetitions['hello']['repetition_number'] == 0
        assert repetitions['hello']['attempts'] == []

    def test_merge_no_new_phrases(self):
        repetitions = {'hello': make_entry()}

        is_merged, message = dop.merge({'hello': 'hola'}, repetitions)

        assert is_merged is False
        assert message == 'No new phrases'

    def test_merge_corrects_translations(self):
        repetitions = {'hello': make_entry()}

        is_merged, _ = dop.merge({'hello': 'hola amigo'}, repetitions)

        assert is_merged is True
        assert repetitions['hello']['translations'] == 'hola amigo'

    def test_merge_empty_phrases(self):
        is_merged, message = dop.merge({}, {'hello': make_entry()})

        assert (is_merged, message) == (False, 'No new phrases')

