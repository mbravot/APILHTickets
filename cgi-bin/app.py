#!/usr/bin/env python3
import sys
import os

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar la aplicación Flask
from app import app

# Configurar el entorno CGI
if __name__ == '__main__':
    from flup.server.fcgi import WSGIServer
    WSGIServer(app).run() 