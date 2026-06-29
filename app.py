from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from config import Config
from models import db, User, FeedbackMessage, Post
from forms import RegistrationForm, ContactForm
import requests
from datetime import datetime
from flask import Response, stream_with_context
import time
import json
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

# Flask-Migrate
from flask_migrate import Migrate
migrate = Migrate(app, db)

# Инициализация SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')


# ========== WEBSOCKET ==========

@socketio.on('connect')
def handle_connect():
    print(f'🔌 Клиент подключился: {request.sid}')
    emit('connected', {'message': 'Подключено к WebSocket!'})

@socketio.on('disconnect')
def handle_disconnect():
    print(f'🔌 Клиент отключился: {request.sid}')

@socketio.on('join_post')
def handle_join_post(data):
    post_id = data.get('post_id')
    room = f'post_{post_id}'
    join_room(room)
    print(f'👤 Клиент {request.sid} присоединился к комнате {room}')
    
    post = Post.query.get(post_id)
    if post:
        emit('like_update', {
            'post_id': post_id,
            'likes_count': post.likes_count
        }, room=request.sid)

@socketio.on('like_post')
def handle_like_post(data):
    post_id = data.get('post_id')
    room = f'post_{post_id}'
    
    post = Post.query.get(post_id)
    if post:
        post.likes_count += 1
        db.session.commit()
        
        emit('like_update', {
            'post_id': post_id,
            'likes_count': post.likes_count
        }, room=room)
        print(f'❤️ Пост {post_id} получил лайк! Всего: {post.likes_count}')
    else:
        emit('error', {'message': 'Пост не найден'}, room=request.sid)


# ========== TELEGRAM ==========

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


# ========== СТРАНИЦЫ ==========

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/partners')
def partners():
    return render_template('partners.html')


@app.route('/post/<int:post_id>')
def view_post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post.html', post=post)


# ========== РЕГИСТРАЦИЯ ==========

@app.route('/api/register', methods=['POST'])
def api_register():
    """API для регистрации через AJAX"""
    from forms import RegistrationForm
    from models import User
    
    data = request.get_json()
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


# ========== ОБРАТНАЯ СВЯЗЬ ==========

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


# ========== API ==========

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


# ========== ЗАПУСК ==========

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Создаём тестовый пост, если его нет
        if not Post.query.first():
            post = Post(
                title="Первый пост",
                content="Это тестовый пост для демонстрации лайков в реальном времени через WebSocket!"
            )
            db.session.add(post)
            db.session.commit()
            print("✅ Тестовый пост создан!")
    
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
