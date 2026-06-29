# seed.py
from app import app, db
from models import User, Post, FeedbackMessage

def seed_database():
    with app.app_context():
        # Проверяем, есть ли уже данные
        if User.query.count() > 0:
            print("База данных уже содержит данные, пропускаем...")
            return
        
        print("Добавляем тестовые данные...")
        
        # Пользователи
        users = [
            {"first_name": "Иван", "last_name": "Петров", "age": 25, "phone": "+7 (999) 123-45-67", "email": "ivan@mail.com", "login": "ivan_petrov", "password": "123456"},
            {"first_name": "Мария", "last_name": "Смирнова", "age": 30, "phone": "+7 (999) 234-56-78", "email": "maria@mail.com", "login": "maria_s", "password": "123456"},
            {"first_name": "Алексей", "last_name": "Иванов", "age": 28, "phone": "+7 (999) 345-67-89", "email": "alex@mail.com", "login": "alex_i", "password": "123456"},
        ]
        
        for u in users:
            user = User(
                first_name=u["first_name"],
                last_name=u["last_name"],
                age=u["age"],
                phone=u["phone"],
                email=u["email"],
                login=u["login"]
            )
            user.set_password(u["password"])
            db.session.add(user)
        
        # Пост
        post = Post(
            title="Добро пожаловать на портал!",
            content="Это тестовый пост для демонстрации системы лайков. Нажмите на кнопку ❤️ и увидите, как счётчик обновляется в реальном времени!"
        )
        db.session.add(post)
        
        # Сообщение обратной связи
        feedback = FeedbackMessage(
            name="Алексей Иванов",
            email="alex@mail.com",
            phone="+7 (999) 345-67-89",
            subject="Вопрос по порталу",
            message="Подскажите, как добавить новый курс?"
        )
        db.session.add(feedback)
        
        db.session.commit()
        print("✅ Тестовые данные успешно добавлены!")
        print(f"   - Пользователей: {User.query.count()}")
        print(f"   - Постов: {Post.query.count()}")
        print(f"   - Сообщений: {FeedbackMessage.query.count()}")

if __name__ == "__main__":
    seed_database()