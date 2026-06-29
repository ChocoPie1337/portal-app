from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from config import Config
from models import db, User, FeedbackMessage
from forms import RegistrationForm, ContactForm
import requests
from datetime import datetime
from models import db, User, FeedbackMessage, Post
from flask import Response, stream_with_context
import time
import json

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

# Глобальный генератор событий (для простоты – используем очередь)
# В реальном проекте лучше использовать Redis или базу данных.
# Здесь мы просто храним последнее обновление и отправляем его всем подключённым клиентам.

last_update = {
    'post_id': None,
    'likes_count': 0,
    'timestamp': 0
}

@app.route('/stream')
def stream():
    def event_stream():
        global last_update
        last_sent = 0
        while True:
            # Проверяем, было ли обновление после последней отправки
            if last_update['timestamp'] > last_sent:
                data = {
                    'post_id': last_update['post_id'],
                    'likes_count': last_update['likes_count']
                }
                yield f"data: {json.dumps(data)}\n\n"
                last_sent = last_update['timestamp']
            time.sleep(0.5)  # небольшая задержка для экономии ресурсов
    
    return Response(stream_with_context(event_stream()), mimetype="text/event-stream")

@app.route('/api/like/<int:post_id>', methods=['POST'])
def like_post(post_id):
    global last_update
    post = Post.query.get_or_404(post_id)
    post.likes_count += 1
    db.session.commit()
    
    # Обновляем глобальное состояние для SSE
    last_update['post_id'] = post_id
    last_update['likes_count'] = post.likes_count
    last_update['timestamp'] = int(time.time())
    
    return jsonify({
        'success': True,
        'post_id': post.id,
        'likes_count': post.likes_count
    })

@app.route('/post/<int:post_id>')
def view_post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post.html', post=post)

# Flask-Migrate
from flask_migrate import Migrate
migrate = Migrate(app, db)


def send_to_telegram(message_data):
    """Отправка уведомления в Telegram"""
    bot_token = app.config['TELEGRAM_BOT_TOKEN']
    chat_id = app.config['TELEGRAM_CHAT_ID']
    
    if not bot_token or not chat_id or bot_token == 'YOUR_BOT_TOKEN_HERE':
        print("Telegram не настроен. Пропускаем отправку.")
        return False, "Telegram not configured"
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    text = f"""
📬 <b>НОВОЕ СООБЩЕНИЕ</b>
━━━━━━━━━━━━━━━

👤 <b>Отправитель:</b> {message_data['name']}
📧 <b>Email:</b> {message_data['email']}
🏷 <b>Тема:</b> {message_data['subject']}

💬 <b>Сообщение:</b>
{message_data['message']}

🕐 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
    """
    
    payload = {
        'chat_id': chat_id,
        'text': text.strip(),
        'parse_mode': 'HTML'
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.ok, response.json() if response.ok else None
    except Exception as e:
        print(f"Telegram error: {e}")
        return False, str(e)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/partners')
def partners():
    return render_template('partners.html')


@app.route('/api/register', methods=['POST'])
def api_register():
    """API для регистрации через AJAX"""
    from forms import RegistrationForm
    from models import User
    import json
    
    data = request.get_json()
    
    # Создаем форму с данными
    form = RegistrationForm(data=data)
    
    if form.validate():
        user = User(
            first_name=form.first_name.data.strip(),
            last_name=form.last_name.data.strip(),
            age=form.age.data,
            phone=form.phone.data.strip() if form.phone.data else '',
            email=form.email.data.strip().lower(),
            login=form.login.data.strip().lower()
        )
        user.set_password(form.password.data)
        
        try:
            db.session.add(user)
            db.session.commit()
            
            # Отправка в Telegram
            message_data = {
                'name': f"{user.first_name} {user.last_name}",
                'email': user.email,
                'subject': '🎉 Новая регистрация',
                'message': f"Зарегистрирован новый пользователь!\nЛогин: {user.login}\nВозраст: {user.age}"
            }
            send_to_telegram(message_data)
            
            return jsonify({
                'success': True,
                'message': 'Регистрация успешна!',
                'user': user.to_dict()
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500
    else:
        return jsonify({
            'success': False,
            'errors': form.errors,
            'message': 'Пожалуйста, исправьте ошибки в форме'
        }), 400

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    
    if form.validate_on_submit():
        user = User(
            first_name=form.first_name.data.strip(),
            last_name=form.last_name.data.strip(),
            age=form.age.data,
            phone=form.phone.data.strip() if form.phone.data else '',
            email=form.email.data.strip().lower(),
            login=form.login.data.strip().lower()
        )
        user.set_password(form.password.data)
        
        try:
            db.session.add(user)
            db.session.commit()
            session['user_id'] = user.id
            session['user_name'] = user.first_name
            
            flash(f'Регистрация успешна! Добро пожаловать, {user.first_name}!', 'success')
            return redirect(url_for('register_success'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка: {str(e)}', 'danger')
    
    return render_template('form.html', form=form)


@app.route('/register/success')
def register_success():
    flash('Регистрация успешна!', 'success')
    return redirect(url_for('index'))


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    form = ContactForm()
    
    if form.validate_on_submit():
        feedback = FeedbackMessage(
            name=form.name.data.strip(),
            email=form.email.data.strip().lower(),
            phone=form.phone.data.strip() if form.phone.data else '',
            subject=form.subject.data,
            message=form.message.data.strip()
        )
        
        try:
            db.session.add(feedback)
            db.session.commit()
            
            subject_dict = dict(form.subject.choices)
            message_data = {
                'name': feedback.name,
                'email': feedback.email,
                'subject': subject_dict.get(feedback.subject, feedback.subject),
                'message': feedback.message
            }
            
            success, _ = send_to_telegram(message_data)
            feedback.is_sent_to_telegram = success
            db.session.commit()
            
            if success:
                flash('Сообщение успешно отправлено!', 'success')
            else:
                flash('Сообщение сохранено, но уведомление не отправлено.', 'warning')
                
            return redirect(url_for('contact_success'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка: {str(e)}', 'danger')
    
    return render_template('contact.html', form=form)


@app.route('/contact/success')
def contact_success():
    return render_template('contact_success.html')


@app.route('/api/users')
def get_users():
    users = User.query.all()
    return jsonify([user.to_dict() for user in users])


@app.route('/api/feedback')
def get_feedback():
    messages = FeedbackMessage.query.order_by(FeedbackMessage.created_at.desc()).limit(50).all()
    return jsonify([msg.to_dict() for msg in messages])


@app.route('/api/stats')
def get_stats():
    stats = {
        'total_users': User.query.count(),
        'total_feedback': FeedbackMessage.query.count()
    }
    return jsonify(stats)


@app.route('/api/check_password/<int:user_id>')
def check_password_hash(user_id):
    """Для проверки шифрования пароля (удалить в продакшене)"""
    user = User.query.get_or_404(user_id)
    return jsonify({
        'user_id': user.id,
        'login': user.login,
        'password_hash': user.password_hash,
        'hash_length': len(user.password_hash),
        'hash_starts_with': user.password_hash[:20] + '...'
    })


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
with app.app_context():
    if not Post.query.first():
        post = Post(
            title="Первый пост",
            content="Это тестовый пост для демонстрации лайков в реальном времени."
        )
        db.session.add(post)
        db.session.commit()
    app.run(debug=True, host='0.0.0.0', port=5000)