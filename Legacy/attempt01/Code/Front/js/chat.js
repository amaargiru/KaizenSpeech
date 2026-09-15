question_id = 1;

const usermsgnode = document.getElementById('usermsg');
usermsgnode.addEventListener("keyup", function (event) {
    if (event.key === "Enter") {
        updateChat();
    }
});

function updateChat() {
    document.getElementById('chatbox').innerHTML += `<div class="chat__item chat__item--responder">
      <img src="images/user_small.png" class="chat__person-avatar" alt="User avatar">
      <div class="chat__messages"><div class="chat__message"><div class="chat__message-time">${getcurrentTime()}</div>
      <div class="chat__message-content">${document.getElementById('usermsg').value}</div></div></div></div>`;

    chainReq();
    document.getElementById('usermsg').value = "";
    return false;
}

function get_next_question() {
    let req;
    if (localStorage.getItem("flywheelJwtToken") === null)
        req = `${app_config.base_url}/get_next_question_anonymous`;
    else {
        req = `${app_config.base_url}/get_next_question`;
        axios.defaults.headers.post['Authorization'] = `Bearer ${localStorage.getItem('flywheelJwtToken')}`;
    }

    axios.defaults.headers.post['Access-Control-Allow-Origin'] = '*';
    axios.defaults.headers.post['Content-Type'] = 'application/x-www-form-urlencoded';
    return axios.post(req)
        .then(response => {
            document.getElementById('chatbox').innerHTML += ` <div class="chat__content"><div class="chat__item">
        <img src="images/icon_small.png" alt="Flywheel english bot" class="chat__person-avatar">
        <div class="chat__messages"><div class="chat__message"><div class="chat__message-time">${getcurrentTime()}</div>
        <div class="chat__message-content">Напишите на английском фразу <b>\"${response.data.native_phrase}\"</b>.</div></div></div></div>`;

            question_id = response.data.question_id;

            const objDiv = document.getElementById("chatbox");
            objDiv.scrollTop = objDiv.scrollHeight;
        }, error => {
            if (error.response.status === 401) {
                document.getElementById('chatbox').innerHTML += ` <div class="chat__content"><div class="chat__item">
        <img src="images/icon_small.png" alt="Flywheel english bot" class="chat__person-avatar">
        <div class="chat__messages"><div class="chat__message"><div class="chat__message-time">${getcurrentTime()}</div>
        <div class="chat__message-content">Привет! Пожалуйста, <a href="signin.html">войдите в свой аккаунт</a>.</div></div></div></div>`;
            }
            return error;
        });
}

function startMessage() {
    if (localStorage.getItem("flywheelJwtToken") === null) {
        document.getElementById('chatbox').innerHTML += `<div class="chat__content"><div class="chat__item">
        <img src="images/icon_small.png" alt="Flywheel english bot" class="chat__person-avatar">
        <div class="chat__messages"><div class="chat__message"><div class="chat__message-time">${getcurrentTime()}</div>
        <div class="chat__message-content">
          Привет! Вы можете <a href="signin.html">войти в свой аккаунт</a> или <a href="signup.html">создать новый аккаунт</a>. 
          Тогда бот определит темы занятий именно под ваш уровень владения английским языком, 
          каждый следующий вопрос будет подобран индивидуально и ваш прогресс значительно ускорится.<br>
          Если вы продолжите учиться без аккаунта, то, к сожалению, вопросы будут задаваться в случайном порядке, 
          а информация о вашем прогрессе не будет сохранена.<br>
          Плюс, к правильным ответам добавятся ссылки на аудиофайлы с примером правильного произношения:<br> <audio controls>
            <source src="${app_config.mp3_url}/MP3/ServiceMP3/Wake_up_Neo_The_Matrix_has_you_follow_the_white_rabbit.mp3" /></audio>
        </div></div></div></div>`;
    }
    return get_next_question();
}

function chainReq() {
    axios.defaults.headers.post['Access-Control-Allow-Origin'] = '*';
    axios.defaults.headers.post['Content-Type'] = 'application/x-www-form-urlencoded';

    let req1;
    if (localStorage.getItem("flywheelJwtToken") === null) {
        req1 = `${app_config.base_url}/get_answer_check_anonymous?question_id=${question_id}&user_input=${(document.getElementById('usermsg').value)}`;
    }
    else {
        req1 = `${app_config.base_url}/get_answer_check?question_id=${question_id}&user_input=${(document.getElementById('usermsg').value)}`;
        axios.defaults.headers.post['Authorization'] = `Bearer ${localStorage.getItem('flywheelJwtToken')}`;
    }

    return axios.post(req1)
        .then(firstResponse => {
            let ans = JSON.parse(firstResponse.data.answer);
            let motivation_msg = "";
            switch (ans.score) {
                case 4:
                    motivation_msg = "Правильно!";
                    break;
                case 3:
                    motivation_msg = "Почти правильно. Правильный ответ:";
                    break;
                case 2:
                    motivation_msg = "Неплохо. Правильный ответ:";
                    break;
                case 1:
                    motivation_msg = "Правильный ответ:";
                    break;
            }

            let hint = "";
            if ((ans.score > 1) && (ans.score <= 3)) {
                for (let i = 0; i < ans.hint.length; i++) {
                    b = ans.hint.charAt(i);
                    if (b === '/') {
                        hint += `<span style="color: red; font-weight: bold;">${ans.hint.charAt(i + 1)}</span>`;
                        i++;
                    }
                    else {
                        hint += `<span style="color: green; font-weight: bold;">${ans.hint.charAt(i)}</span>`;
                    }
                }
                hint += ".";
            }
            else if (ans.score == 1) {
                for (let i = 0; i < ans.hint.length; i++) {
                    b = ans.hint.charAt(i);
                    if (b === '/') {
                        hint += `<span style="color: green; font-weight: bold;">${ans.hint.charAt(i + 1)}</span>`;
                        i++;
                    }
                    else {
                        hint += `<span style="color: green; font-weight: bold;">${ans.hint.charAt(i)}</span>`;
                    }
                }
                hint += ".";
            }

            let speech = "";
            if ((firstResponse.data.link_to_audio !== "") && (firstResponse.data.link_to_audio !== undefined)) {
                speech = `<br> <audio controls> <source src="${app_config.mp3_url}/MP3/AnswersMP3/${firstResponse.data.link_to_audio}" /></audio>`;
            }

            document.getElementById('chatbox').innerHTML += `<div class="chat__content"><div class="chat__item">
        <img src="images/icon_small.png" alt="Flywheel english bot" class="chat__person-avatar">
        <div class="chat__messages"><div class="chat__message"><div class="chat__message-time">${getcurrentTime()}</div>
        <div class="chat__message-content">${motivation_msg} ${hint} ${speech}</div></div></div></div>`;

            get_next_question();

            const objDiv = document.getElementById("chatbox");
            objDiv.scrollTop = objDiv.scrollHeight;
        }, error => {
            if (error.response.status === 401) {
                document.getElementById('chatbox').innerHTML += ` <div class="chat__content"><div class="chat__item">
        <img src="images/icon_small.png" alt="Flywheel english bot" class="chat__person-avatar">
        <div class="chat__messages"><div class="chat__message"><div class="chat__message-time">${getcurrentTime()}</div>
        <div class="chat__message-content">Привет! Пожалуйста, <a href="signin.html">войдите в свой аккаунт</a>.</div></div></div></div>`;
            }
            return error;
        });
}

function getcurrentTime() {
    return new Date().toLocaleTimeString('en-US', {
        hour12: false,
        hour: "numeric",
        minute: "numeric"
    });
}
