from difflib import SequenceMatcher
from typing import List

import jellyfish


class Comparator:
    @staticmethod
    def find_nearest_reference_index(user_input_without_punctuation_lower, references_lower: List[str]):
        max_ratio: float = 0
        max_index: int = 0

        for i, reference in enumerate(references_lower):
            user_string = "".join(user_input_without_punctuation_lower)
            reference_string = references_lower[i]

            current_ratio = jellyfish.jaro_distance(user_string, reference_string)

            if current_ratio > max_ratio:
                max_ratio = current_ratio
                max_index = i

        return max_index, max_ratio

    @staticmethod
    def find_matching_blocks(user_input_without_punctuation_lower, references_lower: List[str], reference_index):
        seq = SequenceMatcher(None, "".join(user_input_without_punctuation_lower), references_lower[reference_index])
        a = seq.get_matching_blocks()
        a = a[:-1]  # Last element is a dummy

        answer_length = len(references_lower[reference_index])
        b: list = [False] * answer_length

        for _, i, n in a:
            if n >= 3:  # Не показываем пользователю слишком короткие группы правильных букв, возможно, он ввел совсем другое слово
                for x in range(i, i + n):
                    b[x] = True

        return b
