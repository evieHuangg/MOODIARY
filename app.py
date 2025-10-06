from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from db import diaries_table, register_user, check_login
from random import choice
from datetime import datetime, timedelta, timezone
import humanize
import os
import json
from gemini import generate_encouragement
from dotenv import load_dotenv
import random
from werkzeug.utils import secure_filename

tz_utc_8 = timezone(timedelta(hours=8))

def time_since(timestr):
    try:
        created_time = datetime.strptime(timestr, '%Y-%m-%d %H:%M:%S').replace(tzinfo=tz_utc_8)
        created_time_utc = created_time.astimezone(timezone.utc)
        now_utc = datetime.now(timezone.utc)
        return humanize.naturaltime(now_utc - created_time_utc)
    except:
        return "unknown time"

app = Flask(__name__)
load_dotenv()
app.secret_key = os.getenv("FLASK_SECRET_KEY")
app.jinja_env.globals.update(time_since=time_since)
app.jinja_env.globals.update(zip=zip)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    with open('static/test.json', encoding='utf-8') as f:
        quiz_data = json.load(f)
    questions = quiz_data["questions"]
    total_questions = len(questions)

    if 'quiz_answers' not in session:
        session['quiz_answers'] = {}

    page = int(request.args.get('page', 1))

    if request.method == 'POST':
        current_q = questions[page - 1]
        selected = request.form.get(current_q["id"])
        if selected is not None:
            answers = session.get('quiz_answers', {})
            answers[current_q["id"]] = int(selected)
            session['quiz_answers'] = answers
            # print("目前累積的作答：", session['quiz_answers'])

        if page < total_questions:
            return redirect(url_for('quiz', page=page + 1))

        else:
            user_answers = []
            for q in questions:
                selected_val = session['quiz_answers'].get(q["id"])
                if selected_val is not None:
                    try:
                        idx = q["values"].index(selected_val)
                        selected_option = q["options"][idx]
                        user_answers.append({
                            "question": q["text"],
                            "selected": selected_option
                        })
                    except ValueError:
                        continue

            suggestion = generate_encouragement(user_answers)

            score = sum(session['quiz_answers'].values())
            session.pop('quiz_answers', None)

            return render_template('quiz_result.html', score=score, suggestion=suggestion)

    current_q = questions[page - 1]
    return render_template('quiz_page.html', q=current_q, page=page, total=total_questions, quiz=quiz_data)

@app.route('/gemini_suggestion', methods=['POST'])
def gemini_suggestion():
    content = request.json.get("content", "")
    suggestion = generate_encouragement(content)
    return jsonify({'suggestion': suggestion})

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))

@app.route('/game')
def play_game():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('game.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.get_json()
        username = data['username']
        password = data['password']
        success = register_user(username, password)
        if success:
            return jsonify({'status': 'success', 'message': '註冊成功'})
        else:
            return jsonify({'status': 'fail', 'message': '使用者已存在'})
    else:
        return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        data = request.get_json()
        username = data['username']
        password = data['password']
        if check_login(username, password):
            session['username'] = username
            return jsonify({'status': 'success', 'username': username})
        else:
            return jsonify({'status': 'fail', 'message': '帳號或密碼錯誤'})

    public_diaries = [d for d in diaries_table.all() if d.get('public')]
    sample_diary = choice(public_diaries) if public_diaries else None
    return render_template('login.html', sample=sample_diary)

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    print(session['username'])
    # 取得所有公開日記
    public_diaries = [d for d in diaries_table.all() if d.get('public')]
    public_diaries = sorted(public_diaries, key=lambda d: d['created_at'], reverse=True)
    # 取得自己的日記
    my_diaries = [d for d in diaries_table.all() if d.get('author') == session['username']]
    random_post = random.choice(my_diaries) if my_diaries else None
    return render_template(
        'dashboard.html',
        public_diaries = public_diaries,
        my_diaries = my_diaries,
        random_post = random_post,
        username = session['username']
    )

@app.route('/write', methods=['GET', 'POST'])
def write():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        content = request.form['content']
        mood = request.form.get('mood')
        is_public = 'public' in request.form
        image = request.files.get('image')
        image_path = None
        if image and image.filename != '':
            print("接收到圖片：", image.filename)
            filename = secure_filename(image.filename)
            upload_folder = os.path.join(BASE_DIR, 'static', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            image.save(os.path.join(upload_folder, filename))
            image_path = f'uploads/{filename}'  # 存在DB的路徑

        diaries_table.insert({
            'author': session['username'],
            'content': content,
            'mood': mood,
            'public': is_public,
            'image_path': image_path,
            'created_at': datetime.now(tz_utc_8).strftime('%Y-%m-%d %H:%M:%S')
        })
        return redirect(url_for('index'))

    public_diaries = [d for d in diaries_table.all() if d.get('public')]
    sample_diary = choice(public_diaries) if public_diaries else None

    return render_template('write.html', sample=sample_diary, username=session['username'])

@app.route('/my_diary')
def my_diary():
    if 'username' not in session:
        return redirect(url_for('login'))
    print(session['username'])

    # 取得用戶的日記，並包含 doc_id 和格式化後的日期
    diaries = []
    for d in diaries_table.all():
        if d.get('author') == session['username']:
            # 格式化 created_at 為 YYYY-MM-DD
            try:
                created_at = datetime.strptime(d['created_at'], '%Y-%m-%d %H:%M:%S')
                formatted_date = created_at.strftime('%Y-%m-%d')
            except ValueError:
                formatted_date = d['created_at']  # 保留原始值以防格式錯誤
            diaries.append({
                **d,
                'id': d.doc_id,
                'formatted_date': formatted_date
            })

    # 按日期降序排列日記
    diaries = sorted(diaries, key=lambda d: d['created_at'], reverse=True)

    return render_template('my_diary.html', diaries=diaries, username=session['username'])

@app.route('/delete_diary/<int:diary_id>', methods=['POST'])
def delete_diary(diary_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    diary = diaries_table.get(doc_id=diary_id)
    if diary and diary.get('author') == session['username']:
        diaries_table.remove(doc_ids=[diary_id])

    return redirect(url_for('my_diary'))

if __name__ == '__main__':
    app.run(port=5002, host="0.0.0.0", debug=False)