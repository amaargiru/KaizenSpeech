from data_level import DataOperations as dop


class TestFindUserMistakes:
    def test_identical_input(self):
        correction = dop.find_user_mistakes('te quiero', 'te quiero')

        assert correction == [True] * len('te quiero')

    def test_typo_detection(self):
        correction = dop.find_user_mistakes('te kiero', 'te quiero')

        assert correction == [True, True, True, False, False, True, True, True, True]

    def test_completely_different_input(self):
        correction = dop.find_user_mistakes('nada', 'te quiero')

        assert correction == [False] * len('te quiero')

