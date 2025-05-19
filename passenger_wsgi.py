import sys
import os

# Agregar el directorio actual al path de Python
INTERP = os.path.expanduser("/home/lahornilla/virtualenv/ticket_flask_api/3.13/bin/python")
if sys.executable != INTERP:
    os.execl(INTERP, INTERP, *sys.argv)

sys.path.append(os.getcwd())

# Cargar variables de entorno
from dotenv import load_dotenv
load_dotenv()

# Importar la aplicación
from app import app as application

# Configurar el entorno
application.debug = False 