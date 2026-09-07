import json
import os
from pathlib import Path


class FileOperations:
    @staticmethod
    def find_or_create_file(filename: str, parents_level_up: int = 2) -> str:
        """Find and open a file if it exists (include the path's logical parents), or create a new empty file"""
        if os.path.exists(filename):  # If file exists in app directory
            return filename

        # If the file doesn't exist in the app directory, start searching in all project directories
        for root, dirs, files in os.walk(Path(__file__).parents[parents_level_up]):
            if filename in files:
                return os.path.join(root, filename)

        # File doesn't exist in all project directories
        with open(filename, 'w'):  # Create file
            pass
        return filename

    @staticmethod
    def read_phrases(file_path: str) -> dict:
        """Read new phrases from file"""
        phrase_mapping: dict = {}

        try:
            with open(file_path, 'r', encoding='utf-8') as phrase_file:
                for string in phrase_file:
                    if string[0] != '#' and '||' in string:  # No comment line and contains native-english separator
                        phrases_pair = list(map(str.strip, string.split('||')))

                        if len(phrases_pair) > 2:
                            print(f'Error. String contains {len(phrases_pair)} "||" separators: {string}. String must contain '
                                  'only one "||" separator between phrases in different languages')
                        else:
                            # Split into separate phrases ('|' delimiter), dropping empty variants with a warning
                            native_phrases = FileOperations._split_into_phrases(phrases_pair[0], 'native', string)
                            english_phrases = FileOperations._split_into_phrases(phrases_pair[1], 'English', string)

                            if not native_phrases or not english_phrases:
                                # A pair with a fully empty part ('|| hola' or 'hello ||') must not get into the dictionary
                                print(f'Warning. Phrase pair with an empty part is skipped: {string.strip()}')
                            else:
                                english_part = english_phrases[0] if len(english_phrases) == 1 else english_phrases

                                for native_phrase in native_phrases:  # Single or multiple native phrases
                                    phrase_mapping[native_phrase] = english_part  # ... and save separate items
        except Exception as e:
            print(f'Cannot open or parse {file_path} file: {repr(e)}')

        return phrase_mapping

    @staticmethod
    def _split_into_phrases(phrase_part: str, language_name: str, source_string: str) -> list:
        """Split a phrase part into separate phrases ('|' delimiter), dropping empty variants"""
        variants: list = list(map(str.strip, phrase_part.split('|')))
        non_empty_variants: list = [variant for variant in variants if variant]

        # Warn only when the part is still usable: a fully empty part is reported by the caller as a skipped pair
        if non_empty_variants and len(non_empty_variants) < len(variants):
            print(f'Warning. Empty {language_name} phrase variant(s) skipped: {source_string.strip()}')

        return non_empty_variants

    @staticmethod
    def read_json_from_file(file_path: str) -> dict:
        """Read JSON data from file"""
        repetitions: dict = {}

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                repetitions = json.load(f)
        except Exception as e:
            print(f'Cannot open or parse {file_path} file: {repr(e)}')

        return repetitions

    @staticmethod
    def save_json_to_file(file_path: str, repetitions: dict):
        """Save JSON data to file"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps(repetitions, ensure_ascii=False, indent=2))
        except Exception as e:
            print(f'Cannot save {file_path} file: {repr(e)}')
