import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from re import Pattern
from typing import List

import jellyfish

datetime_format: str = '%Y.%m.%d %H:%M:%S'
max_attempts_len: int = 10  # Limit for 'Attempts' list


class DataOperations:
    level_excellent: float = 0.99
    level_good: float = 0.97
    level_mediocre: float = 0.65

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
        """Merge new phrases into general dictionary"""
        no_added_message: str = 'No new phrases'
        new_phrases_num: int = 0

        if len(phrases) == 0:
            return False, no_added_message

        for native_part, english_part in phrases.items():
            if native_part not in repetitions:
                repetitions[native_part] = {
                    'translations': english_part,
                    'time_to_repeat': datetime.now().strftime(datetime_format),  # Recommendation to check this phrase right now
                    'easiness_factor': 2.5,  # How easy the card is (and determines how quickly the inter-repetition interval grows)
                    'repetition_number': 0,  # Number of times the card has been successfully recalled in a row
                    'attempts': []}  # In use flag + reserve field in case of transition from supermemo-2 to supermemo-18
                new_phrases_num += 1

            if repetitions[native_part]['translations'] != english_part:  # Correct translations
                repetitions[native_part]['translations'] = english_part
                new_phrases_num += 1

        return (False, no_added_message) if new_phrases_num == 0 else (True, f'Added {new_phrases_num} new phrases')

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
    def update_statistics(statistics: dict, current_phrase: str, best_translation: str):
        """Update user statistics"""

        # Update attempts num
        if 'attempts_num' in statistics:
            statistics['attempts_num'] += 1
        else:
            statistics['attempts_num'] = 1

        # Update native words set
        current_native_words_set = set(DataOperations._compact(current_phrase.lower()).split())

        if 'native_words' in statistics:
            full_native_words_set = set(statistics['native_words'])
            full_native_words_set.update(current_native_words_set)
            statistics['native_words'] = list(full_native_words_set)
        else:
            statistics['native_words'] = list(current_native_words_set)

        statistics['native_words'].sort()

        # Update english words set
        current_english_words_set = set(DataOperations._compact(best_translation.lower()).split())

        if 'english_words' in statistics:
            full_english_words_set = set(statistics['english_words'])
            full_english_words_set.update(current_english_words_set)
            statistics['english_words'] = list(full_english_words_set)
        else:
            statistics['english_words'] = list(current_english_words_set)

        statistics['english_words'].sort()

        return statistics

    @staticmethod
    def find_max_string_similarity(user_input: str, translations: str | List[str]) -> tuple[float, str]:
        """Compares user_input against each string in translations"""
        max_distance: float = 0

        if isinstance(translations, str):
            translations = [translations]
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
        """Restrict use of all special characters and allow letters and numbers only"""
        return ''.join(ch for ch in input_string if ch.isalnum() or ch == ' ')

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
        max_string_size: int = 200
        comma_pattern: Pattern[str] = re.compile(r'(,){2,}')
        white_list: str = " ?!.,:;'¿¡"  # Allow symbols (+ alpha-numeric)

        user_input = user_input[:max_string_size]
        user_input = user_input.strip()  # Remove leading and trailing whitespaces
        user_input = ''.join(ch for ch in user_input if ch.isalnum() or ch in white_list)  # Delete all unwanted symbols
        user_input = ' '.join(user_input.split())  # Replace multiple spaces with one
        user_input = re.sub(comma_pattern, ',', user_input)  # Replace multiple commas with one

        return user_input

    @staticmethod
    # https://en.wikipedia.org/wiki/SuperMemo
    def _supermemo2(repetition: dict, user_result: float) -> dict:
        """Update next attempt time based on user result"""
        if user_result >= DataOperations.level_good:  # Correct response
            if repetition['repetition_number'] == 0:  # + 1 day
                repetition['time_to_repeat'] = (datetime.now() + timedelta(days=1)).strftime(datetime_format)
            elif repetition['repetition_number'] == 1:  # + 6 days
                repetition['time_to_repeat'] = (datetime.now() + timedelta(days=6)).strftime(datetime_format)
            else:  # + (6 * easiness_factor) days
                repetition['time_to_repeat'] = (datetime.now()
                                                + timedelta(days=6 * repetition['easiness_factor'])).strftime(datetime_format)
            repetition['repetition_number'] += 1
        else:  # Incorrect response
            repetition['repetition_number'] = 0

        repetition['easiness_factor'] = repetition['easiness_factor'] + (
                0.1 - (5 - 5 * user_result) * (0.08 + (5 - 5 * user_result) * 0.02))
        repetition['easiness_factor'] = max(repetition['easiness_factor'], 1.3)

        return repetition
