from flask import Flask, request
from config import Config
from models import db
from flask_jwt_extended import JWTManager
from routes import api, auth
from flask_cors import CORS
import os

app = Flask(__name__)

# Configuración base de datos
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://agrico24_mbravo:Inicio01*@186.64.116.150/agrico24_flutter_ticket'
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

# CORS
CORS(app, resources={r"/api/*": {"origins": "*", "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],"allow_headers": ["Content-Type", "Authorization"]}})

# Registrar blueprints
app.register_blueprint(api, url_prefix='/api')
app.register_blueprint(auth, url_prefix='/api/auth')

# Debug para ver solicitudes
@app.before_request
def handle_options():
    print(f"🔹 Recibida petición: {request.method} {request.path}")
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

# Crear tablas al inicio
with app.app_context():
    db.create_all()

# Prueba para la raíz /
@app.route('/')
def home():
    return "✅ API Flask funcionando correctamente en Azure"

# Ejecutar app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
