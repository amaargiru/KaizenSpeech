from data_level import DataOperations as dop, max_phrase_len


class TestCleanupUserInput:
    def test_cleanup_user_input_normal_string(self):
        user_input = "It's a normal user input. Allowed characters: !?!.,;'"
        assert dop._cleanup_user_input(user_input) == user_input

    def test_cleanup_user_input_limit_string_size(self):
        assert len(dop._cleanup_user_input('a' * (max_phrase_len + 100))) == max_phrase_len

    def test_cleanup_user_input_does_not_cut_a_phrase_at_the_limit(self):
        # Issue 28 regression: a phrase of exactly the limit length must survive the cleanup untouched,
        # otherwise the user cannot give a full answer to it
        assert len(dop._cleanup_user_input('a' * max_phrase_len)) == max_phrase_len
        assert dop._cleanup_user_input('a' * max_phrase_len) == 'a' * max_phrase_len

    def test_cleanup_user_input_limit_is_300(self):
        assert max_phrase_len == 300

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
