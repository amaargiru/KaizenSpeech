from data_level import DataOperations as dop


class TestCompactString:
    def test_compacting_string(self):
        assert dop._compact("It's a normal user input?!.,;'") == 'Its a normal user input'

    def test_diacritics_are_folded(self):
        # Issue 3.1: an answer typed on a keyboard without the Spanish layout is a correct answer, so the
        # accents must not take part in the comparison at all
        assert dop._compact('¿Cómo estás?') == 'Como estas'

    def test_letters_with_a_tilde_are_folded_too(self):
        assert dop._compact('El año ñandú') == 'El ano nandu'

    def test_digits_and_spaces_are_kept(self):
        assert dop._compact('Tengo 2 gatos') == 'Tengo 2 gatos'

    def test_the_case_is_kept_for_the_caller_to_lower(self):
        assert dop._compact('SÍ') == 'SI'

    def test_both_parts_of_a_comparison_are_folded_the_same_way(self):
        assert dop._compact('Yo no se') == dop._compact('Yo no sé')
