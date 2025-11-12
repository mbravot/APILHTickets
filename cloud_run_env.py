import os

# Configuración específica para Cloud Run
# Usar unix_socket para conectar a Cloud SQL desde Cloud Run
os.environ['DATABASE_URL'] = 'mysql+pymysql://UserApp:&8y7c()tu9t/+,6`@/lahornilla_base_normalizada?unix_socket=/cloudsql/gestion-la-hornilla:us-central1:gestion-la-hornilla'
os.environ['SECRET_KEY'] = 'Inicio01*'
os.environ['JWT_SECRET_KEY'] = 'Inicio01*'
os.environ['FLASK_ENV'] = 'production'
os.environ['FLASK_DEBUG'] = '0'

# Configuración SMTP
os.environ['SMTP_USUARIO'] = 'desarrollo@lahornilla.cl'
os.environ['SMTP_CLAVE'] = 'qkwtmfbvmjihxkci'
os.environ['SMTP_SERVER'] = 'smtp.gmail.com'
os.environ['SMTP_PORT'] = '587'
os.environ['SMTP_DISPLAY_NAME'] = 'Sistema de Tickets'

print("✅ Variables de entorno configuradas para Cloud Run") 