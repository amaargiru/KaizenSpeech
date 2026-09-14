import pytest

from data_level import DataOperations as dop, max_phrase_len


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

    def test_empty_translation_list_is_safe(self):
        # Guard: an empty list used to crash with IndexError on translations[0]
        distance, best_translation = dop.find_max_string_similarity('hola', [])

        assert distance == 0.0
        assert best_translation == ''

    def test_blank_translations_are_ignored(self):
        distance, best_translation = dop.find_max_string_similarity('hola', ['   ', ''])

        assert distance == 0.0
        assert best_translation == ''

    def test_return_annotation_is_a_valid_type(self):
        # Issue 6 (already fixed): the annotation must be tuple[float, str],
        # not the invalid tuple (float, str).
        raw_annotation = dop.find_max_string_similarity.__annotations__['return']
        assert raw_annotation == tuple[float, str]


class TestLongPhraseIsAnswerable:
    """Issue 28 regression: a long phrase must not become a permanently failed card.

    The user input used to be cut at 200 symbols while the reference phrase was unlimited, so an ideal
    answer to a 224 symbol phrase scored 0.9633 - below level_good - and SM-2 counted a perfect answer
    as a failure. The limit is now max_phrase_len, and longer phrases are rejected when phrases.txt is read.
    """

    # 224 symbols: longer than the old 200 limit, within the new one (the proof case of Issue 28)
    long_reference: str = ('el abuelo siempre cuenta historias interesantes sobre la vida en el pueblo ' * 3).strip()

    def test_reference_length_matches_the_issue_proof(self):
        assert len(self.long_reference) == 224
        assert len(self.long_reference) > 200  # Would have been cut by the old limit
        assert len(self.long_reference) <= max_phrase_len

    def test_input_is_not_cut_for_a_long_phrase(self):
        assert dop._cleanup_user_input(self.long_reference) == self.long_reference

    def test_ideal_answer_to_a_long_phrase_is_excellent(self):
        distance, best_translation = dop.find_max_string_similarity(self.long_reference, [self.long_reference])

        assert distance == 1.0
        assert distance >= dop.level_excellent  # 'Correct!' instead of the old 'Not bad' + SM-2 failure
        assert best_translation == self.long_reference

    def test_ideal_answer_to_a_phrase_at_the_limit_is_excellent(self):
        reference_at_the_limit = 'a' * max_phrase_len

        distance, best_translation = dop.find_max_string_similarity(reference_at_the_limit, [reference_at_the_limit])

        assert distance == 1.0
        assert best_translation == reference_at_the_limit


class TestThresholdsAreCalibratedForJaro:
    """Issue 3.1 regression: level_good must fit the Jaro metric it is applied to.

    The thresholds used to be set for a stricter scale, so on the real 1892 card file 39% of the cards gave
    'Not bad' and an SM-2 failure for a grammatically correct answer typed without accents, and a single
    typo ('te qiero' -> 0.9630) was a failure too. Measured after the fix: a correct answer scores 1.0 with
    the accents folded, a single typo scores 0.97 at the median, a dropped word scores 0.83 and a replaced
    word scores 0.79 - so level_good = 0.95 separates a known phrase from an unknown one.
    """

    def test_thresholds_are_ordered(self):
        assert 0 < dop.level_mediocre < dop.level_good < dop.level_excellent <= 1.0

    @pytest.mark.parametrize('user_input, translation', [
        ('Y que?', 'Y qué?'),
        ('Yo no se', 'Yo no sé'),
        ('Para que?', 'Para qué?'),
        ('Lo esta', 'Lo está'),
        ('si', 'sí'),
        ('Como estas hoy amigo mio', 'Cómo estás hoy amigo mío'),
    ])
    def test_answer_without_accents_is_excellent(self, user_input, translation):
        distance, best_translation = dop.find_max_string_similarity(user_input, [translation])

        assert distance == 1.0  # An accent is not a mistake, the answer is identical after the folding
        assert distance >= dop.level_excellent  # 'Correct!' instead of the old 'Not bad' + SM-2 failure
        assert best_translation == translation

    def test_the_accented_variant_is_chosen_as_the_best_one(self):
        # The old scoring preferred 'Lo es' over 'Lo está' for the answer 'Lo esta' and showed it as the
        # right answer, so the user was told that a correct answer was wrong
        distance, best_translation = dop.find_max_string_similarity('Lo esta', ['Lo es', 'Lo está'])

        assert best_translation == 'Lo está'
        assert distance == 1.0

    def test_single_typo_is_almost_correct_and_passes(self):
        distance, _ = dop.find_max_string_similarity('te qiero', ['te quiero'])

        assert dop.level_good <= distance < dop.level_excellent  # 'Almost correct', and an SM-2 success

    def test_replaced_word_is_a_failure(self):
        distance, _ = dop.find_max_string_similarity('te odio mucho', ['te quiero mucho'])

        assert dop.level_mediocre <= distance < dop.level_good  # 'Not bad', and an SM-2 failure

    def test_dropped_word_is_a_failure(self):
        distance, _ = dop.find_max_string_similarity('Lo esta', ['Lo está bien'])

        assert dop.level_mediocre <= distance < dop.level_good

    def test_another_phrase_is_wrong(self):
        distance, _ = dop.find_max_string_similarity('nada', ['te quiero'])

        assert distance < dop.level_mediocre  # 'Wrong', and an SM-2 failure

