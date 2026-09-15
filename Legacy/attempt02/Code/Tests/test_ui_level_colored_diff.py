"""Tests for the colored diff printed by ui_level.

A space the user did not type must stay visible: it is printed as a red underscore, and no symbol of the
reference phrase may be dropped. An edge space had no neighbours to check and was not printed at all, so
' ab' was shown to the user as 'ab'.
"""

import re

from ui_level import UiOperations as uop

ansi_codes = re.compile(r'\x1b\[[0-9;]*m')
red = '\x1b[31m'


def printed_text(correction: list, reference: str, capsys) -> str:
    """Print the diff and return the captured output without color codes"""
    uop._print_colored_diff(correction, reference)

    return ansi_codes.sub('', capsys.readouterr().out)


class TestPrintColoredDiff:
    def test_correct_symbols_are_printed_as_they_are(self, capsys):
        assert printed_text([True, True, True], 'abc', capsys) == 'abc'

    def test_correct_space_is_printed_as_a_space(self, capsys):
        assert printed_text([True, True, True], 'a b', capsys) == 'a b'

    def test_wrong_letter_is_printed_in_red(self, capsys):
        uop._print_colored_diff([True, False, True], 'abc')

        output = capsys.readouterr().out
        assert ansi_codes.sub('', output) == 'abc'
        assert red + 'b' in output  # The wrong symbol is colored, not replaced by anything else

    def test_missed_space_between_correct_symbols_is_an_underscore(self, capsys):
        # The user typed 'tequiero': the sticky characters are correct, the space between them is not
        assert printed_text([True, True, False, True, True, True, True, True, True], 'te quiero', capsys) == 'te_quiero'

    def test_missed_space_at_the_beginning_is_not_dropped(self, capsys):
        assert printed_text([False, True, True], ' ab', capsys) == '_ab'

    def test_missed_space_at_the_end_is_not_dropped(self, capsys):
        assert printed_text([True, True, False], 'ab ', capsys) == 'ab_'

    def test_missed_space_is_an_underscore_next_to_a_wrong_letter_too(self, capsys):
        assert printed_text([False, False, True, True], 'x ab', capsys) == 'x_ab'

    def test_missed_space_is_printed_in_red(self, capsys):
        uop._print_colored_diff([True, False, True], 'a b')

        assert red + '_' in capsys.readouterr().out

    def test_every_reference_symbol_reaches_the_screen(self, capsys):
        # Whatever the correction map is, the printed answer keeps the length of the reference one
        for reference in [' ab', 'ab ', 'a b', ' te quiero ', 'abc']:
            for first_correct_index in range(len(reference) + 1):
                correction = [i >= first_correct_index for i in range(len(reference))]

                assert len(printed_text(correction, reference, capsys)) == len(reference), f'{reference} {correction}'
