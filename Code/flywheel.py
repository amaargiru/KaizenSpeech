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

        if is_merged:
            fop.save_json_to_file(repetitions_file_path, repetitions)

        print('Type "/exit" or press Ctrl+C to quit')

        try:
            while True:
                current_phrase: str = dop.determine_next_phrase(repetitions)
                user_result, best_translation = uop.user_session(current_phrase, repetitions[current_phrase])

                if user_result is None:  # '/exit' command received
                    break

                dop.update_repetitions(repetitions, current_phrase, user_result)
                fop.save_json_to_file(repetitions_file_path, repetitions)

                statistics = dop.update_statistics(statistics, current_phrase, best_translation)
                fop.save_json_to_file(user_statistics_file_path, statistics)

        except KeyboardInterrupt:
            pass  # Ctrl+C pressed - exit politely (nothing is lost: data is saved after every attempt)

        # Re-save data to guarantee file consistency in case of interruption in the middle of writing
        fop.save_json_to_file(repetitions_file_path, repetitions)
        fop.save_json_to_file(user_statistics_file_path, statistics)

        print('Session finished. All data saved.')
    else:
        print(assessment_error_message)
        sys.exit()
