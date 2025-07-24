#!/usr/bin/env python3
"""
Script para migrar imágenes existentes de la carpeta uploads a Google Cloud Storage
"""
import os
import sys
from pathlib import Path
from cloud_storage import storage_manager
from google.cloud import storage
from werkzeug.utils import secure_filename

def migrate_files_to_cloud_storage():
    """Migra todos los archivos de la carpeta uploads a Cloud Storage"""
    
    uploads_folder = Path('uploads')
    
    if not uploads_folder.exists():
        print("❌ La carpeta 'uploads' no existe")
        return
    
    files = list(uploads_folder.glob('*'))
    
    if not files:
        print("✅ No hay archivos para migrar en la carpeta 'uploads'")
        return
    
    print(f"📁 Encontrados {len(files)} archivos para migrar")
    
    success_count = 0
    error_count = 0
    
    for file_path in files:
        if file_path.is_file():
            try:
                filename = file_path.name
                print(f"🔄 Migrando: {filename}")
                
                # Verificar si ya existe en Cloud Storage
                if storage_manager.file_exists(filename):
                    print(f"⚠️  El archivo {filename} ya existe en Cloud Storage, saltando...")
                    continue
                
                # Subir archivo a Cloud Storage usando upload_from_filename
                try:
                    blob = storage_manager.bucket.blob(filename)
                    blob.upload_from_filename(str(file_path))
                    
                    print(f"✅ {filename} migrado exitosamente")
                    success_count += 1
                    
                    # Opcional: eliminar archivo local después de migración exitosa
                    # os.remove(file_path)
                    # print(f"🗑️  Archivo local {filename} eliminado")
                    
                except Exception as e:
                    print(f"❌ Error al migrar {filename}: {str(e)}")
                    error_count += 1
                    

                        
            except Exception as e:
                print(f"❌ Error inesperado al migrar {filename}: {str(e)}")
                error_count += 1
    
    print(f"\n📊 Resumen de migración:")
    print(f"✅ Archivos migrados exitosamente: {success_count}")
    print(f"❌ Archivos con error: {error_count}")
    print(f"📁 Total de archivos procesados: {len(files)}")
    
    if success_count > 0:
        print(f"\n💡 Los archivos migrados están ahora disponibles en Cloud Storage")
        print(f"🌐 Bucket: {storage_manager.bucket_name}")
        print(f"🔗 URL base: https://storage.googleapis.com/{storage_manager.bucket_name}/")

def verify_cloud_storage_setup():
    """Verifica que Cloud Storage esté configurado correctamente"""
    print("🔍 Verificando configuración de Cloud Storage...")
    
    if not storage_manager.bucket:
        print("❌ Error: No se pudo inicializar el cliente de Cloud Storage")
        print("💡 Asegúrate de que:")
        print("   1. Las credenciales de Google Cloud estén configuradas")
        print("   2. El bucket 'imagenes-tickets-api' exista")
        print("   3. Las variables de entorno GCS_BUCKET_NAME y GCP_PROJECT_ID estén configuradas")
        return False
    
    try:
        # Verificar que el bucket existe y es accesible
        storage_manager.bucket.reload()
        print(f"✅ Bucket '{storage_manager.bucket_name}' accesible")
        return True
    except Exception as e:
        print(f"❌ Error al acceder al bucket: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Iniciando migración a Google Cloud Storage...")
    
    if not verify_cloud_storage_setup():
        sys.exit(1)
    
    print("\n" + "="*50)
    migrate_files_to_cloud_storage()
    print("="*50)
    print("🎉 Proceso de migración completado") 