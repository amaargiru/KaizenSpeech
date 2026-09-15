from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List

from db_schema import database, Question, Answer, User, Questionstat


@dataclass
class UserQuestion:
    native_phrase: str
    references: List[str]
    links_to_audio: List[str]


class Examiner:
    @staticmethod
    def define_next_question_num(current_user: User) -> int:
        question_db_table_len = database.execute_sql("SELECT COUNT(*) FROM question").fetchone()[0]
        current_user_memory_coeff = current_user.memory_coeff

        try:
            current_user_question_stat = Questionstat.select().where(Questionstat.username == current_user.username)
        except Exception:
            return 1  # Stat is empty now

        min_next_question_time = datetime.now() + timedelta(days=1000000)
        for question_candidate in current_user_question_stat:
            if question_candidate.score >= 0:
                final_coeff = question_candidate.score * current_user_memory_coeff
            else:
                final_coeff = question_candidate.score / current_user_memory_coeff

            if final_coeff >= 9:  # Дальше 512 дней вряд ли стоит заглядывать
                final_coeff = 9

            question_candidate_required_datetime = question_candidate.last_attempt + timedelta(days=2 ** final_coeff)
            if question_candidate_required_datetime <= min_next_question_time:
                min_next_question_time = question_candidate_required_datetime
                next_question_id = question_candidate.question_id

        if min_next_question_time < datetime.now() or len(current_user_question_stat) + 1 > question_db_table_len:
            return next_question_id
        else:
            return len(current_user_question_stat) + 1  # Just next question

    @staticmethod
    def get_question(question_id: int = 1) -> UserQuestion:
        native_phrase = Question.get(Question.id == question_id).native_phrase
        query = Answer.select().where(Answer.question_id == question_id)

        references = []
        for ref in query:
            references.append(ref.english_phrase)

        links_to_audio = []
        for ref in query:
            links_to_audio.append(ref.link_to_audio)

        return UserQuestion(native_phrase, references, links_to_audio)
