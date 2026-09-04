from data_level import DataOperations as dop


class TestFindMaxStringSimilarity:
    def test_exact_match(self):
        distance, best_translation = dop.find_max_string_similarity('te quiero', ['te quiero'])

        assert distance == 1.0
        assert best_translation == 'te quiero'

    def test_best_translation_is_selected(self):
        distance, best_translation = dop.find_max_string_similarity('te quiero', ['la quiero', 'te quiero'])

        assert best_translation == 'te quiero'
        assert distance > 0.9

    def test_single_string_translation(self):
        distance, best_translation = dop.find_max_string_similarity('te quiero', 'te quiero')

        assert distance == 1.0
        assert best_translation == 'te quiero'

    def test_case_and_punctuation_insensitive(self):
        distance, _ = dop.find_max_string_similarity('Te, QUIERO!', ['te quiero'])

        assert distance == 1.0

    def test_completely_different_input(self):
        distance, best_translation = dop.find_max_string_similarity('aaaaaa', ['te quiero'])

        assert distance < dop.level_mediocre
        assert best_translation == 'te quiero'

    def test_return_annotation_is_a_valid_type(self):
        # Issue 6 (already fixed): the annotation must be tuple[float, str],
        # not the invalid tuple (float, str).
        raw_annotation = dop.find_max_string_similarity.__annotations__['return']
        assert raw_annotation == tuple[float, str]

