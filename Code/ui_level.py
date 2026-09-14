import os

from colorama import Fore, just_fix_windows_console

from data_level import DataOperations as dop

# Enable ANSI escape sequences in the classic Windows console (no-op on other platforms / modern terminals)
just_fix_windows_console()


class UiOperations:
    @staticmethod
    def user_session(native_phrase: str, repetition: dict) -> tuple[float | None, str]:
        """Console user interface

        native_phrase is the task in the user's own language, the answer is expected in the foreign language
        and is compared with repetition['translations'] (the accepted foreign variants).
        """
        user_input: str = input(f'Enter phrase \"{native_phrase}\" in Spanish: ' + os.linesep)

        if user_input.strip().lower() == '/exit':  # User wants to end the session
            return None, ''

        distance, best_translation = dop.find_max_string_similarity(user_input, repetition['translations'])
        diff = dop.find_user_mistakes(user_input, best_translation)

        if distance >= dop.level_excellent:  # Phrases are identical
            print(Fore.GREEN + 'Correct!' + os.linesep)
        elif distance >= dop.level_good:  # The phrases are very similar, maybe a typo
            print(Fore.RESET + 'Almost correct. Right answer is: ', end='')
            UiOperations._print_colored_diff(diff, best_translation)
            print(os.linesep)
        elif distance >= dop.level_mediocre:  # Phrases have a lot in common
            print(Fore.RESET + 'Not bad. Right answer is: ', end='')
            UiOperations._print_colored_diff(diff, best_translation)
            print(os.linesep)
        else:
            print(Fore.RED + 'Wrong. ', end='')  # There are too many errors
            print(Fore.RESET + 'Right answer is: ' + Fore.GREEN + best_translation + os.linesep)

        print(Fore.RESET, end='')

        return distance, best_translation

    @staticmethod
    def _print_colored_diff(correction, reference) -> None:
        """Visualisation of user errors"""
        for i, ch in enumerate(reference):
            if correction[i]:
                print(Fore.GREEN + ch, end='')
            elif ch != ' ':
                print(Fore.RED + ch, end='')  # Just a letter
            else:
                # A space the user did not type is invisible on its own, so it is always shown as an
                # underscore - at the phrase edges as well, where there are no neighbour symbols to
                # emphasise it. Every symbol of the reference must reach the screen: a dropped one made
                # the printed answer shorter than the reference (' ab' was shown as 'ab')
                print(Fore.RED + '_', end='')
