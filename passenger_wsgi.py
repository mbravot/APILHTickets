import os
import sys
import site

# Añadir el directorio de la aplicación al path
INTERP = os.path.expanduser("/var/www/virtualenv/ticket_flask_api/3.11/bin/python")
if sys.executable != INTERP:
    os.execl(INTERP, INTERP, *sys.argv)

# Añadir el directorio de la aplicación al path
sys.path.append(os.getcwd())

# Cargar variables de entorno
from dotenv import load_dotenv
load_dotenv()

# Importar la aplicación
from app import app as application

# Configurar el entorno
application.debug = False 