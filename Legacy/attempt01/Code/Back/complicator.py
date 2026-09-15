from dataclasses import dataclass
from typing import List


@dataclass
class ComplexUserInput:
    user_input_without_punctuation: List[str]
    transformation_matrix: List[List[int]]


class Complicator:
    @staticmethod
    def complicate_user_input(user_input_cleaned: str) -> ComplexUserInput:
        complex_user_input: ComplexUserInput = ComplexUserInput(user_input_without_punctuation=[], transformation_matrix=[])
        j: int = 0

        for i, ch in enumerate(user_input_cleaned):
            if ch.isalnum() or ch == " " or ch == "'" or ch == ",":
                complex_user_input.user_input_without_punctuation.append(ch)
                complex_user_input.transformation_matrix.append([i, j])
                j += 1

        return complex_user_input
