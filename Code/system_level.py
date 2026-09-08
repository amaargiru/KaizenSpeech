import contextlib
import json
import os
import shutil
import tempfile
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
    def save_json_to_file(file_path: str, repetitions: dict) -> bool:
        """Save JSON data to file atomically, return True if the data reached the disk

        The document is written to a temporary file in the target directory and then swapped in with
        os.replace(). Ctrl+C, a crash, a full disk or any other failure in the middle of saving leaves
        either the previous complete file or the new complete one, but never a truncated/empty file.
        """
        target_directory: Path = Path(file_path).parent
        temp_file_path: str = ''

        try:
            os.makedirs(target_directory, exist_ok=True)  # The directory may not exist yet

            # The temporary file must live in the target directory: os.replace() is atomic only within one volume
            with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=target_directory,
                                             prefix=Path(file_path).name + '.', suffix='.tmp',
                                             delete=False) as temp_file:
                temp_file_path = temp_file.name
                json.dump(repetitions, temp_file, ensure_ascii=False, indent=2)
                temp_file.flush()
                os.fsync(temp_file.fileno())  # Push the data to the disk before the file becomes visible

            if os.path.exists(file_path):
                with contextlib.suppress(OSError):
                    shutil.copymode(file_path, temp_file_path)  # Keep the permissions of the replaced file

            os.replace(temp_file_path, file_path)
            temp_file_path = ''  # The temporary file has become the data file, there is nothing to clean up

            return True
        except (Exception, KeyboardInterrupt) as e:
            # KeyboardInterrupt is caught as well: an interrupted save must be reported as a failed save
            # instead of a traceback, and the data stays in memory for the next save attempt
            print(f'Cannot save {file_path} file: {repr(e)}')

            return False
        finally:
            if temp_file_path:
                with contextlib.suppress(OSError):
                    os.remove(temp_file_path)  # A failed save must not leave garbage next to the data file
