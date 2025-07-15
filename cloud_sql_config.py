import os
from dotenv import load_dotenv
from datetime import timedelta

# Cargar variables de entorno
load_dotenv()

class CloudSQLConfig:
    SECRET_KEY = os.getenv('SECRET_KEY', 'Inicio01*')
    
    # Configuración para Google Cloud SQL
    # Para desarrollo local, usa la conexión TCP
    # Para producción en Google Cloud, usa unix_socket
    import platform
    
    DATABASE_URL = os.getenv('DATABASE_URL')
    if DATABASE_URL:
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    else:
        # Detectar si estamos en Windows (desarrollo local) o Linux (producción)
        if platform.system() == 'Windows':
            # Para desarrollo local en Windows, usar conexión TCP
            # Usando la IP pública de la instancia: 34.41.120.220
            SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://UserApp:&8y7c()tu9t/+,6`@34.41.120.220:3306/lahornilla_base_normalizada'
        else:
            # Para producción en Google Cloud (Linux)
            SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://UserApp:&8y7c()tu9t/+,6`@/lahornilla_base_normalizada?unix_socket=/cloudsql/lahornilla-cloud:us-central1:gestion-la-hornilla'
    
    # Configuración optimizada para Google Cloud SQL
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 3600,
        'pool_timeout': 30,
        'pool_size': 10,
        'max_overflow': 20,
        'connect_args': {
            'charset': 'utf8mb4',
            'sql_mode': 'STRICT_TRANS_TABLES',
            'autocommit': True
        }
    }
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'Inicio01*')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=2)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=15)
    JWT_TOKEN_LOCATION = ['headers']
    JWT_HEADER_NAME = 'Authorization'
    JWT_HEADER_TYPE = 'Bearer' 