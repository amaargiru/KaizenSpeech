from data_level import DataOperations as dop


class TestCleanupUserInput:
    def test_cleanup_user_input_normal_string(self):
        user_input = "It's a normal user input. Allowed characters: !?!.,;'"
        assert dop._cleanup_user_input(user_input) == user_input

    def test_cleanup_user_input_limit_string_size(self):
        assert len(dop._cleanup_user_input('a' * 400)) == 200

    def test_cleanup_user_input_strip(self):
        assert dop._cleanup_user_input('  a  ') == 'a'

    def test_cleanup_user_input_delete_unwanted_symbols(self):
        assert dop._cleanup_user_input(r'/|\\=(%$#😀 abc 😀#$%)=/|\\') == 'abc'

    def test_cleanup_user_input_replace_tabs_with_spaces(self):
        assert dop._cleanup_user_input('\t abc \t') == 'abc'

    def test_cleanup_user_input_replace_multiple_spaces_with_one(self):
        assert dop._cleanup_user_input('a    b    c') == 'a b c'

    def test_cleanup_user_input_replace_multiple_commas_with_one(self):
        assert dop._cleanup_user_input('a,,, b,, c,,,, d') == 'a, b, c, d'
