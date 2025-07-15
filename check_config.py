#!/usr/bin/env python3
"""
Script simple para verificar la configuración
"""

import os

def check_config():
    print("🔹 Verificando configuración...")
    
    # Cargar variables de entorno
    try:
        import temp_env
        print("✅ Variables de entorno cargadas")
    except Exception as e:
        print(f"❌ Error cargando variables: {e}")
        return False
    
    # Verificar DATABASE_URL
    database_url = os.environ.get('DATABASE_URL')
    print(f"🔹 DATABASE_URL: {database_url}")
    
    if '34.41.120.220' in database_url:
        print("✅ Configurado para Google Cloud SQL")
    else:
        print("⚠️  No está configurado para Google Cloud SQL")
    
    return True

if __name__ == "__main__":
    check_config() 