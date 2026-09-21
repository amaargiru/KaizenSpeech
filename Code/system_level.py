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
            with open(file_path, 'r', encoding='utf-8') as phrf:
                for string in phrf:
                    if string[0] != '#' and '||' in string:  # No comment line and contains native-english separator
                        phrases_pair = list(map(str.strip, string.split('||')))

                        if len(phrases_pair) > 2:
                            print(f'Error. String contains {len(phrases_pair)} "||" separators: {string}. String must contain '
                                  'only one "||" separator between phrases in different languages')
                        else:
                            native_part, english_part = phrases_pair[0], phrases_pair[1]

                            if '|' in english_part:  # More than one English phrase
                                english_part = list(map(str.strip, english_part.split('|')))  # Just split into separate english phrases

                            if '|' in native_part:  # More than one native phrase
                                native_part = list(map(str.strip, native_part.split('|')))  # Split into separate native phrases...
                                for native_phrase in native_part:
                                    phrase_mapping[native_phrase] = english_part  # ... and save separate items

                            else:  # Single native phrase
                                phrase_mapping[native_part] = english_part
        except Exception as e:
            print(f'Cannot open or parse {file_path} file: {repr(e)}')

        return phrase_mapping

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
