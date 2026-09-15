import re
import sys
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from re import Pattern
from typing import List

import jellyfish

datetime_format: str = '%Y.%m.%d %H:%M:%S'
max_attempts_len: int = 10  # Limit for 'Attempts' list
max_phrase_len: int = 300  # Limit for a phrase length: a longer phrase cannot be answered by the user


class DataOperations:
    # The bands of the answer quality. The metric is the Jaro similarity of the 'compacted' phrases, so the
    # thresholds are measured on the real phrase file instead of being guessed (Issue 3.1). With the
    # diacritics folded by _compact(), on 1892 real cards: a correct answer scores 1.0 (including the same
    # answer typed without accents, which used to score as low as 0.67 and to be counted as a failure),
    # a single typo scores 0.97 at the median, while a dropped or a replaced word scores 0.83 and 0.79.
    # level_good is both the 'Almost correct' / 'Not bad' boundary of the interface and the success /
    # failure boundary of SM-2, so the verdict the user reads and the verdict written to the data file
    # can never disagree.
    level_excellent: float = 0.99  # 'Correct!': the answer is identical to one of the accepted variants
    level_good: float = 0.95  # 'Almost correct' and an SM-2 success: the phrase is right, at most a typo
    level_mediocre: float = 0.65  # 'Not bad' and an SM-2 failure: only a part of the phrase is right

    # SM-2 constants (https://en.wikipedia.org/wiki/SuperMemo)
    default_easiness_factor: float = 2.5  # EF of a new card
    min_easiness_factor: float = 1.3  # EF floor: below it the intervals would stop growing
    first_interval_days: float = 1  # I(1)
    second_interval_days: float = 6  # I(2)
    failed_interval_days: float = 0  # A failed card becomes due again at once

    @staticmethod
    def data_assessment(phrases: dict, repetitions: dict) -> tuple[bool, str]:
        """Check data before work"""
        if not isinstance(phrases, dict):
            print('Cannot parse phrase file')
            sys.exit()

        if not isinstance(repetitions, dict):
            print('Cannot parse repetitions file')
            sys.exit()

        if len(phrases) == 0 and len(repetitions) == 0:
            return False, 'Both structures have zero length'
        else:
            return True, 'No data assessment errors'

    @staticmethod
    def merge(phrases: dict, repetitions: dict) -> tuple[bool, str]:
        """Synchronize repetitions with the phrases file: add new, update changed, remove deleted

        Both structures are keyed by the native phrase (the task in the user's own language); the value of
        phrases is the foreign phrase or the list of its variants (the expected answer), stored in repetitions
        under the 'translations' key.
        """
        no_changes_message: str = 'No new phrases'

        if len(phrases) == 0:
            # An empty phrase file is treated as a loading error rather than as
            # 'all phrases were deleted': without this guard one bad start
            # (e.g. from a wrong working directory) would erase all repetitions.
            return False, no_changes_message

        added_phrases_num: int = 0
        updated_phrases_num: int = 0
        removed_phrases_num: int = 0

        for native_part, foreign_part in phrases.items():
            if native_part not in repetitions:
                repetitions[native_part] = {
                    'translations': foreign_part,
                    'time_to_repeat': datetime.now().strftime(datetime_format),  # Recommendation to check this phrase right now
                    'easiness_factor': DataOperations.default_easiness_factor,  # How easy the card is (and determines how quickly the inter-repetition interval grows)
                    'repetition_number': 0,  # Number of times the card has been successfully recalled in a row
                    'interval': 0,  # The last inter-repetition interval in days, I(n-1) of the recurrent SM-2 formula
                    'attempts': []}  # In use flag + reserve field in case of transition from supermemo-2 to supermemo-18
                added_phrases_num += 1

            if repetitions[native_part]['translations'] != foreign_part:  # Correct translations
                repetitions[native_part]['translations'] = foreign_part
                updated_phrases_num += 1

        # Remove phrases that were deleted from the phrases file
        for native_part in list(repetitions):
            if native_part not in phrases:
                del repetitions[native_part]
                removed_phrases_num += 1

        changes: list[str] = []
        if added_phrases_num:
            changes.append(f'Added {added_phrases_num} new phrases')
        if updated_phrases_num:
            changes.append(f'Updated {updated_phrases_num} phrases')
        if removed_phrases_num:
            changes.append(f'Removed {removed_phrases_num} phrases')

        return (False, no_changes_message) if len(changes) == 0 else (True, ', '.join(changes))

    @staticmethod
    def determine_next_phrase(repetitions: dict) -> str:
        """Set phrase for next user session"""
        recommended_started_phrase: str = ''
        recommended_continuing_phrase: str = ''

        min_time_to_repeat_started_phrases: datetime = datetime.max
        min_time_to_repeat_not_started_phrases: datetime = datetime.max

        for current_phrase, value in repetitions.items():
            if len(value['attempts']) > 0:
                current_time_to_repeat_started_phrases = datetime.strptime(value['time_to_repeat'], datetime_format)
                if current_time_to_repeat_started_phrases < min_time_to_repeat_started_phrases:
                    recommended_started_phrase = current_phrase
                    min_time_to_repeat_started_phrases = current_time_to_repeat_started_phrases
            else:
                current_time_to_repeat_not_started_phrases = datetime.strptime(value['time_to_repeat'], datetime_format)
                if current_time_to_repeat_not_started_phrases < min_time_to_repeat_not_started_phrases:
                    recommended_continuing_phrase = current_phrase
                    min_time_to_repeat_not_started_phrases = current_time_to_repeat_not_started_phrases

        if min_time_to_repeat_started_phrases <= datetime.now() or recommended_continuing_phrase == '':
            return recommended_started_phrase
        else:
            return recommended_continuing_phrase

    @staticmethod
    def update_repetitions(repetitions: dict, current_phrase: str, user_result: float):
        """Update list of user repetitions"""
        # Update attempt list
        if len(repetitions[current_phrase]['attempts']) == max_attempts_len:
            repetitions[current_phrase]['attempts'].pop(0)
        repetitions[current_phrase]['attempts'].append((datetime.now().strftime(datetime_format), user_result))

        # Update whole repetition data
        repetitions[current_phrase] = DataOperations._supermemo2(repetitions[current_phrase], user_result)

    @staticmethod
    def update_statistics(statistics: dict, native_phrase: str, best_translation: str):
        """Update user statistics

        The words are stored by the role of the phrase they come from, not by a language name (Issue 5.1):
        'native_words' holds the words of the task in the user's own language, 'foreign_words' holds the words
        of the expected answer in the language being learned. The answer used to be stored under
        'english_words' even though it is Spanish.
        """

        # Update attempts num
        if 'attempts_num' in statistics:
            statistics['attempts_num'] += 1
        else:
            statistics['attempts_num'] = 1

        # Update native words set
        current_native_words_set = set(DataOperations._compact(native_phrase.lower()).split())

        if 'native_words' in statistics:
            full_native_words_set = set(statistics['native_words'])
            full_native_words_set.update(current_native_words_set)
            statistics['native_words'] = list(full_native_words_set)
        else:
            statistics['native_words'] = list(current_native_words_set)

        statistics['native_words'].sort()

        # Update foreign words set
        current_foreign_words_set = set(DataOperations._compact(best_translation.lower()).split())

        if 'foreign_words' in statistics:
            full_foreign_words_set = set(statistics['foreign_words'])
            full_foreign_words_set.update(current_foreign_words_set)
            statistics['foreign_words'] = list(full_foreign_words_set)
        else:
            statistics['foreign_words'] = list(current_foreign_words_set)

        statistics['foreign_words'].sort()

        return statistics

    @staticmethod
    def find_max_string_similarity(user_input: str, translations: str | List[str]) -> tuple[float, str]:
        """Compares user_input against each string in translations"""
        max_distance: float = 0

        if isinstance(translations, str):
            translations = [translations]

        # Guard against empty / blank translations: an empty list would crash on translations[0] below
        translations = [translation for translation in translations if translation.strip()]
        if not translations:
            return max_distance, ''

        best_translation: str = translations[0]

        # Cleanup and 'compactify' user input ('I   don't know!!!😀' -> 'i dont know')
        user_input = DataOperations._compact(DataOperations._cleanup_user_input(user_input).lower())

        # 'Compactify' translations
        translations = [(t, DataOperations._compact(t.lower())) for t in translations]

        for translation, compact_translation in translations:
            current_distance = jellyfish.jaro_similarity(user_input, compact_translation)

            if current_distance > max_distance:
                max_distance = current_distance
                best_translation = translation

        return max_distance, best_translation

    @staticmethod
    def _compact(input_string: str) -> str:
        """Restrict use of all special characters and allow letters and numbers only

        The diacritics are folded as well (Issue 3.1): 'Yo no sé' typed on a keyboard without a Spanish
        layout as 'Yo no se' is a correct answer, but Jaro counted every accent as a full mismatch and such
        an answer scored below level_good - 39% of the real phrase file was marked 'Not bad' and recorded as
        an SM-2 failure. Folding is applied to both the user input and the accepted variants, so the phrases
        stay compared in one and the same form.
        """
        decomposed_string: str = unicodedata.normalize('NFD', input_string)
        without_diacritics: str = ''.join(ch for ch in decomposed_string if not unicodedata.combining(ch))

        return ''.join(ch for ch in without_diacritics if ch.isalnum() or ch == ' ')

    @staticmethod
    def find_user_mistakes(user_input: str, reference: str) -> list:
        """Dig for user errors and typos"""

        @dataclass
        class ComplexPhrase:
            phrase_without_punctuation: List[str]
            transformation_matrix: List[int]

        user_input = DataOperations._cleanup_user_input(user_input).lower()
        reference = reference.lower()
        correction_map: list[bool] = [True] * len(reference)

        complex_reference: ComplexPhrase = ComplexPhrase(phrase_without_punctuation=[], transformation_matrix=[])

        # 'Minify' reference phrase and remember transformation shifts
        for i, ch in enumerate(reference):
            if ch.isalnum() or ch == ' ':
                complex_reference.phrase_without_punctuation.append(ch)
                complex_reference.transformation_matrix.append(i)

        minified_reference: str = ''.join(complex_reference.phrase_without_punctuation)
        corr_map: list[bool] = [False] * len(minified_reference)

        # Compare cleaned user input and 'minified' reference
        seq = SequenceMatcher(lambda ch: not (ch.isalnum() or ch == ' '), user_input, minified_reference)
        blocks = seq.get_matching_blocks()
        blocks = blocks[:-1]  # Last element is a dummy

        for _, i, n in blocks:
            if n >= 3:  # Don't show to the user too short groups of correct letters, perhaps he entered a completely different phrase
                for x in range(i, i + n):
                    corr_map[x] = True

        # 'Unminify' reference phrase and restore transformation shifts
        for i, corr in enumerate(corr_map):
            if not corr:
                correction_map[complex_reference.transformation_matrix[i]] = False

        return correction_map

    @staticmethod
    def _cleanup_user_input(user_input: str) -> str:
        """Cleanup user input"""
        comma_pattern: Pattern[str] = re.compile(r'(,){2,}')
        white_list: str = " ?!.,:;'¿¡"  # Allow symbols (+ alpha-numeric)

        # The input is cut at the longest phrase the user can be asked for (Issue 28): a phrase within this
        # limit stays answerable, longer phrases are rejected with a warning when phrases.txt is read
        user_input = user_input[:max_phrase_len]
        user_input = user_input.strip()  # Remove leading and trailing whitespaces
        user_input = ''.join(ch for ch in user_input if ch.isalnum() or ch in white_list)  # Delete all unwanted symbols
        user_input = ' '.join(user_input.split())  # Replace multiple spaces with one
        user_input = re.sub(comma_pattern, ',', user_input)  # Replace multiple commas with one

        return user_input

    @staticmethod
    # https://en.wikipedia.org/wiki/SuperMemo
    def _supermemo2(repetition: dict, user_result: float) -> dict:
        """Update next attempt time based on user result

        The intervals are recurrent (Issue 3.2): I(1) = 1 day, I(2) = 6 days, I(n) = I(n-1) * EF, so with
        EF = 2.5 they grow 1 -> 6 -> 15 -> 38 -> 95 days. Every step after the second one used to be
        '6 * EF' days, which stopped the growth at about 16 days forever, contradicting the promise of the
        'easiness_factor' comment that the interval grows. I(n-1) is kept in the record under the
        'interval' key; a record saved by an older version has no such key, so its sequence is continued
        from the last value the old formula could have produced and the data file stays compatible.

        A failed answer makes the card due again at once (Issue 3): only 'repetition_number' was reset
        before, so the card kept its old - possibly far future - 'time_to_repeat' and the user had no chance
        to retry it, while SM-2 requires repeating a failed item from the beginning.
        """
        easiness_factor: float = repetition.get('easiness_factor', DataOperations.default_easiness_factor)
        repetition_number: int = repetition.get('repetition_number', 0)

        if user_result >= DataOperations.level_good:  # Correct response
            previous_interval: float = float(repetition.get('interval') or 0)  # I(n-1)

            if repetition_number <= 0:
                interval_days: float = DataOperations.first_interval_days  # I(1) = 1 day
            elif repetition_number == 1:
                interval_days = DataOperations.second_interval_days  # I(2) = 6 days
            elif previous_interval > 0:
                interval_days = round(previous_interval * easiness_factor)  # I(n) = I(n-1) * EF
            else:
                # A record of an older version has no stored interval: continue its sequence, the
                # recurrence starts from the next successful answer
                interval_days = round(DataOperations.second_interval_days * easiness_factor)

            repetition['repetition_number'] = repetition_number + 1
        else:  # Incorrect response: the card starts over and is asked for again in this very session
            interval_days = DataOperations.failed_interval_days
            repetition['repetition_number'] = 0

        repetition['interval'] = interval_days
        repetition['time_to_repeat'] = (datetime.now() + timedelta(days=interval_days)).strftime(datetime_format)

        repetition['easiness_factor'] = easiness_factor + (
                0.1 - (5 - 5 * user_result) * (0.08 + (5 - 5 * user_result) * 0.02))
        repetition['easiness_factor'] = max(repetition['easiness_factor'], DataOperations.min_easiness_factor)

        return repetition
