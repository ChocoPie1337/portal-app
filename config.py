import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///portal.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Секретный ключ
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    
    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
    WTF_CSRF_ENABLED = False