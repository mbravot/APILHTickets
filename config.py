import os
from dotenv import load_dotenv
from datetime import timedelta

# Cargar variables de entorno
load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'Inicio01*')  # Cambia esto por una clave segura
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'mysql+pymysql://UserApp:&8y7c()tu9t/+,6`@/lahornilla_base_normalizada?unix_socket=/cloudsql/PROYECTO:REGION:gestion-la-hornilla')
    # Configuración específica para Google Cloud SQL
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,  # Verifica la conexión antes de cada consulta
        'pool_recycle': 3600,   # Recicla conexiones cada hora
        'pool_timeout': 30,     # Tiempo máximo de espera para conexión
        'pool_size': 10,        # Número máximo de conexiones activas
        'max_overflow': 20,     # Conexiones extra si se alcanza el máximo
        'connect_args': {
            'charset': 'utf8mb4',
            'sql_mode': 'STRICT_TRANS_TABLES'
        }
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'Inicio01*')  # Cambia esto por una clave segura
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=2)  # Token expira en 2 horas
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=15)
    JWT_TOKEN_LOCATION = ['headers']
    JWT_HEADER_NAME = 'Authorization'
    JWT_HEADER_TYPE = 'Bearer'

