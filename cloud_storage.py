#!/usr/bin/env python3
"""
Módulo para manejar operaciones de Google Cloud Storage
"""
import os
import logging
from google.cloud import storage
from google.auth.exceptions import DefaultCredentialsError
from werkzeug.utils import secure_filename
import uuid
from dotenv import load_dotenv
from pathlib import Path

# Cargar variables de entorno
dotenv_path = Path(__file__).resolve().parent / '.env'
load_dotenv(dotenv_path)

# Configuración de Cloud Storage
BUCKET_NAME = os.getenv('GCS_BUCKET_NAME', 'imagenes-tickets-api')
PROJECT_ID = os.getenv('GCP_PROJECT_ID', 'gestion-la-hornilla')

class CloudStorageManager:
    def __init__(self):
        self.bucket_name = BUCKET_NAME
        self.project_id = PROJECT_ID
        self.client = None
        self.bucket = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Inicializa el cliente de Cloud Storage"""
        try:
            # Intentar usar credenciales por defecto (para Cloud Run)
            self.client = storage.Client(project=self.project_id)
            self.bucket = self.client.bucket(self.bucket_name)
            logging.info(f"Cliente de Cloud Storage inicializado para bucket: {self.bucket_name}")
        except DefaultCredentialsError:
            # Si no hay credenciales por defecto, usar archivo de credenciales
            credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            if credentials_path and os.path.exists(credentials_path):
                try:
                    self.client = storage.Client.from_service_account_json(
                        credentials_path, project=self.project_id
                    )
                    self.bucket = self.client.bucket(self.bucket_name)
                    logging.info(f"Cliente de Cloud Storage inicializado con credenciales desde: {credentials_path}")
                except Exception as e:
                    logging.warning(f"⚠️ No se pudieron usar las credenciales desde {credentials_path}: {str(e)}")
                    logging.warning("⚠️ Cloud Storage no estará disponible. La aplicación funcionará en modo local.")
                    self.client = None
                    self.bucket = None
            else:
                logging.warning("⚠️ No se encontraron credenciales para Google Cloud Storage")
                logging.warning("⚠️ Cloud Storage no estará disponible. La aplicación funcionará en modo local.")
                self.client = None
                self.bucket = None
        except Exception as e:
            logging.warning(f"⚠️ Error al inicializar cliente de Cloud Storage: {str(e)}")
            logging.warning("⚠️ Cloud Storage no estará disponible. La aplicación funcionará en modo local.")
            self.client = None
            self.bucket = None
    
    def upload_file(self, file, ticket_id, filename=None):
        """
        Sube un archivo al bucket de Cloud Storage
        
        Args:
            file: Archivo de Flask (request.files['file'])
            ticket_id: ID del ticket
            filename: Nombre opcional del archivo (si no se proporciona, se genera uno)
        
        Returns:
            dict: {'success': bool, 'filename': str, 'url': str, 'error': str}
        """
        if not self.bucket:
            return {
                'success': False,
                'error': 'Cliente de Cloud Storage no inicializado'
            }
        
        try:
            # Generar nombre único si no se proporciona
            if not filename:
                file_ext = secure_filename(file.filename).rsplit('.', 1)[1].lower()
                filename = f"t{ticket_id}_{uuid.uuid4().hex}.{file_ext}"
            
            # Crear blob en el bucket
            blob = self.bucket.blob(filename)
            
            # Subir el archivo
            blob.upload_from_file(file, content_type=file.content_type)
            
            # Obtener URL pública (sin hacer público individualmente)
            public_url = f"https://storage.googleapis.com/{self.bucket_name}/{filename}"
            
            logging.info(f"Archivo {filename} subido exitosamente a Cloud Storage")
            
            return {
                'success': True,
                'filename': filename,
                'url': public_url,
                'error': None
            }
            
        except Exception as e:
            logging.error(f"❌ Error al subir archivo a Cloud Storage: {str(e)}")
            return {
                'success': False,
                'error': f'Error al subir archivo: {str(e)}'
            }
    
    def delete_file(self, filename):
        """
        Elimina un archivo del bucket de Cloud Storage
        
        Args:
            filename: Nombre del archivo a eliminar
        
        Returns:
            dict: {'success': bool, 'error': str}
        """
        if not self.bucket:
            return {
                'success': False,
                'error': 'Cliente de Cloud Storage no inicializado'
            }
        
        try:
            blob = self.bucket.blob(filename)
            
            # Verificar si el archivo existe
            if not blob.exists():
                return {
                    'success': False,
                    'error': 'Archivo no encontrado en Cloud Storage'
                }
            
            # Eliminar el archivo
            blob.delete()
            
            logging.info(f"Archivo {filename} eliminado exitosamente de Cloud Storage")
            
            return {
                'success': True,
                'error': None
            }
            
        except Exception as e:
            logging.error(f"❌ Error al eliminar archivo de Cloud Storage: {str(e)}")
            return {
                'success': False,
                'error': f'Error al eliminar archivo: {str(e)}'
            }
    
    def get_file_url(self, filename):
        """
        Obtiene la URL pública de un archivo
        
        Args:
            filename: Nombre del archivo
        
        Returns:
            str: URL pública del archivo
        """
        if not self.bucket:
            return None
        
        try:
            blob = self.bucket.blob(filename)
            if blob.exists():
                return f"https://storage.googleapis.com/{self.bucket_name}/{filename}"
            return None
        except Exception as e:
            logging.error(f"❌ Error al obtener URL del archivo {filename}: {str(e)}")
            return None
    
    def file_exists(self, filename):
        """
        Verifica si un archivo existe en el bucket
        
        Args:
            filename: Nombre del archivo
        
        Returns:
            bool: True si el archivo existe, False en caso contrario
        """
        if not self.bucket:
            return False
        
        try:
            blob = self.bucket.blob(filename)
            return blob.exists()
        except Exception as e:
            logging.error(f"❌ Error al verificar existencia del archivo {filename}: {str(e)}")
            return False

# Instancia global del manager
storage_manager = CloudStorageManager() 