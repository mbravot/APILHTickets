#!/usr/bin/env python3
import os
from dotenv import load_dotenv

# Cargar variables de entorno al inicio
load_dotenv()

from flask import Flask, request
from config import Config
from models import db
from flask_jwt_extended import JWTManager
from routes import api, auth
from flask_cors import CORS

app = Flask(__name__)

# Configuración base de datos con valor por defecto
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'mysql+pymysql://lahornilla_mbravo:Adm1n2021!+@200.73.20.99:35026/lahornilla_ticket')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Otras configuraciones
app.config.from_object(Config)

# Inicializar DB
db.init_app(app)

# Inicializar JWT
jwt = JWTManager(app)

# Crear carpeta uploads si no existe
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Configuración CORS más permisiva
CORS(app, 
     resources={r"/*": {
         "origins": ["*"],
         "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
         "allow_headers": ["Content-Type", "Authorization", "Access-Control-Allow-Origin"],
         "expose_headers": ["Content-Type", "Authorization"],
         "supports_credentials": True
     }})

# Registrar blueprints
app.register_blueprint(api, url_prefix='/api')
app.register_blueprint(auth, url_prefix='/api/auth')

@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = app.make_default_options_response()
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, Access-Control-Allow-Origin"
        response.headers["Access-Control-Max-Age"] = "3600"
        return response

@app.after_request
def after_request(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, Access-Control-Allow-Origin"
    return response

# Crear tablas al inicio
with app.app_context():
    db.create_all()

# Prueba para la raíz /
@app.route('/')
def home():
    return "✅ API Flask funcionando correctamente"

if __name__ == '__main__':
    # Obtener puerto del entorno o usar 8080 por defecto
    #port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=8080)
