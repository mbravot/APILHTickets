import os
from dotenv import load_dotenv
from datetime import timedelta

# Cargar variables de entorno
load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'Inicio01*')  # Cambia esto por una clave segura
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'mysql+pymysql://lahornilla_mbravo:Adm1n2021!+@200.73.20.99:35026/lahornilla_ticket')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'Inicio01*')  # Cambia esto por una clave segura
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)  # Token expira en 1 hora
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_TOKEN_LOCATION = ['headers']
    JWT_HEADER_NAME = 'Authorization'
    JWT_HEADER_TYPE = 'Bearer'
    SQLALCHEMY_POOL_RECYCLE = 280  # Evita la desconexión por inactividad
    SQLALCHEMY_POOL_TIMEOUT = 30   # Tiempo máximo de espera para conexión
    SQLALCHEMY_POOL_SIZE = 10      # Número máximo de conexiones activas
    SQLALCHEMY_MAX_OVERFLOW = 20   # Conexiones extra si se alcanza el máximo
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True  # Verifica la conexión antes de cada consulta
    }
