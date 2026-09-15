import re

MAX_STRING_SIZE: int = 200
comma_pattern = re.compile(r"(,){2,}")
white_list: str = " ?!.,:;'"


class Refiner:
    @staticmethod
    def refine_user_input(user_input: str) -> str:
        user_input = user_input[:MAX_STRING_SIZE]  # Length limit
        user_input = user_input.strip()  # Remove leading and trailing whitespace
        user_input = ''.join(ch for ch in user_input if ch.isalnum() or ch in white_list)  # Delete all unwanted symbols
        user_input = user_input.replace("\t", " ")  # Replace tabs with spaces
        user_input = " ".join(user_input.split())  # Replace multiple spaces with one
        user_input = re.sub(comma_pattern, ",", user_input)  # Replace multiple commas with one

        return user_input
