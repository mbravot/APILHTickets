import sys, os

# Agregar el directorio de la aplicación al path
INTERP = os.path.expanduser("/home/lahornilla/public_html/api/ticket/venv/bin/python")
if sys.executable != INTERP:
    os.execl(INTERP, INTERP, *sys.argv)

# Importar la aplicación
from app import app as application 