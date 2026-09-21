#!/usr/bin/python3.12

from data_level import DataOperations as dop
from system_level import FileOperations as fop
from ui_level import UiOperations as uop
from pronunciation_checker import PronunciationChecker

import pyttsx3

def say(text):
    # Set voice engine
    engine = pyttsx3.init()

    # Change voice
    voices = engine.getProperty('voices')  # Get details of current voices
    engine.setProperty('voice', voices[1].id)  # Change voice
    engine.setProperty('rate', 100)  # Set up new voice rate

    # Say text
    engine.say(text)
    engine.runAndWait()

    # Delete engine - https://stackoverflow.com/questions/79757184/pyttsx3-runandwait-stops-working-after-first-execution
    del engine

say("Welcome, Michael")

checker = PronunciationChecker(
    model_path="C:\\Download\\vosk-model-en-us-0.22",
    silence_timeout=3.0,
)

print("✅ Checker initialized (fully offline).\n")

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

        while True:
            current_phrase: str = dop.determine_next_phrase(repetitions)
            user_result, best_translation = uop.user_session(current_phrase, repetitions[current_phrase])

            say(best_translation)

            dop.update_repetitions(repetitions, current_phrase, user_result)
            fop.save_json_to_file(repetitions_file_path, repetitions)

            statistics = dop.update_statistics(statistics, current_phrase, best_translation)
            fop.save_json_to_file(statistics_file_name, statistics)

            if user_result >= dop.level_excellent:
                while True:
                    # Call the check method
                    result = checker.check(best_translation, verbose=True)

                    # Use the returned data
                    print("\n" + "=" * 50)
                    print(f"📊 Score: {result.percentage}%")
                    print(f"📝 Phrase: {result.highlighted_phrase}")
                    print(f"💬 {result.plain_error_summary}")
                    print()
                    print(f"   Expected phonemes:   {result.expected_phonemes}")
                    print(f"   Recognized phonemes: {result.recognized_phonemes}")

                    # Per-word error details
                    if result.word_errors:
                        print("\n   Word details:")
                        for idx, info in result.word_errors.items():
                            status = "MISSING" if info["is_missing"] else (
                                "OK" if not info["error_char_indices"] else "ERRORS"
                            )
                            rec = info.get("recognized_as", "—") or "—"
                            print(f"     [{idx}] \"{info['word']}\" → \"{rec}\" ({status})")
                            if info["error_char_indices"]:
                                chars = [info["word"][i] for i in sorted(info["error_char_indices"]) if
                                         i < len(info["word"])]
                                print(f"          Problem characters: {chars}")

                    print("=" * 50)

                    say(best_translation)

                    command = input("Enter 'q' to quit from pronunciation checker): ").strip()
                    if command.lower() == "q":
                        print("Next phrase")
                        break
    else:
        print(assessment_error_message)
        exit()
