import json
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext

from comparator import Comparator
from complicator import Complicator
from db_schema import User, Questionstat
from examiner import Examiner
from lower import Lower
from printer import Printer
from refiner import Refiner

# To get a string like this run: openssl rand -hex 32
SECRET_KEY = "f6e936d318b4103412c142893d7331fb83c2228fc31155a8f96de27c3afdeea7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 10 * 365 * 24 * 60


@dataclass
class Token:
    access_token: str
    token_type: str


@dataclass
class TokenData:
    username: Optional[str] = None


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="signin")

app = FastAPI()

app.add_middleware(CORSMiddleware,
                   allow_origins=["*"],
                   allow_credentials=True,
                   allow_methods=["OPTIONS", "POST"],
                   allow_headers=["*"])


# Docs: http://127.0.0.1:8000/docs
# Example: http://127.0.0.1:8000/get_next_question
@app.post("/get_next_question_anonymous")
async def get_next_question_anonymous():
    question_id = Examiner.define_next_question_num()
    question = Examiner.get_question(question_id)

    return {"question_id": question_id,
            "native_phrase": f"{question.native_phrase}"}


# Example: http://127.0.0.1:8000/get_answer_check?question_id=1&user_input=qq
@app.post("/get_answer_check_anonymous")
async def get_answer_check_anonymous(question_id: int, user_input: str):
    question = Examiner.get_question(question_id)
    user_input_cleaned = Refiner.refine_user_input(user_input)
    user_input_complex = Complicator.complicate_user_input(user_input_cleaned)
    user_input_without_punctuation_lower = Lower.list_lower(user_input_complex.user_input_without_punctuation)
    references_lower = Lower.references_lower(question.references)
    index, ratio = Comparator.find_nearest_reference_index(user_input_without_punctuation_lower, references_lower)
    correction = Comparator.find_matching_blocks(user_input_without_punctuation_lower, references_lower, index)
    a = Printer.format_message_to_api(question.references, index, correction, ratio)

    return {"question_id": question_id, "answer": json.dumps(a)}


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_user(username) -> User:
    user = None
    try:
        user = User.get(User.username == username)
    except Exception:
        pass

    return user


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                          detail="Could not validate credentials",
                                          headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception

    user = get_user(token_data.username)

    if user is None:
        raise credentials_exception
    return user


@app.post("/signin", response_model=Token)
async def signin(form_data: OAuth2PasswordRequestForm = Depends()):
    user = get_user(form_data.username)

    if user is None or not pwd_context.verify(form_data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Incorrect username or password",
                            headers={"WWW-Authenticate": "Bearer"})

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": form_data.username}, expires_delta=access_token_expires)
    return {"access_token": access_token,
            "token_type": "bearer"}


@app.post("/signup")
async def signup(username: str, email: str, password: str):
    res: bool = False

    user = get_user(username)

    if user is None:
        time.strftime('%Y-%m-%d %H:%M:%S')
        User.create(username=username,
                    email=email,
                    password_hash=pwd_context.hash(password),
                    memory_coeff=1,
                    last_visit=datetime.now(),
                    attempts=0)
        res = True

    if res:
        return {"result": "New user created successfully",
                "user": username}
    else:
        return {"result": "User exist",
                "user": username}


@app.post("/get_next_question")
async def get_next_question(current_user: User = Depends(get_current_user)):
    question_id = Examiner.define_next_question_num(current_user)
    question = Examiner.get_question(question_id)

    return {"question_id": question_id,
            "native_phrase": f"{question.native_phrase}"}


@app.post("/get_answer_check")
async def get_answer_check(question_id: int, user_input: str, current_user: User = Depends(get_current_user)):
    question = Examiner.get_question(question_id)
    user_input_cleaned = Refiner.refine_user_input(user_input)
    user_input_complex = Complicator.complicate_user_input(user_input_cleaned)
    user_input_without_punctuation_lower = Lower.list_lower(user_input_complex.user_input_without_punctuation)
    references_lower = Lower.references_lower(question.references)
    index, ratio = Comparator.find_nearest_reference_index(user_input_without_punctuation_lower, references_lower)
    correction = Comparator.find_matching_blocks(user_input_without_punctuation_lower, references_lower, index)
    message_to_user = Printer.format_message_to_api(question.references, index, correction, ratio)

    # Refresh user data in DB
    current_user.attempts = int(current_user.attempts or 0) + 1
    time.strftime('%Y-%m-%d %H:%M:%S')
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
            question_stat.score = 1  # Наконец-то правильный ответ, прощаем все предыдущие неправильные ответы
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

    return {"question_id": question_id,
            "answer": json.dumps(message_to_user),
            "link_to_audio": question.links_to_audio[index]}


if __name__ == "__main__":
    uvicorn.run(app)
