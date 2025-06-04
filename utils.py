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
import logging
from datetime import datetime
from pathlib import Path

# Cargar variables de entorno desde la raíz del proyecto
dotenv_path = Path(__file__).resolve().parent / '.env'
load_dotenv(dotenv_path)

# Configurar logging una sola vez
def setup_logging():
    if logging.getLogger().handlers:
        return

    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'mail.log')

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

# Iniciar logging
setup_logging()

# Cargar variables desde .env
SMTP_USUARIO = os.getenv("SMTP_USUARIO")
SMTP_CLAVE = os.getenv("SMTP_CLAVE")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_DISPLAY_NAME = os.getenv("SMTP_DISPLAY_NAME", "Sistema de Tickets")

# Verificar valores cargados
logging.info("Verificando variables de entorno:")
logging.info(f"SMTP_USUARIO: {SMTP_USUARIO}")
logging.info(f"SMTP_SERVER: {SMTP_SERVER}")
logging.info(f"SMTP_PORT: {SMTP_PORT}")
logging.info(f"SMTP_DISPLAY_NAME: {SMTP_DISPLAY_NAME}")
logging.info(f"SMTP_CLAVE: {'OK' if SMTP_CLAVE else 'FALTA'}")

def enviar_correo(destinatario, asunto, cuerpo):
    try:
        # Verificar que todas las variables necesarias estén presentes
        if not all([SMTP_SERVER, SMTP_PORT, SMTP_USUARIO, SMTP_CLAVE]):
            logging.error("Faltan variables de entorno necesarias para el envío de correo")
            logging.error(f"SMTP_SERVER: {'OK' if SMTP_SERVER else 'FALTA'}")
            logging.error(f"SMTP_PORT: {'OK' if SMTP_PORT else 'FALTA'}")
            logging.error(f"SMTP_USUARIO: {'OK' if SMTP_USUARIO else 'FALTA'}")
            logging.error(f"SMTP_CLAVE: {'OK' if SMTP_CLAVE else 'FALTA'}")
            return False

        logging.info(f"Intentando enviar correo a {destinatario}")
        logging.info(f"Usando servidor: {SMTP_SERVER}:{SMTP_PORT}")
        logging.info(f"Usuario SMTP: {SMTP_USUARIO}")
        logging.info(f"Display Name: {SMTP_DISPLAY_NAME}")

        # Crear mensaje
        msg = MIMEMultipart()
        msg['From'] = f"{SMTP_DISPLAY_NAME} <{SMTP_USUARIO}>"
        msg['To'] = destinatario
        msg['Subject'] = asunto
        msg.attach(MIMEText(cuerpo, 'html'))

        # Conectar al servidor SMTP usando TLS (STARTTLS)
        logging.info("Conectando al servidor SMTP (TLS/STARTTLS)...")
        try:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=60) as server:
                server.set_debuglevel(1)
                server.ehlo()
                server.starttls()
                server.ehlo()
                smtp_clave = SMTP_CLAVE.strip()
                logging.info("Intentando login con usuario y contraseña limpios")
                server.login(SMTP_USUARIO, smtp_clave)
                logging.info("Login exitoso, enviando mensaje...")
                server.send_message(msg)
                logging.info("Mensaje enviado exitosamente")
        except smtplib.SMTPAuthenticationError as e:
            logging.error(f"Error de autenticación: {str(e)}")
            logging.error("Asegúrate de:")
            logging.error("1. El usuario y contraseña sean correctos")
            logging.error("2. La cuenta de correo esté activa en cPanel")
            logging.error("3. No haya restricciones de IP en cPanel")
            logging.error("4. La contraseña no tenga espacios al inicio o final")
            logging.error("5. La contraseña no tenga caracteres especiales")
            return False
        except smtplib.SMTPConnectError as e:
            logging.error(f"Error al conectar con el servidor SMTP: {str(e)}")
            logging.error("Verifica que:")
            logging.error("1. El servidor SMTP sea correcto (in-v3.mailjet.com)")
            logging.error("2. El puerto 587 esté habilitado")
            logging.error("3. El servidor esté accesible")
            logging.error("4. Puedes hacer ping a in-v3.mailjet.com")
            return False
        except TimeoutError as e:
            logging.error(f"Timeout al conectar con el servidor SMTP: {str(e)}")
            logging.error("Verifica que:")
            logging.error("1. El servidor SMTP sea accesible desde tu red")
            logging.error("2. El puerto 587 no esté bloqueado por el firewall")
            logging.error("3. El servidor esté respondiendo")
            logging.error("4. Puedes hacer telnet in-v3.mailjet.com 587")
            return False
        except smtplib.SMTPServerDisconnected as e:
            logging.error(f"El servidor cerró la conexión inesperadamente: {str(e)}")
            logging.error("Esto puede ocurrir por:")
            logging.error("1. El servidor está sobrecargado")
            logging.error("2. La conexión es inestable")
            logging.error("3. El servidor tiene restricciones de seguridad")
            return False
        except Exception as e:
            logging.error(f"Error al enviar correo a {destinatario}: {str(e)}")
            logging.error(f"Tipo de error: {type(e).__name__}")
            if hasattr(e, 'smtp_error'):
                logging.error(f"Error SMTP: {e.smtp_error}")
            import traceback
            logging.error("Traceback completo:")
            logging.error(traceback.format_exc())
            return False
        logging.info(f"Correo enviado exitosamente a {destinatario}")
        return True
    except Exception as e:
        logging.error(f"Error general al enviar correo: {str(e)}")
        import traceback
        logging.error("Traceback completo:")
        logging.error(traceback.format_exc())
        return False

def enviar_correo_async(destinatario, asunto, cuerpo):
    thread = threading.Thread(
        target=enviar_correo,
        args=(destinatario, asunto, cuerpo)
    )
    thread.daemon = True
    thread.start()

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
