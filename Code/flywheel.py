#!/usr/bin/python3.12

import sys

from data_level import DataOperations as dop
from system_level import FileOperations as fop
from ui_level import UiOperations as uop

phrases_file_name: str = 'phrases.txt'
repetitions_file_name: str = 'repetitions.json'
statistics_file_name: str = 'user_statistics.txt'

if __name__ == '__main__':
    phrases_file_path = fop.find_or_create_file(phrases_file_name)
    repetitions_file_path = fop.find_or_create_file(repetitions_file_name)
    user_statistics_file_path = fop.find_or_create_file(statistics_file_name)

    phrases: dict = fop.read_phrases(phrases_file_path)
    repetitions: dict = fop.read_json_from_file(repetitions_file_path)
    can_work, assessment_error_message = dop.data_assessment(phrases, repetitions)

    statistics: dict = fop.read_json_from_file(user_statistics_file_path)

    if can_work:
        is_merged, merge_message = dop.merge(phrases, repetitions)
        print(merge_message)

        save_failed: bool = False

        if is_merged and not fop.save_json_to_file(repetitions_file_path, repetitions):
            save_failed = True  # The file is not writable: every answer of the session would be lost

        if not save_failed:
            print('Type "/exit" or press Ctrl+C to quit')

        try:
            while not save_failed:
                current_phrase: str = dop.determine_next_phrase(repetitions)
                user_result, best_translation = uop.user_session(current_phrase, repetitions[current_phrase])

                if user_result is None:  # '/exit' command received
                    break

                dop.update_repetitions(repetitions, current_phrase, user_result)
                statistics = dop.update_statistics(statistics, current_phrase, best_translation)

                # save_json_to_file() writes a complete file or keeps the previous one, so a reported
                # failure means 'the data did not reach the disk' and the session must not go on silently
                if not fop.save_json_to_file(repetitions_file_path, repetitions):
                    save_failed = True
                elif not fop.save_json_to_file(user_statistics_file_path, statistics):
                    save_failed = True

        except KeyboardInterrupt:
            pass  # Ctrl+C pressed - exit politely (nothing is lost: data is saved after every attempt)

        # The final save persists the answers of the iteration broken by Ctrl+C. It is not a 'repair' of a
        # half-written file any more: an interrupted save cannot corrupt anything, writes are atomic now.
        repetitions_saved: bool = fop.save_json_to_file(repetitions_file_path, repetitions)
        statistics_saved: bool = fop.save_json_to_file(user_statistics_file_path, statistics)

        if repetitions_saved and statistics_saved:
            print('Session finished. All data saved.')
        else:
            unsaved_file_paths: list[str] = [path for path, is_saved in ((repetitions_file_path, repetitions_saved),
                                                                         (user_statistics_file_path, statistics_saved))
                                             if not is_saved]
            print(f'Session finished, but {", ".join(unsaved_file_paths)} WAS NOT saved. '
                  'The file keeps the last successfully saved data, nothing was corrupted.')
            sys.exit(1)
    else:
        print(assessment_error_message)
        sys.exit()
