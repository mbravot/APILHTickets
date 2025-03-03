from flask import Flask, request
from config import Config
from models import db
from flask_jwt_extended import JWTManager
from routes import api, auth  # Importa ambos blueprints
from flask_cors import CORS
import os

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
jwt = JWTManager(app)

# Importar archivos al ticket
UPLOAD_FOLDER = 'uploads'  # Carpeta donde se guardarán los archivos
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)  # Crear carpeta si no existe

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Máximo 16MB por archivo

# Configurar CORS para permitir métodos HTTP
CORS(app, resources={r"/api/*": {"origins": "*", "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],"allow_headers": ["Content-Type", "Authorization"]}})

app.register_blueprint(api, url_prefix='/api')
app.register_blueprint(auth, url_prefix='/api/auth')  # Registrar auth

# 🔹 Verificar que Flask recibe las solicitudes
@app.before_request
def handle_options():
    print(f"🔹 Recibida petición: {request.method} {request.path}")  # 🛠️ Debug
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

# Crear tablas si no existen
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)


    # 🔹 Configuración de la base de datos
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://agrico24_mbravo:Inicio01*@186.64.116.150/agrico24_flutter_ticket'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False