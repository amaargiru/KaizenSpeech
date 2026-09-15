import pathlib
import sys
import time
from datetime import datetime

from comparator import Comparator
from complicator import Complicator
from db_schema import User, Questionstat
from examiner import Examiner
from fw_logger import FlyWheelLogger
from lower import Lower
from printer import Printer
from refiner import Refiner

log_max_file_size = 1024 ** 2  # Maximum size of one log file
log_max_file_count = 10  # Maximum number of log files
log_file_path = "logs//fw.log"

if __name__ == "__main__":

    try:
        path = pathlib.Path(log_file_path)  # Create a path to the log file if it doesn't exist
        path.parent.mkdir(parents=True, exist_ok=True)
        logger = FlyWheelLogger.get_logger(log_file_path, log_max_file_size, log_max_file_count)
    except Exception as err:
        print(f"Error when trying to create log directory {str(err)}")
        sys.exit(1)  # Emergency exit with non-zero code

    user_id: int = 1

    logger.info("Start")

    while True:
        current_user = User.get(User.username == "amaargiru")

        question_id = Examiner.define_next_question_num(current_user)
        question = Examiner.get_question(question_id)
        user_input: str = input(f"Enter phrase \"{question.native_phrase}\" in english: ")
        user_input_cleaned = Refiner.refine_user_input(user_input)
        user_input_complex = Complicator.complicate_user_input(user_input_cleaned)
        user_input_without_punctuation_lower = Lower.list_lower(user_input_complex.user_input_without_punctuation)
        references_lower = Lower.references_lower(question.references)

        index, ratio = Comparator.find_nearest_reference_index(user_input_without_punctuation_lower, references_lower)
        correction = Comparator.find_matching_blocks(user_input_without_punctuation_lower, references_lower, index)
        Printer.color_print_message_to_user(question.references, index, correction, ratio)
        a = Printer.format_message_to_api(question.references, index, correction, ratio)

        # Refresh user data in DB
        current_user.attempts = int(current_user.attempts or 0) + 1
        time.strftime("%Y-%m-%d %H:%M:%S")
        current_user.last_visit = datetime.now()

        memory_coeff = float(current_user.memory_coeff)
        memory_coeff = 1.01 * memory_coeff if ratio > Printer.level4ratio else 0.99 * memory_coeff
        current_user.memory_coeff = memory_coeff

        current_user.save(only=[User.attempts, User.last_visit, User.memory_coeff])

        question_stat: Questionstat
        result = None

        try:
            result = Questionstat.get(Questionstat.username == current_user.username and Questionstat.question_id == question_id)
        except Exception:
            pass

        if result is not None:
            question_stat = result
            question_stat.attempts = int(question_stat.attempts or 0) + 1

            if ratio <= Printer.level4ratio:
                question_stat.score = int(question_stat.score or 0) - 1
            elif question_stat.score < 0:
                question_stat.score = 1  # Finally the right answer, forgetting all the previous wrong answers
            else:
                question_stat.score = int(question_stat.score or 0) + 1

            question_stat.last_attempt = datetime.now()
        else:
            question_stat = Questionstat.create(last_attempt=datetime.now(),
                                                question_id=question_id,
                                                attempts=1,
                                                score=1 if ratio > Printer.level4ratio else -1,
                                                username=current_user.username)

        question_stat.save()
