import os

# Configurar variables de entorno para Google Cloud SQL
# Para desarrollo local en Windows, usar conexión TCP
# Para producción en Google Cloud, usar unix_socket
# Configuración para desarrollo local (Windows)
# CONFIGURACIÓN PARA GOOGLE CLOUD SQL
# Para desarrollo local en Windows, usar conexión TCP (IP pública)
# Para producción en Google Cloud, usar unix_socket
# 
# IMPORTANTE: Reemplaza [TU_IP_PUBLICA] con la IP real de tu instancia de Cloud SQL
# Para obtener la IP: Google Cloud Console > SQL > Instancias > gestion-la-hornilla > Conexiones > Dirección IP pública
# 
# CONFIGURACIÓN DEFINITIVA PARA GOOGLE CLOUD SQL
# Usando la IP pública de la instancia: 34.41.120.220
os.environ['DATABASE_URL'] = 'mysql+pymysql://UserApp:&8y7c()tu9t/+,6`@34.41.120.220:3306/lahornilla_base_normalizada'
os.environ['SECRET_KEY'] = 'Inicio01*'
os.environ['JWT_SECRET_KEY'] = 'Inicio01*'
os.environ['FLASK_ENV'] = 'development'
os.environ['FLASK_DEBUG'] = '1'

print("✅ Variables de entorno configuradas para Google Cloud SQL") 