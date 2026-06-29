from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, PasswordField, SubmitField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Regexp, EqualTo, ValidationError
import re


class RegistrationForm(FlaskForm):
    first_name = StringField('Имя', validators=[
        DataRequired(message='Имя обязательно'),
        Length(min=2, max=50),
        Regexp(r'^[A-Za-zА-Яа-яЁё\s-]+$', message='Только буквы')
    ])
    
    last_name = StringField('Фамилия', validators=[
        DataRequired(message='Фамилия обязательна'),
        Length(min=2, max=50),
        Regexp(r'^[A-Za-zА-Яа-яЁё\s-]+$', message='Только буквы')
    ])
    
    age = IntegerField('Возраст', validators=[
        DataRequired(message='Возраст обязателен'),
        NumberRange(min=18, max=100, message='Возраст от 18 до 100 лет')
    ])
    
    phone = StringField('Телефон', validators=[
        Regexp(r'^\+7\s?\(?[0-9]{3}\)?\s?[0-9]{3}[-]?[0-9]{2}[-]?[0-9]{2}$|^$', 
               message='Формат: +7 (XXX) XXX-XX-XX')
    ])
    
    email = StringField('Email', validators=[
        DataRequired(message='Email обязателен'),
        Email(message='Введите корректный email')
    ])
    
    login = StringField('Логин', validators=[
        DataRequired(message='Логин обязателен'),
        Length(min=4, max=20),
        Regexp(r'^[A-Za-z0-9_]+$', message='Только буквы, цифры и _')
    ])
    
    password = PasswordField('Пароль', validators=[
        DataRequired(message='Пароль обязателен'),
        Length(min=6, max=20, message='Пароль от 6 до 20 символов')
    ])
    
    confirm_password = PasswordField('Подтверждение пароля', validators=[
        DataRequired(message='Подтвердите пароль'),
        EqualTo('password', message='Пароли не совпадают')
    ])
    
    submit = SubmitField('Зарегистрироваться')
    
    def validate_login(self, login):
        from models import User
        from app import app
        with app.app_context():
            user = User.query.filter_by(login=login.data).first()
            if user:
                raise ValidationError('Этот логин уже занят')
    
    def validate_email(self, email):
        from models import User
        from app import app
        with app.app_context():
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('Этот email уже зарегистрирован')


class ContactForm(FlaskForm):
    name = StringField('Имя', validators=[
        DataRequired(message='Имя обязательно'),
        Length(min=2, max=100)
    ])
    
    email = StringField('Email', validators=[
        DataRequired(message='Email обязателен'),
        Email(message='Введите корректный email')
    ])
    
    phone = StringField('Телефон')
    
    subject = SelectField('Тема', choices=[
        ('question', '📝 Вопрос по порталу'),
        ('support', '🛠 Техническая поддержка'),
        ('cooperation', '🤝 Сотрудничество'),
        ('other', '💡 Другое')
    ], validators=[DataRequired()])
    
    message = TextAreaField('Сообщение', validators=[
        DataRequired(message='Сообщение обязательно'),
        Length(min=10, max=2000)
    ])
    
    submit = SubmitField('Отправить')