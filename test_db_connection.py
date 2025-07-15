#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from cloud_sql_config import CloudSQLConfig

# Cargar variables de entorno
load_dotenv()

def test_database_connection():
    """Prueba la conexión a la base de datos de Google Cloud SQL"""
    try:
        print("🔹 Probando conexión a Google Cloud SQL...")
        print(f"🔹 URI de conexión: {CloudSQLConfig.SQLALCHEMY_DATABASE_URI}")
        
        # Crear engine con la configuración
        engine = create_engine(
            CloudSQLConfig.SQLALCHEMY_DATABASE_URI,
            **CloudSQLConfig.SQLALCHEMY_ENGINE_OPTIONS
        )
        
        # Probar conexión
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("✅ Conexión exitosa a Google Cloud SQL!")
            
            # Probar consulta a una tabla
            try:
                result = connection.execute(text("SHOW TABLES"))
                tables = result.fetchall()
                print(f"✅ Tablas disponibles: {len(tables)}")
                for table in tables[:5]:  # Mostrar solo las primeras 5
                    print(f"   - {table[0]}")
            except Exception as e:
                print(f"⚠️  No se pudieron listar las tablas: {e}")
                
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        print("🔹 Verifica:")
        print("   1. Que la instancia de Cloud SQL esté activa")
        print("   2. Que las credenciales sean correctas")
        print("   3. Que el unix_socket esté configurado correctamente")
        print("   4. Que tengas permisos de acceso a la base de datos")
        return False
    
    return True

if __name__ == "__main__":
    test_database_connection() 