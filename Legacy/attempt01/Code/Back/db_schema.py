from peewee import *

database = MySQLDatabase('flywheel', **{'charset': 'utf8', 'sql_mode': 'PIPES_AS_CONCAT',
                                        'use_unicode': True, 'user': 'root', 'passwd': '8008'})


class UnknownField(object):
    def __init__(self, *_, **__):
        pass


class BaseModel(Model):
    class Meta:
        database = database


class Answer(BaseModel):
    english_phrase = CharField(column_name="englishPhrase")
    link_to_audio = CharField(column_name="linkToAudio", null=True)
    question_id = IntegerField(column_name="questionId", index=True)

    class Meta:
        table_name = "answer"


class Grammartheme(BaseModel):
    theme = CharField()

    class Meta:
        table_name = "grammartheme"


class Grammarthemestat(BaseModel):
    last_attempt = DateTimeField(column_name="lastAttempt", null=True)
    theme_id = IntegerField(column_name="themeId")
    theme_stat = IntegerField(column_name="themeStat")
    username = CharField(index=True)

    class Meta:
        table_name = "grammarthemestat"


class Question(BaseModel):
    native_phrase = CharField(column_name="nativePhrase")

    class Meta:
        table_name = "question"


class Questionstat(BaseModel):
    attempts = IntegerField()
    last_attempt = DateTimeField(column_name="lastAttempt")
    question_id = IntegerField(column_name="questionId")
    score = IntegerField()
    username = CharField(index=True)

    class Meta:
        table_name = "questionstat"


class Questiontogrammartheme(BaseModel):
    question_id = IntegerField(column_name="questionId")
    theme_id = IntegerField(column_name="themeId", index=True)

    class Meta:
        table_name = "questiontogrammartheme"


class Questiontoword(BaseModel):
    question_id = IntegerField(column_name="questionId")
    word_id = IntegerField(column_name="wordId", index=True)

    class Meta:
        table_name = "questiontoword"


class Questiontowordtheme(BaseModel):
    question_id = IntegerField(column_name="questionId")
    theme_id = IntegerField(column_name="themeId", index=True)

    class Meta:
        table_name = "questiontowordtheme"


class User(BaseModel):
    attempts = IntegerField()
    email = CharField()
    last_visit = DateTimeField(column_name="lastVisit")
    memory_coeff = FloatField(column_name="memoryCoeff")
    password_hash = CharField(column_name="passwordHash")
    username = CharField(index=True)

    class Meta:
        table_name = "user"


class Word(BaseModel):
    word = CharField(index=True)

    class Meta:
        table_name = "word"


class Wordstat(BaseModel):
    last_attempt = DateTimeField(column_name="lastAttempt")
    username = CharField(index=True)
    word_id = IntegerField(column_name="wordId")
    word_stat = IntegerField(column_name="wordStat")

    class Meta:
        table_name = "wordstat"


class Wordtheme(BaseModel):
    theme = CharField()

    class Meta:
        table_name = "wordtheme"


class Wordthemestat(BaseModel):
    last_attempt = DateTimeField(column_name="lastAttempt")
    theme_id = IntegerField(column_name="themeId")
    theme_stat = IntegerField(column_name="themeStat")
    username = CharField(index=True)

    class Meta:
        table_name = "wordthemestat"
