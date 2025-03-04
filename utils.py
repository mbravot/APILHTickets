from flask import jsonify
from flask_jwt_extended import get_jwt_identity
from functools import wraps
from models import Usuario
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import threading

# Cargar variables de entorno    
load_dotenv()

SMTP_USUARIO = os.getenv("SMTP_USUARIO")
SMTP_CLAVE = os.getenv("SMTP_CLAVE")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))

def enviar_correo(destinatario, asunto, cuerpo):
    mensaje = MIMEMultipart()
    mensaje['From'] = SMTP_USUARIO
    mensaje['To'] = destinatario
    mensaje['Subject'] = asunto
    mensaje.attach(MIMEText(cuerpo, 'html'))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as servidor:
            servidor.starttls()
            servidor.login(SMTP_USUARIO, SMTP_CLAVE)
            servidor.send_message(mensaje)
        print(f"✅ Correo enviado exitosamente a {destinatario}")
    except Exception as e:
        print(f"❌ Error al enviar correo a {destinatario}: {str(e)}")

def enviar_correo_async(destinatario, asunto, cuerpo):
    hilo = threading.Thread(target=enviar_correo, args=(destinatario, asunto, cuerpo))
    hilo.start()

def role_required(required_role):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_user_id = get_jwt_identity()
            user = Usuario.query.get(current_user_id)
            
            if not user or user.rol_obj.rol != required_role:
                return jsonify({'message': 'No tienes permisos para acceder a esta ruta'}), 403
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


#hola