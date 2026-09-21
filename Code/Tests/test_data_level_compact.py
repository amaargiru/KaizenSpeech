from data_level import DataOperations as dop


class TestCompactString:
    def test_compacting_string(self):
        assert dop._compact("It's a normal user input?!.,;'") == 'Its a normal user input'
